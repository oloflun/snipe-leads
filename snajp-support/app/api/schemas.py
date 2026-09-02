"""Pydantic-scheman för API:t."""

from pydantic import BaseModel, Field, model_validator


class Attachment(BaseModel):
    data_url: str = Field(..., description="Bild som data-URL (data:image/...;base64,...)")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    subject: str = ""
    channel: str = "web"
    customer_email: str | None = None
    customer_name: str | None = None
    attachments: list[Attachment] = []
    #: Fas 2.5 (snipe-vxq): supportkörningar kunde inte märkas som test alls —
    #: adminytans Testkörningar-flik LOVADE märkningen i sin egen beskrivning
    #: medan fältet saknades här, så varje admintest räknades som kundvolym.
    #: Samma fält och samma innebörd som LeadsBatchRequest.is_test.
    is_test: bool = False


class TriageEmail(BaseModel):
    sender: str = Field(..., alias="from")
    subject: str = ""
    body: str = Field(..., min_length=1, max_length=8000)

    model_config = {"populate_by_name": True}


class TriageRequest(BaseModel):
    emails: list[TriageEmail] = Field(..., min_length=1, max_length=20)


class CreateKeyRequest(BaseModel):
    tenant_name: str = Field(..., min_length=2, max_length=80)
    slug: str | None = Field(default=None, min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")


class KbArticle(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=10, max_length=8000)
    category: str = "ovrigt"


class ContextDocRequest(BaseModel):
    """Leads Fas A (Del F): produktmarknadsföring, kundresearch, uppladdat
    material, eller retentionsplaybook. `content` är redan extraherad text —
    fil-till-text-parsning (PDF/DOCX) sker inte här, se app/api/leads.py."""

    kind: str = Field(..., pattern=r"^(product_marketing|customer_research|upload|retention_playbook)$")
    content: str = Field(..., min_length=1, max_length=50000)
    source: str = ""


class OnboardingChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)


class ProspectRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    contact_name: str | None = None
    contact_email: str | None = None


class LeadsConfigRequest(BaseModel):
    """Båda fälten är valfria: UI:t har två separata formulär, och en PUT från
    det ena får inte nolla det andra."""

    # `auto_send` finns med i mönstret men släpps inte igenom av routen utan
    # att kan_aktivera_auto_send() godkänt. Att avvisa den redan här hade gett
    # ett pydantic-fel utan förklaring; kunden ska få veta VAD som saknas.
    autonomy: str | None = Field(
        default=None, pattern=r"^(draft|first_contact|meeting|auto_send)$"
    )
    icp: dict | None = None


class LeadsRunOverrides(BaseModel):
    """Styrning som gäller EN körning, aldrig arbetsytans sparade ICP.

    Skälet till att detta inte är inställningar: den som ska köra en gång mot
    en särskild nisch vill inte ändra sin målgrupp, köra, och sedan komma ihåg
    att ändra tillbaka. Glöms återställningen bearbetas nästa körning fel
    målgrupp utan att någon ser det — och felet upptäcks först i utskicken.

    Tomma fält betyder "använd den globala inställningen". Ett tomt värde är
    alltså inte samma sak som "inga branscher".
    """

    # Speglar `LIST_FIELDS` i app/leads/icp.py, ALLA sex. Fyra av dem saknades
    # tidigare, och följden var att en provkörning mot en särskild nisch inte
    # gick att styra: rollerna, signalerna som krävs och de diskvalificerande
    # kom alltid från arbetsytans sparade ICP. Just de tre ÄR nischen — geografi
    # och bransch är bara var man letar.
    industries: list[str] | None = None
    exclude_industries: list[str] | None = None
    geography: list[str] | None = None
    roles: list[str] | None = None
    must_have: list[str] | None = None
    deal_breakers: list[str] | None = None
    anstallda_min: int | None = Field(default=None, ge=0)
    anstallda_max: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _spannet_maste_ga_ihop(self) -> "LeadsRunOverrides":
        lo, hi = self.anstallda_min, self.anstallda_max
        if lo is not None and hi is not None and lo > hi:
            raise ValueError(
                f"Minsta antal anställda ({lo}) är större än största ({hi}). "
                "Ett spann som utesluter allt ger noll prospekt utan att säga varför."
            )
        return self

    def har_nagot(self) -> bool:
        # model_fields_set och inte en handskriven lista: listan glömdes bort
        # när fälten utökades, och en override som inte räknas här skickas
        # aldrig vidare — den försvinner tyst i stället för att styra körningen.
        return any(getattr(self, namn) is not None for namn in type(self).model_fields)


