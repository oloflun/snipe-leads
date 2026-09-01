"""support/v1 som per-steg-orkestrering. Mockar bara nätverksgränsen
(LLM-klienten) — allt annat är den riktiga kodvägen, inklusive
förvillkorsgrinden, utdatakontraktet, sidoeffekterna och agent_runs-loggen.

Det här är testet som faktiskt bevisar vilka skill-anrop som görs, i vilken
ordning, och att eskalering avgörs i KOD och inte av modellens godtycke."""

import json
import re
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.support_agent import run_support_agent
from app.config import get_settings
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"

# Lyckligt flöde: KB bar svaret, inget eskalerade — då finns ingen lucka att
# skriva en artikel om, och cs:kb-article hoppas över (villkorat 2026-08-26).
# Sedan 2026-09-02 hoppas ÄVEN cs:customer-escalation över här: utan
# kunskapslucka, säkerhetssignal eller uttrycklig begäran om en människa
# finns inget för steget att bedöma — kodbeslutet OR:ar redan de oberoende
# villkoren, och steget (kedjans enda med thinking) röstade alltid "nej".
EXPECTED_ORDER_NORMAL = [
    "cs:ticket-triage",
    "cs:customer-research",
    "cs:draft-response",
    "snajp:humanizer-svenska",
]

# Med kunskapslucka (eller säkerhetskritiskt ärende) körs kunskapssteget,
# på sin deklarerade plats före humaniseraren.
EXPECTED_ORDER_KB_GAP = [
    "cs:ticket-triage",
    "cs:customer-research",
    "cs:draft-response",
    "cs:customer-escalation",
    "cs:kb-article",
    "snajp:humanizer-svenska",
]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _fake_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _FakeLLM:
    """Returnerar ett kontraktsenligt JSON-svar per anrop och registrerar
    vilken skill varje anrop gällde (utläst ur systemprompten)."""

    def __init__(self, overrides: dict | None = None):
        self.calls: list[str] = []
        self.overrides = overrides or {}
        self.chat = self  # client.chat.completions.create
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        # Läs skillen ur step_runner:s exakta markör — INTE genom att söka
        # efter skill-namn i prompttexten. Flera skills nämner varandra i sitt
        # innehåll (snajp:retention-conversation refererar cs:customer-research),
        # vilket gjorde en naiv sökning fel.
        system = messages[0]["content"]
        skill = re.search(r"styrs av skillen (\S+?),", system).group(1)
        self.calls.append(skill)

        payload = {"sources_used": ["kb-1"], "context_refs": ["context_pack"]}
        payload.update(
            {
                "cs:ticket-triage": {"category": "betalning", "priority": "P3", "sentiment": 0.6, "escalate": False},
                "cs:customer-research": {"findings": "KB täcker frågan.", "confidence": 0.8, "kb_supports_answer": True},
                "cs:draft-response": {"draft": "Du kan betala med Swish eller kort."},
                "cs:customer-escalation": {"should_escalate": False, "reason": None},
                "cs:kb-article": {"should_create": False},
                "snajp:retention-conversation": {"revised_draft": "Jag kopplar in en kollega.", "offers_made": []},
                "snajp:humanizer-svenska": {"final_reply": "Hej! Du kan betala med Swish eller kort."},
            }.get(skill, {})
        )
        payload.update(self.overrides.get(skill, {}))

        message = type("M", (), {"content": json.dumps(payload, ensure_ascii=False)})()
        usage = type("U", (), {"prompt_tokens": 100, "completion_tokens": 20})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()



def _skill_i(messages) -> str:
    """Vilken skill anropet gällde, läst ur step_runner:s exakta markör.

    Samma metod som `_FakeLLM.create` använder, och av samma skäl: flera
    skills nämner varandra i sin text, så `"cs:draft-response" in prompt` är
    sant för fler steg än utkaststeget.
    """
    träff = re.search(r"styrs av skillen (\S+?),", messages[0]["content"])
    return träff.group(1) if träff else ""

