#!/usr/bin/env python3
"""Granska en kunds väntande leads-utkast mot stilgrinden, utanför appen.

    python scripts/granska_utkast.py --slug snajp              # tabell
    python scripts/granska_utkast.py --slug snajp --visa 5     # plus de fem första texterna
    python scripts/granska_utkast.py --slug snajp --json ut.json

Läser utkasten i granskningskön (awaiting_review) och de godkända som väntar
på sändfönstret (queued) i development, och kör app/leads/stilkontroll.py på
var och en: markörerna, erbjudandets siffror och produkt (ur trådens
tilldelade erbjudande och kundens villkor) och batchkontrollen mot de andra.
Skriver ingenting. Samma kod som kedjan kör, så ett utkast som passerar här
passerar där.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "scripts"))
sys.path.insert(0, str(ROT / "snajp-support"))

import psycopg2  # noqa: E402
import psycopg2.extras  # noqa: E402

from railway_migrate import dsn  # noqa: E402
from railway_provision import env_read  # noqa: E402

from app.leads import erbjudanden, stilkontroll as stil  # noqa: E402

SQL = """
select q.id queue_id, q.status, q.created_at, p.company_name, p.contact_name, p.contact_email,
       m.subject, m.body, o.name erbjudande
  from send_queue q
  join outreach_threads t on t.id = q.thread_id
  left join prospects p on p.id = t.prospect_id
  left join offers o on o.id = t.offer_id
  left join lateral (
    select subject, body from outreach_messages om
     where om.thread_id = q.thread_id and om.direction = 'outbound'
       and om.sent_at is null and om.kasserad_at is null
     order by om.created_at desc, om.id desc limit 1
  ) m on true
 where q.tenant_id = %(t)s and q.status in ('awaiting_review', 'queued')
 order by p.company_name
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--visa", type=int, default=0, help="skriv ut de N första texterna")
    ap.add_argument("--json", help="spara fynden per utkast som JSON")
    ap.add_argument("--bara-fynd", action="store_true", help="lista bara utkast med fynd")
    a = ap.parse_args()

    conn = psycopg2.connect(dsn(env_read(), "development"), connect_timeout=20)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("select id from ss_tenants where slug = %s", (a.slug,))
    tenant = cur.fetchone()
    if not tenant:
        sys.exit(f"Kunden {a.slug} finns inte.")
    t = str(tenant["id"])
    cur.execute("select settings from agent_configs where tenant_id = %s and agent_type = 'leads'", (t,))
    rad = cur.fetchone()
    installningar = rad["settings"] if rad else {}
    if isinstance(installningar, str):
        installningar = json.loads(installningar)
    villkor_alla = erbjudanden.normalisera((installningar or {}).get("erbjudanden")).get("villkor") or {}
    produkter = [str(p.get("namn") or "") for p in (installningar or {}).get("produkter") or []]

    cur.execute(SQL, {"t": t})
    rader = cur.fetchall()
    texter = [str(r["body"] or "") for r in rader]
    ut = []
    raknare: Counter[str] = Counter()
    for i, r in enumerate(rader):
        body = texter[i]
        brod = body.casefold()
        # Produkten mejlet handlar om: den av kundens produkter som nämns.
        produkt = next((p for p in produkter if p.split(",")[0].strip().casefold() in brod), None)
        villkor = erbjudanden.villkor_for(villkor_alla.get(r["erbjudande"] or ""), produkt) if r["erbjudande"] else ""
        # Brödtexten utan kodens signatur och fot: det är den kedjan prövade.
        fynd = stil.kontrollera(stil._brodtext(body)).anmarkningar
        if r["erbjudande"]:
            fynd += stil.erbjudande_fynd(body, villkor=villkor, produkt=produkt or (produkter[0] if produkter else None))
        fynd += stil.mot_andra(body, [*texter[:i], *texter[i + 1 :]])
        koder = [f.kod for f in fynd]
        raknare.update(koder)
        ut.append({
            "queue_id": str(r["queue_id"]), "status": r["status"], "bolag": r["company_name"],
            "kontakt": r["contact_name"], "erbjudande": r["erbjudande"], "produkt": produkt,
            "amne": r["subject"], "ingang": stil.ingang(body), "ord": sum(len(m.split()) for m in stil._meningar(stil._brodtext(body))),
            "fynd": [f.beskrivning for f in fynd], "koder": koder,
        })

    print(f"{len(ut)} utkast hos {a.slug}, {sum(1 for u in ut if not u['koder'])} utan fynd")
    print("fynd per kod:", dict(raknare.most_common()))
    print()
    for u in ut:
        if a.bara_fynd and not u["koder"]:
            continue
        print(f"- {u['bolag'][:38]:38} {u['status']:16} {u['erbjudande'] or '-':12} {u['ord']:>3} ord | {u['ingang'][:70]}")
        for f in u["fynd"]:
            print(f"      ! {f}")
    for u, r in list(zip(ut, rader))[: a.visa]:
        print("\n" + "=" * 78 + f"\n{u['bolag']} | {r['subject']}\n" + "-" * 78 + f"\n{r['body']}")
    if a.json:
        Path(a.json).write_text(json.dumps(ut, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
