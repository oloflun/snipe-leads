"""Testkund → riktig kund: kopiera KONFIGURATION, inte historik.

CLI: scripts/konvertera_testkund.py. HTTP: POST /api/admin/konvertera.
Samma spärrar och samma tabeller på båda vägarna — två kopior av SQL:en
hade blivit två tillfällen att skriva den olika.
"""

from __future__ import annotations

import copy
import uuid
from typing import Any

from ..leads.befordran import saknade_falt
from ..storage.base import Storage
from ..storage.memory import MemoryStorage

TABELLER: list[tuple[str, tuple[str, ...]]] = [
    ("ss_knowledge_base", ("title", "content", "category", "embedding")),
    ("ss_category_rules", ("category", "mode")),
    ("agent_configs", ("agent_type", "settings", "instructions_md", "tone", "taxonomy")),
    ("agent_context_docs", ("kind", "content", "source", "version")),
]

PROSPEKT_KOLUMNER: tuple[str, ...] = (
    "company_name",
    "contact_name",
    "contact_email",
    "language_state",
    "status",
    "icp_fit",
    "qualified",
    "disqualifiers",
    "orgnr",
    "ort",
    "postnr",
    "sni",
    "website",
    "anstallda",
    "omsattning",
    "score_breakdown",
    "score_total",
)


def kontrollera_riktning(fran: str, till: str) -> str | None:
    """None = ok. Annars svensk avvisning, samma text som CLI:t."""
    if fran == till:
        return "Källa och mål är samma tenant."
    if not fran.startswith("testkund-"):
        return f"Källan {fran!r} är inte en testtenant. Riktningen är envägs."
    if till.startswith("testkund-"):
        return f"Målet {till!r} är en testtenant. Riktningen är envägs."
    return None


async def _tenant_med_slug(storage: Storage, slug: str) -> dict[str, Any] | None:
    for rad in await storage.list_tenants():
        if rad.get("slug") == slug:
            return rad
    return None


async def sammanfatta(storage: Storage, fran_id: str, till_id: str) -> dict[str, Any]:
    kb_fran = await storage.list_kb(fran_id)
    kb_till = await storage.list_kb(till_id)
    docs_fran = await storage.list_context_docs(fran_id)
    docs_till = await storage.list_context_docs(till_id)
    regler_fran = await storage.get_category_rules(fran_id)
    regler_till = await storage.get_category_rules(till_id)
    return {
        "kunskapsbas": {"fran": len(kb_fran), "till": len(kb_till)},
        "rostdokument": {"fran": len(docs_fran), "till": len(docs_till)},
        "fackregler": {"fran": len(regler_fran), "till": len(regler_till)},
    }


