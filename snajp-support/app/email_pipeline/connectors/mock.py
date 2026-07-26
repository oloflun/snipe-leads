"""Mock-connector: svenska testmail för att demonstrera hela pipelinen utan
en riktig inkorg. En av bilderna är en riktig (minimal) PNG så att bilage-
och vision-flödet exerceras på riktigt.
"""

import uuid

from ..models import InboundAttachment, InboundEmail

# 1x1 röd PNG — giltig bild, minimal storlek.
_RED_PIXEL_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def build_mock_emails() -> list[InboundEmail]:
    batch = uuid.uuid4().hex[:8]  # unika message-ids per seedning
    return [
        InboundEmail(
            provider="mock",
            provider_message_id=f"mock-{batch}-1",
            from_email="anna.lindqvist@mail.se",
            from_name="Anna Lindqvist",
            subject="Kan inte logga in på mitt konto",
            body_text=(
                "Hej! Jag försöker logga in men får bara ett felmeddelande. Jag har "
                "försökt återställa lösenordet men inget mail kommer fram. Bifogar en "
                "skärmdump på felet. Kan ni hjälpa mig?"
            ),
            attachments=[
                InboundAttachment(
                    filename="skarmdump-fel.png",
                    content_type="image/png",
                    data_url=_RED_PIXEL_PNG,
                    is_image=True,
                    size_bytes=68,
                )
            ],
        ),
        InboundEmail(
            provider="mock",
            provider_message_id=f"mock-{batch}-2",
            from_email="johan.berg@mail.se",
            from_name="Johan Berg",
            subject="Var är mitt paket?",
            body_text=(
                "Beställde för en vecka sedan och spårningen har inte uppdaterats på "
                "fyra dagar. Leveransen skulle ta 2–4 vardagar. När kommer paketet?"
            ),
        ),
        InboundEmail(
            provider="mock",
            provider_message_id=f"mock-{batch}-3",
            from_email="sara.nystrom@mail.se",
            from_name="Sara Nyström",
            subject="Dubbeldragning på kortet",
            body_text=(
                "Jag ser två dragningar på exakt samma belopp för min beställning. "
                "Har ni debiterat mig dubbelt? Vill gärna få det utrett."
            ),
        ),
        InboundEmail(
            provider="mock",
            provider_message_id=f"mock-{batch}-4",
            from_email="erik.holm@mail.se",
            from_name="Erik Holm",
            subject="Trasig vara — kräver återbetalning",
            body_text=(
                "Vasen kom fram i tusen bitar trots bubbelplast. Helt oacceptabelt!! "
                "Jag vill ha pengarna tillbaka omgående, annars anmäler jag er till ARN."
            ),
        ),
        InboundEmail(
            provider="mock",
            provider_message_id=f"mock-{batch}-5",
            from_email="maria.ek@mail.se",
            from_name="Maria Ek",
            subject="Har min beställning gått igenom?",
            body_text=(
                "Hej! Jag la en order i går kväll men har inte fått någon "
                "orderbekräftelse. Har min beställning gått igenom? Ordernummer vet "
                "jag inte eftersom jag inte fått något mail."
            ),
        ),
        InboundEmail(
            provider="mock",
            provider_message_id=f"mock-{batch}-6",
            from_email="lars.strand@mail.se",
            from_name="Lars Strand",
            subject="Fråga om öppettider",
            body_text="Hej, har ni öppet i butiken på midsommarafton? Mvh Lars",
        ),
    ]