class ExempelbolagRequest(BaseModel):
    """Påhittade bolag som passar ICP:t, för en arbetsyta utan prospekt.

    Taket är lågt med flit: exempelbolag är en väg in i produkten, inte en
    lista att arbeta ur. Vill kunden ha femtio bolag ska de komma från en
    körning mot riktiga källor.
    """

    limit: int = Field(default=3, ge=1, le=10)
    #: Samma överskrivningar som körningen. Ett formulär som beskriver en
    #: målgrupp och skapar bolag ur en annan är värre än inga bolag alls.
    overrides: LeadsRunOverrides | None = None
    #: Frö för urvalet. Tomt = nytt slumpat per anrop, vilket är vad knappen
    #: "Uppdatera" behöver. Ett angivet frö ger samma lista igen och finns för
    #: att ett utfall ska gå att återskapa när någon undrar över det.
    fro: str | None = Field(default=None, max_length=64)


class LeadsBatchRequest(BaseModel):
    #: `sok` (2026-09-02) är snabbsökningens scope: EN Gemini-sökning som
    #: hittar bolag med kontaktväg och stannar där — inga researchjobb, inga
    #: utkast. Byggd för leads-panelen ("Sök Leads"), där hela poängen är att
    #: få en lista på en minut till kostnaden av ett enda anrop.
    scope: str = Field(default="research", pattern=r"^(sok|research|research_and_draft)$")
    # Taket på 50 är ekonomiskt, inte tekniskt: varje prospekt är upp till nio
    # LLM-anrop i research (tre om grinden efter ICP-kvalificeringen fäller),
    # så en batch på 50 kan vara 450 — över tenant-timtaket.
    limit: int = Field(default=10, ge=1, le=50)

    #: Överskrivningar för just den här körningen. Se LeadsRunOverrides.
    overrides: LeadsRunOverrides | None = None

    #: Testkörning: räknas som körning men märks så att den går att skilja från
    #: kundtrafik i portföljvyn. Utan flaggan blir en provkörning omöjlig att
    #: skilja från riktig volym, och hälsobedömningen ljuger.
    is_test: bool = False

    #: Bolag kunden själv vill träffa — en funktion, inte kedjan. Tom lista
    #: betyder att agenten ska HITTA bolag som matchar ICP:t. Namnen här blir
    #: prospekt i DEN här körningen; gamla rader i registret blandas inte in.
    company_names: list[str] = Field(default_factory=list, max_length=50)


class ProspectPatchRequest(BaseModel):
    status: str | None = None
    icp_fit: float | None = Field(default=None, ge=0, le=1)
    qualified: bool | None = None
    disqualifiers: list[str] | None = None
    orgnr: str | None = Field(default=None, max_length=20)
    website: str | None = Field(default=None, max_length=500)
    contact_email: str | None = Field(default=None, max_length=200)


class BefordraRequest(BaseModel):
    """Ifyllnad vid flytta-över. Tom kropp = validera det som redan ligger."""

    orgnr: str | None = Field(default=None, max_length=20)
    website: str | None = Field(default=None, max_length=500)
    contact_email: str | None = Field(default=None, max_length=200)


class ProspectSourceRequest(BaseModel):
    source_url: str = Field(..., min_length=4, max_length=2000)
    source_type: str = Field(
        default="company_website",
        pattern=r"^(company_website|public_news|business_register|job_signal|manual_note|enrichment_adapter|linkedin|other)$",
    )
    lawful_basis: str = Field(..., min_length=3, max_length=500)


class ResearchStepRequest(BaseModel):
    prospect_id: str
    brief: str = Field(..., min_length=1, max_length=2000)


