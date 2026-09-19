"""Det ett verktygsanrop lämnar tillbaka — samma form för HTTP och MCP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: Ebbots gräns för vad ett verktygssvar får ta i anspråk (16 384 tecken).
#: Det som går till PROMPTEN kapas hårdare i uppslag.py — flera anrop per
#: ärende delar på samma kontextfönster.
MAX_RESULTATTEXT = 16_384


def kapa(text: str, grans: int) -> str:
    if len(text) <= grans:
        return text
    return text[: grans - 40].rstrip() + f"\n… [kapat, {len(text) - grans + 40} tecken till]"


@dataclass
class Verktygsresultat:
    verktyg: str
    ok: bool
    #: HTTP-status (HTTP-verktyg), None för MCP och simulerade anrop.
    status: int | None = None
    #: Tvättad (inga hemligheter) och kapad text. Det enda modellen ser.
    data: str = ""
    #: Svensk feltext när ok är falskt. Går både till modellen och loggen.
    fel: str | None = None
    #: Testchatten: ett skrivande anrop som INTE skickades.
    simulerad: bool = False
    skrivande: bool = False
    latens_ms: int = 0

    def for_modellen(self) -> dict[str, Any]:
        if self.simulerad:
            return {
                "verktyg": self.verktyg,
                "simulerat": True,
                "besked": "Testläge: anropet skickades inte. Säg inte till kunden att något är gjort.",
            }
        if not self.ok:
            return {"verktyg": self.verktyg, "fel": self.fel or "Anropet misslyckades."}
        ut: dict[str, Any] = {"verktyg": self.verktyg, "data": self.data}
        if self.status is not None:
            ut["status"] = self.status
        return ut

    def for_logg(self) -> dict[str, Any]:
        """step_log / agent_runs: VAD som hände, aldrig svarsdatan.

        Svaret kan bära kunduppgifter ur kundens CRM; loggen ska gå att visa
        i en spårvy utan att bli ett andra kundregister.
        """
        return {
            "verktyg": self.verktyg,
            "ok": self.ok,
            "status": self.status,
            "fel": self.fel,
            "simulerad": self.simulerad,
            "skrivande": self.skrivande,
            "latens_ms": self.latens_ms,
            "tecken": len(self.data),
        }
