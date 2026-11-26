"""Hjälpens egen kund i systemet: Snajps supportagent för den inloggade ytan.

Plan: docs/PLAN-HJALPRUTAN-2026-11-25.md, del 2. Hjälprutan i appen frågar
Snajps agent under en EGEN tenant (`Settings.hjalp_tenant_slug`, förvalt
"snajp-hjalp"), skild från "snajp" som marknadssidans anonyma demo använder:
en anstormning på marknadssidan ska inte stänga kundernas hjälp, och den
anonyma vägen ska inte kunna nå kundernas samtal.

## Kunskapsbasen

Snajps befintliga artiklar (snajp_kb.py) plus produkthjälp för den inloggade
ytan nedan. Ett undantag: snajp_kb.py:s "Hitta rätt på arbetsytan" beskriver
en äldre meny (Iris › Bolag, Granskning) och ersätts här av
"Arbetsytans meny", som speglar dagens. Artikeln i snajp_kb.py rörs inte;
marknadssidans demo använder den fortfarande.

Varje påstående nedan är belagt i koden eller gränssnittets texter, med
källan i en kommentar. Ändras gränssnittet ska artikeln ändras i samma
ändring, annars beskriver agenten en knapp som inte finns.

## Så skapas kunden i en miljö

Kunden skapas inte av koden vid uppstart. Ordningen, med en människa vid
tangentbordet (CLAUDE.md: Railway och nycklar är driftsteg):

  1. `seed_hjalp` nedan, via `python -m app.tenants.snajp_hjalp` med
     miljöns DATABASE_URL. Den skapar tenanten med `kraver_avtal = false`
     (en intern tenant; avtalsgrinden hade annars svarat 403 på varje
     fråga, se app/avtalsgrind.py) och lägger in artiklarna.
  2. `python scripts/railway_tenantnyckel.py --slug snajp-hjalp --name "Snajp Hjälp" --env development --apply`
     utfärdar nyckeln (upsert: tenanten från steg 1 återanvänds och dess
     avtalsflagga rörs inte). Skriptet sätter variabeln SNAJP_KEY_SNAJP_HJALP
     på web, och det är samma namn som Next läser (lib/snajp/hjalp.ts).
     Körs steg 2 före steg 1 får tenanten avtalsgrinden PÅ och måste slås
     av i Kunder & Data.
"""

from __future__ import annotations

from ..config import get_settings
from .snajp_kb import KB_ARTICLES as SNAJP_KB

#: Namnet i ss_tenants. create_tenant är en upsert som skriver om namnet, så
#: det står här och härleds inte ur sluggen (se app/tenants/__init__.py).
HJALP_TENANT_NAME = "Snajp Hjälp"

#: snajp_kb.py-artiklar som INTE följer med till hjälpen (se docstringen).
UTESLUTNA_SNAJP_RUBRIKER: tuple[str, ...] = ("Hitta rätt på arbetsytan",)

