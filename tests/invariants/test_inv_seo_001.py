"""INV-SEO-001: sökordssidorna hänger ihop, och priserna i länkarna följer prislistan.

Anton 2026-11-05: Snajp syntes bara på varumärket. Sajten hade tre produkt-
adresser utan sökord i titeln och utan H1, och FAQ:ns svar saknades i HTML:en.
Samma dag: "se till att priserna automatiskt uppdateras i länkarna vid ändring
på hemsidan".

Grinden läser källan och fäller:

* en post i lib/landningar.ts utan egen mapp, innehåll, schema eller tenantspärr;
* en titel som är dubblett, längre än vad Google visar (60 tecken) eller har ett
  tankstreck; en beskrivning utanför 70 till 160 tecken;
* ett kronbelopp skrivet för hand i sidornas metadata, sökordssidornas innehåll,
  schemat eller llms.txt (allt ska räknas ur lib/pricing.ts);
* att hjälterubriken slutar vara en h1, eller att FAQ-svaren åter tas ur HTML:en.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _syskon(namn: str):
    spec = importlib.util.spec_from_file_location(namn, Path(__file__).with_name(f"{namn}.py"))
    modul = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modul)
    return modul


_utan_kommentarer = _syskon("test_inv_ui_001")._utan_kommentarer


def _las(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _landningar() -> list[str]:
    """Adresserna i LANDNINGAR, och bara där: FAMILJ längre ned har egna `vag:`."""
    registret = _las("lib/landningar.ts").split("export const LANDNINGAR", 1)[1].split("] as const", 1)[0]
    return re.findall(r'^\s*vag: "(/[^"]+)"', registret, re.MULTILINE)


def test_registret_har_poster():
    assert len(_landningar()) >= 8


def test_mallen_har_tenantsparr_och_schema():
    kalla = _las("components/marketing/LandningsRutt.tsx")
    for krav in ("await notFoundOnTenant()", "<JsonLd", "landningSchema(", "<Landningssida"):
        assert krav in kalla, krav


def test_varje_post_har_sida_och_innehall():
    innehall = _las("lib/landningssidor.ts")
    fel = []
    for vag in _landningar():
        sida = ROOT / "app" / vag.strip("/") / "page.tsx"
        if not sida.is_file():
            fel.append(f"{vag}: saknar {sida.relative_to(ROOT).as_posix()}")
            continue
        kalla = sida.read_text(encoding="utf-8")
        for krav in ("sidmeta(", f'<LandningsRutt vag="{vag}" />'):
            if krav not in kalla:
                fel.append(f"{vag}: page.tsx saknar {krav}")
        if f'vag: "{vag}"' not in innehall:
            fel.append(f"{vag}: saknar innehåll i lib/landningssidor.ts")
    assert not fel, "\n".join(fel)


def test_relaterade_sidor_finns():
    kanda = set(_landningar())
    relaterade = re.findall(r'"(/[^"]+)"', " ".join(re.findall(r"relaterade: \[([^\]]*)\]", _las("lib/landningssidor.ts"))))
    okanda = sorted(set(relaterade) - kanda)
    assert relaterade and not okanda, okanda


def test_sitemapen_laser_registret():
    assert "LANDNINGAR" in _las("app/sitemap.ts")


def _sidor() -> list[Path]:
    return sorted((ROOT / "app").rglob("page.tsx"))


#: `${prisrad("leads")}` blir t.ex. "Från 4 490 kr/mån." när sidan renderas. Längden
#: mäts med ett femsiffrigt belopp, så att en titel inte går över gränsen den
#: dag ett pris passerar 9 999 kr.
_PRISRAD = re.compile(r"\$\{prisrad\([^)]*\)\}")
_STORSTA_PRISRAD = "Från 99 999 kr/mån."
#: Titeln och beskrivningen i ett `sidmeta({ vag, titel, beskrivning })`-anrop.
_SIDMETA = re.compile(
    r"sidmeta\(\{\s*vag:[^,]+,\s*titel:\s*([\"`])(?P<titel>.*?)\1,\s*beskrivning:\s*([\"`])(?P<beskrivning>.*?)\3",
    re.DOTALL,
)


def _metatext(falt: str) -> list[tuple[str, str]]:
    ut = []
    for sida in _sidor():
        for m in _SIDMETA.finditer(sida.read_text(encoding="utf-8")):
            ut.append((sida.relative_to(ROOT).as_posix(), _PRISRAD.sub(_STORSTA_PRISRAD, m.group(falt))))
    return ut


def test_titlarna_ar_unika_och_ryms():
    titlar = _metatext("titel")
    assert len(titlar) >= 14, titlar
    fel = [f"{fil}: {len(t)} tecken: {t}" for fil, t in titlar if len(t) > 60]
    fel += [f"{fil}: tankstreck: {t}" for fil, t in titlar if re.search("[–—]", t)]
    sedda: dict[str, str] = {}
    for fil, t in titlar:
        if t in sedda:
            fel.append(f"{fil} och {sedda[t]} har samma titel: {t}")
        sedda[t] = fil
    assert not fel, "\n".join(fel)


def test_beskrivningarna_ryms():
    fel = [
        f"{fil}: {len(b)} tecken: {b}"
        for fil, b in _metatext("beskrivning")
        if not 70 <= len(b) <= 160 or re.search("[–—]", b)
    ]
    assert not fel, "\n".join(fel)


#: Ett kronbelopp: "4 490 kr", "4490 kr", "1 590kr". Mellanslaget kan vara hårt.
_KRONOR = re.compile(r"\d{1,3}(?:[   ]\d{3})+\s?kr\b|\d{4,}\s?kr\b")

#: Allt som bär pris ut ur sajten: metadata, sökordssidorna, schemat, llms.txt.
_PRISBARARE = [
    *(p.relative_to(ROOT).as_posix() for p in _sidor()),
    "lib/landningar.ts",
    "lib/landningssidor.ts",
    "lib/seo.ts",
    "lib/llms.ts",
    "components/marketing/Landningssida.tsx",
    "components/marketing/LandningsRutt.tsx",
    "components/marketing/Sidfot.tsx",
]


def test_inga_handskrivna_priser():
    fel = [
        f"{rel}: {m.group(0)}"
        for rel in _PRISBARARE
        for m in _KRONOR.finditer(_utan_kommentarer(_las(rel)))
    ]
    assert not fel, "Priset ska räknas ur lib/pricing.ts (prisrad, paketpris, formateraPris):\n" + "\n".join(fel)


def test_ingen_handskriven_bindningstid():
    """Bindningstiden är lika mycket ett villkor i en sökträff som priset:
    "ingen bindningstid" skriven för hand blir fel den dag BINDNINGSTID_MANADER ändras."""
    fel = [
        f"{rel}: {rad.strip()[:100]}"
        for rel in _PRISBARARE
        for rad in _utan_kommentarer(_las(rel)).splitlines()
        if re.search(r"bindningstid|minimum term", rad)
    ]
    assert not fel, "Bindningstiden ska läsas ur lib/pricing.ts (BINDNING):\n" + "\n".join(fel)


def test_grinden_fäller_ett_handskrivet_pris():
    assert _KRONOR.search('beskrivning: "Från 4 490 kr/mån."')
    assert _KRONOR.search("kostar 3990 kr")
    assert not _KRONOR.search("beskrivning: `Ni godkänner. ${prisrad(\"leads\")}`")
    assert not _KRONOR.search("en demo på 15 till 20 minuter")


#: Antons regel 2026-11-06: produkten heter supportagent i all text på sajten.
#: "Supportbot" är ett sökord och får stå i en sökträffs titel och beskrivning,
#: men bara bredvid "supportagent".
_SUPPORTBOT = re.compile(r"(?i)support[\s-]?bot")
_SYNLIG_TEXT = [
    "lib/landningssidor.ts",
    "lib/landningar.ts",
    "lib/faq.ts",
    *(p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "components" / "marketing").rglob("*.ts*"))),
]


def test_supportbot_bara_i_sokträffen():
    fel = [
        f"{rel}: {rad.strip()[:100]}"
        for rel in _SYNLIG_TEXT
        for rad in _utan_kommentarer(_las(rel)).splitlines()
        if _SUPPORTBOT.search(rad)
    ]
    for sida in _sidor():
        utan_meta = _SIDMETA.sub("", _utan_kommentarer(sida.read_text(encoding="utf-8")))
        fel += [f"{sida.relative_to(ROOT).as_posix()}: {rad.strip()[:100]}" for rad in utan_meta.splitlines() if _SUPPORTBOT.search(rad)]
    for falt in ("titel", "beskrivning"):
        fel += [
            f"{fil}: {falt} nämner supportbot utan supportagent: {t}"
            for fil, t in _metatext(falt)
            if _SUPPORTBOT.search(t) and not re.search(r"(?i)supportagent", t)
        ]
    assert not fel, "Sajten säger supportagent; supportbot får bara stå i titel och beskrivning bredvid supportagent:\n" + "\n".join(fel)


def test_jamforelserna_har_kalla_och_ar_aktuella():
    """Jämförande reklam ska gå att kontrollera: varje leverantör har en källa på
    sin egen sajt, och kontrollen får inte bli gammal (lib/jamforelser.ts)."""
    import datetime

    kalla = _utan_kommentarer(_las("lib/jamforelser.ts"))
    datum = re.search(r'KONTROLLERAD = "(\d{4}-\d{2}-\d{2})"', kalla)
    assert datum, "KONTROLLERAD saknas i lib/jamforelser.ts"
    alder = (datetime.date.today() - datetime.date.fromisoformat(datum.group(1))).days
    assert alder <= 120, f"Jämförelsen kontrollerades för {alder} dagar sedan. Kör om kontrollen (docs/SEO-JAMFORELSER-KALLOR.md) och ändra KONTROLLERAD."
    namn = re.findall(r'namn: "([^"]+)"', kalla)
    kallor = re.findall(r'kalla: "([^"]+)"', kalla)
    assert len(namn) >= 10 and len(namn) == len(kallor), (namn, kallor)
    assert all(k.startswith("https://") for k in kallor), kallor
    # Snajps eget pris står aldrig här: det räknas ur lib/pricing.ts.
    assert "Snajp" not in "".join(namn), namn


def test_hjalterubriken_ar_en_h1():
    assert re.search(r'<h1\s+key=\{nyckel\}\s+data-mo="hero-h1"', _las("components/marketing/LandingPhoto.tsx"))


def test_faq_svaren_star_i_html():
    kalla = _las("components/marketing/FaqDragspel.tsx")
    assert "hidden={!utfalld}" in kalla
    assert "{utfalld ? (" not in kalla
