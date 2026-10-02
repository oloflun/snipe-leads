"""INV-COPY-001 — varje komponent med användarvänd text är tvåspråkig.

Anton visade 2026-10-02 femton skärmdumpar av den engelska versionen: `/kvitton`,
`/support`, `/leads`, `/demo` och Iris-vyerna var till stor del svenska trots att
språkväxlaren stod på EN, och den föregående sessionens egna nya komponenter var
enspråkiga. Regeln "varje ny komponent ska vara tvåspråkig" fanns redan som
minnesanteckning; det räckte inte, för en regel i prosa bryts av nästa komponent
som byggs (samma lärdom som INV-UI-001).

Grinden läser källan: en rad med svenska bokstäver (å ä ö) i en strängliteral eller i
JSX-text, som inte står på en `sv:`/`en:`-rad (alltså inte är halvan av ett
`{ sv, en }`-par), är ett fynd. Identifierare (`värde`, `följKörning`) räknas inte:
bara det som når skärmen. Kommentarer stryks först.

Mekanismen: `lib/i18n.tsx` (`useLocale().text({ sv, en })`, `t(nyckel)`), eller en
modulkonstant av `Localized`. Adminytan använder `lib/admin/sprak.ts` på samma sätt.

Namnet är INV-COPY-001 och inte INV-I18N-001 med flit: meta-testet
(`test_meta_invariants.py`) parsar bara id:n utan siffror i områdesdelen.
"""

from __future__ import annotations

import re
from pathlib import Path

import importlib.util

ROOT = Path(__file__).resolve().parents[2]


def _syskon(namn: str):
    spec = importlib.util.spec_from_file_location(namn, Path(__file__).with_name(f"{namn}.py"))
    modul = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modul)
    return modul


_UI = _syskon("test_inv_ui_001")
_APPYTOR_UI = _UI.APPYTOR
_utan_kommentarer = _UI._utan_kommentarer

#: Allt som renderar text till en besökare: appytorna (INV-UI-001:s lista), demon,
#: produktsidorna, marknadsytan, inloggning/onboarding och de juridiska sidorna.
YTOR = [
    *_APPYTOR_UI,
    *sorted((ROOT / "app" / "demo").rglob("*.tsx")),
    *sorted((ROOT / "app" / "kvitton").rglob("*.tsx")),
    *sorted((ROOT / "app" / "support").rglob("*.tsx")),
    *sorted((ROOT / "app" / "leads").rglob("*.tsx")),
    *sorted((ROOT / "app" / "avregistrera").rglob("*.tsx")),
    *sorted((ROOT / "app" / "integritetspolicy").rglob("*.tsx")),
    *sorted((ROOT / "app" / "villkor").rglob("*.tsx")),
    *sorted((ROOT / "app" / "angerratt").rglob("*.tsx")),
    *sorted((ROOT / "app" / "cookies").rglob("*.tsx")),
    *sorted((ROOT / "components" / "marketing").rglob("*.tsx")),
    *sorted((ROOT / "components" / "crm").rglob("*.tsx")),
    *sorted((ROOT / "components" / "auth").rglob("*.tsx")),
    ROOT / "lib" / "demo" / "sektioner.ts",
]

#: Ordböcker och fixturdata är svenska med flit, eller bär sina par i en annan form.
UNDANTAG = {
    "lib/i18n.tsx",
    "lib/admin/sprak.ts",
    "components/marketing/copy.ts",
    "components/DesignDrafts.tsx",
}

_SVENSKA = re.compile(r"[åäöÅÄÖ]")
#: Halvan av ett språkpar: `sv: "…"`, `en: "…"`, eller `{ sv: …, en: … }` på en rad.
_PARAD = re.compile(r"\b(?:sv|en)\s*:\s*(?:\"|'|`)")
_STRANG = re.compile(r"\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\\n]|\\.)*`")
_TAGG = re.compile(r"<[^<>]*>")
_UTTRYCK = re.compile(r"\{[^{}]*\}")
_KODRAD = re.compile(r"[=(;]|^\s*(?:import|export|const|let|type|interface|return)\b")
#: `paket.populärast`, `svar.korning` – egenskaper, inte text.
_MEDLEM = re.compile(r"[\w$]+\.[\w$.]*")
#: `sv: [` … `]` – ett språkpar vars halvor är listor över flera rader.
_PARLISTA_START = re.compile(r"\b(?:sv|en)\s*:\s*\[\s*$")
#: Personnamn och bolagsnamn i exempeldata ("Jonas Vikström") är desamma på engelska.
_NAMNFALT = re.compile(r"\b(?:namn|name|company_name|avsandare)\s*:\s*[\"'`]")


def _synlig_svenska(rad: str) -> bool:
    """Svenska bokstäver som når skärmen: i en strängliteral, eller i JSX-text."""
    if _PARAD.search(rad) or _NAMNFALT.search(rad):
        return False
    if any(_SVENSKA.search(s) for s in _STRANG.findall(rad)):
        return True
    # JSX-text på egen rad ("Inga körningar än.") har varken citattecken, taggar
    # eller uttryck kvar när de strukits — och ser inte ut som kod.
    utan = _MEDLEM.sub("", _UTTRYCK.sub("", _TAGG.sub("", _STRANG.sub("", rad))))
    return bool(_SVENSKA.search(utan)) and not _KODRAD.search(utan)


