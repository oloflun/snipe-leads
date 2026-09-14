"""Leads Fas C (Del F): outreach.

sa:draft-outreach + mk:cold-email/references/personalization.md  (skapa)
  -> mk:cold-email/SKILL.md                                       (granska)
  -> snajp:humanizer-svenska                                      (ALLTID sist)

sa:draft-outreach producerar som standard även LinkedIn-kopia ("Copy for
LinkedIn (always)", SKILL.md rad 40). Den utdatan stängs av här — krockar
med LinkedIn-policyn i G4 (proveniensgrinden tillåter LinkedIn bara som
verifiering, aldrig som kanal). Vi använder e-postvägen. sa:draft-outreach
kräver självt "No markdown formatting" (rad 291) — samma gate som
cs:draft-response (app/agent/tools.strip_markdown) tillämpas här också,
humanizern får inte återinföra formatering.
"""

from __future__ import annotations

from ..agent.tools import strip_markdown
from ..agentcore.packs import Playbook, PlaybookStep, RunLedger, check_preconditions

# thinking AV i hela leadsflödet — se research_playbook.THINKING för beslutet.
from .research_playbook import THINKING  # noqa: E402

# De hårda reglerna (LinkedIn-förbudet, ren text, språkläget) låg tidigare som
# en f-sträng mitt i leads_agent.run_outreach_draft, alltså i USER-position och
# på ett ställe ingen letade. Nu är de en overlay i SYSTEM-position: samma text,
# starkare placering, och versionerad via overlay_hash i pack_version.
_HARD_RULES = "leads-hard-rules"

# Temperaturerna speglar supportbeslutet 2026-08-25: 0.3 på allt gav svar som
# återanvände samma fraser ordagrant mellan ärenden, så FORMULERINGSSTEG fick
# 0.5 (utkast) och 0.7 (humanizer) medan analys- och bedömningssteg behöll den
# kalla defaulten. Leads-kedjan fick aldrig samma justering — utkastet och
# humaniseraren var de kallaste stegen i just den kedja vars hela uppgift är
# formulering, och 2026-08-09-utkastens likformighet ("supportagenten",
# "returfrågor" som ämnesrader) är precis det symptomet. Granskningssteget
# (mk:cold-email hel) förblir kallt: det BEDÖMER, det formulerar inte.
OUTREACH_V1 = Playbook(
    name="leads/outreach-v1",
    steps=(
        PlaybookStep(
            skill="sa:draft-outreach",
            requires=("offer_selected",),
            overlay=_HARD_RULES,
            thinking=THINKING,
            temperature=0.5,
        ),
        PlaybookStep(
            skill="mk:cold-email",
            requires=("skill:sa:draft-outreach",),
            scope=("references/personalization.md",),
            rationale="Skapandesteget behöver personaliseringssignaler, inte hela mk:cold-email-metodiken än.",
            overlay=_HARD_RULES,
            thinking=THINKING,
            temperature=0.5,
        ),
        # granska: hel skill — bedömning, inte formulering; kall default.
        PlaybookStep(
            skill="mk:cold-email",
            requires=("skill:mk:cold-email",),
            overlay=_HARD_RULES,
            thinking=THINKING,
        ),
        PlaybookStep(
            skill="snajp:humanizer-svenska",
            requires=("skill:mk:cold-email",),
            overlay=_HARD_RULES,
            thinking=THINKING,
            temperature=0.7,
        ),
    ),
)

