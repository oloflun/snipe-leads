"""Mock-connector: svenska testmail för att demonstrera hela pipelinen utan
en riktig inkorg. En av bilderna är en riktig (minimal) PNG så att bilage-
och vision-flödet exerceras på riktigt.

## Varför det är en pool och inte en fast lista

Listan var tidigare sex fasta mail. Två följder, båda synliga i drift:

 1. **Inget hände när man tryckte igen.** "Hämta testmail" lade till samma sex
    ärenden en gång till, med nya id:n. Inkorgen växte men visade inget nytt.
 2. **Allt eskalerades.** Fyra av de sex innehöll pengar, juridik eller ilska
    ("återbetalning", "ARN", "dubbeldragning"), och de två som återstod hade
    ingen träff i kunskapsbasen. Grundningsregeln (`processor.py` steg 2)
    tvingar då eskalering — korrekt beteende, men en skärm där sex av sex är
    röda visar inte en agent som vägrar gissa, den visar en produkt som inte
    fungerar.

Poolen är därför uppdelad i två delar, och urvalet blandar dem med flit:
`BESVARBARA` ska agenten kunna svara på (och gör det, om kunskapsbasen har
täckning), `ESKALERANDE` ska den lämna till en människa. Ett demoutfall utan
någon eskalering vore lika missvisande åt andra hållet — spärrarna är en del av
produkten.
"""

import random
import uuid

from ..models import InboundAttachment, InboundEmail

# 1x1 röd PNG — giltig bild, minimal storlek.
_RED_PIXEL_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _mail(
    *,
    fran: str,
    namn: str,
    amne: str,
    text: str,
    kategori: str,
    bild: bool = False,
) -> dict:
    """Ett testmail.

    `kategori` är det fack ärendet HÖR till, inte det agenten kommer fram till
    — klassificeringen görs av agenten som vanligt. Fältet finns för att
    "Uppdatera" ska kunna hämta nya mail till just den inkorg kunden står i,
    och måste därför vara ett värde ur `config.CATEGORIES`.
    """
    return {
        "fran": fran,
        "namn": namn,
        "amne": amne,
        "text": text,
        "kategori": kategori,
        "bild": bild,
    }


