"""Kodgrinden efter ICP-kvalificeringen: storlek och bemanningsbolag.

Uppmätt 2026-09-15 som QA-kunden Nordform (målgrupp: IT-konsulter,
redovisningsbyråer, arkitektkontor, reklambyråer, 10–49 anställda):
researchen godkände Andara Group med icp_fit 0,70 fast utkastet själv kallade
bolaget "rekryterings- och bemanningsföretag", och storleken bedömdes olika
från bolag till bolag - Eccera fälldes för ">49", Filed för "okänt antal".

Grinden kan bara SKÄRPA modellens bedömning (fälla ett bolag), aldrig
godkänna ett som modellen underkänt. Den läser två fält researchen
returnerar - `antal_anstallda` (bara med belägg i källmaterialet) och
`ar_bemanningsforetag` - plus bolagsnamnet, och mäter dem mot kundens ICP.
Okänd storlek fäller ingenting: de flesta småbolag skriver aldrig ut sitt
antal anställda, och att fälla dem för det tömmer målgruppen.
"""

from __future__ import annotations

from typing import Any

from .sources.jobtech import ar_formedlare

#: Ord i kundens målgrupp som betyder att bemanningsbolag ÄR målgruppen -
#: en kund som säljer till rekryteringsföretag ska inte få dem bortfällda.
_BEMANNING_I_MALGRUPPEN = ("bemanning", "rekryter", "staffing", "recruit", "konsultförmedl")

#: icp_fit för ett bolag grinden fäller. Taket, inte noll: modellens övriga
#: bedömning kan vara riktig, men bolaget ska aldrig sorteras över ett som
#: faktiskt kvalificerar.
TAK_ICP_FIT = 0.3


def _heltal(varde: Any) -> int | None:
    if isinstance(varde, bool):
        return None
    try:
        tal = int(varde)
    except (TypeError, ValueError):
        return None
    return tal if tal >= 0 else None


def _storleksintervall(icp: dict[str, Any]) -> tuple[int | None, int | None]:
    size = icp.get("size") or {}
    lag, hog = _heltal(size.get("anstallda_min")), _heltal(size.get("anstallda_max"))
    if lag is None and hog is None:
        gammal = icp.get("company_size") or {}
        lag, hog = _heltal(gammal.get("min")), _heltal(gammal.get("max"))
    return lag, hog


def bemanning_ar_malgruppen(icp: dict[str, Any]) -> bool:
    text = " ".join(
        str(v) for falt in ("industries", "must_have") for v in (icp.get(falt) or [])
    ).casefold()
    return any(ord in text for ord in _BEMANNING_I_MALGRUPPEN)


def skarp_kvalificering(
    fynd: dict[str, Any], icp: dict[str, Any] | None, *, company_name: str
) -> dict[str, Any]:
    """Returnerar en kopia av researchfynden med grindens skäl inlagda."""
    icp = icp or {}
    ut = dict(fynd)
    skal: list[str] = []

    if not bemanning_ar_malgruppen(icp) and (
        ut.get("ar_bemanningsforetag") is True or ar_formedlare(company_name or "")
    ):
        skal.append(
            "Bemannings- eller rekryteringsföretag: deras rekryteringar gäller "
            "kundernas behov, inte den egna verksamheten."
        )

    antal = _heltal(ut.get("antal_anstallda"))
    lag, hog = _storleksintervall(icp)
    if antal is not None:
        if hog is not None and antal > hog:
            skal.append(f"Storlek: {antal} anställda enligt källmaterialet, målgruppen är högst {hog}.")
        elif lag is not None and antal < lag:
            skal.append(f"Storlek: {antal} anställda enligt källmaterialet, målgruppen är minst {lag}.")

    if not skal:
        return ut

    befintliga = [str(d) for d in (ut.get("disqualifiers") or [])]
    ut["disqualifiers"] = befintliga + [s for s in skal if s not in befintliga]
    ut["qualified"] = False
    try:
        fit = float(ut.get("icp_fit"))
    except (TypeError, ValueError):
        fit = None
    ut["icp_fit"] = TAK_ICP_FIT if fit is None else min(fit, TAK_ICP_FIT)
    return ut