PRODUKTHJALP: list[dict] = [
    {
        # lib/routes.ts appRoutes och settingsSections, lib/i18n.tsx nav.*.
        "title": "Arbetsytans meny",
        "category": "teknisk_support",
        "content": (
            "Arbetsytan nås efter inloggning och har en meny till vänster (på mobilen en rad "
            "längst ned). Vilka poster som syns beror på vilka agenter ni har.\n"
            "• Översikt: alla agenters körningar och resultat på ett ställe.\n"
            "• Att göra: det som väntar på ett beslut från dig.\n"
            "• Leads: Iris, leadsagenten. Flikarna är Översikt, Konversationer, Uppföljningar, "
            "Inkorg, Samtal, Listor, Körningar och Erbjudanden.\n"
            "• Kundtjänst: supportagentens ärenden, med flikarna Översikt, Ärenden och Testchatt "
            "(och Testmail på riktiga konton).\n"
            "• Inställningar: företaget, kunskapsbasen, Iris, kundtjänsten och kontot.\n"
            "Knappen Meny längst ned i sidomenyn öppnar Hjälp och fel, där du frågar om Snajp "
            "och rapporterar fel."
        ),
    },
    {
        # components/dashboard/StartView.tsx och Aktivitet.tsx.
        "title": "Översikt",
        "category": "teknisk_support",
        "content": (
            "Översikt är startsidan. Den visar alla agenters arbete på ett ställe: nyckeltal för "
            "körningar, levererade leads, överlämningar och kostnad, vilka Iris-körningar som pågår "
            "just nu med förloppet, beställt mot levererat per vecka och hur körningarna slutade, "
            "samt kundtjänstens körningar per vecka, dygnsbudgeten och de samtal agenten lämnat "
            "över till en människa. Saker som väntar på ditt beslut står inte här utan under Att göra."
        ),
    },
    {
        # components/leads/AttGora.tsx.
        "title": "Att göra",
        "category": "teknisk_support",
        "content": (
            "Att göra samlar det som väntar på ett beslut från dig, i viktordning. Överst står hur "
            "mycket som väntar och hur länge det väntat. Därunder står köerna:\n"
            "• Eskalerat till dig: ärenden supportagenten lämnat över till en människa.\n"
            "• Svar att godkänna: agentens svar som väntar på ditt ja innan de skickas.\n"
            "• Larm: avvisade utskick och systemfel. Likadana larm står som en rad.\n"
            "• Leads: svar från dina leads, Iris utkast och dagens samtal. De hanteras under Leads, "
            "och länkarna Öppna inkorgen, Öppna utkasten och Öppna samtalen tar dig dit.\n"
            "• Kvitton att granska, för den som har kvittohanteraren.\n"
            "När inget väntar står det Inget väntar på dig."
        ),
    },
    {
        # components/leads/LeadsSida.tsx SEGMENT_ETIKETT, LeadsOversikt.tsx,
        # Konversationer.tsx, IrisInkorg.tsx.
        "title": "Leads: flikarna och vad de visar",
        "category": "teknisk_support",
        "content": (
            "Leads är Iris, leadsagenten som hittar bolag, läser deras webbplatser och skriver "
            "utkast till mejl. Sidan har åtta flikar:\n"
            "• Översikt: nyckeltalen (utkast att godkänna, skickade mejl, svar från leads, leads i "
            "listan, möten bokade), de senaste utkasten, pågående körningar och listan med "
            "Iris-leads. Nyaste överst; Ny är bolag Iris just hittat, Redo de du granskat och vill "
            "kontakta.\n"
            "• Konversationer: när ett bolag svarar på ett mejl från Iris hamnar svaret här, med ett "
            "utkast till svar.\n"
            "• Uppföljningar: bolag som fått mejl utan att svara, och uppföljningarna som väntar på "
            "ditt ja.\n"
            "• Inkorg: Inkommande och Skickat. Under Skickat syns varje mejl som Skickas snart, "
            "Väntar på svar, Svarat, Möte eller Ej intresserad.\n"
            "• Samtal: ringlistan och återkopplingen.\n"
            "• Listor: egna importerade listor, beställda listor och er kundlista.\n"
            "• Körningar: varje körning med förlopp och resultat.\n"
            "• Erbjudanden: erbjudandena Iris får använda i mejlen.\n"
            "Ett bolag öppnas i en låda från höger, var du än står."
        ),
    },
    {
        # components/leads/LeadsSida.tsx (Kör Iris), LeadsRunForm.tsx,
        # IrisKorningar.tsx.
        "title": "Så kör du Iris",
        "category": "teknisk_support",
        "content": (
            "1. Gå till Leads och tryck Kör Iris.\n"
            "2. Välj Antal leads och Omfattning: Research och utkast, eller Bara research. Under "
            "Filtrera kan du snäva in sökningen, till exempel antal anställda, eller lägga in egna "
            "bolag (ett per rad). Lämnar du filtren tomma letar Iris själv utifrån er sparade "
            "målgrupp.\n"
            "3. Tryck Starta körning. Följ körningen visar förloppet.\n"
            "Körningen fortsätter på servern, så du kan lämna sidan och komma tillbaka. Under "
            "Leads › Körningar ser du varje körning med förlopp och resultat, och där kan du pausa, "
            "fortsätta eller avbryta en körning. Vid paus eller avbrott blir bolag som redan "
            "researchas klara, men inga nya startas. Ett avbrott går inte att ångra.\n"
            "Hittar sökningen inga bolag, prova en bredare målgrupp."
        ),
    },
    {
        # IrisGranskning.tsx, KorningensUtkast.tsx, Bolagssida.tsx.
        "title": "Så godkänner du ett utkast",
        "category": "teknisk_support",
        "content": (
            "Iris skickar inget mejl utan ditt ja. Utkasten som väntar står under Leads › Översikt "
            "(Utkast att godkänna), i varje körning och i bolagets låda.\n"
            "1. Öppna utkastet och läs det. Du kan ändra texten innan du godkänner.\n"
            "2. Tryck Godkänn och skicka.\n"
            "Ett godkänt mejl går genom sändspärrarna och skickas i tur och ordning från kön, "
            "vardagar från 08:00. I listan står det då Godkänt, skickas 08–16. Ett utkast som "
            "stoppats av en sändspärr märks Stoppat av sändspärr."
        ),
    },
    {
        # components/leads/Uppfoljningar.tsx.
        "title": "Uppföljningar",
        "category": "teknisk_support",
        "content": (
            "När Iris mejl gått ut utan svar står bolagen under Leads › Uppföljningar, med datumet "
            "för nästa uppföljning. Med automatiska uppföljningar påslagna skriver Iris förfallna "
            "uppföljningar en gång i timmen; annars skrivs en uppföljning när du väljer Skapa "
            "uppföljning. Varje uppföljning väntar på ditt ja innan den skickas, och ett svar från "
            "bolaget stoppar resten."
        ),
    },
    {
        # components/leads/Samtalslista.tsx, lib/leads/konversationer.ts.
        "title": "Samtal: ringlistan och återkopplingen",
        "category": "teknisk_support",
        "content": (
            "Leads › Samtal har två delar.\n"
            "• Återkoppling: kontaktade leads med telefonnummer, äldst kontakt först. De som ska "
            "ringas i dag står överst.\n"
            "• Ringlista: bolag utan mejladress men med telefon och namngiven VD. Numret är "
            "bolagets och antas gå till VD.\n"
            "Efter ett samtal väljer du utfall (till exempel Ej svar, Återkom med ett datum, Ej "
            "intresserad, Kontakta inte eller Möte bokat), skriver en anteckning om du vill och "
            "trycker Spara."
        ),
    },
    {
        # components/leads/LeadslistorView.tsx.
        "title": "Listor",
        "category": "teknisk_support",
        "content": (
            "Under Leads › Listor finns egna listor ur ert CRM eller ett kalkylblad, listor ni "
            "beställt och er kundlista. Varje bolag i en lista öppnas som ett lead, och Skapa "
            "utkast gör samma research och utkast som för Iris-leads.\n"
            "Listorna är bredare och kallare än Iris: bolag med VD:ns telefon eller mejl, för samtal "
            "eller ett mer generellt utskick. Ett bolag som redan är ett Iris-lead, står i en annan "
            "lista eller är er befintliga kund kommer aldrig med.\n"
            "Kunder ni laddar upp (Ladda upp befintliga kunder) utesluts från Iris och listor. Två "
            "eller fler klara listor kan slås ihop; dubbletter tas bort på organisationsnummer och "
            "källistorna rörs inte."
        ),
    },
    {
        # components/leads/IrisErbjudanden.tsx.
        "title": "Erbjudanden",
        "category": "teknisk_support",
        "content": (
            "Under Leads › Erbjudanden skriver ni de erbjudanden Iris får använda i mejlen. Iris "
            "fördelar de påslagna erbjudandena mellan bolagen efter vikten och mäter vad som ger "
            "svar. Erbjudandet styr hela mejlet, och agenten anpassar det till varje bolags "
            "verksamhet. Mejlet lovar bara det som står i villkoren. Ändringar gäller nya utkast.\n"
            "Tryck Lägg till erbjudande och beskriv med era ord vad mottagaren får, vad det kostar "
            "och vad de gör för att få det. Fyll i villkoren för minst en produkt först."
        ),
    },
    {
        # components/leads/IrisProdukter.tsx, IrisInstallningar.tsx,
        # lib/routes.ts (/settings/leads).
        "title": "Så lägger du till en produkt",
        "category": "teknisk_support",
        "content": (
            "Produkterna Iris säljer står under Inställningar › Iris › Målgrupp och automation, i "
            "rutan Produkter och målgrupp.\n"
            "1. Tryck Lägg till produkt.\n"
            "2. Fyll i Namn och Nyttan för kunden.\n"
            "3. Tryck Spara produkter och målgrupp.\n"
            "Ändringen gäller från nästa körning. Iris väljer den produkt som passar varje bolag "
            "bäst och skriver bara om den. Högst åtta produkter. I samma ruta står målsegmenten, "
            "bäst först, som sökningen tar i tur och ordning."
        ),
    },
    {
        # components/snajp/SupportWorkspaceTabs.tsx, AttGora.tsx,
        # lib/routes.ts settingsSections (Kundtjänst).
        "title": "Kundtjänst",
        "category": "teknisk_support",
        "content": (
            "Kundtjänst är supportagentens yta. Den svarar på inkommande ärenden utifrån er egen "
            "kunskapsbas.\n"
            "• Ärenden: den interna inkorgen med agentens svar.\n"
            "• Testmail (på riktiga konton): testärenden som inte blandas med skarpa.\n"
            "• Testchatt: en riktig agent mot er egen kunskapsbas, för att prova svaren. "
            "Testkörningar räknas inte som kundvolym.\n"
            "Svar som väntar på ditt ja och ärenden agenten lämnat över står under Att göra. Under "
            "Inställningar › Kundtjänst kopplar ni inkorgar och bestämmer när agenten får svara själv."
        ),
    },
    {
        # components/settings/Kunskapsbas.tsx, WebbplatsForslag.tsx.
        "title": "Så lägger du till kunskap i kunskapsbasen",
        "category": "teknisk_support",
        "content": (
            "Kunskapsbasen är det agenterna svarar ur. Den finns under Inställningar › Företaget › "
            "Kunskapsbas.\n"
            "Skriv själv: under Skriv eller klistra in fyller du i en rubrik (till exempel Ångerrätt "
            "och returer) och texten agenterna ska svara ur, och trycker Spara i kunskapsbasen.\n"
            "Från er webbplats: Läs in er webbplats läser sajten och skriver förslag. Det brukar ta "
            "en till tre minuter, och ni kan lämna sidan under tiden. Förslagen blir artiklar först "
            "när ni lägger till dem, och era egna texter ändras inte. Ett förslag med samma rubrik "
            "som en befintlig artikel läggs inte till.\n"
            "Kategorin Erbjudande och säljfakta är det Iris läser om vad ni säljer."
        ),
    },
    {
        # Planens del 3 (POST /api/kb/forslag med källan chatt).
        "title": "Lär agenten om ert företag från Hjälprutan",
        "category": "teknisk_support",
        "content": (
            "I Hjälp och fel kan du skriva eller klistra in text om ert företag. Rutan visar exakt "
            "den rubrik och text som sparas, och du kan ändra båda. Texten hamnar som ett förslag i "
            "er egen kunskapsbas, i samma förslagslista som webbplatsens förslag, märkt med var den "
            "kom ifrån. Den blir en artikel först när ni lägger till den. Snajps agent skriver "
            "aldrig i någon annans kunskapsbas."
        ),
    },
    {
        # lib/routes.ts settingsSections.
        "title": "Inställningar",
        "category": "teknisk_support",
        "content": (
            "Inställningar är uppdelade i delar:\n"
            "• Företaget: Företaget, Vad ni säljer, Kunskapsbas och Så ska agenten låta.\n"
            "• Iris: Målgrupp och automation, med produkter och målsegment.\n"
            "• Kundtjänst: När agenten får svara själv, och Inkorgar.\n"
            "• Kontot: Team, Plan och fakturering, Tillägg, Notiser och Tema.\n"
            "Vad ni säljer fyller ni i med fyra fält: vad ni säljer, vem ni säljer till, erbjudandet "
            "och nästa steg ni vill ha. Tryck Spara affärskontexten."
        ),
    },
    {
        # Planens del 1 och 5, och statusorden i kontraktet
        # (app/api/plattformsarenden.py, migration 156).
        "title": "Rapportera ett fel i Snajp, och vad som händer sedan",
        "category": "teknisk_support",
        "content": (
            "Öppna Meny längst ned i sidomenyn och välj Hjälp och fel. Välj Något är fel och fyll i "
            "vad du gjorde, vad som hände och vad du väntade dig. Du kan lägga till en bild. Under "
            "fälten står vad som skickas med: sidan, tiden och din roll. Rapporten kvitteras direkt "
            "med ett ärendenummer som börjar på F-.\n"
            "Under Mina ärenden i samma ruta ser du var rapporten står:\n"
            "• Mottaget: rapporten är sparad hos Snajp.\n"
            "• Vi undersöker: en människa hos Snajp har läst den.\n"
            "• Rättning på gång: rättningen tas fram.\n"
            "• Redo att testa: en testversion är klar. Öppna den och svara på Fungerade det? Svarar "
            "du nej går ärendet tillbaka till Rättning på gång med din kommentar och samma nummer.\n"
            "• Godkänd, granskas av oss: du svarade ja, och Snajp granskar innan något går ut.\n"
            "• Ute i Snajp: rättningen finns i Snajp.\n"
            "• Behöver mer från dig: Snajp har en fråga, och du svarar i kortet.\n"
            "• Stängd: en människa har skrivit varför.\n"
            "Bara du som skrev rapporten ser den. Du kan fortsätta fråga i Hjälp och fel medan felet rättas."
        ),
    },
]