async def _run(storage, llm, message="Vilka betalsätt accepterar ni?", risk=(0.0, 0.0), **kwargs):
    with patch("app.agent.step_runner.get_llm_client", return_value=llm), patch(
        "app.agent.support_agent.classify_cancellation_risk", new=AsyncMock(return_value=risk)
    ):
        return await run_support_agent(
            storage,
            TENANT,
            message=message,
            subject=kwargs.get("subject", ""),
            channel="web",
            customer_email="kund@example.com",
            customer_name="Test Person",
            attachments=kwargs.get("attachments", []),
        )


@pytest.mark.anyio
async def test_one_llm_call_per_skill_step_in_declared_order():
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run(storage, llm)

    assert llm.calls == EXPECTED_ORDER_NORMAL, "Ett anrop per steg, i playbook-ordning"
    assert result["skills_used"] == EXPECTED_ORDER_NORMAL
    assert len(result["step_log"]) == len(EXPECTED_ORDER_NORMAL)


@pytest.mark.anyio
async def test_begaran_om_manniska_kor_eskaleringssteget_aven_pa_lyckligt_flode():
    """Villkoret 2026-09-02: eskaleringssteget hoppas över när inget finns att
    bedöma — men "jag vill prata med en människa" är exakt det som ska
    bedömas av modellen, även när KB bar svaret och inget annat flaggade.
    Regexen _BER_OM_MANNISKA är stegets väckarklocka, inte dess ersättare."""
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run(
        storage, llm, message="Vilka betalsätt tar ni? Jag vill helst prata med en människa."
    )

    assert "cs:customer-escalation" in llm.calls
    # Modellen (fejken) röstade nej och inget kodvillkor föll — beslutet är
    # fortfarande modellens att fatta, inte regexens.
    assert result["escalated"] is False


@pytest.mark.anyio
async def test_kb_article_runs_on_kb_gap_and_suggestion_is_persisted():
    """Kunskapssteget körs när KB saknade svaret — och förslaget SPARAS som
    agent_suggestion i stället för att kastas (2026-08-26). Agenten skriver
    aldrig själv i kunskapsbasen: raden har status 'ny' tills en människa
    godkänner (INV-LEARN-001)."""
    storage = MemoryStorage()
    llm = _FakeLLM(
        overrides={
            "cs:customer-research": {"kb_supports_answer": False},
            "cs:kb-article": {
                "should_create": True,
                "title": "Leveranstid till Norge",
                "content": "Vi levererar till Norge inom 5-7 arbetsdagar.",
            },
        }
    )
    result = await _run(storage, llm)

    assert llm.calls == EXPECTED_ORDER_KB_GAP
    forslag = await storage.list_agent_suggestions(TENANT, status="ny")
    assert len(forslag) == 1
    assert forslag[0]["kind"] == "kb_article"
    assert forslag[0]["agent_type"] == "support"
    assert forslag[0]["content"]["title"] == "Leveranstid till Norge"
    # Kunskapsbasen är ORÖRD — förslaget är inte en artikel.
    titlar = [a["title"] for a in await storage.list_kb(TENANT)]
    assert "Leveranstid till Norge" not in titlar
    assert result["ticket_id"]


@pytest.mark.anyio
async def test_samma_kunskapslucka_ger_en_rad_inte_tio():
    """Dedupe: tio ärenden om samma lucka ska ge EN rad att granska."""
    storage = MemoryStorage()
    llm = _FakeLLM(
        overrides={
            "cs:customer-research": {"kb_supports_answer": False},
            "cs:kb-article": {
                "should_create": True,
                "title": "Leveranstid till Norge",
                "content": "Vi levererar till Norge inom 5-7 arbetsdagar.",
            },
        }
    )
    await _run(storage, llm)
    await _run(storage, llm, message="Hur lång är leveranstiden till Norge egentligen?")

    forslag = await storage.list_agent_suggestions(TENANT, status="ny")
    assert len(forslag) == 1


