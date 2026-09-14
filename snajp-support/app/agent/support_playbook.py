"""support/v1 — playbook-DEFINITIONEN (plan Del E).

Själva körningen ligger i app/agent/support_agent.py, som kör ETT LLM-anrop
per steg via app/agent/step_runner.py. Den här modulen deklarerar bara
kedjan och dess förvillkor.

Historik värd att känna till: en tidigare version renderade alla steg till
EN hopklistrad systemprompt (`render_support_instructions`). Den togs bort
— den gjorde läsgarantin overifierbar, eftersom man bara kunde se vad som
injicerats, aldrig vad modellen faktiskt använt. Förvillkorsgrinden
(`requires`) verkställs nu per steg vid själva anropet i step_runner.
"""

from __future__ import annotations

from ..agentcore.packs import Playbook, PlaybookStep

SUPPORT_V1 = Playbook(
    name="support/v1",
    steps=(
        PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",)),
        PlaybookStep(skill="cs:customer-research", requires=("skill:cs:ticket-triage",)),
        # Overlayen bär samtalsformen: hälsa bara i första turen, ingen
        # avslutningsfras i chatt, och kort öppen motfråga när kunden inte sagt
        # vad ärendet gäller. cs:draft-response är skriven för MEJL, där både
        # hälsning och avsked hör till formen — utan overlayen ser varje replik
        # i en chatt ut som ett nytt brev.
        # temperature 0.5: utkastet är ett formuleringssteg, och 0.3 gav
        # svar som öppnade likadant i ärende efter ärende. Fakta kommer ur
        # KB-underlaget och grindas efteråt — det är formen som får variera.
        PlaybookStep(
            skill="cs:draft-response",
            requires=("skill:cs:customer-research",),
            overlay="support-conversation",
            temperature=0.5,
        ),
        # thinking PÅ, medvetet mot den globala AV-defaulten: det enda steget
        # där "ska detta till en människa?" avgörs. En felaktig eskalering
        # (åt endera hållet) är dyrare än den extra latensen. Beslut 2026-08-07.
        #
        # VILLKORAT sedan 2026-09-02: körs bara när det finns något att
        # bedöma — kunskapsbasen saknade svaret, ärendet är säkerhetskritiskt
        # (påhopp, uppsägningsrisk, triageflagga, lågt sentiment, känsligt
        # mönster) eller kunden ber uttryckligen om en människa. På lyckliga
        # flödet röstade modellen i praktiken alltid "nej" och kodbeslutet
        # OR:ar ändå de oberoende villkoren — steget var kedjans dyraste
        # anrop (thinking) för noll informationsvinst just där.
        PlaybookStep(
            skill="cs:customer-escalation",
            requires=("skill:cs:draft-response",),
            thinking="enabled",
            condition="kb_gap_or_safety_or_human_request",
        ),
        # VILLKORAT sedan 2026-08-26: körs bara när kunskapsbasen saknade
        # svaret eller ärendet är säkerhetskritiskt. Ett ärende där KB bar
        # svaret och inget eskalerade har per definition ingen lucka att
        # skriva en artikel om — steget var där ren kostnad (~1 anrop av 6)
        # med noll utbyte. Utdatan persisteras numera som förslag
        # (agent_suggestions, migration 051) i stället för att kastas.
        PlaybookStep(
            skill="cs:kb-article",
            requires=("skill:cs:customer-escalation",),
            condition="kb_gap_or_escalation",
        ),
        # ÖPPEN FRÅGA: thinking-läge inte beslutat här. Triggas bara när
        # uppsägningsrisk redan är sann (dvs. ärendet eskalerar oavsett) —
        # kan höra ihop med cs:customer-escalation-beslutet ovan, men
        # användaren sa uttryckligen "vid eskalering" (singular) om
        # bedömningssteget. Fråga innan du sätter thinking="enabled" här.
        PlaybookStep(
            skill="snajp:retention-conversation",
            requires=("skill:cs:draft-response",),
            condition="cancellation_risk",
        ),
        # Samma overlay här: humaniseraren är sista handen på texten och skulle
        # annars glatt sätta tillbaka ett "Hej" och en avslutningsfras som
        # utkaststeget just avstått från. Overlays nycklas på syfte, inte på
        # skill (se agentcore/overlays.py), så den delas mellan stegen.
        # temperature 0.7: humaniserarens enda uppgift är naturlig svenska,
        # och den kördes tidigare på samma 0.3 som analysstegen — den mest
        # formuleringstunga delen av kedjan var alltså den kallaste.
        PlaybookStep(
            skill="snajp:humanizer-svenska",
            # cs:draft-response och inte cs:kb-article: humaniseraren
            # bearbetar UTKASTET, och kb-artikelstegets utdata når aldrig
            # svaret. Det gamla kravet band humaniseraren till ett steg som
            # numera är villkorat — och hade fällt varje ärende där
            # kunskapssteget hoppats över, på ett beroende som aldrig fanns.
            requires=("skill:cs:draft-response",),
            overlay="support-conversation",
            temperature=0.7,
        ),
    ),
)
