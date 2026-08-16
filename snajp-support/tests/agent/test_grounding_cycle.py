"""INV-GROUND-001 — ett utkast med ostödda påståenden köas aldrig.

Mockar BARA nätverksgränsen (LLM-klienten). Grinden, reparationsloopen,
delta-humaniseringen, språkgrinden och köningen körs genom den riktiga
kodvägen — annars bevisar testet bara att mocken är konsekvent med sig själv.

Det bärande testet är test_still_unsupported_after_one_repair_hands_off:
det är hela invarianten. Om det någonsin börjar passera av fel skäl (t.ex.
för att grinden slutade fälla) fångar test_loop_is_bounded_at_one_repair och
test_unsupported_claim_triggers_repair det.
"""

from __future__ import annotations

import json
import re
from unittest.mock import patch

import pytest

from app.agent.leads_agent import run_outreach_draft
from app.config import get_settings
from app.leads.grounding_playbook import GROUNDING_V1
from app.leads.outreach_playbook import OUTREACH_V1
from app.storage.memory import MemoryStorage

TENANT = "tenant-a"
OUTREACH_ORDER = [s.skill for s in OUTREACH_V1.steps]
GROUNDING_ORDER = [s.skill for s in GROUNDING_V1.steps]

# Siffran finns inte i något underlag testet skickar in.
INVENTED = "Vi har minskat återkommande frågor med 63 procent."
GROUNDED = "Ni erbjuder fri retur inom 30 dagar."
EVIDENCE = ("Fri retur inom 30 dagar",)


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


class _Scripted:
    """Svarar per (skill, n:te anropet för den skillen).

    Humanizern förekommer i BÅDA playbooksen, så skill-namnet ensamt räcker
    inte för att veta vilket steg som frågar — därför räknaren.
    """

    def __init__(self, *, final_body: str, repaired_body: str | None = None, segments=...):
        self.calls: list[str] = []
        self.counts: dict[str, int] = {}
        self.final_body = final_body
        self.repaired_body = repaired_body
        self.segments = segments
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        system = messages[0]["content"]
        skill = re.search(r"styrs av skillen (\S+?),", system).group(1)
        self.calls.append(skill)
        self.counts[skill] = self.counts.get(skill, 0) + 1
        nth = self.counts[skill]

        payload = {"sources_used": ["context_pack"], "context_refs": ["context_pack"]}
        if skill == "sa:draft-outreach":
            payload.update({"subject": "Returfrågor", "body": "utkast"})
        elif skill == "mk:cold-email":
            payload.update(
                {"improved_subject": "Returfrågor", "improved_body": "utkast",
                 "revised_subject": "Returfrågor", "revised_body": "utkast",
                 "passes_review": True, "violations": []}
            )
        elif skill == "snajp:humanizer-svenska" and nth == 1:
            payload.update({"final_subject": "Returfrågor", "final_body": self.final_body})
        elif skill == "snajp:humanizer-svenska":
            # Delta-steget i GROUNDING_V1.
            user = messages[1]["content"]
            given = json.loads(re.search(r"\[\s*\{.*\}\s*\]", user, re.DOTALL).group(0))
            if self.segments is ...:
                payload["segments"] = [{"index": s["index"], "text": s["text"]} for s in given]
            else:
                payload["segments"] = self.segments
        elif skill == "mk:copy-editing":
            payload.update(
                {"repaired_subject": "Returfrågor",
                 "repaired_body": self.repaired_body if self.repaired_body is not None else GROUNDED,
                 "removed_claims": ["63 procent"]}
            )

        class _Msg:
            content = json.dumps(payload, ensure_ascii=False)
            reasoning_content = None

        class _Choice:
            message = _Msg()

        class _Response:
            choices = [_Choice()]
            usage = None

        return _Response()


#: Produktbeskrivningen är sedan DEL 2.1 ett förvillkor för outreach — en tom
#: sådan avbryter körningen innan första LLM-anropet. De här testerna mäter
#: grundningscykeln, så de får ett giltigt underlag.
PRODUKTBESKRIVNING = (
    "Snajp säljer en kundservice- och leadsagent till svenska småföretag. "
    "Målgruppen är bolag med 1–49 anställda som får fler mejl än de hinner "
    "besvara. Agenten grundar varje svar i kundens egen kunskapsbas."
)


async def _run(storage, llm, **kwargs):
    storage.outreach_threads.setdefault(TENANT, {})["thread-1"] = {
        "id": "thread-1",
        "language_state": kwargs.pop("language_state", "sv"),
    }
    await storage.save_context_doc(
        TENANT, kind="product_marketing", content=PRODUKTBESKRIVNING
    )
    with patch("app.agent.step_runner.get_llm_client", return_value=llm):
        return await run_outreach_draft(
            storage, TENANT,
            thread_id="thread-1",
            prospect_email="kundservice@exempelbolaget.se",
            tenant_name="Snajp",
            company_name="Exempelbolaget",
            offer_summary="Pilot på returfrågor",
            context_pack="### Kontextpaket\n...",
            brief="Skriv ett kort första mejl.",
            research_evidence=kwargs.pop("research_evidence", EVIDENCE),
            **kwargs,
        )


# -- Det rena fallet -------------------------------------------------------