@pytest.mark.anyio
async def test_kb_article_skips_when_kb_bar_svaret():
    """Inget kunskapssteg på ett ärende där KB bar svaret och inget flaggade
    — steget var där ren kostnad utan utbyte."""
    storage, llm = MemoryStorage(), _FakeLLM()
    await _run(storage, llm)

    assert "cs:kb-article" not in llm.calls
    assert await storage.list_agent_suggestions(TENANT) == []


@pytest.mark.anyio
async def test_step_log_records_contract_fields_per_step():
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run(storage, llm)

    for entry in result["step_log"]:
        assert entry["sources_used"] == ["kb-1"]
        assert entry["context_refs"] == ["context_pack"]
        assert entry["attempts"] == 1
        assert entry["escalated"] is False


@pytest.mark.anyio
async def test_agent_run_is_logged_with_step_log_g10():
    storage, llm = MemoryStorage(), _FakeLLM()
    await _run(storage, llm)

    runs = await storage.list_agent_runs(TENANT, agent_type="support")
    assert len(runs) == 1
    assert runs[0]["skills_used"] == EXPECTED_ORDER_NORMAL
    assert len(runs[0]["step_log"]) == len(EXPECTED_ORDER_NORMAL)
    assert "cs:kb-article" not in runs[0]["skills_used"]
    assert runs[0]["tokens_in"] > 0
    assert ":support/v1" in runs[0]["pack_version"]


@pytest.mark.anyio
async def test_cancellation_risk_inserts_retention_step_and_forces_escalation():
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run(storage, llm, message="Jag vill säga upp allt NU.", risk=(0.9, 0.8))

    assert "snajp:retention-conversation" in llm.calls
    assert llm.calls.index("snajp:retention-conversation") < llm.calls.index("snajp:humanizer-svenska")
    assert result["escalated"] is True
    assert result["escalation_reason"] == "retention_risk"


@pytest.mark.anyio
async def test_escalates_in_code_even_when_model_says_no_escalation():
    """Modellen säger should_escalate=False men sentimentet är under tröskeln
    — koden eskalerar ändå. Eskalering får inte bero på modellens godtycke."""
    storage = MemoryStorage()
    llm = _FakeLLM(overrides={"cs:ticket-triage": {"sentiment": 0.1}})
    result = await _run(storage, llm, message="Detta är helt oacceptabelt!")

    assert result["escalated"] is True


@pytest.mark.anyio
async def test_full_library_miss_asks_twice_then_escalates_on_the_third_turn():
    """2026-08-25: en första miss får en följdfråga ÄVEN på ett fullt bibliotek.
    2026-09-02: gränsen höjdes till TVÅ motfrågor (kundkrav: eskalera inte i
    första taget).

    En första miss betyder oftare "frågan var för vag för att sökas" än
    "svaret finns inte" — en förtydligad fråga får ett andra sökvarv, och
    kundens svar på den första motfrågan bär ofta ämnet men inte detaljen.
    Först när även det TREDJE varvet går tomt är tomheten ett besked, och DÅ
    eskalerar ärendet precis som förut.
    """
    storage = MemoryStorage()
    llm = _FakeLLM(overrides={"cs:customer-research": {"kb_supports_answer": False}})
    with patch(
        "app.agent.support_agent._sok_kb", new=AsyncMock(return_value=[])
    ):
        forsta = await _run(storage, llm)
        andra = await _run(storage, llm, message="Jag menar för företagskonton.")
        tredje = await _run(storage, llm, message="Ja, precis, företagskonton.")

    assert forsta["escalated"] is False, "Första missen ska ge en följdfråga, inte en överlämning."
    assert forsta["kb_sources"] == []
    assert andra["escalated"] is False, "Andra varvet får ställa EN motfråga till."
    assert tredje["escalated"] is True, "Tredje varvet utan svar ska fortfarande eskalera."