# V2 (2026-09-02, kostnadsarbetet): 4 anrop -> 2, med SAMMA skillinnehåll.
#
# Steg 1 slår ihop V1:s skapa+personalisera+granska till ETT anrop:
# sa:draft-outreach (hel) + mk:cold-email via extra_skills i SAMMA steg —
# personaliseringsreferensen och granskningschecklistan (§ Quality Check +
# § What to Avoid, sektionerna som utgör själva granskningen i SKILL.md).
# Skilltexterna är alltså DESAMMA som V1 injicerade, i ett anrop i stället
# för tre — "ersätt workflowen, inte skillsen".
#
# Steg 2 är humanizern, oförändrat HEL och oförändrat SIST: INV-LANG-002
# (humanizern måste vara den som rörde texten sist) bevaras strukturellt
# utan invariantändring. Grundningscykeln (villkorad, max 1 runda) och
# tomtext-omförsöket behålls exakt — se run_outreach_draft_v2 i
# app/agent/leads_research_v2.py.
OUTREACH_V2 = Playbook(
    name="leads/outreach-v2",
    steps=(
        PlaybookStep(
            skill="sa:draft-outreach",
            requires=("offer_selected",),
            overlay=_HARD_RULES,
            thinking=THINKING,
            temperature=0.5,
            # Per-steg-modellval (Sebbes beslut 2026-09-02): utkastfasens
            # INPUT är 55 % av leadkostnaden, och stegets jobb — fem rader
            # text efter ett regelverk som står i prompten — bär en lättare
            # modell. LEADS_DRAFT_MODEL styr per miljö; tom = ärv MODEL.
            # Flippas först efter domarbenchmarken.
            model_setting="leads_draft_model",
            # sa:draft-outreach skopas (2026-09-02). Steget bar 51 % av kedjans
            # kr/lead på in-sidan, så skillen mättes sektionsvis. Kvar är varje
            # REGEL och stegets process: Execution Flow (Steg 1-5), kallmejls-
            # mallen, stilguiden, What NOT to Do — plus det arbetade Notion-
            # exemplet, som är ett kallt mejl, alltså stegets EGEN texttyp.
            # (Lärdomen från humanizerskopningen nedan: offra inte exemplet i
            # måltexttypen. Här behövde det inte offras — "§ Example" och
            # exempelrubriken balanserar varandras kodstaket och tas ihop.)
            #
            # Bortskopat, i storleksordning: "How It Works" (1 278) och
            # "Connectors (Optional)" (355) + "Capability by Connector" (400)
            # beskriver en connector-drivet Gmail-flöde som inte finns här;
            # varm/re-engagement/post-event-mallarna (726) är fel scenario;
            # "Channel Selection" (307) och "LinkedIn Message (if no email)"
            # (178) avgör en kanalfråga som _HARD_RULES redan har avgjort.
            #
            # Och "Company Configuration [CUSTOMIZE]" (533): den är OIFYLLD i
            # skillen — "[Your Name]", "[Customer 1]: [Result]", "My company:
            # [Company Name]", default-CTA "Worth a 15-min call?". Den laddades
            # hel fram till nu, så platshållarna gick in i varje svenskt
            # kallmejl. Hur ofta de FÄRGADE utdatan är en annan fråga: över
            # samtliga benchmarkkörningar slår CTA:n igenom i 1 av 18 utkast
            # ("värt 15 minuter"), så modellen skriver oftast en egen. Att
            # skopa bort blocket är alltså i första hand kostnad, i andra hand
            # en undanröjd felkälla — inte en fix på ett pågående fel.
            # Ska avsändaruppgifter in i prompten hör de hemma i tenant-
            # konfigurationen, inte som skelett i en skilltext.
            rationale=(
                "V2-kostnadsarbetet. sa:draft-outreach skopas till processen "
                "(Execution Flow), kallmejlsmallen, stilguiden, What NOT to Do "
                "och det arbetade exemplet; bort går connector-flödet, fel "
                "scenariomallar, kanalvalet (avgjort av hårda reglerna) och det "
                "oifyllda [CUSTOMIZE]-blocket. mk:cold-email skopas till "
                "personaliseringsreferensen + granskningssektionerna (Quality "
                "Check, What to Avoid) — resten är metodik för kampanjer och "
                "uppföljningssekvenser som steget inte utför."
            ),
            scope=(
                "§ Execution Flow",
                "§ Cold Outreach (No Prior Relationship)",
                "§ Email Style Guidelines",
                "§ What NOT to Do",
                "§ Example",
                "§ Outreach Draft: David Tibbitts @ Notion",
            ),
            extra_skills=(
                (
                    "mk:cold-email",
                    (
                        "references/personalization.md",
                        "§ Quality Check",
                        "§ What to Avoid",
                    ),
                ),
            ),
        ),
        PlaybookStep(
            skill="snajp:humanizer-svenska",
            requires=("skill:sa:draft-outreach",),
            overlay=_HARD_RULES,
            thinking=THINKING,
            temperature=0.7,
            # EGET fält, INTE utkastets. Distinktionen är hela poängen med
            # per-steg-valet: domarbenchmarken 2026-09-02 underkände lite-
            # modellen på humanizern separat (tappade å/ä/ö, 3/4 domar) —
            # en miljö som sätter LEADS_DRAFT_MODEL för utkastet får ALDRIG
            # tyst dra med sig sista handen på texten. Stod fel
            # (leads_draft_model) efter en patchflytt 2026-09-02; låst av
            # test_stegen_har_skilda_modellfalt i test_leads_v2_wiring.py.
            model_setting="leads_humanizer_model",
            # Skopningen (2026-09-02, uppmätt i två steg). Hela skillen är
            # 27 081 tecken; den skopade renderingen 16 255 — 40 % bort.
            #
            # Steg 1 (1713ebf): exempelblocket (6 851) och registren för
            # rapport/artikel/socialt (842) bort. Steg 2 (den här): tre mönster
            # ur katalogen som inte kan uppstå i ett kallmejl — 10 (sociala
            # medier: hashtags, inläggsavslut), 14 (kunskapsavgränsning: "inom
            # ramen för mina kunskaper") och 16 (bullets/emoji; ren text krävs
            # redan av _HARD_RULES och strip_markdown städar efteråt). Kvar är
            # de 13 andra mönstren, rösten, affärsregistret, processen,
            # utdataformatet och snabbreferensen — varje REGEL som styr ett
            # kallt mejl. Mönstren listas därför var för sig i stället för
            # under katalogrubriken.
            #
            # Prövat och förkastat: att ge tillbaka "§ Exempel 1: Affärs-
            # skrivande" (h3-rubriken är valbar för sig — ett tidigare
            # påstående här om att den var odelbar var fel). Uppmätt på 5
            # fixtures blev exemplet dyrare (8 780 mot 8 254 in/anrop) och
            # HOMOGENISERADE: tre av fyra mejl öppnade erbjudandet med samma
            # "vi (på Snajp) har byggt/utvecklat en svensk AI-supportagent",
            # plus två grammatikfel ("er egna", tilltalsbyte). Utan exemplet
            # skrev modellen fyra olika öppningar. Ett arbetat exempel i
            # måltexttypen är alltså en mall, inte en försäkring, i det här
            # steget.
            #
            # Utfall per steg (in/anrop, gemini-3.6-flash, samma 5 fixtures):
            #   research 5 963 -> 5 963, utkast 6 326 -> 6 298,
            #   humanizer 9 054 -> 8 254; kr/lead 0,1927 -> 0,1888;
            #   kontakt 3/5 -> 3/5, qualified 4/4 -> 4/4.
            #
            # V1-steget behåller hel skill; skopningen är V2:s och mäts av
            # scripts/benchmark_leads_kedja.py.
            scope=(
                "§ Din uppgift",
                "§ PERSONLIGHET OCH RÖST",
                "§ 1. Signifikansuppblåsning",
                "§ 2. Landskap- och trenduppramning",
                "§ 3. Participfraser som falsk analys",
                "§ 4. Vaga attributioner och vagbeskrivningar",
                "§ 5. Passiv röst som falsk formalitet",
                "§ 6. Nominaliseringsöverdrift",
                "§ 7. Anglifieringsimporter",
                "§ 8. Strukturella AI-mönster",
                "§ 9. Negativ parallellism (svensk variant)",
                "§ 11. Sycofantiska öppningar och avslutningar",
                "§ 12. Utfyllnadsfraser",
                "§ 13. Överdriven osäkerhetssignalering",
                "§ 15. Kopulaundvikande (utgör/representerar/utgör)",
                "§ Affärsskrivande (mejl, offerter, presentationer, intern kommunikation)",
                "§ PROCESS",
                "§ Utdataformat",
                "§ Snabbreferens: Vanliga byten",
            ),
            rationale=(
                "Kalla mejl är affärsskrivande. Utelämnat: exempelblocket, "
                "registren för rapport/artikel/socialt, och tre mönster som "
                "inte kan uppstå i ett kallmejl (sociala medier, kunskaps-"
                "avgränsning, bullets/emoji) — 40 % av skillen. De 13 övriga "
                "mönstren, rösten, affärsregistret, processen och utdata-"
                "formatet laddas i sin helhet."
            ),
        ),
    ),
)

