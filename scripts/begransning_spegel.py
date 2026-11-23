"""Begränsningarna av behandlingen (art. 18, migration 124) i development-spegeln.

Development är en spegel av produktionen och gallrar själv det synken inte för
över (migration 133). Spegelns gallring skyddar bara de adresser som har en
aktiv begränsning i SPEGELNS egen tabell, så en markering som bara står i main
skyddar ingenting där (Codex runda 15, 2026-11-20). Två vägar för över den:

* `scripts/gdpr_radera.py` skriver samma rad i båda miljöerna i samma körning;
* `scripts/railway_synk.py` för över alla rader var tionde minut, så att en
  skrivning som föll tas igen, och stämplar `mirror_meta.begransningar_synkade_at`.

Spegelns gallring kör inte skarpt utan en stämpel från de senaste två timmarna
(migration 147). Så kan en markering som saknas i spegeln aldrig gallras bort.

Raden skrivs med main:s id och tider. Finns redan en annan aktiv rad för samma
adress i spegeln (satt direkt mot development) står den kvar: den skyddar lika
mycket, och det unika indexet tillåter bara en aktiv rad per adress.
"""
from __future__ import annotations

import json

KOLUMNER = ("id", "email", "skal", "begard_at", "havd_at", "havd_skal", "created_at")

LAS_SQL = (
    "select to_jsonb(b) from public.behandlingsbegransningar b"
)


def spegla_rad(cur, rad: dict) -> str:
    """Skriv en rad från main i spegeln. Svarar 'uppdaterad', 'infogad' eller
    'krock' (en annan aktiv rad för adressen finns redan och står kvar).

    Idempotent: samma rad två gånger ger 'uppdaterad' utan ändring."""
    cur.execute(
        "update public.behandlingsbegransningar "
        "set email = %s, skal = %s, begard_at = %s::timestamptz, havd_at = %s::timestamptz, "
        "    havd_skal = %s, created_at = %s::timestamptz "
        "where id = %s::uuid",
        (rad["email"], rad["skal"], rad["begard_at"], rad.get("havd_at"), rad.get("havd_skal"),
         rad["created_at"], rad["id"]),
    )
    if cur.rowcount:
        return "uppdaterad"
    cur.execute(
        "insert into public.behandlingsbegransningar "
        "select * from jsonb_populate_record(null::public.behandlingsbegransningar, %s::jsonb) "
        "on conflict do nothing",
        (json.dumps({k: rad.get(k) for k in KOLUMNER}, default=str),),
    )
    return "infogad" if cur.rowcount else "krock"


def stampla(cur) -> None:
    """Stämpeln spegelns gallring kräver (147). Bara i en databas med mirror_meta."""
    cur.execute("select to_regclass('public.mirror_meta') is not null")
    if not cur.fetchone()[0]:
        return
    cur.execute(
        "alter table public.mirror_meta add column if not exists begransningar_synkade_at timestamptz"
    )
    cur.execute("update public.mirror_meta set begransningar_synkade_at = now()")
