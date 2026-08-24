"""Periodrapporten — EN uträkning, två anropare.

Låg tidigare som `_period()` i `app/api/bookkeeping.py`. Den flyttade hit när
chatten tillkom, och det är inte städning: chattens verktyg måste svara med
SAMMA siffror som `/api/bookkeeping/period`, annars kan kunden få två olika tal
för samma period beroende på om de klickade eller frågade.

Att kopiera funktionen in i verktyget hade varit den snabba vägen och exakt
det misstag `moms_fran_brutto` redan förhindrar en gång: en andra uträkning som
ser likadan ut och glider isär vid första avrundningen.

## Ordningen är hela poängen

Underlag, verifikat, grind, SEDAN summor. Summorna räknas ALDRIG före grinden.
Att visa trovärdiga tal för en period som inte går ihop är värre än att visa
inga alls — se STATUS.md 2026-08-16, där adminvyn gav fyra kunder med
nollställda men rimliga siffror.
"""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal
from typing import Any

from ..notifications.internlarm import larma
from .math import (
    Konteringsrad,
    Post,
    moms_fran_brutto,
    netto_fran_brutto,
    summera_period,
)
from .verifieringsgrind import STATUS_GRANSKA, check_period


def kr(varde: Decimal | None) -> str | None:
    """Belopp som STRÄNG i JSON-svaret.

    Ett JSON-tal blir en float hos varje mottagare — webbläsaren räknar
    `0.1 + 0.2` till `0.30000000000000004` precis som Python gör. Hela modulens
    premiss är att belopp inte får bli float, och den premissen slutar inte
    gälla för att värdet passerat ett nätverk.
    """
    return None if varde is None else f"{varde:f}"


async def berakna_period(
    storage: Any, tenant_id: str, fran: date, till: date
) -> dict[str, Any]:
    underlag = await storage.list_bk_underlag(tenant_id, fran=fran, till=till)
    verifikat = await storage.list_bk_verifikat(tenant_id, fran=fran, till=till)

    rader_per_verifikat = [
        [
            Konteringsrad(
                konto=r["konto"],
                debet=r["debet"],
                kredit=r["kredit"],
                text=r.get("text", ""),
            )
            for r in v["rader"]
        ]
        for v in verifikat
    ]
    verdikt = check_period(underlag=underlag, verifikat=rader_per_verifikat)

    # Summorna räknas bara på underlag som faktiskt har fälten. Ett fällt
    # underlag bidrar inte med ett gissat belopp — det står i brist-listan.
    #
    # Momsen räknas av `moms_fran_brutto`, inte här. En andra uträkning på den
    # här sidan hade varit en kopia som glider isär från den grinden och
    # verifikaten använder — och avrundningen hade dessutom saknats, så
    # periodsumman kunde avvika från verifikatens med några ören utan att
    # någonting sa ifrån.
    poster = []
    for u in underlag:
        if not (
            u.get("datum")
            and u.get("riktning")
            and u.get("brutto") is not None
            and u.get("momssats") is not None
        ):
            continue
        poster.append(
            Post(
                datum=date.fromisoformat(u["datum"]),
                riktning=u["riktning"],
                netto=netto_fran_brutto(u["brutto"], u["momssats"]),
                moms=moms_fran_brutto(u["brutto"], u["momssats"]),
                motpart=u.get("motpart") or "",
                underlag_id=u["id"],
            )
        )
    summor = summera_period(poster)

    # Larmet ligger HÄR och inte i `verifieringsgrind.check_period`. Grinden är
    # en ren funktion — den tar dictar och rader och returnerar ett verdikt, gör
    # ingen I/O och vet inte vilken tenant den räknar på. Att lägga ett
    # mejlutskick där hade gjort den omöjlig att anropa från ett test utan att
    # tänka på nätverk, och den anropas från fyra ställen.
    #
    # `berakna_period` är dessutom den ENDA anroparen av check_period, så det
    # här är inte en av flera vägar förbi larmet — det är vägen.
    if verdikt.status == STATUS_GRANSKA:
        # Nyckeln bär periodens brister, inte bara perioden. Rapporten hämtas
        # varje gång någon öppnar vyn eller frågar chatten, och utan bristerna
        # i nyckeln hade EN oförändrad trasig period larmat om och om igen.
        # Ändras bristerna är det däremot en NY sak att titta på.
        brister = verdikt.as_report()
        await larma(
            f"Bokföringsperiod kräver granskning ({fran.isoformat()}–{till.isoformat()})",
            tenant_id=tenant_id,
            vad=(
                f"Perioden {fran.isoformat()}–{till.isoformat()} går inte ihop: "
                f"{len(brister)} brist(er) över {len(underlag)} underlag."
            ),
            varfor="; ".join(brister[:5]) + (" …" if len(brister) > 5 else ""),
            # sha256 och inte hash(): den inbyggda hashen saltas per process
            # (PYTHONHASHSEED), så nyckeln hade sett olika ut i varje replik
            # och i varje omstart — och en dubblettspärr med en instabil nyckel
            # är ingen dubblettspärr.
            nyckel=(
                f"bokforing-period:{tenant_id}:{fran}:{till}:"
                + hashlib.sha256("\n".join(brister).encode()).hexdigest()[:16]
            ),
        )

    return {
        "fran": fran.isoformat(),
        "till": till.isoformat(),
        "status": verdikt.status,
        "brister": verdikt.as_report(),
        "summor": {
            "intakter": kr(summor.intakter),
            "kostnader": kr(summor.kostnader),
            "utgaende_moms": kr(summor.utgaende_moms),
            "ingaende_moms": kr(summor.ingaende_moms),
            "resultat_fore_skatt": kr(summor.resultat_fore_skatt),
            "moms_att_betala": kr(summor.moms_att_betala),
            "antal_poster": summor.antal_poster,
        },
        "antal_underlag": len(underlag),
        "antal_verifikat": len(verifikat),
        "_verifikat": verifikat,
    }
