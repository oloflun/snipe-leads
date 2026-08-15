"""Målgruppsstyrning (ICP) — vem agenten får kontakta.

Gränsen mot SOUL hålls hård och skrivs ut i UI:t: **SOUL styr ton, ICP styr
urval.** Två fält, två syften. Att blanda dem hade betytt att en kund som
vill ändra vilka bolag agenten letar efter i stället skriver om hur den låter.

ICP är STRUKTURERAD data. Den går aldrig in som fri text i en prompt utan
wrappas som allt annat kundskrivet (`wrap_untrusted_content`, INV-SEC-009) —
fälten är kundskrivna och en `must_have`-rad är en lika bra injektionsyta som
en SOUL-rad.
"""

from __future__ import annotations

from typing import Any

from .untrusted_content import wrap_untrusted_content

#: Fälten och deras form. En okänd nyckel tas bort i stället för att kastas
#: vidare — annars blir varje stavfel i frontend en tyst prompt-injektion.
LIST_FIELDS = (
    "industries",
    "exclude_industries",
    "geography",
    "roles",
    "must_have",
    "deal_breakers",
)

MAX_ITEMS_PER_FIELD = 25
MAX_CHARS_PER_ITEM = 200


def empty_icp() -> dict[str, Any]:
    return {field: [] for field in LIST_FIELDS} | {"company_size": {"min": None, "max": None}}


def normalize_icp(raw: object) -> dict[str, Any]:
    """Rensar inkommande ICP till exakt de fält vi känner till.

    Tar bort okända nycklar, kapar listor och strängar. Kapningen är inte
    kosmetik: fälten går in i kontextpaketet, och ett fält utan tak är ett
    sätt att fylla hela kontextfönstret med kundskriven text och tränga ut
    våra egna instruktioner.
    """
    icp = empty_icp()
    if not isinstance(raw, dict):
        return icp

    for field in LIST_FIELDS:
        values = raw.get(field)
        if not isinstance(values, list):
            continue
        icp[field] = [
            str(value).strip()[:MAX_CHARS_PER_ITEM]
            for value in values[:MAX_ITEMS_PER_FIELD]
            if str(value).strip()
        ]

    size = raw.get("company_size")
    if isinstance(size, dict):
        icp["company_size"] = {
            "min": _as_positive_int(size.get("min")),
            "max": _as_positive_int(size.get("max")),
        }

    return icp


def _as_positive_int(value: object) -> int | None:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def is_empty(icp: dict[str, Any]) -> bool:
    if any(icp.get(field) for field in LIST_FIELDS):
        return False
    size = icp.get("company_size") or {}
    return size.get("min") is None and size.get("max") is None


def render_icp(raw: object) -> str:
    """ICP som ett eget avsnitt i kontextpaketet.

    Placeras ÖVER produktbeskrivningen: urvalskriterierna avgör om ett
    prospekt ska bearbetas alls, och den frågan kommer före hur erbjudandet
    formuleras.

    Tom ICP ger tom sträng, inte ett avsnitt som säger "inga kriterier". Ett
    tomt avsnitt läser modellen som en instruktion att inte filtrera, vilket
    är en annan sak än att kriterier saknas.
    """
    icp = normalize_icp(raw)
    if is_empty(icp):
        return ""

    lines: list[str] = []
    labels = {
        "industries": "Branscher att fokusera på",
        "exclude_industries": "Branscher att undvika",
        "geography": "Geografi",
        "roles": "Beslutsfattarroller",
        "must_have": "Signaler som krävs",
        "deal_breakers": "Diskvalificerande",
    }
    for field in LIST_FIELDS:
        values = icp[field]
        if values:
            lines.append(f"- {labels[field]}: {', '.join(values)}")

    size = icp["company_size"]
    if size["min"] is not None or size["max"] is not None:
        low = size["min"] if size["min"] is not None else "—"
        high = size["max"] if size["max"] is not None else "—"
        lines.append(f"- Bolagsstorlek (anställda): {low}–{high}")

    body = "\n".join(lines)

    # Kundskrivet innehåll, alltså wrappat. Samma behandling som SOUL får:
    # texten är data att ta hänsyn till, aldrig instruktioner att lyda.
    return (
        "## MÅLGRUPP (ICP)\n"
        "Urvalskriterier som kunden satt. Diskvalificera mot dessa INNAN du "
        "räknar icp_fit.\n\n" + wrap_untrusted_content(body, source="kundens ICP-konfiguration")
    )
