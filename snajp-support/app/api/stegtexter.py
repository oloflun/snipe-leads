"""Agentsvar till kunden bär inte stegloggarnas texter (fas 2, 2026-11-10).

Stegloggen i utförligt läge (step_runner.RunTrace.as_log / as_full) bär för
varje steg agentens användarmeddelande (verksamhetskontext, SOUL, kundminne,
kunskapsbasens artiklar, bolagsfakta med webbplatsbedömningen), modellens råa
utdata och dess resonemang. Den hör hemma i agent_runs, där plattformsadmin
läser den bakom masternyckeln.

Den följde ändå med ut på tre vägar: jobbsvaret (`GET /api/jobs/{id}`, som den
anonyma chattwidgeten pollar, så varje besökare kunde läsa kundens interna
instruktioner i webbläsarens nätverksflik), researchstegets direkta svar och
prospektsvarets. `utan_stegtexter` tar bort texterna och lämnar mätvärdena
(steg, försök, tid, tokens, lager) kvar.
"""

from __future__ import annotations

from typing import Any

#: Stegloggens textfält. `output` finns bara i as_full (`step_outputs`).
_STEGTEXTER = frozenset({"user_message", "raw_output", "reasoning_content", "system_prompt", "output"})
#: Nycklarna en steglogg ligger under i ett agentsvar.
_STEGLOGGAR = frozenset({"step_log", "step_outputs"})
#: Så djupt i svaret en steglogg letas. Chattens ligger överst, leadsjobbens
#: ett par nivåer in. Gränsen håller kostnaden nere för en körnings tillstånd
#: på flera megabyte, som pollas var tredje sekund.
_DJUP = 4


def utan_stegtexter(varde: Any, djup: int = 0) -> Any:
    """`varde` utan stegloggarnas texter.

    Rensar där svaret LÄMNAS UT, inte där det sparas: kvotbokföringen och
    återtagen läser det lagrade svaret, och redan lagrade jobb täcks. Ett
    värde utan steglogg lämnas tillbaka som samma objekt, utan kopia.
    """
    if djup >= _DJUP:
        return varde
    if isinstance(varde, list):
        nya = [utan_stegtexter(v, djup + 1) for v in varde]
        return nya if any(n is not g for n, g in zip(nya, varde)) else varde
    if not isinstance(varde, dict):
        return varde
    ut: dict[str, Any] | None = None
    for nyckel, v in varde.items():
        if nyckel in _STEGLOGGAR and isinstance(v, list):
            ny: Any = [
                {f: x for f, x in s.items() if f not in _STEGTEXTER}
                if isinstance(s, dict) and not _STEGTEXTER.isdisjoint(s)
                else s
                for s in v
            ]
            if all(n is g for n, g in zip(ny, v)):
                ny = v
        else:
            ny = utan_stegtexter(v, djup + 1)
        if ny is not v:
            if ut is None:
                ut = dict(varde)
            ut[nyckel] = ny
    return varde if ut is None else ut
