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
    bild: bool = False,
) -> dict:
    return {"fran": fran, "namn": namn, "amne": amne, "text": text, "bild": bild}


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
    ),
    _mail(
        fran="lars.strand@mail.se",
        namn="Lars Strand",
        amne="Fråga om öppettider",
        text="Hej, har ni öppet i butiken på midsommarafton? Mvh Lars",
    ),
    _mail(
        fran="ingrid.persson@mail.se",
        namn="Ingrid Persson",
        amne="Kan jag byta leveransadress?",
        text=(
            "Hej! Jag har lagt en order men skrev fel gatunummer. Går det att "
            "ändra adressen innan paketet skickas?"
        ),
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
    ),
    _mail(
        fran="peter.wallin@mail.se",
        namn="Peter Wallin",
        amne="Hur lång är garantin?",
        text=(
            "Hej, jag köpte en produkt hos er i våras. Hur lång garantitid gäller, "
            "och vad täcker den om det visar sig vara ett tillverkningsfel?"
        ),
    ),
    _mail(
        fran="sofia.holmberg@mail.se",
        namn="Sofia Holmberg",
        amne="Vad kostar frakten till Norrland?",
        text=(
            "Hej! Vi sitter i Umeå. Vad kostar frakten dit, och finns det fri frakt "
            "över någon summa?"
        ),
    ),
    _mail(
        fran="kalle.astrom@mail.se",
        namn="Kalle Åström",
        amne="Får jag en kurs för nya medarbetare?",
        text=(
            "Vi har anställt fyra nya på lagret. Kan vi boka en utbildning för dem, "
            "och hur många deltagare får plats per tillfälle?"
        ),
    ),
    _mail(
        fran="nina.forsberg@mail.se",
        namn="Nina Forsberg",
        amne="Sidan laddar inte i kassan",
        text=(
            "Hej, när jag ska betala står sidan bara och laddar. Har provat både "
            "Chrome och Safari. Vad kan jag göra?"
        ),
    ),
    _mail(
        fran="omar.haddad@mail.se",
        namn="Omar Haddad",
        amne="När skickas min beställning?",
        text=(
            "Hej! Jag lade en order i tisdags och den står fortfarande som "
            "behandlas. När skickas den?"
        ),
    ),
    _mail(
        fran="elin.sandberg@mail.se",
        namn="Elin Sandberg",
        amne="Hämtar ni i ombud eller hem till dörren?",
        text=(
            "Hej! Levererar ni till ombud eller hem till dörren? Jag är sällan hemma "
            "på dagarna."
        ),
    ),
    _mail(
        fran="mats.ohlsson@mail.se",
        namn="Mats Ohlsson",
        amne="Behöver kvitto för bokföringen",
        text=(
            "Hej, jag behöver kvittot på min order till bokföringen. Kan ni skicka "
            "det som PDF? Momsen ska framgå."
        ),
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
    ),
    _mail(
        fran="tobias.lund@mail.se",
        namn="Tobias Lund",
        amne="Radera mina personuppgifter",
        text=(
            "Hej. Jag vill att ni raderar mitt konto och alla mina personuppgifter "
            "enligt GDPR. Bekräfta när det är gjort."
        ),
    ),
    _mail(
        fran="camilla.berg@mail.se",
        namn="Camilla Berg",
        amne="Tredje gången varan är fel",
        text=(
            "Det här är tredje gången jag får fel storlek. Jag är riktigt trött på "
            "det här och kräver kompensation för besväret."
        ),
    ),
]

#: Hur många av de valda som får vara eskalerande. Ett av sex speglar hur en
#: riktig inkorg ser ut — de flesta ärenden är frågor, inte tvister.
ESKALERANDE_ANDEL = 1


def build_mock_emails(*, antal: int = 6, slump: random.Random | None = None) -> list[InboundEmail]:
    """Ett NYTT urval testmail varje gång, med blandat utfall.

    `slump` går att skicka in i tester för ett förutsägbart urval; i drift är
    poängen den motsatta — två klick i rad ska inte ge samma inkorg.
    """
    rng = slump or random.Random()
    batch = uuid.uuid4().hex[:8]  # unika message-ids per seedning

    antal_eskalerande = min(ESKALERANDE_ANDEL, antal, len(ESKALERANDE))
    valda = rng.sample(ESKALERANDE, antal_eskalerande)
    valda += rng.sample(BESVARBARA, min(antal - antal_eskalerande, len(BESVARBARA)))
    rng.shuffle(valda)

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
