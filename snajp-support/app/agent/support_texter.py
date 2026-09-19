"""Supportagentens fasta texter, per språk (bd snipe-xtr).

## Varför fasta texter alls

Fyra repliker skrivs av KOD och inte av modellen, med flit: kvittensen medan
en människa inte svarat än (ingen modell körs i ett överlämnat samtal),
överlämningsbeskedet när modellen inte gav något att bygga på, raden som
läggs till när modellens eskaleringsbedömning lämnar över, och
osäkerhetssvaret när faktagrinden fäller ett svar två gånger. Ett löfte om en
människa får bara ges när ärendet faktiskt är överlämnat — därför är det kod.

## Språken

Modellskriven text följer kundens språk (support_regler.svarsprak). De fasta
texterna finns på svenska och engelska; ett tredje språk får den engelska,
som är den närmaste gemensamma nämnaren för en kund som inte skriver
svenska. Varje nyckel har flera varianter, så att en kund som träffar samma
text två gånger inte läser exakt samma mening två gånger.
"""

from __future__ import annotations

import random

_TEXTER: dict[str, dict[str, tuple[str, ...]]] = {
    "sv": {
        "kvittens": (
            "Det är tillagt i ärendet, så kollegan ser det direkt när ärendet tas "
            "över. Svaret kommer här i chatten.",
            "Tack, jag har lagt till det. Kollegan som tar över ser hela samtalet "
            "och svarar här.",
            "Noterat i ärendet. Du behöver inte upprepa något — svaret kommer i den "
            "här chatten.",
        ),
        "overlamningsrad": (
            "Jag kopplar också in en kollega som tar över här i chatten. Hela "
            "samtalet följer med, så du behöver inte börja om.",
            "En kollega tar över härifrån, i samma chatt och med hela samtalet "
            "framför sig.",
        ),
        "overlamningssvar": (
            "Det här behöver en kollega titta på, så jag lämnar över ärendet. Svaret "
            "kommer här i chatten, och hela samtalet följer med — du behöver inte "
            "upprepa något.",
            "Jag kopplar in en kollega som tar över härifrån, i samma chatt. Hela "
            "samtalet följer med, så du behöver inte börja om.",
            "En kollega tar över ärendet nu. Du får svaret här i chatten, och "
            "kollegan ser allt vi skrivit hittills.",
        ),
        "osakerhet": (
            "Det här vill jag inte gissa på, och jag hittar inget säkert svar i det "
            "underlag jag har. Vill du att jag kopplar in en kollega?",
            "Jag har ingen uppgift om det som jag kan stå för. Ska jag koppla in en "
            "kollega som kan svara säkert?",
        ),
        "tomt": (
            "Där fick jag inte ihop ett bra svar. Kan du beskriva vad du är ute "
            "efter på ett annat sätt, så gör jag ett nytt försök?",
            "Jag vill inte gissa mig till ett svar här. Berätta gärna lite mer om "
            "vad du behöver, så tittar jag igen.",
            "Den frågan kunde jag inte besvara ordentligt på första försöket. "
            "Formulera den gärna på ett annat sätt så löser vi det.",
        ),
    },
    "en": {
        "kvittens": (
            "That's added to your case, so my colleague sees it as soon as they "
            "take over. The reply will come here in the chat.",
            "Thanks, I've added that. The colleague taking over sees the whole "
            "conversation and will reply here.",
            "Noted on your case. No need to repeat anything — the reply will come "
            "in this chat.",
        ),
        "overlamningsrad": (
            "I'm also bringing in a colleague who will take over here in the chat. "
            "The whole conversation comes along, so you won't have to start over.",
            "A colleague will take it from here, in the same chat and with the whole "
            "conversation in front of them.",
        ),
        "overlamningssvar": (
            "This needs a colleague to look at it, so I'm handing your case over. "
            "The reply will come here in the chat, and the whole conversation comes "
            "along — no need to repeat anything.",
            "I'm bringing in a colleague who will take it from here, in the same "
            "chat. The whole conversation comes along, so you won't have to start over.",
            "A colleague is taking over your case now. You'll get the reply here in "
            "the chat, and they can see everything we've written so far.",
        ),
        "osakerhet": (
            "I don't want to guess on this, and I can't find a reliable answer in "
            "the information I have. Would you like me to bring in a colleague?",
            "I don't have information on that I can stand behind. Shall I bring in "
            "a colleague who can give you a reliable answer?",
        ),
        "tomt": (
            "I couldn't put together a good answer there. Could you describe what "
            "you're looking for another way, so I can try again?",
            "I don't want to guess at an answer here. Tell me a bit more about what "
            "you need and I'll take another look.",
        ),
    },
}

NYCKLAR = tuple(_TEXTER["sv"])


def text(nyckel: str, sprak: str | None) -> str:
    """En slumpad variant av den fasta texten på kundens språk.

    Svenska för "sv" eller ett saknat språk; engelska för alla andra — den
    fasta texten finns inte på varje språk, och engelska når fler än svenska
    gör hos en kund som inte skriver svenska."""
    lista = _TEXTER["sv" if (sprak or "sv") == "sv" else "en"][nyckel]
    return random.choice(lista)
