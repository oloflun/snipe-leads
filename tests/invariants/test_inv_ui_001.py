"""INV-UI-001 — appytorna bär ingen mikrotext och ingen andra typografi.

Anton förbjöd 2026-09-19 all liten "beskrivande" text (FEEDBACK.md F-016): kickers,
överrader, spärrade mono-etiketter, ingresser som beskriver sidan. Den 2026-09-27 fanns
ändå 282 `kicker` kvar på appytorna, fyra olika sidrubriker och kursiva Fraunces-rubriker
på två av sex adminsidor. Regeln stod i prosa i fem dokument; det var inte nog, för en
regel i prosa bryts av nästa flytande mening (chain-discipline R2).

Testet läser källan, inte den renderade sidan, med flit: det fäller en NY vy som någon
bygger med de gamla klasserna innan den ens har renderats. Kommentarer strykes först —
husets kommentarer förklarar gärna varför en kicker togs bort, och det ska de få göra.

Formen på appytorna: `components/ui.tsx` (Sidhuvud, Sektion, Nyckeltal, etikett, meta,
flik …) och plans/2026-09-27-appytor-enhetlighet.md.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: De inloggade ytorna. Marknadssidorna har egen apparat och egen grind (gate 99).
APPYTOR = [
    *sorted((ROOT / "app" / "admin").rglob("*.tsx")),
    *sorted((ROOT / "app" / "dashboard").rglob("*.tsx")),
    *sorted((ROOT / "app" / "settings").rglob("*.tsx")),
    *sorted((ROOT / "components" / "admin").rglob("*.tsx")),
    *sorted((ROOT / "components" / "dashboard").rglob("*.tsx")),
    *sorted((ROOT / "components" / "leads").rglob("*.tsx")),
    *sorted((ROOT / "components" / "settings").rglob("*.tsx")),
    *sorted((ROOT / "components" / "kvitton").rglob("*.tsx")),
    *sorted((ROOT / "components" / "snajp").rglob("*.tsx")),
    *sorted((ROOT / "components" / "shell").rglob("*.tsx")),
    *(
        ROOT / "components" / namn
        for namn in (
            "ui.tsx",
            "AppShell.tsx",
            "WorkspaceViews.tsx",
            "SoulEditor.tsx",
            "VyVaxel.tsx",
            "ImpersonationBanner.tsx",
            "AgentSajtKnapp.tsx",
            "EjAktiverad.tsx",
            "auth/SignOutButton.tsx",
        )
    ),
]

#: (namn, mönster). Klasserna som gav appytorna en andra röst, och em-strecket som
#: DESIGN.md förbjuder i all synlig text.
FORBJUDET = [
    ("kicker", re.compile(r"\bkicker\b")),
    ("versaler som etikett", re.compile(r"\buppercase\b")),
    ("spärrning", re.compile(r"tracking-\[0\.(?:0[6-9]|[1-9])")),
    ("kursiv rubrik", re.compile(r"italic-disp|font-display italic|italic font-display")),
    ("em-streck", re.compile("—")),
]

_BLOCKKOMMENTAR = re.compile(r"/\*.*?\*/", re.DOTALL)
# `//` bara efter blanktecken eller radstart — annars äter den `https://` i strängar.
_RADKOMMENTAR = re.compile(r"(^|\s)//.*$", re.MULTILINE)


def _utan_kommentarer(kalla: str) -> str:
    # Blockkommentarer ersätts med lika många radbrytningar, så radnumren står kvar.
    kalla = _BLOCKKOMMENTAR.sub(lambda m: "\n" * m.group(0).count("\n"), kalla)
    return _RADKOMMENTAR.sub(r"\1", kalla)


def _fynd(sokvag: Path) -> list[str]:
    rader = _utan_kommentarer(sokvag.read_text(encoding="utf-8")).splitlines()
    return [
        f"{sokvag.relative_to(ROOT).as_posix()}:{nr}: {namn}: {rad.strip()[:110]}"
        for nr, rad in enumerate(rader, 1)
        for namn, monster in FORBJUDET
        if monster.search(rad)
    ]


def test_appytorna_finns():
    # Ett glob som inte hittar något ger ett tomt och därmed alltid grönt test.
    assert len(APPYTOR) > 40
    saknas = [p for p in APPYTOR if not p.exists()]
    assert not saknas, saknas


def test_ingen_mikrotext_eller_andra_typografi():
    fynd = [f for p in APPYTOR for f in _fynd(p)]
    assert not fynd, "Appytorna ska använda primitiverna i components/ui.tsx:\n" + "\n".join(fynd)


def test_grinden_fäller_det_den_ska():
    # M3: grinden bevisas mot ett känt trasigt fall, annars mäter den ingenting.
    trasig = '<p className="kicker text-mineral">Översikt</p>\n<h1 className="font-display italic-disp">A — B</h1>'
    rena = '// en kicker togs bort här — se F-016\n<a href="https://snajp.se">x</a>'
    assert {namn for namn, m in FORBJUDET if m.search(_utan_kommentarer(trasig))} == {
        "kicker",
        "kursiv rubrik",
        "em-streck",
    }
    assert not any(m.search(_utan_kommentarer(rena)) for _, m in FORBJUDET)