#: Nexts `export const metadata = { title, description }` renderas på servern utan
#: kundens språkval och är sidans sökmotortext, inte gränssnittet: utanför grinden.
_METADATA = re.compile(r"^export const metadata\b[^\n]*=\s*\{.*?^\};?", re.DOTALL | re.MULTILINE)


#: `// inte-copy` på raden: data som råkar vara svenska (en fixturnyckel, en
#: backendfras koden matchar mot), inte text som når skärmen. Markören står
#: synlig i källan; en \u-escape hade gömt samma sak.
_MARKOR = "inte-copy"


def _fynd(sokvag: Path) -> list[str]:
    ratext = sokvag.read_text(encoding="utf-8")
    markerade = {nr for nr, rad in enumerate(ratext.splitlines(), 1) if _MARKOR in rad}
    kalla = _utan_kommentarer(ratext)
    kalla = _METADATA.sub(lambda m: "\n" * m.group(0).count("\n"), kalla)
    rader = kalla.splitlines()
    fynd: list[str] = []
    i_parlista = False
    for nr, rad in enumerate(rader, 1):
        if i_parlista:
            if rad.strip().startswith("]"):
                i_parlista = False
            continue
        if _PARLISTA_START.search(rad):
            i_parlista = True
            continue
        if nr in markerade:
            continue
        if _synlig_svenska(rad):
            fynd.append(f"{sokvag.relative_to(ROOT).as_posix()}:{nr}: {rad.strip()[:110]}")
    return fynd


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def test_ytorna_finns():
    assert len(YTOR) > 60
    saknas = [p for p in YTOR if not p.exists()]
    assert not saknas, saknas


def test_grinden_fäller_det_den_ska():
    assert _synlig_svenska('        <p className={meta}>Hämtar körningar…</p>')
    assert _synlig_svenska('        Inga körningar än. Starta en under Bolag.')
    assert _synlig_svenska('  setFel("Körningen avbröts.");')
    assert _synlig_svenska('  <Tabell ariaLabel="Körningar" />')
    # Paret, identifieraren och engelskan går igenom.
    assert not _synlig_svenska('  titel: { sv: "Körningar", en: "Runs" },')
    assert not _synlig_svenska('    sv: "Hämtar körningar…",')
    assert not _synlig_svenska('  const värde = följKörning(sparatId);')
    assert not _synlig_svenska('  <p>{text({ sv: "Klar", en: "Done" })}</p>')
    assert not _synlig_svenska('  <p className="text-ink">Runs</p>')
    assert not _synlig_svenska('                paket.populärast')


#: Skuld, inte en permanent lucka: filerna som var enspråkiga när grinden sattes
#: 2026-10-02 (89 filer, mätt med den här grinden). Varje
#: fil stryks när den översatts — test_skulden_ar_fortfarande_skuld tvingar fram
#: det. Ordningen för översättningen står i plans/ (Fas 5): förra sessionens
#: komponenter först, sedan demon, produktsidorna, Iris, support/kvitton/
#: inställningar, auth/admin/marknad, juridiken.
_SKULD_2026_10_02: set[str] = {
    "app/admin/agentanvandning/page.tsx",
    "app/admin/korningar/[id]/page.tsx",
    "app/admin/korningar/page.tsx",
    "app/admin/kunder/[id]/data/page.tsx",
    "app/admin/kunder/[id]/page.tsx",
    "app/admin/page.tsx",
    "app/admin/paket/page.tsx",
    "app/admin/testkorningar/page.tsx",
    "app/angerratt/page.tsx",
    "app/avregistrera/[token]/page.tsx",
    "app/cookies/page.tsx",
    "app/integritetspolicy/page.tsx",
    "app/villkor/page.tsx",
    "components/SoulEditor.tsx",
    "components/admin/AgentAnvandning.tsx",
    "components/admin/Agentinstruktioner.tsx",
    "components/admin/Avstangning.tsx",
    "components/admin/KonverteraTestkund.tsx",
    "components/admin/Kunddata.tsx",
    "components/admin/Kundprofil.tsx",
    "components/admin/PaketHantering.tsx",
    "components/admin/Testkorningar.tsx",
    "components/auth/LoginForm.tsx",
    "components/auth/OnboardingWizard.tsx",
    "components/auth/ResetPasswordForm.tsx",
    "components/crm/CrmDemo.tsx",
    "components/snajp/InboxTriage.tsx",
    "components/snajp/IntegrationSection.tsx",
    "components/snajp/JournalVy.tsx",
}


def test_varje_yta_ar_tvasprakig():
    fynd = [
        f
        for p in YTOR
        if _rel(p) not in UNDANTAG and _rel(p) not in _SKULD_2026_10_02
        for f in _fynd(p)
    ]
    assert not fynd, (
        f"{len(fynd)} rader svenska utan engelskt par (INV-COPY-001). "
        "Gå via lib/i18n.tsx: text({ sv, en }) eller en Localized-konstant.\n"
        + "\n".join(fynd[:60])
    )


def test_skulden_ar_fortfarande_skuld():
    """En fil på skuldlistan som blivit ren ska strykas, annars växer listan till en
    permanent lucka utan att någon märker det."""
    rena = [
        rel
        for rel in sorted(_SKULD_2026_10_02)
        if (ROOT / rel).exists() and not _fynd(ROOT / rel)
    ]
    borta = [rel for rel in sorted(_SKULD_2026_10_02) if not (ROOT / rel).exists()]
    assert not rena and not borta, {"stryk, nu rena": rena, "stryk, finns inte": borta}