def _artiklar() -> list[dict]:
    snajp = [a for a in SNAJP_KB if a["title"] not in UTESLUTNA_SNAJP_RUBRIKER]
    return snajp + PRODUKTHJALP


#: Hjälpens kunskapsbas: Snajps artiklar och produkthjälpen.
KB_ARTICLES: list[dict] = _artiklar()


async def seed_hjalp(storage, *, slug: str | None = None) -> dict[str, int]:
    """Skapar hjälpens kund (om den saknas) och synkar dess kunskapsbas mot filen.

    Filen ÄGER artiklarna, som för "snajp" i seed_kb.seed_tenant: en artikel
    som saknas läggs till, en ändrad byts (delete + add, det finns ingen
    update), en oförändrad lämnas, och rubriker som inte finns i filen rörs
    aldrig. Idempotent: en andra körning gör ingenting. Två artiklar med samma
    rubrik i filen vore en dubblett i basen; KB_ARTICLES har inga, och
    testet vaktar det (tests/test_snajp_hjalp_kb.py).

    Returnerar {"tillagda": n, "bytta": n}.
    """
    slug = slug or get_settings().hjalp_tenant_slug
    # kraver_avtal=False gäller bara en NY tenant (create_tenant är en upsert
    # som aldrig rör en befintligs flagga). Hjälpen är en intern tenant.
    tenant = await storage.create_tenant(slug=slug, name=HJALP_TENANT_NAME, kraver_avtal=False)
    befintliga = {
        (artikel.get("title") or "").strip().lower(): artikel for artikel in await storage.list_kb(tenant["id"])
    }
    tillagda = bytta = 0
    for article in KB_ARTICLES:
        gammal = befintliga.get(article["title"].strip().lower())
        if gammal is not None:
            if (gammal.get("content") or "").strip() == article["content"].strip():
                continue
            await storage.delete_kb_article(tenant["id"], gammal["id"])
            bytta += 1
        else:
            tillagda += 1
        await storage.add_kb_article(
            tenant["id"],
            title=article["title"],
            content=article["content"],
            category=article["category"],
            embedding=None,
        )
    return {"tillagda": tillagda, "bytta": bytta}


async def main() -> None:
    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL saknas. Inget att seeda.")
        return
    from ..storage.postgres import PostgresStorage

    storage = await PostgresStorage.connect(settings.database_url)
    try:
        utfall = await seed_hjalp(storage)
        print(
            f"{settings.hjalp_tenant_slug}: {utfall['tillagda']} nya och {utfall['bytta']} bytta artiklar "
            "(utan vektorer; scripts/fyll_embeddings.py fyller dem)."
        )
    finally:
        await storage.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