_HEADER = """Du skriver ett kallt utskick till {company_name} åt {tenant_name}.
Nedan följer, i bestämd ordning, de skills som styr arbetet.

VIKTIGT — åsidosätter sa:draft-outreach:s standardbeteende (G4): producera
ALDRIG LinkedIn-kopia eller ett LinkedIn-anslutningsmeddelande, oavsett vad
skillen nedan säger om att alltid inkludera det. E-postvägen är den enda
kanalen. Om ingen verifierad e-post finns: eskalera, föreslå inte LinkedIn
som fallback.

Ren text, aldrig markdown (sa:draft-outreach är redan explicit om detta) —
humanizern får inte återinföra asterisker, fetstil eller punktlistor.

Erbjudande som styr vinkeln: {offer_summary}
{context_pack}
"""


def render_outreach_instructions(
    *, tenant_name: str, company_name: str, offer_summary: str, context_pack: str
) -> tuple[str, RunLedger]:
    ledger = RunLedger(satisfied={"offer_selected", "context_pack"})
    parts: list[str] = [
        _HEADER.format(
            tenant_name=tenant_name,
            company_name=company_name,
            offer_summary=offer_summary,
            context_pack=context_pack,
        )
    ]
    for step in OUTREACH_V1.steps:
        check_preconditions(step, ledger)
        rendered = step.render()
        ledger.mark_skill_injected(step.skill)
        ledger.executed_order.append(step.skill)
        parts.append(f"---\n### Skill: {step.skill}\n{rendered}")
    return "\n\n".join(parts), ledger


def finalize_outreach_body(draft: str) -> str:
    """Samma markdown-grind som cs:draft-response (app/agent/tools.py) —
    sa:draft-outreach kräver plain text lika explicit ('Never use asterisks,
    bold, or other markdown', SKILL.md rad 291). Humanizern får inte
    återinföra formatering; det här är kodgrinden som garanterar det
    oavsett vad modellen faktiskt skrev, samma princip som hela Del C."""
    return strip_markdown(draft)