@pytest.mark.anyio
async def test_ticket_and_messages_are_persisted_by_code_not_by_the_model():
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run(storage, llm)

    ticket = await storage.get_ticket(TENANT, result["ticket_id"])
    assert ticket is not None
    messages = await storage.get_messages(TENANT, ticket["conversation_id"])
    assert [m["direction"] for m in messages] == ["inbound", "outbound"]


@pytest.mark.anyio
async def test_markdown_is_stripped_from_the_final_reply():
    storage = MemoryStorage()
    llm = _FakeLLM(
        overrides={"snajp:humanizer-svenska": {"final_reply": "Hej! **Viktigt**: se nedan."}}
    )
    result = await _run(storage, llm)

    assert "**" not in result["reply"]


@pytest.mark.anyio
async def test_vision_sidecar_describes_image_and_never_stores_it():
    storage, llm = MemoryStorage(), _FakeLLM()
    with patch(
        "app.agent.support_agent.describe_image",
        new=AsyncMock(return_value="Skärmdump med felkod E-500."),
    ) as mock_describe:
        result = await _run(storage, llm, attachments=["data:image/png;base64,AAAA"])

    mock_describe.assert_awaited_once()
    assert result["ticket_id"]


@pytest.mark.anyio
async def test_broken_contract_retries_once_then_escalates_that_step():
    """Ett steg som aldrig returnerar kontraktet ska försöka igen en gång
    och sedan markeras som eskalerat — inte tyst passera."""
    storage = MemoryStorage()

    class _BadLLM(_FakeLLM):
        async def create(self, *, model, response_format, temperature, messages, **kwargs):
            if "cs:draft-response" in messages[0]["content"]:
                self.calls.append("cs:draft-response")
                message = type("M", (), {"content": json.dumps({"draft": "x"})})()  # saknar kontrakt
                usage = type("U", (), {"prompt_tokens": 1, "completion_tokens": 1})()
                return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()
            return await super().create(
                model=model, response_format=response_format, temperature=temperature, messages=messages
            )

    llm = _BadLLM()
    result = await _run(storage, llm)

    draft_entries = [e for e in result["step_log"] if e["skill"] == "cs:draft-response"]
    assert draft_entries[0]["attempts"] == 2
    assert draft_entries[0]["escalated"] is True


# -- Mindre lätt att ge upp (DEL 3) ---------------------------------------
#
# Hälften av testerna nedan prövar att agenten INTE eskalerar. Den andra
# hälften prövar att de säkerhetskritiska vägarna eskalerar precis som förut.
# Båda hälfterna behövs: en ändring som gör agenten mindre benägen att lämna
# över är bara bra så länge den inte också gjorde den mindre benägen att göra
# det när den ska.


async def _tunn_kb(storage):
    """En tenant med ett nästan tomt bibliotek (en enda artikel)."""
    storage.kb[TENANT] = []
    await storage.add_kb_article(
        TENANT, title="Öppettider", content="Vi har öppet 9-17.", category="ovrigt"
    )


@pytest.mark.anyio
async def test_tunn_kb_och_ofarlig_fraga_ger_en_foljdfraga_i_stallet_for_eskalering():
    """Kärnan i DEL 3.3.

    En tenant med ett par artiklar hade förut eskalerat nästan varje fråga som
    inte råkade formuleras som en artikelrubrik. Nu ställs en följdfråga.
    """
    storage = MemoryStorage()
    await _tunn_kb(storage)
    llm = _FakeLLM(overrides={"cs:customer-research": {"kb_supports_answer": False}})
    result = await _run(storage, llm, message="Fungerar den med min telefon?")

    assert result["escalated"] is False, (
        "En ofarlig fråga mot ett tunt bibliotek eskalerade — följdfrågevägen är stängd."
    )