#: Ärenden agenten SKA kunna svara på: en fråga, inget krav på pengar tillbaka,
#: ingen juridik, ingen ilska. Facken är de som kunskapsbasen täcker.
BESVARBARA = [
    _mail(
        fran="johan.berg@mail.se",
        namn="Johan Berg",
        amne="Var är mitt paket?",
        text=(
            "Beställde för en vecka sedan och spårningen har inte uppdaterats på "
            "fyra dagar. Leveransen skulle ta 2–4 vardagar. När kommer paketet?"
        ),
        kategori="leverans",
    ),
    _mail(
        fran="maria.ek@mail.se",
        namn="Maria Ek",
        amne="Har min beställning gått igenom?",
        text=(
            "Hej! Jag la en order i går kväll men har inte fått någon "
            "orderbekräftelse. Har min beställning gått igenom? Ordernummer vet "
            "jag inte eftersom jag inte fått något mail."
        ),
        kategori="orderstatus",
    ),
    _mail(
        fran="lars.strand@mail.se",
        namn="Lars Strand",
        amne="Fråga om öppettider",
        text="Hej, har ni öppet i butiken på midsommarafton? Mvh Lars",
        kategori="ovrigt",
    ),
    _mail(
        fran="ingrid.persson@mail.se",
        namn="Ingrid Persson",
        amne="Kan jag byta leveransadress?",
        text=(
            "Hej! Jag har lagt en order men skrev fel gatunummer. Går det att "
            "ändra adressen innan paketet skickas?"
        ),
        kategori="leverans",
    ),
    _mail(
        fran="anna.lindqvist@mail.se",
        namn="Anna Lindqvist",
        amne="Kan inte logga in på mitt konto",
        text=(
            "Hej! Jag försöker logga in men får bara ett felmeddelande. Jag har "
            "försökt återställa lösenordet men inget mail kommer fram. Bifogar en "
            "skärmdump på felet. Kan ni hjälpa mig?"
        ),
        bild=True,
        kategori="teknisk_support",
    ),
    _mail(
        fran="peter.wallin@mail.se",
        namn="Peter Wallin",
        amne="Hur lång är garantin?",
        text=(
            "Hej, jag köpte en produkt hos er i våras. Hur lång garantitid gäller, "
            "och vad täcker den om det visar sig vara ett tillverkningsfel?"
        ),
        kategori="garanti",
    ),
    _mail(
        fran="sofia.holmberg@mail.se",
        namn="Sofia Holmberg",
        amne="Vad kostar frakten till Norrland?",
        text=(
            "Hej! Vi sitter i Umeå. Vad kostar frakten dit, och finns det fri frakt "
            "över någon summa?"
        ),
        kategori="leverans",
    ),
    _mail(
        fran="kalle.astrom@mail.se",
        namn="Kalle Åström",
        amne="Får jag en kurs för nya medarbetare?",
        text=(
            "Vi har anställt fyra nya på lagret. Kan vi boka en utbildning för dem, "
            "och hur många deltagare får plats per tillfälle?"
        ),
        kategori="utbildning",
    ),
    _mail(
        fran="nina.forsberg@mail.se",
        namn="Nina Forsberg",
        amne="Sidan laddar inte i kassan",
        text=(
            "Hej, när jag ska betala står sidan bara och laddar. Har provat både "
            "Chrome och Safari. Vad kan jag göra?"
        ),
        kategori="teknisk_support",
    ),
    _mail(
        fran="omar.haddad@mail.se",
        namn="Omar Haddad",
        amne="När skickas min beställning?",
        text=(
            "Hej! Jag lade en order i tisdags och den står fortfarande som "
            "behandlas. När skickas den?"
        ),
        kategori="orderstatus",
    ),
    _mail(
        fran="elin.sandberg@mail.se",
        namn="Elin Sandberg",
        amne="Hämtar ni i ombud eller hem till dörren?",
        text=(
            "Hej! Levererar ni till ombud eller hem till dörren? Jag är sällan hemma "
            "på dagarna."
        ),
        kategori="leverans",
    ),
    _mail(
        fran="mats.ohlsson@mail.se",
        namn="Mats Ohlsson",
        amne="Behöver kvitto för bokföringen",
        text=(
            "Hej, jag behöver kvittot på min order till bokföringen. Kan ni skicka "
            "det som PDF? Momsen ska framgå."
        ),
        kategori="betalning",
    ),
    # Påfyllnad så att VARJE fack har minst tre ärenden. Utan den hade
    # "Uppdatera" i ett smalt fack gett samma två mail varje gång — alltså
    # exakt felet poolen en gång infördes för att lösa, fast per inkorg.
    _mail(
        fran="hanna.lindgren@mail.se",
        namn="Hanna Lindgren",
        amne="Gäller garantin om jag köpt via en återförsäljare?",
        text=(
            "Hej! Jag köpte produkten hos en av era återförsäljare och inte direkt "
            "av er. Gäller garantin ändå, och är det er eller butiken jag ska vända "
            "mig till om något går sönder?"
        ),
        kategori="garanti",
    ),
    _mail(
        fran="bjorn.ek@mail.se",
        namn="Björn Ek",
        amne="Garantin efter en reparation",
        text=(
            "Hej, ni lagade min enhet i mars. Börjar garantitiden om efter en "
            "reparation, eller löper den vidare från köpet?"
        ),
        kategori="garanti",
    ),
    _mail(
        fran="lovisa.hallberg@mail.se",
        namn="Lovisa Hallberg",
        amne="Utbildning på plats eller digitalt?",
        text=(
            "Hej! Vi funderar på en genomgång för vårt team. Håller ni utbildningen "
            "på plats hos oss eller digitalt, och hur lång är den?"
        ),
        kategori="utbildning",
    ),
    _mail(
        fran="samir.aziz@mail.se",
        namn="Samir Aziz",
        amne="Finns det material att läsa i förväg?",
        text=(
            "Hej, vi har utbildning bokad nästa månad. Finns det något underlag vi "
            "kan gå igenom innan, så att tiden räcker till det praktiska?"
        ),
        kategori="utbildning",
    ),
    _mail(
        fran="karin.vikstrom@mail.se",
        namn="Karin Vikström",
        amne="Kan jag lägga till en vara i min order?",
        text=(
            "Hej! Jag la en beställning i morse och glömde en artikel. Går det att "
            "lägga till den innan ni packar, eller måste jag göra en ny order?"
        ),
        kategori="orderstatus",
    ),
    _mail(
        fran="anders.molin@mail.se",
        namn="Anders Molin",
        amne="Kan vi betala mot faktura?",
        text=(
            "Hej, vi är ett företag och vill helst betala mot faktura med 30 dagar. "
            "Går det att lägga upp, och behöver ni något från oss först?"
        ),
        kategori="betalning",
    ),
    _mail(
        fran="petra.sjogren@mail.se",
        namn="Petra Sjögren",
        amne="Var hittar jag era villkor?",
        text=(
            "Hej! Jag hittar inte era köpvillkor på sajten. Kan ni skicka en länk "
            "eller bifoga dem?"
        ),
        kategori="ovrigt",
    ),
    _mail(
        fran="daniel.ahlin@mail.se",
        namn="Daniel Åhlin",
        amne="Appen loggar ut mig hela tiden",
        text=(
            "Hej, appen loggar ut mig var tionde minut sedan förra uppdateringen. "
            "Samma sak på både telefon och surfplatta. Finns det någon inställning "
            "jag missat?"
        ),
        kategori="teknisk_support",
    ),
    _mail(
        fran="mikaela.rosen@mail.se",
        namn="Mikaela Rosén",
        amne="Hur går ett byte till?",
        text=(
            "Hej! Jag beställde fel storlek. Hur gör jag för att byta, och står jag "
            "för returfrakten?"
        ),
        kategori="retur_reklamation",
    ),
]

