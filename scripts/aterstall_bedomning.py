#!/usr/bin/env python3
"""Återställ leads vars bedömning skrevs över av en felaktig omkörning.

    python scripts/aterstall_bedomning.py --tenant <id> --sedan "2026-10-11 18:00"           # torrkörning
    python scripts/aterstall_bedomning.py --tenant <id> --sedan "2026-10-11 18:00" --apply   # skriv

Snajps omkörning 2026-10-11 (Tillbaka till Iris + nya utkast) fällde 100 av
100 leads till nivå C, och de doldes: researchuppgiften saknade fältet
produkt och målområdet "Göteborg & Norrland (Umeå)" lästes som ett område.
Varje prospekt som researchats sedan --sedan får tillbaka bedömningen från
sin senaste research FÖRE --sedan, ur stegloggen (agent_runs, steget
grind:bedomning): nivå, poäng, rader, skäl, qualified och icp_fit.
Kontakter rörs inte (kontakttrappan uppgraderar bara). Bara development.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg2  # noqa: E402
import psycopg2.extras  # noqa: E402

from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402

FORRA = """
select distinct on (p.id) p.id, p.company_name, p.niva nu_niva, p.motivering, p.disqualifiers nu_disq,
       a.created_at, a.output, g as grind
  from prospects p
  join agent_runs a on a.prospect_id = p.id and a.agent_type = 'leads_research' and a.created_at < %(sedan)s
  cross join lateral jsonb_array_elements(a.step_log) g
 where p.tenant_id = %(t)s and g->>'step' = 'grind:bedomning'
   and p.id in (select prospect_id from leads_job_ledger
                 where tenant_id = %(t)s and created_at >= %(sedan)s and scope like 'research%%')
 order by p.id, a.created_at desc
"""
BERORDA = """
select count(distinct prospect_id) from leads_job_ledger
 where tenant_id = %(t)s and created_at >= %(sedan)s and scope like 'research%%'
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--sedan", required=True, help="tidpunkt då den felaktiga omkörningen började")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    conn = psycopg2.connect(dsn(env_read(), "development"), connect_timeout=20)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    arg = {"t": a.tenant, "sedan": a.sedan}
    cur.execute(BERORDA, arg)
    berorda = cur.fetchone()["count"]
    cur.execute(FORRA, arg)
    rader = cur.fetchall()
    print(f"{berorda} omkörda prospekt, {len(rader)} med en tidigare bedömning")
    for r in rader:
        g = r["grind"]
        try:
            icp_fit = float(json.loads(r["output"] or "{}").get("icp_fit"))
        except (TypeError, ValueError, AttributeError):
            icp_fit = None
        motivering = r["motivering"] or ""
        # Omkörningen satte "Bortvald: <skäl>. " framför modellens text.
        prefix = f"Bortvald: {(r['nu_disq'] or [''])[0]}. "
        if g.get("niva") in ("A", "B") and motivering.startswith(prefix):
            motivering = motivering[len(prefix):]
        print(f"  {r['company_name'][:40]:40} {r['nu_niva']} -> {g.get('niva')}  poäng {g.get('score_total')}")
        if a.apply:
            cur.execute(
                """update prospects set niva = %s, qualified = %s, score_total = %s, disqualifiers = %s,
                          score_breakdown = %s::jsonb, icp_fit = coalesce(%s, icp_fit), motivering = %s
                    where tenant_id = %s and id = %s""",
                (g.get("niva"), bool(g.get("qualified")), g.get("score_total"), g.get("disqualifiers") or [],
                 json.dumps(g.get("rader") or [], ensure_ascii=False), icp_fit, motivering, a.tenant, r["id"]),
            )
    if a.apply:
        conn.commit()
        print(f"Återställde {len(rader)} prospekt.")
    else:
        print("Torrkörning: inget skrevs. Kör med --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