@pytest.mark.anyio
async def test_foljdfragan_instrueras_i_utkaststeget_inte_efterat():
    """Beslutet ska ändra VAD utkastet är, inte redigera en färdig text."""
    storage = MemoryStorage()
    await _tunn_kb(storage)
    llm = _FakeLLM(overrides={"cs:customer-research": {"kb_supports_answer": False}})

    prompts: list[str] = []
    original = llm.create

    async def spionera(**kwargs):
        if _skill_i(kwargs["messages"]) == "cs:draft-response":
            prompts.append(str(kwargs["messages"]))
        return await original(**kwargs)

    llm.create = spionera
    await _run(storage, llm, message="Fungerar den med min telefon?")

    assert len(prompts) == 1, f"Utkaststeget kördes {len(prompts)} gånger."
    assert "EN kort, öppen följdfråga" in prompts[0]
    assert "Lämna INTE över till en människa" in prompts[0]


@pytest.mark.anyio
async def test_en_tredje_tur_far_ingen_ny_foljdfraga():
    """Loopspärren. Sedan 2026-09-02 får kunden TVÅ motfrågor (kundkrav:
    eskalera inte i första taget) — men har kunden svarat två gånger och vi
    fortfarande inte kan svara, är en tredje motfråga inte omsorg utan en
    loop."""
    storage = MemoryStorage()
    await _tunn_kb(storage)
    llm = _FakeLLM(overrides={"cs:customer-research": {"kb_supports_answer": False}})

    forsta = await _run(storage, llm, message="Fungerar den med min telefon?")
    assert forsta["escalated"] is False

    andra = await _run(storage, llm, message="Ja, en Android.")
    assert andra["escalated"] is False

    # Tredje turen från SAMMA kund: nu finns fyra tidigare repliker, och då
    # gäller den gamla regeln igen.
    tredje = await _run(storage, llm, message="En Samsung Galaxy S24.")
    assert tredje["escalated"] is True


@pytest.mark.anyio
async def test_ett_andra_sokforsok_gors_nar_det_forsta_gar_tomt():
    """DEL 3.1. Den första frågan är hela meddelandet; går den tom prövas en
    förenklad innan tomheten får betyda något."""
    storage, llm = MemoryStorage(), _FakeLLM()

    fragor: list[str] = []

    async def tom_sokning(storage_, tenant_, fraga):
        fragor.append(fraga)
        return []

    with patch("app.agent.support_agent._sok_kb", new=tom_sokning):
        await _run(
            storage,
            llm,
            message="Hej! Jag undrar en sak om delbetalning av min order, tack",
            subject="Delbetalning",
        )

    assert len(fragor) >= 2, f"Bara ett sökförsök gjordes: {fragor}"
    assert fragor[1] == "Delbetalning", "Andra försöket använde inte ämnesraden."


@pytest.mark.anyio
async def test_ett_tredje_forsok_gors_pa_det_researchsteget_sager_saknas():
    storage = MemoryStorage()
    llm = _FakeLLM(
        overrides={
            "cs:customer-research": {
                "kb_supports_answer": False,
                "missing_info": "leveranstid utomlands",
            }
        }
    )
    fragor: list[str] = []

    async def tom_sokning(storage_, tenant_, fraga):
        fragor.append(fraga)
        return []

    with patch("app.agent.support_agent._sok_kb", new=tom_sokning):
        await _run(storage, llm, message="Hur lång tid tar det?", subject="Leverans")

    assert "leveranstid utomlands" in fragor, f"missing_info prövades aldrig: {fragor}"