#: Ärenden som SKA nå en människa: pengar tillbaka, juridik, GDPR eller uttalad
#: ilska. De finns med för att spärrarna är en del av produkten — en demo där
#: agenten svarar på allt visar en agent som gissar.
ESKALERANDE = [
    _mail(
        fran="erik.holm@mail.se",
        namn="Erik Holm",
        amne="Trasig vara — kräver återbetalning",
        text=(
            "Vasen kom fram i tusen bitar trots bubbelplast. Helt oacceptabelt!! "
            "Jag vill ha pengarna tillbaka omgående, annars anmäler jag er till ARN."
        ),
        kategori="retur_reklamation",
    ),
    _mail(
        fran="sara.nystrom@mail.se",
        namn="Sara Nyström",
        amne="Dubbeldragning på kortet",
        # Kravet på pengarna tillbaka är det som gör ärendet eskalerande, och
        # det måste stå i texten. Utan raden var mailet en vanlig betalfråga
        # som hamnade i ESKALERANDE — den eskalerade bara så länge
        # kunskapsbasen saknade täckning för betalningar, alltså av fel skäl.
        # När demons KB fick betalartiklar blev poolens löfte osant, och testet
        # som vaktar blandningen började falla ungefär var fjärde körning.
        text=(
            "Jag ser två dragningar på exakt samma belopp för min beställning. "
            "Har ni debiterat mig dubbelt? Jag vill ha den felaktiga dragningen "
            "återbetald omgående."
        ),
        kategori="betalning",
    ),
    _mail(
        fran="tobias.lund@mail.se",
        namn="Tobias Lund",
        amne="Radera mina personuppgifter",
        text=(
            "Hej. Jag vill att ni raderar mitt konto och alla mina personuppgifter "
            "enligt GDPR. Bekräfta när det är gjort."
        ),
        kategori="ovrigt",
    ),
    _mail(
        fran="camilla.berg@mail.se",
        namn="Camilla Berg",
        amne="Tredje gången varan är fel",
        text=(
            "Det här är tredje gången jag får fel storlek. Jag är riktigt trött på "
            "det här och kräver kompensation för besväret."
        ),
        kategori="retur_reklamation",
    ),
]

