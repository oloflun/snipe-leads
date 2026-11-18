"""Licensförteckning över beroendena, och en grind mot copyleft (ISO 27001 A.5.32).

    python scripts/licenser.py                 # skriv förteckningen till stdout
    python scripts/licenser.py --skriv         # skriv docs/compliance/licenser.md
    python scripts/licenser.py --kontrollera   # exit 1 vid ej godkänd licens

VAD SOM RÄKNAS

npm: lockfilerna för det som byggs och driftsätts, inte alla lockfiler i
repot. `package-lock.json` i roten är webbtjänsten (`web`), och
`support-webb/package-lock.json` är den fristående agentsajten (tjänsten
`support`, se DEPLOY.md). `marknad/video/` är ett fristående
Remotion-projekt som aldrig byggs eller deployas (dess README och
`.dockerignore`), och email-studio/ har ingen lockfil. Lockfil v2/v3 bär
fältet `license` per paket, så inget behöver installeras.

pip: `snajp-support/requirements.txt` (backenden) och
`scripts/requirements-scripts.txt` (driftskripten, körs från en
utvecklingsmaskin, därför dev). Licensen läses ur de INSTALLERADE paketens
metadata, så resultatet är bara rättvisande i en miljö där filerna är
installerade. Skriptet går från requirements-raderna och följer
`Requires-Dist` (med extras och markörer) genom de installerade
distributionerna; andra paket i samma miljö räknas inte. Saknas ett paket
som requirements kräver fäller --kontrollera, så att en ofullständig miljö
inte ger grönt. CI installerar i en ren miljö (jobbet `licenser` i
.github/workflows/verify.yml), och det är den körningen som avgör.

Rader efter kommentaren `# test` i requirements.txt räknas som dev. Ett
paket som nås både från en prod- och en dev-rad räknas som prod.

GRINDEN

Ett SPDX-uttryck tolkas med OR och AND: "MIT OR GPL-3.0" godtas eftersom ett
tillåtande alternativ finns, "MIT AND GPL-3.0" gör det inte. Copyleft (GPL,
LGPL, AGPL, MPL, EPL, CDDL, EUPL, OSL, SSPL, CC-BY-SA och liknande) och
okända eller saknade licenser fäller, om inte paketet står i vitlistan
`docs/compliance/licenser-vitlista.json` med samma licens. Ett undantag
gäller ett paket i ett ekosystem, en version eller ett versionsintervall och
den licenstext som granskades: ändras licensen gäller undantaget inte längre.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.metadata as im
import json
import platform
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
UT = ROT / "docs" / "compliance" / "licenser.md"
VITLISTA = ROT / "docs" / "compliance" / "licenser-vitlista.json"

# Lockfil -> projektnamn i förteckningen. Se modulens docstring för urvalet.
NPM_LOCKFILER: tuple[tuple[str, str], ...] = (
    ("package-lock.json", "web"),
    ("support-webb/package-lock.json", "support-webb"),
)
# Requirementsfil -> om hela filen är dev (driftskripten deployas aldrig).
PIP_KRAV: tuple[tuple[str, bool], ...] = (
    ("snajp-support/requirements.txt", False),
    ("scripts/requirements-scripts.txt", True),
)

# --------------------------------------------------------------------------
# Licensklassning

TILLATANDE = {
    "0bsd", "mit", "mit-0", "isc", "apache-2.0", "apache-1.1", "bsd-2-clause",
    "bsd-3-clause", "bsd-3-clause-clear", "bsd-4-clause", "bsd", "unlicense",
    "cc0-1.0", "cc-by-3.0", "cc-by-4.0", "python-2.0", "psf-2.0", "psf",
    "blueoak-1.0.0", "zlib", "bsl-1.0", "wtfpl", "x11", "zpl-2.1", "zpl-2.0",
    "hpnd", "public-domain", "afl-2.1", "afl-3.0", "ncsa", "mit-cmu",
}
# Prefix som gör en licens copyleft (eller på annat sätt villkorad, som
# CC-BY-NC). Prefix, inte exakta id:n, så att "LGPL", "GPL-2.0-only" och
# "LGPL-3.0-or-later" alla fångas.
COPYLEFT_PREFIX = (
    "agpl", "lgpl", "gpl", "mpl", "epl", "cddl", "eupl", "osl", "sspl",
    "cc-by-sa", "cc-by-nc", "cc-by-nd", "cpl", "cecill", "ms-rl", "rpl",
    "sleepycat", "odbl", "apsl", "qpl", "busl", "elastic",
)

# Fritext och klassificerare -> SPDX-liknande id. Nycklar i gemener.
SYNONYMER = {
    "mit license": "MIT", "the mit license": "MIT", "mit licence": "MIT",
    "expat": "MIT", "isc license": "ISC", "isc license (iscl)": "ISC",
    "iscl": "ISC", "bsd license": "BSD", "new bsd license": "BSD-3-Clause",
    "bsd 3-clause license": "BSD-3-Clause", "3-clause bsd license": "BSD-3-Clause",
    "bsd-3": "BSD-3-Clause", "bsd 2-clause license": "BSD-2-Clause",
    "apache 2.0": "Apache-2.0", "apache 2": "Apache-2.0",
    "apache license 2.0": "Apache-2.0", "apache license, version 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0", "apache-2": "Apache-2.0",
    "apache license version 2.0": "Apache-2.0", "apache": "Apache-2.0",
    "python software foundation license": "PSF-2.0",
    "the unlicense (unlicense)": "Unlicense", "public domain": "Public-Domain",
    "zope public license": "ZPL-2.1",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0", "mpl 2.0": "MPL-2.0",
    "gnu lesser general public license v3 (lgplv3)": "LGPL-3.0",
    "gnu lesser general public license v3 or later (lgplv3+)": "LGPL-3.0-or-later",
    "gnu lesser general public license v2 (lgplv2)": "LGPL-2.0",
    "gnu lesser general public license v2 or later (lgplv2+)": "LGPL-2.0-or-later",
    "gnu library or lesser general public license (lgpl)": "LGPL",
    "lgpl with exceptions": "LGPL",
    "gnu general public license v2 (gplv2)": "GPL-2.0",
    "gnu general public license v2 or later (gplv2+)": "GPL-2.0-or-later",
    "gnu general public license v3 (gplv3)": "GPL-3.0",
    "gnu general public license v3 or later (gplv3+)": "GPL-3.0-or-later",
    "gnu affero general public license v3": "AGPL-3.0",
    "gnu affero general public license v3 or later (agplv3+)": "AGPL-3.0-or-later",
    "eclipse public license 2.0 (epl-2.0)": "EPL-2.0",
}

OKAND = "okänd"


def _klass_id(lic_id: str) -> str:
    """Ett enskilt id -> 'tillatande', 'copyleft' eller 'okand'."""
    s = lic_id.strip().lower()
    if s in TILLATANDE:
        return "tillatande"
    if s.startswith(COPYLEFT_PREFIX):
        return "copyleft"
    # BSD-varianter och Apache-varianter med suffix räknas som tillåtande.
    if re.fullmatch(r"bsd(-\d-clause.*)?", s) or s.startswith("apache-2"):
        return "tillatande"
    return "okand"


_TOKEN = re.compile(r"\(|\)|[^\s()]+")


def tolka(uttryck: str | None) -> str:
    """Klassa ett SPDX-uttryck: 'tillatande', 'copyleft' eller 'okand'.

    OR: det bästa alternativet gäller (ett tillåtande räcker). AND: det
    sämsta gäller. WITH (undantagsklausul) ändrar inte klassen: en GPL med
    Classpath-undantag ska fortfarande beslutas av en människa. Ett uttryck
    som inte går att tolka är okänt.
    """
    if not uttryck or not uttryck.strip():
        return "okand"
    tokens = _TOKEN.findall(uttryck)
    rang = {"tillatande": 0, "okand": 1, "copyleft": 2}
    pos = 0

    def uttr() -> str:
        nonlocal pos
        resultat = term()
        while pos < len(tokens) and tokens[pos].upper() == "OR":
            pos += 1
            hoger = term()
            resultat = min(resultat, hoger, key=rang.__getitem__)
        return resultat

    def term() -> str:
        nonlocal pos
        resultat = faktor()
        while pos < len(tokens) and tokens[pos].upper() == "AND":
            pos += 1
            hoger = faktor()
            resultat = max(resultat, hoger, key=rang.__getitem__)
        return resultat

    def faktor() -> str:
        nonlocal pos
        if pos >= len(tokens):
            raise ValueError("uttrycket tar slut")
        tok = tokens[pos]
        if tok == "(":
            pos += 1
            resultat = uttr()
            if pos >= len(tokens) or tokens[pos] != ")":
                raise ValueError("saknar )")
            pos += 1
        elif tok == ")" or tok.upper() in ("AND", "OR", "WITH"):
            raise ValueError(f"oväntat {tok}")
        else:
            pos += 1
            resultat = _klass_id(tok.rstrip("+*"))
        if pos < len(tokens) and tokens[pos].upper() == "WITH":
            pos += 2  # undantagets namn
        return resultat

    try:
        resultat = uttr()
    except ValueError:
        return "okand"
    if pos != len(tokens):
        return "okand"
    return resultat


def normalisera(text: str | None) -> str:
    """Fritext ur lockfil eller metadata -> ett uttryck att visa och tolka."""
    if text is None:
        return OKAND
    s = text.strip()
    if not s or s.upper() in ("UNKNOWN", "NONE"):
        return OKAND
    forsta = s.splitlines()[0].strip()
    nyckel = forsta.lower().rstrip(".")
    if nyckel in SYNONYMER:
        return SYNONYMER[nyckel]
    if len(s) > 120 or "\n" in s:
        # Hela licenstexten inklistrad: visa bara första raden.
        return forsta[:80] if forsta else OKAND
    return s


# --------------------------------------------------------------------------
# Insamling


@dataclass(frozen=True)
class Paket:
    ekosystem: str  # "npm" eller "pip"
    projekt: str  # lockfilens/requirementsfilens projekt
    namn: str
    version: str
    licens: str
    kalla: str  # varifrån licensen lästes
    prod: bool

    @property
    def klass(self) -> str:
        return tolka(self.licens) if self.licens != OKAND else "okand"


def las_lockfil(sokvag: Path, projekt: str) -> list[Paket]:
    """Alla paket i en npm-lockfil v2/v3, ett per (namn, version)."""
    data = json.loads(sokvag.read_text(encoding="utf-8"))
    if int(data.get("lockfileVersion", 1)) < 2 or "packages" not in data:
        raise SystemExit(f"{sokvag}: lockfil v1 saknar licensfält, kör npm install med npm 7+")
    sett: dict[tuple[str, str], Paket] = {}
    for nyckel, post in data["packages"].items():
        if not nyckel or post.get("link"):
            continue  # roten själv, och workspace-länkar
        namn = post.get("name") or nyckel.rsplit("node_modules/", 1)[-1]
        version = str(post.get("version", "?"))
        lic = post.get("license")
        if isinstance(lic, dict):  # äldre form {type, url}
            lic = lic.get("type")
        prod = not (post.get("dev") or post.get("devOptional"))
        p = Paket("npm", projekt, namn, version, normalisera(lic), "lockfil", prod)
        tidigare = sett.get((namn, version))
        if tidigare is None or (prod and not tidigare.prod):
            sett[(namn, version)] = p
    return list(sett.values())


def _norm_namn(namn: str) -> str:
    return re.sub(r"[-_.]+", "-", namn).lower()


_KRAV_NAMN = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[([^\]]*)\])?")


def _tolka_krav(rad: str) -> tuple[str, set[str], str | None] | None:
    """'pkg[a,b]>=1; marker' -> (normnamn, extras, marker)."""
    rad = rad.split(" #", 1)[0].strip()
    if not rad or rad.startswith(("#", "-")):
        return None
    m = _KRAV_NAMN.match(rad)
    if not m:
        return None
    extras = {e.strip().lower() for e in (m.group(3) or "").split(",") if e.strip()}
    marker = rad.split(";", 1)[1].strip() if ";" in rad else None
    return _norm_namn(m.group(1)), extras, marker


def _marker_galler(marker: str | None, extra: str = "") -> bool:
    if not marker:
        return True
    try:
        from packaging.markers import Marker  # följer med pytest

        return Marker(marker).evaluate({"extra": extra})
    except ImportError:
        # Utan packaging: ta med allt utom extras som inte begärts. Hellre
        # ett paket för mycket i förteckningen än ett för lite.
        m = re.search(r"extra\s*==\s*['\"]([^'\"]+)['\"]", marker)
        return m is None or _norm_namn(m.group(1)) == _norm_namn(extra)
    except Exception:
        return True


def lasa_krav(sokvag: Path, allt_dev: bool) -> list[tuple[str, set[str], bool]]:
    """Requirementsrader -> (namn, extras, prod). '# test' startar dev-delen."""
    ut: list[tuple[str, set[str], bool]] = []
    dev = allt_dev
    for rad in sokvag.read_text(encoding="utf-8").splitlines():
        if rad.strip().lower() == "# test":
            dev = True
            continue
        krav = _tolka_krav(rad)
        if krav is None:
            continue
        namn, extras, marker = krav
        if _marker_galler(marker):
            ut.append((namn, extras, not dev))
    return ut


def _installerade() -> dict[str, im.Distribution]:
    ut: dict[str, im.Distribution] = {}
    for d in im.distributions():
        namn = d.metadata.get("Name")
        if namn:
            ut.setdefault(_norm_namn(namn), d)
    return ut


def pip_licens(meta) -> tuple[str, str]:
    """(licens, källa) ur en distributions metadata."""
    uttryck = meta.get("License-Expression")
    if uttryck and uttryck.strip():
        return uttryck.strip(), "License-Expression"
    klassificerare = []
    for c in meta.get_all("Classifier") or []:
        delar = [d.strip() for d in c.split("::")]
        if delar[0] != "License" or delar[-1] == "OSI Approved" or len(delar) < 2:
            continue
        namn = delar[-1]
        klassificerare.append(SYNONYMER.get(namn.lower(), namn))
    if klassificerare:
        # Flera licensklassificerare betyder i praktiken dubbellicens.
        unika = sorted(set(klassificerare))
        return " OR ".join(unika), "klassificerare"
    return normalisera(meta.get("License")), "License-fält"


def las_pip(krav: list[tuple[str, set[str], bool]], projekt: str) -> tuple[list[Paket], list[str]]:
    """Följ Requires-Dist från requirementsraderna. -> (paket, saknade)."""
    inst = _installerade()
    prod_for: dict[str, bool] = {}
    saknade: set[str] = set()
    ko: list[tuple[str, set[str], bool]] = list(krav)
    sedda: set[tuple[str, frozenset[str], bool]] = set()
    while ko:
        namn, extras, prod = ko.pop()
        nyckel = (namn, frozenset(extras), prod)
        if nyckel in sedda:
            continue
        sedda.add(nyckel)
        dist = inst.get(namn)
        if dist is None:
            saknade.add(namn)
            continue
        prod_for[namn] = prod_for.get(namn, False) or prod
        for rad in dist.requires or []:
            krav_rad = _tolka_krav(rad)
            if krav_rad is None:
                continue
            barn, barn_extras, marker = krav_rad
            if any(_marker_galler(marker, e) for e in ({""} | extras)):
                # En markör som bara gäller ett extra vi inte bett om faller
                # bort här: _marker_galler(marker, "") är då falsk.
                ko.append((barn, barn_extras, prod))
    paket = []
    for namn, prod in prod_for.items():
        dist = inst[namn]
        lic, kalla = pip_licens(dist.metadata)
        paket.append(
            Paket("pip", projekt, dist.metadata["Name"], dist.version, lic, kalla, prod)
        )
    return paket, sorted(saknade)


def samla() -> tuple[list[Paket], list[str]]:
    paket: list[Paket] = []
    for fil, projekt in NPM_LOCKFILER:
        paket += las_lockfil(ROT / fil, projekt)
    # Varje requirementsfil för sig, så att projektkolumnen säger varifrån
    # paketet kommer. Ett paket som båda drar in står under den första filen
    # (backenden), med prod om någon av dem behöver det i prod.
    pip: dict[str, Paket] = {}
    saknade: set[str] = set()
    for fil, allt_dev in PIP_KRAV:
        projekt = fil.split("/", 1)[0]
        hittade, fattas = las_pip(lasa_krav(ROT / fil, allt_dev), projekt)
        saknade.update(fattas)
        for p in hittade:
            nyckel = _norm_namn(p.namn)
            tidigare = pip.get(nyckel)
            if tidigare is None:
                pip[nyckel] = p
            elif p.prod and not tidigare.prod:
                pip[nyckel] = replace(tidigare, prod=True)
    paket += pip.values()
    return sorterade(paket), sorted(saknade)


def sorterade(paket: list[Paket]) -> list[Paket]:
    return sorted(paket, key=lambda p: (p.ekosystem, p.projekt, p.namn.lower(), p.version))


# --------------------------------------------------------------------------
# Vitlistan


def _versionstupel(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:4])


def version_matchar(version: str, spec: str) -> bool:
    """'*', exakt '1.2.3', eller kommaseparerade jämförelser '>=1.3,<2'."""
    spec = spec.strip()
    if spec in ("", "*"):
        return True
    if not re.match(r"^[<>=!]", spec):
        return version == spec
    v = _versionstupel(version)
    for del_ in spec.split(","):
        m = re.match(r"^\s*(>=|<=|==|!=|>|<)\s*(.+?)\s*$", del_)
        if not m:
            return False
        op, mal = m.group(1), _versionstupel(m.group(2))
        ok = {
            ">=": v >= mal, "<=": v <= mal, ">": v > mal, "<": v < mal,
            "==": v == mal, "!=": v != mal,
        }[op]
        if not ok:
            return False
    return True


def las_vitlista(sokvag: Path = VITLISTA) -> list[dict]:
    if not sokvag.exists():
        return []
    data = json.loads(sokvag.read_text(encoding="utf-8"))
    poster = data.get("undantag", [])
    for i, post in enumerate(poster):
        for falt in ("ekosystem", "paket", "version", "licens", "motivering"):
            if not str(post.get(falt, "")).strip():
                raise SystemExit(f"{sokvag}: undantag {i} saknar fältet '{falt}'")
    return poster


def undantag_for(p: Paket, vitlista: list[dict]) -> dict | None:
    for post in vitlista:
        if (
            post["ekosystem"] == p.ekosystem
            and post["paket"] == p.namn
            and post["licens"] == p.licens
            and version_matchar(p.version, post["version"])
        ):
            return post
    return None


def ar_obeslutad(post: dict) -> bool:
    return not str(post.get("godkant_av", "")).strip()


# --------------------------------------------------------------------------
# Utskrift


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def rendera(paket: list[Paket], vitlista: list[dict], saknade: list[str], datum: str) -> str:
    antal: dict[str, int] = {}
    for p in paket:
        antal[f"{p.ekosystem} ({p.projekt})"] = antal.get(f"{p.ekosystem} ({p.projekt})", 0) + 1
    rader = [
        "# Licensförteckning över beroendena",
        "",
        "Genererad av `python scripts/licenser.py --skriv`. Redigera inte för hand:",
        "kör skriptet igen. Grinden `python scripts/licenser.py --kontrollera` körs i",
        "CI (jobbet `licenser` i `.github/workflows/verify.yml`) och fäller på",
        "copyleft och okända licenser som inte står i",
        "[`licenser-vitlista.json`](licenser-vitlista.json). ISO 27001 A.5.32.",
        "",
        f"- Genererad: {datum}",
        f"- Python-miljö: {platform.python_version()} ({sys.platform})",
        "- npm: läst ur lockfilerna `package-lock.json` (web) och",
        "  `support-webb/package-lock.json` (agentsajten). `marknad/video/` byggs",
        "  inte och är inte med.",
        "- pip: `snajp-support/requirements.txt` och `scripts/requirements-scripts.txt`",
        "  med alla transitiva beroenden, lästa ur de installerade paketens metadata.",
        "  Versionerna är de som var installerade där filen genererades; en lokal",
        "  miljö kan skilja sig från CI:s rena installation, och det är CI-körningen",
        "  som avgör grinden. `dev` för pip betyder testberoenden (raderna efter",
        "  `# test`) och driftskripten.",
        "",
        "Antal paket: " + ", ".join(f"{k}: {v}" for k, v in sorted(antal.items())) + ".",
        "",
    ]
    if saknade:
        rader += [
            "**Ofullständig miljö:** följande krav var inte installerade och saknas i",
            "förteckningen: " + ", ".join(f"`{s}`" for s in saknade) + ".",
            "",
        ]
    behov = [(p, undantag_for(p, vitlista)) for p in paket if p.klass != "tillatande"]
    rader += ["## Väntar på beslut eller är undantagna", ""]
    if not behov:
        rader += ["Inga paket med copyleft eller okänd licens.", ""]
    else:
        rader += [
            "Status `obeslutad` betyder att paketet står i vitlistan utan namn i",
            "`godkant_av`: grinden släpper igenom det, men licensen är inte beslutad.",
            "Bedömningen är ett underlag, inte ett beslut.",
            "",
            "| Ekosystem | Projekt | Paket | Version | Licens | Status | Motivering | Bedömning (underlag) |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for p, post in behov:
            if post is None:
                status, motiv, bed = "EJ GODKÄND (fäller CI)", "", ""
            else:
                status = "obeslutad" if ar_obeslutad(post) else f"godkänd av {post['godkant_av']}"
                motiv, bed = post["motivering"], post.get("bedomning", "")
            rader.append(
                f"| {p.ekosystem} | {p.projekt} | {_cell(p.namn)} | {_cell(p.version)} | "
                f"{_cell(p.licens)} | {status} | {_cell(motiv)} | {_cell(bed)} |"
            )
        rader.append("")
    rader += [
        "## Alla paket",
        "",
        "| Ekosystem | Projekt | Paket | Version | Licens | Källa | Prod/dev |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in paket:
        rader.append(
            f"| {p.ekosystem} | {p.projekt} | {_cell(p.namn)} | {_cell(p.version)} | "
            f"{_cell(p.licens)} | {p.kalla} | {'prod' if p.prod else 'dev'} |"
        )
    rader.append("")
    return "\n".join(rader)


def kontrollera(paket: list[Paket], vitlista: list[dict], saknade: list[str]) -> int:
    fel = 0
    if saknade:
        fel += 1
        print(
            "FEL: miljön saknar paket som requirements kräver: " + ", ".join(saknade)
            + "\n  Installera dem (pip install -r ...) så att förteckningen blir fullständig."
        )
    obeslutade = []
    for p in paket:
        if p.klass == "tillatande":
            continue
        post = undantag_for(p, vitlista)
        if post is None:
            fel += 1
            orsak = "copyleft" if p.klass == "copyleft" else "okänd eller saknad licens"
            print(f"FEL: {p.ekosystem} {p.projekt} {p.namn} {p.version}: {orsak} ({p.licens})")
        elif ar_obeslutad(post):
            obeslutade.append(p)
    anvanda = {id(undantag_for(p, vitlista)) for p in paket}
    for post in vitlista:
        if id(post) not in anvanda:
            print(
                f"Notis: undantaget {post['ekosystem']} {post['paket']} {post['version']} "
                f"({post['licens']}) matchar inget paket längre och kan strykas."
            )
    if obeslutade:
        print(f"Notis: {len(obeslutade)} paket står i vitlistan som obeslutade (godkant_av tomt).")
    if fel:
        print(
            "\nSå godkänns ett paket: lägg ett undantag i docs/compliance/licenser-vitlista.json"
            "\nmed ekosystem, paket, version (exakt, '*' eller t.ex. '>=1.3,<2'), licens (exakt"
            "\nsom ovan), motivering och godkant_av. Licensen ska bedömas av en människa"
            "\ninnan godkant_av fylls i; utan namn visas undantaget som obeslutat."
        )
        return 1
    print(f"OK: {len(paket)} paket, inga ej godkända licenser.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--skriv", action="store_true", help=f"skriv {UT.relative_to(ROT)}")
    ap.add_argument("--kontrollera", action="store_true", help="exit 1 vid ej godkänd licens")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows-konsolen är cp1252
    paket, saknade = samla()
    vitlista = las_vitlista()
    if args.skriv:
        text = rendera(paket, vitlista, saknade, dt.date.today().isoformat())
        UT.parent.mkdir(parents=True, exist_ok=True)
        UT.write_bytes(text.encode("utf-8"))
        print(f"Skrev {UT.relative_to(ROT)} ({len(paket)} paket)")
    if args.kontrollera:
        return kontrollera(paket, vitlista, saknade)
    if not args.skriv:
        sys.stdout.buffer.write(
            rendera(paket, vitlista, saknade, dt.date.today().isoformat()).encode("utf-8")
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