class OutreachDraftRequest(BaseModel):
    # Endera: en befintlig tråd, eller ett prospekt att skapa/återanvända
    # tråden för. Före 2026-08-26 KRÄVDES thread_id — men ingen kodväg skapade
    # någonsin en tråd, så fältet gick inte att fylla i utan hand-SQL:
    # utkastvägen var obrytbar i produktion och ingen märkte det, eftersom
    # MemoryStorage saknar FK-kontrollen som hade avslöjat den döda referensen.
    thread_id: str | None = None
    prospect_id: str | None = None
    prospect_email: str
    company_name: str = Field(..., min_length=1, max_length=200)
    offer_summary: str = Field(..., min_length=1, max_length=2000)
    brief: str = Field(..., min_length=1, max_length=2000)
    # Fas B:s underlag, vidarebefordrat av anroparen. Utan det har
    # grundningsgrinden ingenting att mäta utkastets påståenden mot — och det
    # var precis därför den påhittade "30 procent"-siffran var ofalsifierbar
    # (fältet research_summary fanns i signaturen men skickades aldrig).
    research_summary: str = Field(default="", max_length=8000)
    research_evidence: list[str] = Field(default_factory=list, max_length=60)


class ProcessaOmRequest(BaseModel):
    """Kör om research (och ev. utkast) för REDAN SPARADE prospekt.

    Skapar inga nya rader. Används när en körning hittade bolagen men dog
    innan kontakt/utkast — 'Processa om' i registret.
    """

    prospect_ids: list[str] = Field(..., min_length=1, max_length=50)
    scope: str = Field(default="research_and_draft", pattern=r"^(research|research_and_draft)$")
    is_test: bool = False


class LeadsListaRequest(BaseModel):
    """Beställning av en leadslista (tillägget 'leadlists', migration 060).

    Volymkörning utan utkast och utan sändning: discovery-federationen
    (JobTech, nyhets-RSS, Gemini-utfyllnad) bygger en granskningsbar tabell.
    Taket 200 speglar check-villkoret i migration 060; budgetgrinden
    (app/leads/budget.py) står dessutom framför endpointen.
    """

    titel: str = Field(..., min_length=1, max_length=200)
    antal: int = Field(default=25, ge=1, le=200)
    is_test: bool = False
    overrides: LeadsRunOverrides | None = None


class AgentFeedbackRequest(BaseModel):
    """Kundens dom över en agentkörning. corrected_output är människans egen
    formulering av vad svaret BORDE ha varit — den starkaste signalen in i
    lärandeflödet."""

    run_id: str
    verdict: str = Field(..., pattern="^(good|bad|needs_review)$")
    comment: str | None = Field(default=None, max_length=4000)
    corrected_output: str | None = Field(default=None, max_length=20_000)


class ProspektsvarRequest(BaseModel):
    """Ett inkommande prospektsvar. Endera tråden eller prospektet pekas ut —
    prospekt utan tråd får en (svar på ett mejl skickat utanför systemet ska
    också kunna hanteras)."""

    thread_id: str | None = None
    prospect_id: str | None = None
    body: str = Field(..., min_length=1, max_length=20_000)


class SoulRequest(BaseModel):
    # Taket verkställs på TVÅ ställen: här vid API-gränsen och i
    # soul.render_soul. Ett dokument som stoppats direkt i databasen ska inte
    # kunna gå förbi bara för att det aldrig passerade den här modellen.
    content: str = Field(default="", max_length=4000)


class InstruktionRequest(BaseModel):
    """Globala eller kundspecifika agentinstruktioner, skrivna av admin.

    `ravtext` är vad admin skrev. `strukturera=False` sparar den ostrukturerad
    (kalla='manuell') — det är vägen för den som redigerat modellens utkast för
    hand och inte vill få det omskrivet igen.

    Taket speglar agentcore.instruktioner.MAX_TECKEN. Det verkställs på TVÅ
    ställen av samma skäl som SoulRequest: en rad som stoppats direkt i
    databasen ska inte gå förbi för att den aldrig passerade den här modellen.
    """

    ravtext: str = Field(default="", max_length=12_000)
    #: Sätts av den som redigerat modellens utkast direkt. Tom => struktureras
    #: ur ravtext.
    strukturerad_md: str | None = Field(default=None, max_length=12_000)
    strukturera: bool = True