@pytest.mark.anyio
async def test_clean_draft_never_calls_the_grounding_playbook():
    """Ett rent utkast ska kosta FYRA anrop. Grindningen är villkorad —
    det är hela skälet att den är en kodloop och inte två extra steg."""
    storage, llm = MemoryStorage(), _Scripted(final_body=GROUNDED)
    result = await _run(storage, llm)

    assert llm.calls == OUTREACH_ORDER
    assert result["grounding"]["fired"] is False
    assert result["queued"] is True


# -- Reparationsvägen ------------------------------------------------------


@pytest.mark.anyio
async def test_unsupported_claim_triggers_repair_then_delta_humanize():
    storage, llm = MemoryStorage(), _Scripted(final_body=INVENTED)
    result = await _run(storage, llm)

    assert llm.calls == OUTREACH_ORDER + GROUNDING_ORDER
    grounding = result["grounding"]
    assert grounding["fired"] is True
    assert grounding["repaired"] is True
    assert grounding["ok"] is True
    assert any("63" in claim for claim in grounding["unsupported_before"])
    assert grounding["unsupported_after"] == []
    assert result["queued"] is True
    assert "63" not in result["body"]


@pytest.mark.anyio
async def test_only_changed_sentences_go_to_the_humanizer():
    """Delta-egenskapen. Går hela mejlet dit har vi slagit om en redan
    godkänd röst och betalat för det."""
    storage = MemoryStorage()
    llm = _Scripted(
        final_body=f"Hej Anna. {INVENTED} Hör av dig.",
        repaired_body="Hej Anna. Vi minskar återkommande frågor. Hör av dig.",
    )
    result = await _run(storage, llm)

    assert result["grounding"]["segments_changed"] == 1
    assert result["grounding"]["delta_humanized"] is True


# -- Invarianten -----------------------------------------------------------


@pytest.mark.anyio
async def test_still_unsupported_after_one_repair_hands_off_never_queues():
    """INV-GROUND-001. Den ENDA utgången för ett kvarstående ostött
    påstående är en människa."""
    storage = MemoryStorage()
    # Reparationen "lagar" genom att hitta på en NY siffra.
    llm = _Scripted(final_body=INVENTED, repaired_body="Vi minskade frågorna med 45 procent.")
    result = await _run(storage, llm)

    assert result["queued"] is False
    assert result["escalated"] is True
    assert result["grounding"]["ok"] is False
    assert any("45" in claim for claim in result["grounding"]["unsupported_after"])
    assert storage.send_queue.get(TENANT, []) == [], "ostött påstående nådde kön"


@pytest.mark.anyio
async def test_loop_is_bounded_at_one_repair():
    """Sex anrop, aldrig fler. Utan gränsen kan loopen oscillera: varje
    reparationsrunda kan införa NYA påståenden som fäller nästa grindning."""
    storage = MemoryStorage()
    llm = _Scripted(final_body=INVENTED, repaired_body="Fortfarande 77 procent kvar.")
    await _run(storage, llm)

    assert llm.calls == OUTREACH_ORDER + GROUNDING_ORDER
    assert len(llm.calls) == 6


# -- Delta-mekanikens felläge ---------------------------------------------


@pytest.mark.anyio
async def test_delta_shape_violation_keeps_repaired_text_and_still_queues():
    """Humanizern returnerar fel indexmängd.

    MEDVETET: vi splicar inte, behåller den reparerade texten, och köar ändå.
    Texten är grindren och den orörda delen redan humaniserad — det som
    saknas är stilbehandling av en mening. Att eskalera på en stilnyans är
    hur man lär folk att ignorera eskaleringskön."""
    storage = MemoryStorage()
    llm = _Scripted(
        final_body=INVENTED,
        segments=[{"index": 99, "text": "fel index"}],
    )
    result = await _run(storage, llm)

    assert result["grounding"]["delta_humanized"] is False
    assert "delta_error" in result["grounding"]
    assert result["queued"] is True, "en stilregression ska inte blockera utskicket"
    assert "63" not in result["body"]


# -- Ordningen och språkgrinden -------------------------------------------


@pytest.mark.anyio
async def test_humanizer_variant_comes_from_the_trace_not_a_step_index():
    """Efter en delta-humanisering är OUTREACH_V1:s fjärde steg inte längre
    det som rörde texten sist. Ett hårdkodat steps[3] hade varit sant av en
    slump här, och fel så fort någon ordnar om stegen."""
    from app.leads.language_gate import last_humanizer_variant

    storage, llm = MemoryStorage(), _Scripted(final_body=INVENTED)
    result = await _run(storage, llm)

    assert result["queued"] is True
    assert last_humanizer_variant(result["skills_used"]) == "snajp:humanizer-svenska"
    assert result["skills_used"][-1] == "snajp:humanizer-svenska"


def test_grounding_step_requires_the_humanizer_ran_first():
    """Ordningsvillkoret ligger i förvillkorsgrinden, inte i en kommentar."""
    assert GROUNDING_V1.steps[0].requires == ("skill:snajp:humanizer-svenska",)
    assert GROUNDING_V1.steps[1].requires == ("skill:mk:copy-editing",)


@pytest.mark.anyio
async def test_grounding_playbook_refuses_to_run_before_the_humanizer():
    """Kör GROUNDING_V1 mot en ledger där humanizern inte kört."""
    from app.agentcore.packs import MissingRequirementError, RunLedger, check_preconditions

    with pytest.raises(MissingRequirementError):
        check_preconditions(GROUNDING_V1.steps[0], RunLedger(satisfied={"context_pack"}))
