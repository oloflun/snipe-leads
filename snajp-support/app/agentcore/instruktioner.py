"""Instruktionslagren som faktiskt når modellen — och beviset på vilka de var.

## Vad som var fel innan

`agent_configs.instructions_md` och `.tone` har funnits sedan migration 010
utan att någon läst dem. En kund kunde ändra sina instruktioner och få exakt
samma svar, eftersom texten aldrig lämnade databasen. Den här modulen är
läsvägen som saknades.

## Skiktordningen, och varför den ser ut så

    1. GLOBAL      DB (agent_global_instructions) → annars agent-core/AGENTS.md
    2. skill       vendorad metodik (agent-core/skills/)
    3. overlay     agent-core/overlays/<namn>.md
    4. KUND        agent_configs.instructions_md
    5. kontrakt    sätts av kod, kan inte nås av något lager ovanför

Mest generellt först, mest specifikt sist, och "senare vinner vid konflikt"
sagt uttryckligen i avgränsartexten. Kundlagret ligger EFTER overlayen därför
att det är det mest specifika av våra lager: en overlay gäller ett steg för
alla kunder, kundinstruktionen gäller alla steg för en kund, och den som
skriver den senare vill att den ska ta.

## Varför kundlagret ligger i SYSTEMposition

Därför att det är VÅR text. Fältet är admin-only — det redigeras från
/admin/kunder/<slug>, aldrig från kundens egna inställningar. Kundskriven text
(SOUL, affärskontext, kunskapsbas) ligger kvar i USERposition, wrappad som
opålitligt innehåll.

Gränsen går alltså vid VEM SOM SKREV texten, inte vid vad den handlar om. Det
är hela INV-SEC-009: en kund ska kunna be om en ton och ska inte kunna be om
att reglerna ignoreras, och den enda robusta skillnaden mellan de två är
positionen i meddelandekedjan. Flyttar någon det här fältet till kundens yta
måste det samtidigt flyttas till USERposition. De två besluten är ETT beslut.

## Varför hashen finns

`agent_runs.pack_version` ska kunna svara på "vilken text läste den här
körningen?" (INV-AUDIT-001). Instruktionerna är nu fritt redigerbara i drift,
alltså kan versionen inte längre härledas ur git. Hashen räknas därför ur den
faktiskt använda texten, per körning.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .overlays import load_global_instructions as load_global_instructions_fil

#: Tak per lager. Instruktioner är inte en kunskapsbas: allt som ligger här
#: betalas i varje LLM-anrop, i varje steg, för varje ärende. En playbook med
#: åtta steg betalar taket åtta gånger.
#:
#: Talet är satt efter vad AGENTS.md faktiskt är (~4 500 tecken i dag) med
#: rejäl marginal. Kapning är medvetet TYST i läsvägen och HÖGLJUDD i
#: skrivvägen (api/admin.py validerar innan sparning) — en körning ska inte
#: falla på ett dokument någon råkade klistra in för mycket i.
MAX_TECKEN = 12_000

_GLOBAL_OPEN = """## GLOBALA REGLER (Snajp — gäller varje steg, varje kund)
Dessa gäller ÖVER skillen nedan där de krockar. De är policy, inte stil.
"""
_GLOBAL_CLOSE = "## SLUT GLOBALA REGLER"

_KUND_OPEN = """## KUNDSPECIFIKA INSTRUKTIONER ({tenant})
Dessa kommer FRÅN OSS och gäller för just den här kunden. De gäller ÖVER både
skillen och overlayen där de krockar, men ALDRIG över de globala reglerna ovan
och aldrig över kodgrindarna — grindarna körs efter dig och läser inte det du
skriver om dem.
"""
_KUND_CLOSE = "## SLUT KUNDSPECIFIKA INSTRUKTIONER"


@dataclass(frozen=True)
class Instruktionslager:
    """Den upplösta instruktionskedjan för EN körning.

    Frozen och färdigrenderad: hämtas en gång per körning och skickas ner till
    varje steg. Alternativet — att varje steg läser databasen själv — hade gett
    åtta läsningar per ärende och, värre, möjligheten att ett sparande mitt i
    en körning gör att steg 1 och steg 8 läste olika instruktioner. En körning
    ska ha EN uppsättning.
    """

    global_md: str
    kund_md: str
    tenant_namn: str = ""
    #: True när global_md kommer ur agent-core/AGENTS.md därför att ingen aktiv
    #: rad fanns i databasen. Går till spårvyn: "ingen har skrivit några
    #: instruktioner" och "instruktionerna nådde inte fram" ser annars likadana ut.
    global_fran_fil: bool = True

    @property
    def global_block(self) -> str:
        if not self.global_md:
            return ""
        return f"{_GLOBAL_OPEN}\n{self.global_md}\n{_GLOBAL_CLOSE}"

    @property
    def kund_block(self) -> str:
        if not self.kund_md:
            return ""
        oppning = _KUND_OPEN.format(tenant=self.tenant_namn or "den här kunden")
        return f"{oppning}\n{self.kund_md}\n{_KUND_CLOSE}"

    @property
    def hash(self) -> str:
        """Ur den FAKTISKT ANVÄNDA texten, inte ur radens id.

        Ett id säger vilken rad som lästes men inte vad som stod i den, och
        raden går att redigera. Två körningar med samma hash läste bevisligen
        samma text.
        """
        underlag = f"{self.global_md}\x00{self.kund_md}".encode("utf-8")
        return hashlib.sha256(underlag).hexdigest()


def _kapa(text: str | None) -> str:
    return (text or "").strip()[:MAX_TECKEN]


async def las_instruktioner(
    storage,
    tenant_id: str | None = None,
    *,
    agent_type: str = "support",
    tenant_namn: str = "",
) -> Instruktionslager:
    """Hämtar båda lagren. Felar aldrig — en trasig läsning ger ett tunnare
    lager, inte ett dött ärende.

    Toleransen är avsiktligt asymmetrisk och speglar
    overlays.load_global_instructions: ett saknat policylager ska inte fälla
    varje agentanrop, medan en saknad SKILL måste fälla steget (ett steg utan
    sin skill utför inte steget alls). Skillnaden är om lagret bär METODIKEN
    eller bara skärper den.
    """
    global_md = ""
    fran_fil = True
    try:
        rad = await storage.get_global_instructions()
    except Exception:  # noqa: BLE001 — se docstringen
        rad = None
    if rad and (rad.get("strukturerad_md") or "").strip():
        global_md = _kapa(rad["strukturerad_md"])
        fran_fil = False
    else:
        global_md = _kapa(load_global_instructions_fil())

    kund_md = ""
    if tenant_id:
        try:
            config = await storage.get_agent_config(tenant_id, agent_type=agent_type)
            kund_md = _kapa(config.get("instructions_md"))
        except Exception:  # noqa: BLE001
            kund_md = ""

    return Instruktionslager(
        global_md=global_md,
        kund_md=kund_md,
        tenant_namn=tenant_namn,
        global_fran_fil=fran_fil,
    )


def demo() -> None:
    """Kontrollen: hashen följer TEXTEN, blocken bär sin avgränsare, och tomt
    lager ger tomt block i stället för en tom rubrik modellen ska tolka."""
    a = Instruktionslager(global_md="regel ett", kund_md="")
    b = Instruktionslager(global_md="regel ett", kund_md="", tenant_namn="Annat namn")
    c = Instruktionslager(global_md="regel två", kund_md="")
    assert a.hash == b.hash, "namnet är inte instruktionstext och ska inte ändra hashen"
    assert a.hash != c.hash, "ändrad instruktion måste ge ny hash"

    assert a.kund_block == "", "tomt kundlager ska ge tom sträng, inte en rubrik"
    assert "SLUT GLOBALA REGLER" in a.global_block

    d = Instruktionslager(global_md="g", kund_md="k", tenant_namn="Livrustningen")
    assert "Livrustningen" in d.kund_block
    assert d.hash != a.hash

    # Att flytta text mellan lagren ska INTE ge samma hash: "global g, kund k"
    # och "global gk, kund tomt" är olika prompter.
    e = Instruktionslager(global_md="gk", kund_md="")
    assert d.hash != e.hash, "nollbyte behövs mellan lagren i hashunderlaget"

    assert len(_kapa("x" * (MAX_TECKEN + 500))) == MAX_TECKEN
    print("instruktioner: ok")


if __name__ == "__main__":
    demo()