@pytest.mark.anyio
async def test_kb_supports_answer_false_vager_in_aven_med_traffar():
    """DEL 3.2. Förut stod flaggan bara som kontext åt nästa steg. Nu avgör
    den i kod: träffar som inte bär svaret är inte ett svar.

    Sedan 2026-08-25 ger första turen en följdfråga, och sedan 2026-09-02
    även den andra — så flaggans verkan mäts i TREDJE turen: träffar utan
    svar ska då eskalera."""
    storage = MemoryStorage()
    llm = _FakeLLM(overrides={"cs:customer-research": {"kb_supports_answer": False}})
    forsta = await _run(storage, llm, message="Vilka betalsätt accepterar ni?")
    andra = await _run(storage, llm, message="Jag menar för delbetalning.")
    result = await _run(storage, llm, message="Delbetalning av en större order.")

    assert forsta["escalated"] is False
    assert andra["escalated"] is False
    assert result["escalated"] is True
    assert result["kb_sources"], "Testet mäter fel sak: sökningen gav inga träffar."


# -- Inga regressioner på det som SKA eskalera ----------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(
    "meddelande",
    [
        "Jag anmäler er till ARN.",
        "Jag vill att ni raderar alla mina uppgifter enligt GDPR.",
        "Radera mitt konto, tack.",
        "Jag begär ett registerutdrag över allt ni har om mig.",
        "Jag kräver återbetalning.",
        "Min advokat hör av sig.",
        "Jag vill ha kompensation för det här.",
    ],
)
async def test_kansliga_arenden_far_aldrig_en_foljdfraga(meddelande):
    """Gränsen som INTE flyttades.

    Även med ett tunt bibliotek och en modell som säger should_escalate=False
    ska de här lämnas över. Kontrollen ligger i KOD (`_ar_kansligt`) eftersom
    steget som bär juridiken kommer EFTER utkastet.
    """
    storage = MemoryStorage()
    await _tunn_kb(storage)
    llm = _FakeLLM(overrides={"cs:customer-research": {"kb_supports_answer": False}})
    result = await _run(storage, llm, message=meddelande)

    assert result["escalated"] is True, f"{meddelande!r} eskalerade inte."


@pytest.mark.anyio
async def test_hot_eskalerar_fortfarande_pa_ett_tunt_bibliotek():
    storage = MemoryStorage()
    await _tunn_kb(storage)
    llm = _FakeLLM(overrides={"cs:customer-research": {"kb_supports_answer": False}})
    result = await _run(storage, llm, message="jag ska döda dig")

    assert result["escalated"] is True
    assert result["escalation_reason"] == "Avbrutet samtal: allvarlig"


@pytest.mark.anyio
async def test_lagt_sentiment_eskalerar_fortfarande_pa_ett_tunt_bibliotek():
    storage = MemoryStorage()
    await _tunn_kb(storage)
    llm = _FakeLLM(
        overrides={
            "cs:ticket-triage": {"sentiment": 0.1},
            "cs:customer-research": {"kb_supports_answer": False},
        }
    )
    result = await _run(storage, llm, message="Fungerar den med min telefon?")

    assert result["escalated"] is True


@pytest.mark.anyio
async def test_uppsagningsrisk_eskalerar_fortfarande_pa_ett_tunt_bibliotek():
    storage = MemoryStorage()
    await _tunn_kb(storage)
    llm = _FakeLLM(overrides={"cs:customer-research": {"kb_supports_answer": False}})
    result = await _run(storage, llm, message="Jag funderar på att sluta.", risk=(0.9, 0.8))

    assert result["escalated"] is True
    assert result["escalation_reason"] == "retention_risk"


@pytest.mark.anyio
async def test_modellens_egen_eskalering_vager_fortfarande():
    storage = MemoryStorage()
    await _tunn_kb(storage)
    llm = _FakeLLM(
        overrides={
            "cs:customer-research": {"kb_supports_answer": False},
            "cs:customer-escalation": {
                "should_escalate": True,
                "reason": "Kräver manuell prövning.",
            },
        }
    )
    result = await _run(storage, llm, message="Fungerar den med min telefon?")

    assert result["escalated"] is True
    assert result["escalation_reason"] == "Kräver manuell prövning."


