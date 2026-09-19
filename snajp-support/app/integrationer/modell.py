"""Konfigurationen för en integration: HTTP-förfrågningar och MCP-servrar.

## Ebbot-kompatibel med flit

HTTP-delen tar SAMMA JSON som Ebbots `http_request`-verktyg (`requests`,
`name`, `description`, `method`, `url`, `headers`, `body`, `placeholders`,
`responsePath`), så att en kund som flyttar från Ebbot kan klistra in sin
konfiguration oförändrad. Varje förfrågan blir ett eget verktyg med namnet
`request_<name i snake_case>`, som hos dem.

## Våra tillägg, och varför

Platshållaren `{{nyckel}}` har tre NAMNRYMDER, och skillnaden mellan dem är
säkerhetsgränsen:

  {{hemlighet.x}}   Kundens API-nyckel, krypterad i vila. Sätts in av koden.
                    Modellen ser aldrig värdet, och svaret tvättas från det.
  {{kund.email}}    Kontextvärden ur ärendet (kund.email, kund.namn,
  {{arende.id}} …   kund.telefon, kund.id, arende.id, kanal, tenant.namn).
                    Sätts in av KODEN. En orderuppslagning bunden till
                    {{kund.email}} kan inte pratas över till någon annans
                    order, hur meddelandet än är formulerat.
  {{nyckel}}        Argument som MODELLEN fyller i, deklarerat i
                    `placeholders` (Ebbot-formen). Odeklarerade blir strängar.

Ebbots eget exempel låter modellen fylla i API-token som ett argument. Det
gör inte vi: en bar platshållare med samma namn som en sparad hemlighet
räknas som hemligheten, så en inklistrad Ebbot-konfig med `{{token}}` fungerar
— utan att modellen blir ombedd att hitta på en nyckel.

`skrivande` (sant som standard för allt utom GET) styr två saker: i
testchatten SIMULERAS skrivande anrop i stället för att skickas, och ett
ärende får högst ett skrivande anrop. En POST som bara söker markeras
`"skrivande": false`.

`handelser` binder en förfrågan till en händelse i stället för till modellen
(`arende_eskalerat` -> skapa ärendet i kundens Zendesk). Sådana förfrågningar
syns inte i modellens verktygslista, och alla deras platshållare måste gå att
fylla i av koden.

## Läs strikt

Till skillnad från regelinställningarna (support_regler: läs tolerant) är det
här konfiguration som leder till nätverksanrop. Ogiltigt avvisas när det
sparas, med ett svenskt besked om VAD som är fel — ett tyst standardvärde för
en URL finns inte.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

import jmespath
from jmespath.exceptions import JMESPathError
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .natvakt import NatvaktError, kontrollera_url

PLATSHALLARE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)\s*\}\}")

METODER = ("GET", "POST", "PUT", "PATCH", "DELETE")
TYPER = ("string", "number", "integer", "boolean", "object", "array")

#: Kontextvärden koden fyller i ur ärendet. Utökas här — ingen annanstans.
KONTEXTNAMN = (
    "kund.email",
    "kund.namn",
    "kund.telefon",
    "kund.id",
    "arende.id",
    "arende.kategori",
    "kanal",
    "tenant.namn",
)

#: Händelser en förfrågan kan bindas till, och vilka `handelse.*`-värden
#: koden fyller i för var och en. Dokumentationen till kunden läser härifrån.
HANDELSER: dict[str, tuple[str, ...]] = {
    "arende_eskalerat": (
        "handelse.orsak",
        "handelse.orsakskod",
        "handelse.samtal",
        "handelse.meddelanden",
        "handelse.senaste_meddelande",
        "handelse.arendelank",
        "handelse.tidpunkt",
    ),
}

HEMLIGHET_PREFIX = "hemlighet."
_RESERVERADE_PREFIX = ("hemlighet", "kund", "arende", "tenant", "handelse", "kanal")


class KonfigFel(ValueError):
    """Konfigurationen går inte att använda. Meddelandet är till admin."""


def slug(text: str, *, max_langd: int = 48) -> str:
    """"Sök order (v2)" -> "sok_order_v2". Samma form som Ebbots verktygsnamn."""
    ascii_ = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    ren = re.sub(r"[^a-z0-9]+", "_", ascii_.lower()).strip("_")
    return (ren or "verktyg")[:max_langd].rstrip("_")


def platshallare_i(varde: Any) -> set[str]:
    """Alla platshållarnamn i en sträng eller JSON-struktur (även i nycklar)."""
    hittade: set[str] = set()
    if isinstance(varde, str):
        hittade.update(PLATSHALLARE.findall(varde))
    elif isinstance(varde, dict):
        for k, v in varde.items():
            hittade |= platshallare_i(str(k))
            hittade |= platshallare_i(v)
    elif isinstance(varde, list):
        for v in varde:
            hittade |= platshallare_i(v)
    return hittade


def ar_hemlighet(namn: str) -> bool:
    return namn.startswith(HEMLIGHET_PREFIX)


def ar_kontext(namn: str) -> bool:
    return namn in KONTEXTNAMN or namn.startswith("handelse.")


class Platshallare(BaseModel):
    """Ett argument modellen fyller i. Ebbots fält + `enum` (vårt tillägg)."""

    model_config = ConfigDict(extra="ignore")

    key: str = Field(min_length=1, max_length=40)
    type: Literal["string", "number", "integer", "boolean", "object", "array"] = "string"
    description: str = Field(default="", max_length=400)
    default: Any = None
    enum: list[str | int | float] | None = None

    @field_validator("key")
    @classmethod
    def _nyckel(cls, v: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v):
            raise ValueError(f"Platshållaren {v!r} får bara innehålla bokstäver, siffror och _.")
        if v.split("_", 1)[0].lower() in _RESERVERADE_PREFIX and "." in v:
            raise ValueError(f"{v!r} krockar med en reserverad namnrymd.")
        return v

    @property
    def kravs(self) -> bool:
        return self.default is None


class HttpForfragan(BaseModel):
    """En förfrågan i Ebbots `requests`-array, plus `skrivande`."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str = Field(min_length=1, max_length=60)
    description: str = Field(default="", max_length=800)
    method: str = "GET"
    url: str = Field(min_length=8, max_length=2000)
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any = None
    placeholders: list[Platshallare] = Field(default_factory=list)
    responsePath: str | None = Field(default=None, max_length=300)
    skrivande: bool | None = None

    @field_validator("method")
    @classmethod
    def _metod(cls, v: str) -> str:
        v = (v or "GET").upper().strip()
        if v not in METODER:
            raise ValueError(f"Metoden {v!r} stöds inte. Tillåtna: {', '.join(METODER)}.")
        return v

    @field_validator("responsePath")
    @classmethod
    def _svarsvag(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        try:
            jmespath.compile(v)
        except JMESPathError as fel:
            raise ValueError(f"responsePath {v!r} är inte ett giltigt JMESPath-uttryck.") from fel
        return v.strip()

    @field_validator("headers")
    @classmethod
    def _rubriker(cls, v: dict[str, str]) -> dict[str, str]:
        for namn, varde in v.items():
            if not re.fullmatch(r"[A-Za-z0-9!#$%&'*+.^_`|~-]+", namn or ""):
                raise ValueError(f"Rubriknamnet {namn!r} är ogiltigt.")
            if "\n" in str(varde) or "\r" in str(varde):
                raise ValueError(f"Rubriken {namn!r} innehåller en radbrytning.")
        return v

    @model_validator(mode="after")
    def _url_och_platshallare(self) -> HttpForfragan:
        url = self.url.strip()
        if not url.lower().startswith("https://"):
            raise ValueError(f"{self.name}: bara https-adresser är tillåtna.")
        self.url = url
        # Värddelen: bara hemligheter och kontext får stå där. Ett argument
        # från modellen i värdnamnet vore att låta meddelandet välja server.
        vardel = url[len("https://"):].split("/", 1)[0].split("?", 1)[0]
        for namn in PLATSHALLARE.findall(vardel):
            if not (ar_hemlighet(namn) or ar_kontext(namn)):
                raise ValueError(
                    f"{self.name}: platshållaren {{{{{namn}}}}} står i värdnamnet. Där får "
                    "bara {{hemlighet.x}} stå — modellens argument hör hemma i sökvägen."
                )
        if not PLATSHALLARE.search(vardel):
            try:
                kontrollera_url(PLATSHALLARE.sub("x", url))
            except NatvaktError as fel:
                raise ValueError(f"{self.name}: {fel}") from fel
        nycklar = [p.key for p in self.placeholders]
        if len(nycklar) != len(set(nycklar)):
            raise ValueError(f"{self.name}: två platshållare har samma key.")
        if self.method == "GET" and self.body not in (None, "", {}):
            raise ValueError(f"{self.name}: en GET-förfrågan kan inte ha en body.")
        return self

    @property
    def verktygsnamn(self) -> str:
        return f"request_{slug(self.name)}"

    @property
    def ar_skrivande(self) -> bool:
        return self.method != "GET" if self.skrivande is None else self.skrivande

    def anvanda_namn(self) -> set[str]:
        """Varje platshållarnamn förfrågan använder, i url/rubriker/kropp."""
        return (
            platshallare_i(self.url)
            | platshallare_i(self.headers)
            | platshallare_i(self.body)
        )

    def argument(self, hemlighetsnamn: set[str] | frozenset[str] = frozenset()) -> list[Platshallare]:
        """Argumenten MODELLEN ska fylla i.

        Deklarerade platshållare först (i deklarationsordning), sedan
        odeklarerade som strängar — Ebbot-beteendet. En bar platshållare med
        samma namn som en sparad hemlighet är hemligheten, inte ett argument.
        """
        anvanda = self.anvanda_namn()
        ut: list[Platshallare] = [
            p for p in self.placeholders if p.key not in hemlighetsnamn and p.key in anvanda
        ]
        deklarerade = {p.key for p in self.placeholders}
        for namn in sorted(anvanda):
            if "." in namn or namn in deklarerade or namn in hemlighetsnamn or namn == "kanal":
                continue
            ut.append(Platshallare(key=namn))
        return ut

    def hemligheter(self, hemlighetsnamn: set[str] | frozenset[str] = frozenset()) -> set[str]:
        """Namnen på hemligheterna förfrågan behöver (utan prefixet)."""
        ut = set()
        for namn in self.anvanda_namn():
            if ar_hemlighet(namn):
                ut.add(namn[len(HEMLIGHET_PREFIX):])
            elif "." not in namn and namn in hemlighetsnamn:
                ut.add(namn)
        return ut

    def json_schema(self, hemlighetsnamn: set[str] | frozenset[str] = frozenset()) -> dict[str, Any]:
        egenskaper: dict[str, Any] = {}
        kravda: list[str] = []
        for p in self.argument(hemlighetsnamn):
            schema: dict[str, Any] = {"type": p.type}
            if p.description:
                schema["description"] = p.description
            if p.enum:
                schema["enum"] = p.enum
            if p.default is not None:
                schema["default"] = p.default
            else:
                kravda.append(p.key)
            egenskaper[p.key] = schema
        return {
            "type": "object",
            "properties": egenskaper,
            "required": kravda,
            "additionalProperties": False,
        }


class HttpKonfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    requests: list[HttpForfragan] = Field(min_length=1, max_length=25)
    #: händelse -> förfrågans `name`. Se HANDELSER.
    handelser: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _unika_och_handelser(self) -> HttpKonfig:
        namn = [r.verktygsnamn for r in self.requests]
        dubbletter = sorted({n for n in namn if namn.count(n) > 1})
        if dubbletter:
            raise ValueError(
                f"Två förfrågningar får samma verktygsnamn ({', '.join(dubbletter)}). "
                "Byt namn på den ena."
            )
        per_namn = {r.name: r for r in self.requests}
        for handelse, forfragan_namn in self.handelser.items():
            if handelse not in HANDELSER:
                raise ValueError(
                    f"Okänd händelse {handelse!r}. Tillåtna: {', '.join(HANDELSER)}."
                )
            forfragan = per_namn.get(forfragan_namn)
            if forfragan is None:
                raise ValueError(f"Händelsen {handelse} pekar på {forfragan_namn!r}, som inte finns.")
            tillatna = set(KONTEXTNAMN) | set(HANDELSER[handelse])
            for p in forfragan.anvanda_namn():
                if ar_hemlighet(p) or p in tillatna:
                    continue
                deklarerad = next((x for x in forfragan.placeholders if x.key == p), None)
                if deklarerad is None or deklarerad.default is None:
                    raise ValueError(
                        f"{forfragan.name}: {{{{{p}}}}} kan inte fyllas i vid händelsen "
                        f"{handelse} — ingen modell väljer argument där. Använd "
                        f"{', '.join('{{' + h + '}}' for h in HANDELSER[handelse][:3])} …, "
                        "eller ge platshållaren ett default."
                    )
        return self

    def verktygsforfragningar(self) -> list[HttpForfragan]:
        """Förfrågningarna modellen får välja bland (inte händelsebundna)."""
        bundna = set(self.handelser.values())
        return [r for r in self.requests if r.name not in bundna]

    def hemligheter(self, hemlighetsnamn: set[str] | frozenset[str] = frozenset()) -> set[str]:
        ut: set[str] = set()
        for r in self.requests:
            ut |= r.hemligheter(hemlighetsnamn)
        return ut


class McpKonfig(BaseModel):
    """En fjärr-MCP-server. Fälten följer Ebbots MCP-konfiguration.

    Bara fjärrtransporter (Streamable HTTP, och SSE för äldre servrar). En
    stdio-server vore ett kommando på VÅR maskin som kunden väljer — det
    finns inte, oavsett hur konfigurationen ser ut.
    """

    model_config = ConfigDict(extra="ignore")

    url: str = Field(min_length=8, max_length=2000)
    transport: Literal["streamable_http", "sse"] = "streamable_http"
    #: Rubriken som bär hemligheten `auth` (Ebbots "Auth Header Name").
    #: Värdet skickas som det är sparat — "Bearer abc…" om servern vill det.
    auth_header_name: str = Field(default="Authorization", max_length=80)
    #: Övriga statiska rubriker; får referera {{hemlighet.x}}.
    headers: dict[str, str] = Field(default_factory=dict)
    #: Tom = alla verktyg servern erbjuder, utom de den själv märker som
    #: destruktiva (Ebbots beteende, med den skärpningen). Satt = bara dessa.
    tillatna_verktyg: list[str] = Field(default_factory=list, max_length=100)
    #: Verktyg som ändrar något hos kunden. Simuleras i testchatten och
    #: räknas mot taket på ett skrivande anrop per ärende. Verktyg som servern
    #: själv inte märker som readOnlyHint räknas också hit.
    skrivande_verktyg: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("url")
    @classmethod
    def _url(cls, v: str) -> str:
        v = v.strip()
        if PLATSHALLARE.search(v):
            raise ValueError("MCP-adressen får inte innehålla platshållare.")
        try:
            kontrollera_url(v)
        except NatvaktError as fel:
            raise ValueError(str(fel)) from fel
        return v

    @field_validator("auth_header_name")
    @classmethod
    def _auth_rubrik(cls, v: str) -> str:
        v = (v or "Authorization").strip()
        if not re.fullmatch(r"[A-Za-z0-9!#$%&'*+.^_`|~-]+", v):
            raise ValueError(f"Rubriknamnet {v!r} är ogiltigt.")
        return v

    def hemligheter(self, hemlighetsnamn: set[str] | frozenset[str] = frozenset()) -> set[str]:
        ut = {n[len(HEMLIGHET_PREFIX):] for n in platshallare_i(self.headers) if ar_hemlighet(n)}
        return ut


Typ = Literal["http", "mcp"]


def las_konfig(typ: str, konfig: dict[str, Any]) -> HttpKonfig | McpKonfig:
    """Strikt: kastar KonfigFel med ett begripligt svenskt besked."""
    from pydantic import ValidationError

    try:
        if typ == "http":
            return HttpKonfig.model_validate(konfig)
        if typ == "mcp":
            return McpKonfig.model_validate(konfig)
    except ValidationError as fel:
        raise KonfigFel(_beskriv_valideringsfel(fel)) from fel
    raise KonfigFel(f"Okänd integrationstyp {typ!r}. Tillåtna: http, mcp.")


def _beskriv_valideringsfel(fel: Any) -> str:
    rader = []
    for e in fel.errors()[:5]:
        plats = ".".join(str(x) for x in e.get("loc", ()) if x != "__root__")
        meddelande = str(e.get("msg", "")).removeprefix("Value error, ")
        rader.append(f"{plats}: {meddelande}" if plats else meddelande)
    return "; ".join(rader) or "Ogiltig konfiguration."


def saknade_hemligheter(
    typ: str, konfig: HttpKonfig | McpKonfig, hemlighetsnamn: set[str]
) -> list[str]:
    """Hemligheter konfigurationen refererar men som inte är sparade."""
    behovs = konfig.hemligheter(hemlighetsnamn)
    if typ == "mcp":
        # `auth` är valfri för MCP (en öppen server behöver ingen).
        behovs.discard("auth")
    return sorted(behovs - set(hemlighetsnamn))