async def kora(
    storage: Storage,
    *,
    fran: str,
    till: str,
    apply: bool = False,
    prospect_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Torrkör (apply=False) eller skriv. Returnerar en rapport, kastar inte
    för affärsfel — anroparen översätter till HTTP."""
    fel = kontrollera_riktning(fran, till)
    if fel:
        return {"ok": False, "fel": fel}

    kalla = await _tenant_med_slug(storage, fran)
    mal = await _tenant_med_slug(storage, till)
    if not kalla:
        return {"ok": False, "fel": f"Ingen tenant med slug {fran!r}."}
    if not mal:
        return {"ok": False, "fel": f"Ingen tenant med slug {till!r}."}

    fran_id, till_id = kalla["id"], mal["id"]
    rapport = await sammanfatta(storage, fran_id, till_id)
    rapport.update(
        {
            "ok": True,
            "apply": apply,
            "fran": {"slug": fran, "id": fran_id, "name": kalla.get("name")},
            "till": {"slug": till, "id": till_id, "name": mal.get("name")},
            "prospekt": [],
        }
    )

    ider = prospect_ids or []
    if ider:
        rapport["prospekt"] = await _prospektplan(storage, fran_id, till_id, ider)

    if not apply:
        rapport["meddelande"] = (
            "Torrkörning. Inget skrevs. Bekräfta för att skriva över målets "
            "kunskapsbas, regler, agentinställningar och röstdokument."
        )
        return rapport

    pool = getattr(storage, "pool", None)
    if pool is not None:
        await _verkstall_postgres(storage, fran_id, till_id, ider)
    elif isinstance(storage, MemoryStorage):
        await _verkstall_minne(storage, fran_id, till_id, ider)
    else:
        return {
            "ok": False,
            "fel": "Konvertering kan inte skriva mot den här lagringsytan.",
        }

    rapport["meddelande"] = (
        "Klart. Målets konfiguration är nu identisk med testytans. "
        "Ärenden, mail och körningar kopierades inte."
    )
    return rapport


async def _prospektplan(
    storage: Storage, fran_id: str, till_id: str, ider: list[str]
) -> list[dict[str, Any]]:
    fran_lista = {p["id"]: p for p in await storage.list_prospects(fran_id, limit=500)}
    mal_nycklar = {
        p.get("foretagsnyckel")
        for p in await storage.list_prospects(till_id, limit=500)
        if p.get("foretagsnyckel")
    }
    plan: list[dict[str, Any]] = []
    for pid in ider:
        rad = fran_lista.get(pid)
        if not rad:
            plan.append({"id": pid, "atgard": "saknas", "namn": None})
            continue
        krock = bool(rad.get("foretagsnyckel") and rad.get("foretagsnyckel") in mal_nycklar)
        if krock:
            atgard, detalj = "krock", []
        elif rad.get("origin") == "example":
            brister = saknade_falt(
                orgnr=rad.get("orgnr"),
                website=rad.get("website"),
                contact_email=rad.get("contact_email"),
            )
            atgard, detalj = ("valideringsfel", brister) if brister else ("kopiera", [])
        else:
            atgard, detalj = "kopiera", []
        plan.append(
            {
                "id": pid,
                "namn": rad.get("company_name"),
                "atgard": atgard,
                "detalj": detalj,
            }
        )
    return plan


async def _verkstall_minne(
    storage: MemoryStorage, fran_id: str, till_id: str, ider: list[str]
) -> None:
    storage.kb[till_id] = [
        {**copy.deepcopy(rad), "id": str(uuid.uuid4()), "tenant_id": till_id}
        for rad in storage.kb.get(fran_id, [])
    ]
    storage.context_docs[till_id] = [
        {**copy.deepcopy(rad), "id": str(uuid.uuid4()), "tenant_id": till_id}
        for rad in storage.context_docs.get(fran_id, [])
    ]
    for (tid, kategori), lage in list(storage.category_rules.items()):
        if tid == till_id:
            del storage.category_rules[(tid, kategori)]
    for (tid, kategori), lage in list(storage.category_rules.items()):
        if tid == fran_id:
            storage.category_rules[(till_id, kategori)] = lage
    for nyckel in list(storage.agent_settings):
        if nyckel[0] == till_id:
            del storage.agent_settings[nyckel]
    for (tid, typ), varden in list(storage.agent_settings.items()):
        if tid == fran_id:
            storage.agent_settings[(till_id, typ)] = copy.deepcopy(varden)
    for nyckel in list(storage.agent_instructions):
        if nyckel[0] == till_id:
            del storage.agent_instructions[nyckel]
    for (tid, typ), varden in list(storage.agent_instructions.items()):
        if tid == fran_id:
            storage.agent_instructions[(till_id, typ)] = copy.deepcopy(varden)

    if not ider:
        return
    fran = {p["id"]: p for p in storage.prospects.get(fran_id, [])}
    mal_nycklar = {
        p.get("foretagsnyckel")
        for p in storage.prospects.get(till_id, [])
        if p.get("foretagsnyckel")
    }
    for pid in ider:
        rad = fran.get(pid)
        if not rad:
            continue
        if rad.get("foretagsnyckel") and rad.get("foretagsnyckel") in mal_nycklar:
            continue
        if rad.get("origin") == "example" and saknade_falt(
            orgnr=rad.get("orgnr"),
            website=rad.get("website"),
            contact_email=rad.get("contact_email"),
        ):
            continue
        kopia = await storage.create_prospect(
            till_id,
            company_name=rad["company_name"],
            contact_name=rad.get("contact_name"),
            contact_email=rad.get("contact_email"),
            origin="manual",
            profil={
                k: rad[k]
                for k in ("orgnr", "website", "ort", "sni")
                if rad.get(k) is not None
            },
        )
        mal_nycklar.add(kopia.get("foretagsnyckel"))


async def _verkstall_postgres(
    storage: Storage, fran_id: str, till_id: str, ider: list[str]
) -> None:
    pool = storage.pool
    async with pool.acquire() as conn:
        async with conn.transaction():
            for tabell, kolumner in TABELLER:
                kol = ", ".join(kolumner)
                await conn.execute(
                    f"delete from public.{tabell} where tenant_id = $1", till_id
                )
                await conn.execute(
                    f"""insert into public.{tabell} (tenant_id, {kol})
                        select $1, {kol} from public.{tabell} where tenant_id = $2""",
                    till_id,
                    fran_id,
                )
            if not ider:
                return
            rader = await conn.fetch(
                f"""select id, origin, foretagsnyckel, {", ".join(PROSPEKT_KOLUMNER)}
                      from public.prospects
                     where tenant_id = $1 and id = any($2::uuid[])""",
                fran_id,
                ider,
            )
            for rad in rader:
                data = dict(rad)
                if data.get("foretagsnyckel"):
                    krock = await conn.fetchval(
                        "select 1 from public.prospects where tenant_id = $1 and foretagsnyckel = $2",
                        till_id,
                        data["foretagsnyckel"],
                    )
                    if krock:
                        continue
                if data.get("origin") == "example" and saknade_falt(
                    orgnr=data.get("orgnr"),
                    website=data.get("website"),
                    contact_email=data.get("contact_email"),
                ):
                    continue
                kol = ", ".join(PROSPEKT_KOLUMNER)
                platser = ", ".join(f"${i}" for i in range(2, len(PROSPEKT_KOLUMNER) + 2))
                varden = [data[k] for k in PROSPEKT_KOLUMNER]
                ny = await conn.fetchval(
                    f"""insert into public.prospects (tenant_id, origin, {kol})
                        values ($1, 'manual', {platser}) returning id""",
                    till_id,
                    *varden,
                )
                await conn.execute(
                    """insert into public.prospect_sources
                         (tenant_id, prospect_id, source_url, source_type, lawful_basis, retrieved_at)
                       select $1, $2, source_url, source_type, lawful_basis, retrieved_at
                         from public.prospect_sources
                        where tenant_id = $3 and prospect_id = $4""",
                    till_id,
                    ny,
                    fran_id,
                    data["id"],
                )
