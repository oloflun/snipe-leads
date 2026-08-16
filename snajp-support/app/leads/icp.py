"""Målgruppsstyrning (ICP) — vem agenten får kontakta.

Gränsen mot SOUL hålls hård och skrivs ut i UI:t: **SOUL styr ton, ICP styr
urval.** Två fält, två syften. Att blanda dem hade betytt att en kund som
vill ändra vilka bolag agenten letar efter i stället skriver om hur den låter.

ICP är STRUKTURERAD data. Den går aldrig in som fri text i en prompt utan
wrappas som allt annat kundskrivet (`wrap_untrusted_content`, INV-SEC-009) —
fälten är kundskrivna och en `must_have`-rad är en lika bra injektionsyta som
en SOUL-rad.

## Två funktioner, två stränghetsgrader — och varför

`normalize_icp` är FÖRLÅTANDE och används på LÄSVÄGEN. Den möter data som
redan ligger i databasen, kanske skriven av en äldre version av det här
schemat. En läsning som kastar hade gjort en gammal rad till ett trasigt UI,
och kunden hade inte kunnat rätta den eftersom sidan som visar formuläret är
just den som kraschar.

`validate_icp` är STRIKT och används på SKRIVVÄGEN (`PUT /api/leads/config`
→ 422). Där finns en människa som kan rätta felet, och ett tyst tillrättalagt
värde är farligare än ett felmeddelande: ett ICP som tyst tappar sitt
geografiska filter blir "alla företag i Sverige", vilket är exakt det utfall
DEL 1.1 förbjuder.

Okända nycklar tas bort i `normalize_icp` men ger INTE fel i `validate_icp`.
Det är medvetet och får inte ändras: den tysta borttagningen är det verifierade
skyddet mot insmugglade `system_prompt`-nycklar, och att i stället svara 422
hade berättat för en angripare exakt vilken nyckel som filtrerades bort.
"""

from __future__ import annotations

from typing import Any

from .geo import OkandRegionError, beskriv_region, kanda_regioner
from .sni import OgiltigSniKodError, beskriv_kod, normalisera_kod, validera_kod
from .untrusted_content import wrap_untrusted_content

#: Fritextfälten och deras form. En okänd nyckel tas bort i stället för att
#: kastas vidare — annars blir varje stavfel i frontend en tyst prompt-injektion.
LIST_FIELDS = (
    "industries",
    "exclude_industries",
    "geography",
    "roles",
    "must_have",
    "deal_breakers",
)

#: Strukturerade listfält (DEL 1.1). Skilda från LIST_FIELDS eftersom de
#: valideras mot ett format i stället för bara kapas.
GEO_FIELD = "geo"
SNI_FIELDS = ("sni_codes", "exclude_sni")
DOMAIN_FIELD = "exclude_domains"

MAX_ITEMS_PER_FIELD = 25
MAX_CHARS_PER_ITEM = 200

#: "Småföretag" enligt EU:s definition är 1–49 anställda. Det här är den
#: default UI:t och ICP-profilerna (`app/leads/profiles/`) FÖRIFYLLER med.
#:
#: Den appliceras medvetet INTE inne i `normalize_icp`. Två skäl:
#:
#:  1. Normaliseringen måste vara idempotent — `normalize_icp(normalize_icp(x))`
#:     ska ge samma sak. En default som fylls i vid varje passage gör ett tomt
#:     ICP till ett filtrerande ICP bara genom att läsas, och `render_icp` hade
#:     börjat skriva ut ett storleksavsnitt som ingen kund valt.
#:  2. Ett tyst påtvingat storleksfilter smalnar av urvalet utan att någon
#:     bestämt det. Defaults hör hemma där någon kan se dem och ändra dem.
SMAFORETAG_ANSTALLDA: tuple[int, int] = (1, 49)

#: Hårt tak per körning. Defaulten är ekonomisk (varje prospekt är åtta
#: LLM-anrop) och taket är en spärr mot att någon skriver in 10 000 i ett
#: formulär och startar en körning som kostar mer än kundens månadsavgift.
DEFAULT_MAX_PROSPECTS = 25
MAX_PROSPECTS_TAK = 100


class IcpValidationError(ValueError):
    """Ett ICP som inte går att spara. Meddelandet går rakt ut till kunden i
    ett 422 och ska därför vara begripligt på svenska utan att avslöja
    interna fältnamn mer än nödvändigt."""


def empty_size() -> dict[str, Any]:
    return {
        "anstallda_min": None,
        "anstallda_max": None,
        "omsattning_min": None,
        "omsattning_max": None,
    }


def empty_icp() -> dict[str, Any]:
    return (
        {field: [] for field in LIST_FIELDS}
        | {"company_size": {"min": None, "max": None}}
        | {GEO_FIELD: [], "sni_codes": [], "exclude_sni": [], DOMAIN_FIELD: []}
        | {"size": empty_size(), "max_prospects_per_run": DEFAULT_MAX_PROSPECTS}
    )


