"""Kunskapsbas-mall för ett bolag som säljer hjärtstartare (AED).

Alla artiklar är PLATSHÅLLARE — strukturen är på plats, innehållet är generiskt
och måste ersättas med bolagets riktiga villkor innan skarp drift. Varje text
inleds med [PLATSHÅLLARE] så att det syns i dashboarden och i agentens källor
om något råkar användas som underlag för ett svar.

Ersätt innehållet via dashboardens kunskapsbas-flik eller `POST /api/kb`.
Behåll gärna rubrik och kategori — de styr träffsäkerheten i sökningen.
"""

PLACEHOLDER_PREFIX = "[PLATSHÅLLARE — ersätt med er egen text] "

KB_TEMPLATE: list[dict] = [
    # ── Teknisk support ────────────────────────────────────────────────────
    {
        "title": "Hjärtstartaren larmar eller piper",
        "category": "teknisk_support",
        "content": (
            "En hjärtstartare som piper signalerar oftast att självtestet misslyckats "
            "eller att batteriet börjar ta slut. Kontrollera statusindikatorn: grön "
            "bock betyder driftklar, rött kryss eller blinkande lampa betyder att "
            "enheten behöver åtgärdas. Notera eventuell felkod i displayen och uppge "
            "den vid kontakt — den avgör om det räcker med byte av batteri eller "
            "elektroder, eller om enheten behöver skickas in för service."
        ),
    },
    {
        "title": "Byte av batteri och elektroder",
        "category": "teknisk_support",
        "content": (
            "Elektroder och batteri är förbrukningsvaror med bäst-före-datum. "
            "Elektroder byts vanligtvis vartannat till vart fjärde år eller efter "
            "varje användning; batteriet enligt tillverkarens intervall. Enheten "
            "varnar när något behöver bytas. Ange enhetens modellbeteckning vid "
            "beställning — elektroder är modellspecifika och passar inte mellan "
            "fabrikat. Vuxen- och barnelektroder är olika artiklar."
        ),
    },
    {
        "title": "Enheten startar inte eller ser skadad ut",
        "category": "teknisk_support",
        "content": (
            "Om enheten inte startar vid öppnat lock: kontrollera att batteriet "
            "sitter korrekt och inte passerat utgångsdatum. Vid synliga skador, "
            "fukt eller om enheten tappats ska den tas ur bruk och kontrolleras "
            "innan den sätts tillbaka i beredskap. En hjärtstartare som inte klarar "
            "självtestet får inte betraktas som driftklar."
        ),
    },
    # ── Garanti ────────────────────────────────────────────────────────────
    {
        "title": "Garantitid och vad garantin omfattar",
        "category": "garanti",
        "content": (
            "Garantin omfattar fabrikations- och materialfel på själva enheten under "
            "garantitiden räknat från leveransdatum. Förbrukningsvaror som elektroder "
            "och batterier har egen, kortare hållbarhet och omfattas inte av "
            "enhetsgarantin. Garantin gäller vid normal användning enligt "
            "bruksanvisningen; skador från fall, fukt, felaktig förvaring eller "
            "obehörigt ingrepp omfattas inte."
        ),
    },
    {
        "title": "Så gör du ett garantiärende",
        "category": "garanti",
        "content": (
            "Uppge serienummer, inköpsdatum och en beskrivning av felet, gärna med "
            "foto på enheten och eventuell felkod. Vi bedömer ärendet och återkommer "
            "med besked om reparation, utbyte eller om felet ligger utanför garantin. "
            "Behåll originalförpackningen om enheten ska skickas in."
        ),
    },
    # ── Leverans & frakt ───────────────────────────────────────────────────
    {
        "title": "Leveranstider och fraktalternativ",
        "category": "leverans",
        "content": (
            "Lagerförda produkter skickas normalt inom en till två arbetsdagar. "
            "Leveranstiden tillkommer utöver det och beror på fraktsätt. Vid större "
            "beställningar eller specialbeställda modeller kan leveranstiden vara "
            "längre — det anges då i orderbekräftelsen. Spårningsnummer skickas via "
            "mail när försändelsen lämnat lagret."
        ),
    },
    {
        "title": "Försenad eller skadad leverans",
        "category": "leverans",
        "content": (
            "Kontrollera först spårningsinformationen i leveransmailet. Har paketet "
            "inte rört sig på flera arbetsdagar startar vi en efterlysning hos "
            "transportören. Synliga transportskador ska anmälas så snart som möjligt "
            "efter mottagandet, med foto på emballage och innehåll — vi behöver det "
            "för att driva ärendet mot transportören."
        ),
    },
    # ── Utbildning & användarstöd ──────────────────────────────────────────
    {
        "title": "HLR-utbildning och kurser",
        "category": "utbildning",
        "content": (
            "Vi erbjuder utbildning i hjärt-lungräddning med hjärtstartare (D-HLR) "
            "för arbetsplatser och föreningar. Utbildningen omfattar praktisk "
            "träning på övningsdocka och handhavande av hjärtstartaren. "
            "Rekommendationen är repetition varje till vartannat år för att behålla "
            "färdigheten. Kontakta oss med antal deltagare och önskad ort så "
            "återkommer vi med förslag på upplägg och tid."
        ),
    },
    {
        "title": "Hur man använder en hjärtstartare",
        "category": "utbildning",
        "content": (
            "Hjärtstartaren talar om vad som ska göras steg för steg när den slås på. "
            "Den analyserar hjärtrytmen och avger endast stöt om rytmen är stötbar — "
            "en hjärtstartare kan alltså inte ge stöt till någon som inte behöver "
            "det. Larma alltid 112 först och påbörja hjärt-lungräddning medan "
            "hjärtstartaren hämtas. Följ enhetens röstinstruktioner."
        ),
    },
    {
        "title": "Manualer och underhållsrutiner",
        "category": "utbildning",
        "content": (
            "Bruksanvisning medföljer varje enhet och finns även att beställa. "
            "Rekommenderad rutin: kontrollera statusindikatorn regelbundet, håll koll "
            "på utgångsdatum för elektroder och batteri, och dokumentera kontrollerna. "
            "Utse gärna en ansvarig person per enhet så att kontrollen inte glöms bort."
        ),
    },
    # ── Reklamation & retur ────────────────────────────────────────────────
    {
        "title": "Returer och ångerrätt",
        "category": "retur_reklamation",
        "content": (
            "Oanvända produkter i originalförpackning kan returneras inom gällande "
            "returfrist. Kontakta oss först för returnummer — returer utan sådant kan "
            "inte hanteras. Återbetalning sker efter att returen inkommit och "
            "kontrollerats. Observera att öppnade elektrodförpackningar av "
            "hygien- och säkerhetsskäl inte kan tas i retur."
        ),
    },
    {
        "title": "Reklamation av defekt produkt",
        "category": "retur_reklamation",
        "content": (
            "Vid fel på en levererad produkt: beskriv felet, uppge ordernummer och "
            "serienummer och bifoga gärna foto. Vi bedömer ärendet och återkommer med "
            "besked om reparation, utbyte eller ersättning. Har produkten använts i en "
            "skarp situation, nämn det — då hanteras ärendet med förtur."
        ),
    },
    # ── Betalning & faktura ────────────────────────────────────────────────
    {
        "title": "Betalningsvillkor och fakturafrågor",
        "category": "betalning",
        "content": (
            "Fakturan skickas i samband med leverans och innehåller ordernummer och "
            "eventuell referens. Behöver ni ändra referens, fakturaadress eller "
            "faktureringsmetod, kontakta oss med ordernumret. Vid frågor om ett "
            "specifikt belopp, uppge fakturanummer så reder vi ut det."
        ),
    },
    {
        "title": "Priser, offert och moms",
        "category": "betalning",
        "content": (
            "Priser anges exklusive moms för företagskunder och inklusive moms för "
            "privatpersoner om inget annat framgår. Vid större inköp eller flera "
            "enheter lämnar vi offert — uppge antal, modell och önskat "
            "leveransdatum. Offerter har begränsad giltighetstid som framgår av "
            "offerten."
        ),
    },
    # ── Orderstatus ────────────────────────────────────────────────────────
    {
        "title": "Orderbekräftelse och status på beställning",
        "category": "orderstatus",
        "content": (
            "En orderbekräftelse skickas via mail direkt efter lagd beställning. "
            "Har den inte kommit fram, kontrollera skräpposten och hör av dig med "
            "namn och ungefärlig beställningstidpunkt så letar vi upp ordern. "
            "Beställningar kan normalt ändras eller avbrytas fram tills de packats."
        ),
    },
    {
        "title": "Beställa fler enheter eller tillbehör",
        "category": "orderstatus",
        "content": (
            "Vid kompletterande beställning, uppge gärna tidigare ordernummer eller "
            "modellbeteckning så att tillbehören säkert passar era befintliga "
            "enheter. Vanliga tillbehör är väggskåp, larm till skåp, skyltning, "
            "extra elektroder och reservbatteri."
        ),
    },
    # ── Övrigt ─────────────────────────────────────────────────────────────
    {
        "title": "Kontaktvägar och svarstider",
        "category": "ovrigt",
        "content": (
            "Vi besvarar mail under kontorstid på vardagar. Ärenden som rör en enhet "
            "som är ur funktion prioriteras. Vid pågående nödsituation — ring 112, "
            "kontakta aldrig kundtjänst i ett akut läge."
        ),
    },
]


def as_articles(prefixed: bool = True) -> list[dict]:
    """Mallartiklarna, som standard märkta som platshållare."""
    return [
        {
            "title": article["title"],
            "category": article["category"],
            "content": (PLACEHOLDER_PREFIX + article["content"]) if prefixed else article["content"],
        }
        for article in KB_TEMPLATE
    ]
