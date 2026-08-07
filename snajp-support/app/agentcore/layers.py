"""Skiktmodellen (plan Del B). Fyra skikt, komponerade vid varje körning,
versionerade var för sig:

  Skikt 0  Baseline    agentkärna: reasoning, verktyg, grindar   versionerad, pinnad per kund
  Skikt 1  Playbook    skill-kedjan + ordningen per agenttyp     versionerad med baselinen
  Skikt 2  Tenant      KB, ton, instruktioner, godkända svar     kunden äger
  Skikt 3  Run         kanal, språkläge, tråd, prospektdata      per ärende

En kund är pinnad. Ny baseline når aldrig en kund automatiskt (INV-AGENT-002)
— se evals.decide_promotion för grinden som verkställer det.
"""

from __future__ import annotations

from dataclasses import dataclass

from .packs import Playbook


@dataclass(frozen=True)
class Baseline:
    """Skikt 0. `manifest_hash` är agent-core/manifest.json:s hash — ändras
    en enda vendorad fil ändras baseline-versionen (Del D)."""

    manifest_hash: str
    model: str = "deepseek-v4-flash"
    vision_model: str = "gemini-3.6-flash"  # G9 — sidovagn, tas bort när v4-flash får vision


@dataclass(frozen=True)
class TenantLayer:
    """Skikt 2 — kunden äger detta."""

    tenant_id: str
    tone: str
    instructions_md: str
    taxonomy: tuple[str, ...]  # A4 — kundkonfigurerbar, valideras mot DB-check-villkoret
    language_policy: str = "sv_default"


@dataclass(frozen=True)
class RunLayer:
    """Skikt 3 — per ärende."""

    channel: str
    language_state: str = "sv"  # "sv" | "en_confirmed" — INV-LANG-001
    thread_id: str | None = None


@dataclass(frozen=True)
class ComposedRun:
    """De fyra skikten komponerade för en enskild körning."""

    baseline: Baseline
    playbook: Playbook
    tenant: TenantLayer
    run: RunLayer

    @property
    def pinned_pack_version(self) -> str:
        """Vad en kund faktiskt pinnar: baseline + playbook ihop. Tenant- och
        run-skikten ändras utan att röra pinningen (kunden äger sin KB/ton
        fritt; det är bara agentkärnan + skill-kedjan som är pack-versionerad)."""
        return f"{self.baseline.manifest_hash}:{self.playbook.name}"