# -- Läsvägen: förlåtande ---------------------------------------------------


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

    # Regioner: okända nycklar tystas bort här (läsvägen), men fälls i
    # validate_icp (skrivvägen). En sparad region som vi senare tagit bort ur
    # geo.py ska inte göra kundens inställningssida omöjlig att öppna.
    kanda = set(kanda_regioner())
    geo_raw = raw.get(GEO_FIELD)
    if isinstance(geo_raw, list):
        icp[GEO_FIELD] = [
            str(v).strip()
            for v in geo_raw[:MAX_ITEMS_PER_FIELD]
            if str(v).strip() in kanda
        ]

    for field in SNI_FIELDS:
        values = raw.get(field)
        if not isinstance(values, list):
            continue
        koder: list[str] = []
        for value in values[:MAX_ITEMS_PER_FIELD]:
            kod = normalisera_kod(value)
            if kod and kod not in koder:
                koder.append(kod)
        icp[field] = koder

    domains = raw.get(DOMAIN_FIELD)
    if isinstance(domains, list):
        icp[DOMAIN_FIELD] = [
            rensad
            for rensad in (_normalize_domain(v) for v in domains[:MAX_ITEMS_PER_FIELD])
            if rensad
        ]

    icp["size"] = _normalize_size(raw.get("size"), company_size=icp["company_size"])

    # company_size speglas ur size så att båda alltid säger samma sak. Det
    # gamla fältet är kvar för det befintliga UI:t; det nya är det som
    # källorna och scoringen läser. Två fält som kan säga emot varandra hade
    # varit ett filter vars utfall beror på vem som läser det.
    icp["company_size"] = {
        "min": icp["size"]["anstallda_min"],
        "max": icp["size"]["anstallda_max"],
    }

    icp["max_prospects_per_run"] = _normalize_tak(raw.get("max_prospects_per_run"))

    return icp


def _normalize_size(raw: object, *, company_size: dict[str, Any]) -> dict[str, Any]:
    size = empty_size()

    # Det gamla fältet är utgångsläget, så en kund som bara fyllt i
    # company_size inte tappar sitt storleksfilter när size införs.
    size["anstallda_min"] = company_size.get("min")
    size["anstallda_max"] = company_size.get("max")

    if not isinstance(raw, dict):
        return size

    for nyckel in size:
        if nyckel in raw:
            size[nyckel] = _as_positive_int(raw.get(nyckel))

    return size


def _normalize_tak(raw: object) -> int:
    tak = _as_positive_int(raw)
    if tak is None or tak < 1:
        return DEFAULT_MAX_PROSPECTS
    return min(tak, MAX_PROSPECTS_TAK)