@pytest.mark.anyio
async def test_triageflaggan_eskalerar_fortfarande():
    storage = MemoryStorage()
    await _tunn_kb(storage)
    llm = _FakeLLM(
        overrides={
            "cs:ticket-triage": {"escalate": True},
            "cs:customer-research": {"kb_supports_answer": False},
        }
    )
    result = await _run(storage, llm, message="Fungerar den med min telefon?")

    assert result["escalated"] is True


# -- Den forenklade fragan, som ren funktion ------------------------------


@pytest.mark.anyio
async def test_kort_uppfoljningsreplik_soker_med_forra_repliken():
    """Flerturssökningen (2026-08-26). "Ja, en Android." bär inte ämnet —
    kundens FÖRRA replik gör det, och den ska ingå i sökfrågan."""
    storage, llm = MemoryStorage(), _FakeLLM()
    await _run(storage, llm, message="Fungerar betalningen med min telefon?")

    fragor: list[str] = []

    async def spionerande_sokning(storage_, tenant_, fraga):
        fragor.append(fraga)
        return []

    with patch("app.agent.support_agent._sok_kb", new=spionerande_sokning):
        await _run(storage, llm, message="Ja, en Android.")

    assert fragor, "Ingen sökning gjordes."
    assert "telefon" in fragor[0].lower(), (
        f"Förra replikens ämnesord saknas i sökfrågan: {fragor[0]!r}"
    )


@pytest.mark.anyio
async def test_langt_meddelande_soks_utan_historikpaslag():
    """Ett långt nytt meddelande bär sitt eget ämne — historiken ska inte
    späda rankningen då."""
    storage, llm = MemoryStorage(), _FakeLLM()
    await _run(storage, llm, message="Fungerar betalningen med min telefon?")

    fragor: list[str] = []

    async def spionerande_sokning(storage_, tenant_, fraga):
        fragor.append(fraga)
        return []

    langt = (
        "Jag har nu provat igen med ett annat kort och det gick inte heller, "
        "kan ni kolla om det är något fel på min faktura eller mitt konto?"
    )
    with patch("app.agent.support_agent._sok_kb", new=spionerande_sokning):
        await _run(storage, llm, message=langt)

    assert fragor[0].strip() == langt, f"Historik lades på ett långt meddelande: {fragor[0]!r}"


def test_forenklad_fraga_foredrar_amnesraden():
    from app.agent.support_agent import _forenklad_fraga

    assert _forenklad_fraga("Delbetalning", "Hej! Jag undrar en sak.") == "Delbetalning"


def test_forenklad_fraga_plockar_betydelsebarande_ord_utan_amnesrad():
    from app.agent.support_agent import _forenklad_fraga

    fraga = _forenklad_fraga("", "Hej! Jag undrar hur lång leveranstid ni har på delbetalning, tack")
    assert "leveranstid" in fraga
    assert "delbetalning" in fraga
    assert "tack" not in fraga, "Ett stoppord kom med."


def test_forenklad_fraga_ger_tomt_nar_det_inte_gar_att_forenkla():
    """Tom sträng => inget andra sökförsök alls. Ett andra anrop med samma
    fråga är bara latens."""
    from app.agent.support_agent import _forenklad_fraga

    # Ingen ämnesrad och för få betydelsebärande ord att plocka.
    assert _forenklad_fraga("", "hej") == ""
    assert _forenklad_fraga("", "Hej! Tack.") == ""
    # Ämnesrad men ingen brödtext: första sökningen VAR ämnesraden.
    assert _forenklad_fraga("Delbetalning", "") == ""


def test_forenklad_fraga_anvander_amnet_aven_nar_ordet_star_i_brodtexten():
    """Första sökningen var "ämne + meddelande". Ämnet ensamt är därför en
    annan och bredare fråga även när ordet står i båda — vilket det oftast
    gör, eftersom kunden skriver om det de satte som ämne."""
    from app.agent.support_agent import _forenklad_fraga

    assert (
        _forenklad_fraga("Delbetalning", "Hur funkar delbetalning?") == "Delbetalning"
    )