#: Hur många av de valda som får vara eskalerande när ingen kategori är vald.
#: Ett av sex speglar hur en riktig inkorg ser ut — de flesta ärenden är
#: frågor, inte tvister.
ESKALERANDE_ANDEL = 1


def _pool_for(kategori: str | None) -> list[dict]:
    """Mailen som hör till ett fack, besvarbara och eskalerande tillsammans."""
    alla = BESVARBARA + ESKALERANDE
    if not kategori:
        return alla
    return [m for m in alla if m.get("kategori") == kategori]


def kategorier_med_mail() -> list[str]:
    """Facken poolen faktiskt kan fylla. Används av testerna."""
    return sorted({m["kategori"] for m in BESVARBARA + ESKALERANDE})


def build_mock_emails(
    *,
    antal: int = 8,
    kategori: str | None = None,
    slump: random.Random | None = None,
) -> list[InboundEmail]:
    """Ett NYTT urval testmail varje gång, med blandat utfall.

    `kategori` begränsar urvalet till ett fack. Det är vad "Uppdatera" gör när
    kunden står i ett filtrerat läge: nya mail till DEN inkorgen, inte till
    alla. Utan den möjligheten fyllde varje klick hela inkorgen igen, och det
    fack man tittade på råkade få noll nya.

    Blandningen gäller bara det ofiltrerade läget. Ett fack innehåller det det
    innehåller — begär man "retur_reklamation" ska man få returärenden, inte en
    kvot besvarbara som poolen inte har.

    `slump` går att skicka in i tester för ett förutsägbart urval; i drift är
    poängen den motsatta — två klick i rad ska inte ge samma inkorg.
    """
    rng = slump or random.Random()
    batch = uuid.uuid4().hex[:8]  # unika message-ids per seedning

    if kategori:
        pool = _pool_for(kategori)
        valda = rng.sample(pool, min(antal, len(pool))) if pool else []
    else:
        # Ett ärende ur VARJE fack, inte sex slumpade ur högen.
        #
        # Sex slumpade lämnade regelmässigt två eller tre inkorgar tomma, och
        # en kund som klickar sig runt bland facken hittar då tomma flikar och
        # drar slutsatsen att sorteringen inte fungerar. Ett per fack visar det
        # knappen finns för: att posten hamnar rätt.
        #
        # Blandningen besvarbart/eskalerande sköter sig själv — facken
        # betalning och retur_reklamation bär de eskalerande ärendena — men
        # kvoten garanteras nedan, för en demo utan en enda eskalering visar en
        # agent som svarar på allt.
        valda = []
        for fack in sorted({m["kategori"] for m in BESVARBARA + ESKALERANDE}):
            pool = _pool_for(fack)
            if pool:
                valda.append(rng.choice(pool))

        if not any(m in ESKALERANDE for m in valda):
            ersatt = rng.choice(ESKALERANDE)
            for index, m in enumerate(valda):
                if m["kategori"] == ersatt["kategori"]:
                    valda[index] = ersatt
                    break
            else:
                valda.append(ersatt)

        rng.shuffle(valda)
        valda = valda[:antal] if antal < len(valda) else valda

    mail = []
    for index, scenario in enumerate(valda, start=1):
        mail.append(
            InboundEmail(
                provider="mock",
                provider_message_id=f"mock-{batch}-{index}",
                from_email=scenario["fran"],
                from_name=scenario["namn"],
                subject=scenario["amne"],
                body_text=scenario["text"],
                attachments=(
                    [
                        InboundAttachment(
                            filename="skarmdump-fel.png",
                            content_type="image/png",
                            data_url=_RED_PIXEL_PNG,
                            is_image=True,
                            size_bytes=68,
                        )
                    ]
                    if scenario["bild"]
                    else []
                ),
            )
        )
    return mail