class TenantProfilRequest(BaseModel):
    """Adminens skrivning mot EN kunds agentprofil.

    Varje fält är valfritt, och None betyder "rör inte". Det är inte
    bekvämlighet: formuläret sparar en sektion i taget, och ett utelämnat fält
    som tolkats som tom sträng hade nollställt kundens SOUL varje gång någon
    ändrade tonen.
    """

    agent_type: str = Field(default="support", pattern="^(support|leads)$")
    instruktioner_rav: str | None = Field(default=None, max_length=12_000)
    instruktioner_md: str | None = Field(default=None, max_length=12_000)
    strukturera: bool = True
    tone: str | None = Field(default=None, max_length=500)
    soul: str | None = Field(default=None, max_length=4000)
    affarskontext: str | None = Field(default=None, max_length=20_000)


class KunddataRequest(BaseModel):
    """Adminens skrivning mot kundregistret (migration 053).

    Samma semantik som TenantProfilRequest: None betyder "rör inte", tom
    sträng nollställer. Datumfälten tas emot som text och valideras i
    lagringslagrets delade normalisera_kunddata — ett datum som inte parsar
    ska ge ett 422 med fältnamnet, inte ett databas-undantag.
    """

    orgnr: str | None = Field(default=None, max_length=20)
    faktureringsadress: str | None = Field(default=None, max_length=500)
    faktureringsmejl: str | None = Field(default=None, max_length=320)
    telefon: str | None = Field(default=None, max_length=40)
    foretagsadress: str | None = Field(default=None, max_length=500)
    kund_sedan: str | None = Field(default=None, max_length=10)
    avtal_signerat: str | None = Field(default=None, max_length=10)


class KontaktRequest(BaseModel):
    """En kontaktperson i kundregistret. `namn` krävs vid skapande;
    uppdateringen låter utelämnade fält vara (None) och nollställer tomma."""

    namn: str | None = Field(default=None, max_length=200)
    roll: str | None = Field(default=None, max_length=200)
    mejl: str | None = Field(default=None, max_length=320)
    telefon: str | None = Field(default=None, max_length=40)


class KbArticleRequest(BaseModel):
    articles: list[KbArticle] = Field(..., min_length=1, max_length=50)


class KbExtraheraRequest(BaseModel):
    """Fas 5.5 (Testchatt, snipe-0r9): PDF in, textlager ut. Filen sparas
    aldrig, se app/api/kb.py. Taket här är medvetet GROVARE än det riktiga
    (~8 MB, kb.MAX_PDF_BYTES): 14 000 000 tecken täcker en base64-kodad fil
    en bra bit förbi 8 MB, så den exakta, begripliga gränsen sätts av
    endpointens egen kontroll på de AVKODADE bytesen — inte av pydantic,
    vars valideringsfel inte är skrivet för en kund att läsa."""

    filename: str = Field(default="dokument.pdf", min_length=1, max_length=255)
    data_url: str = Field(..., min_length=10, max_length=14_000_000)


class IngestAttachment(BaseModel):
    filename: str = "bilaga"
    content_type: str = "application/octet-stream"
    data_url: str | None = None


class SeedMockRequest(BaseModel):
    """Kroppen till "Hämta testmail" och "Uppdatera".

    Båda fälten är frivilliga: utan kropp byts hela testinkorgen ut, precis som
    innan facken fanns. `category` begränsar till ett fack — det är vad
    "Uppdatera" skickar när kunden står i ett filtrerat läge.
    """

    category: str | None = None
    antal: int | None = None


class IngestEmailRequest(BaseModel):
    """API-first-ingest: externa system (Zendesk, CRM, webhook) postar mail hit."""

    from_email: str = Field(..., alias="from", min_length=3)
    from_name: str | None = None
    subject: str = ""
    body: str = Field(..., min_length=1, max_length=16000)
    provider_message_id: str | None = None
    attachments: list[IngestAttachment] = []

    model_config = {"populate_by_name": True}


class ApproveDraftRequest(BaseModel):
    edited_content: str | None = Field(default=None, max_length=16000)
    note: str | None = None


class RejectDraftRequest(BaseModel):
    note: str | None = None


class CategoryRuleRequest(BaseModel):
    category: str
    mode: str = Field(..., pattern="^(auto|draft|escalate)$")