def _normalize_domain(raw: object) -> str:
    """'https://www.Exempel.se/kontakt' → 'exempel.se'.

    Kunder klistrar in URL:er, inte domäner. Att kräva ren domän hade betytt
    att uteslutningslistan tyst inte matchade någonting, vilket är den
    farligaste sortens fel i ett NEGATIVT filter — den kund man ville undanta
    får mejlet ändå.
    """
    text = str(raw or "").strip().lower()
    if not text:
        return ""
    for prefix in ("https://", "http://"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    text = text.split("/", 1)[0].split("?", 1)[0].split("@")[-1]
    if text.startswith("www."):
        text = text[4:]
    return text.strip(".")[:MAX_CHARS_PER_ITEM]


def _as_positive_int(value: object) -> int | None:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def is_empty(icp: dict[str, Any]) -> bool:
    if any(icp.get(field) for field in LIST_FIELDS):
        return False
    if icp.get(GEO_FIELD) or icp.get("sni_codes") or icp.get("exclude_sni"):
        return False
    if icp.get(DOMAIN_FIELD):
        return False
    size = icp.get("size") or {}
    if any(size.get(nyckel) is not None for nyckel in empty_size()):
        return False
    legacy = icp.get("company_size") or {}
    return legacy.get("min") is None and legacy.get("max") is None


# -- Skrivvägen: strikt -----------------------------------------------------


def validate_icp(raw: object) -> dict[str, Any]:
    """Validerar och returnerar ett normaliserat ICP, eller höjer.

    Anropas av `PUT /api/leads/config`, som översätter felet till 422. Se
    modulens docstring om varför skrivvägen är strängare än läsvägen.
    """
    if raw is None:
        return empty_icp()
    if not isinstance(raw, dict):
        raise IcpValidationError(
            "Målgruppen måste vara ett objekt med fält, inte ett ensamt värde."
        )

    for field in (*LIST_FIELDS, GEO_FIELD, *SNI_FIELDS, DOMAIN_FIELD):
        if field in raw and not isinstance(raw[field], list):
            raise IcpValidationError(f"Fältet {field!r} måste vara en lista.")

    # Regioner — okänd nyckel fälls här, till skillnad från på läsvägen.
    for nyckel in raw.get(GEO_FIELD) or []:
        try:
            beskriv_region(str(nyckel).strip())
        except OkandRegionError as error:
            raise IcpValidationError(str(error)) from None

    for field in SNI_FIELDS:
        for kod in raw.get(field) or []:
            try:
                validera_kod(kod)
            except OgiltigSniKodError as error:
                raise IcpValidationError(str(error)) from None

    for domain in raw.get(DOMAIN_FIELD) or []:
        rensad = _normalize_domain(domain)
        if not rensad or "." not in rensad:
            raise IcpValidationError(
                f"{domain!r} ser inte ut som en domän. Skriv den som exempel.se "
                "(en hel webbadress går också bra)."
            )

    _validera_size(raw.get("size"))
    _validera_company_size(raw.get("company_size"))
    _validera_tak(raw.get("max_prospects_per_run"))

    return normalize_icp(raw)


def _validera_size(raw: object) -> None:
    if raw is None:
        return
    if not isinstance(raw, dict):
        raise IcpValidationError("Storleksfältet måste vara ett objekt.")

    tal: dict[str, int | None] = {}
    for nyckel in empty_size():
        if nyckel not in raw or raw[nyckel] is None:
            tal[nyckel] = None
            continue
        värde = _as_positive_int(raw[nyckel])
        if värde is None:
            raise IcpValidationError(
                f"{nyckel.replace('_', ' ')} måste vara ett heltal som är noll eller större."
            )
        tal[nyckel] = värde

    _kolla_intervall(
        tal["anstallda_min"], tal["anstallda_max"], "Antal anställda", enhet="anställda"
    )
    _kolla_intervall(tal["omsattning_min"], tal["omsattning_max"], "Omsättningen", enhet="kr")


def _validera_company_size(raw: object) -> None:
    if raw is None:
        return
    if not isinstance(raw, dict):
        raise IcpValidationError("Bolagsstorleken måste vara ett objekt.")
    låg = _as_positive_int(raw.get("min")) if raw.get("min") is not None else None
    hög = _as_positive_int(raw.get("max")) if raw.get("max") is not None else None
    if raw.get("min") is not None and låg is None:
        raise IcpValidationError("Minsta bolagsstorlek måste vara ett heltal, noll eller större.")
    if raw.get("max") is not None and hög is None:
        raise IcpValidationError("Största bolagsstorlek måste vara ett heltal, noll eller större.")
    _kolla_intervall(låg, hög, "Bolagsstorleken", enhet="anställda")


def _kolla_intervall(låg: int | None, hög: int | None, etikett: str, *, enhet: str) -> None:
    if låg is not None and hög is not None and låg > hög:
        raise IcpValidationError(
            f"{etikett}: undre gränsen ({låg} {enhet}) är högre än den övre ({hög} {enhet})."
        )


def _validera_tak(raw: object) -> None:
    if raw is None:
        return
    tak = _as_positive_int(raw)
    if tak is None or tak < 1:
        raise IcpValidationError(
            "Taket för antal prospekt per körning måste vara minst 1."
        )
    if tak > MAX_PROSPECTS_TAK:
        raise IcpValidationError(
            f"Taket för antal prospekt per körning är högst {MAX_PROSPECTS_TAK}. "
            "Varje prospekt kostar åtta LLM-anrop — dela upp körningen i stället."
        )


# -- Rendering till kontextpaketet ------------------------------------------


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

    if icp[GEO_FIELD]:
        lines.append(
            "- Geografiskt område: " + "; ".join(beskriv_region(n) for n in icp[GEO_FIELD])
        )

    if icp["sni_codes"]:
        lines.append("- Branschkoder (SNI): " + "; ".join(beskriv_kod(k) for k in icp["sni_codes"]))
    if icp["exclude_sni"]:
        lines.append(
            "- Branschkoder att UNDANTA: " + "; ".join(beskriv_kod(k) for k in icp["exclude_sni"])
        )

    size = icp["size"]
    if size["anstallda_min"] is not None or size["anstallda_max"] is not None:
        lines.append(
            f"- Antal anställda: {_intervall(size['anstallda_min'], size['anstallda_max'])}"
        )
    if size["omsattning_min"] is not None or size["omsattning_max"] is not None:
        lines.append(
            "- Omsättning (SEK): "
            + _intervall(size["omsattning_min"], size["omsattning_max"])
        )

    if icp[DOMAIN_FIELD]:
        lines.append("- Domäner att aldrig kontakta: " + ", ".join(icp[DOMAIN_FIELD]))

    body = "\n".join(lines)

    # Kundskrivet innehåll, alltså wrappat. Samma behandling som SOUL får:
    # texten är data att ta hänsyn till, aldrig instruktioner att lyda.
    return (
        "## MÅLGRUPP (ICP)\n"
        "Urvalskriterier som kunden satt. Diskvalificera mot dessa INNAN du "
        "räknar icp_fit.\n\n" + wrap_untrusted_content(body, source="kundens ICP-konfiguration")
    )


def _intervall(låg: object, hög: object) -> str:
    return f"{låg if låg is not None else '—'}–{hög if hög is not None else '—'}"
