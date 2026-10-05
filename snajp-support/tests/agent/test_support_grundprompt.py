"""Grundprompten (2026-10-05): allt kundarbete utgår från
agent-core/prompts/support-systemprompt.md.

Kontrollerar att den faktiskt NÅR modellen — i varje steg i chattkedjan, i
mejlinkorgens enda anrop och i omformuleringen — att varje platshållare fylls,
och att dess beslut (avsnitt 11) får följder i kod. Mockar bara nätverksgränsen.
"""

import json
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent import support_systemprompt
from app.agent.support_agent import (
    _LOVAR_KOLLEGA,
    _ar_kansligt,
    kb_kartan,
    run_support_agent,
    tolka_beslut,
)
from app.agent.triage import tolka_svar, triage_email_llm
from app.config import CATEGORIES, get_settings
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"


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


class _LLM:
    def __init__(self, overrides: dict | None = None):
        self.calls: list[str] = []
        self.system_by_skill: dict[str, str] = {}
        self.user_by_skill: dict[str, str] = {}
        self.overrides = overrides or {}
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        system = messages[0]["content"]
        skill = re.search(r"styrs av skillen (\S+?),", system).group(1)
        self.calls.append(skill)
        self.system_by_skill[skill] = system
        self.user_by_skill[skill] = messages[1]["content"]
        payload = {"sources_used": ["kb-1"], "context_refs": ["context_pack"]}
        payload.update(
            {
                "cs:ticket-triage": {
                    "category": "betalning", "priority": "P3", "sentiment": 0.6,
                    "escalate": False, "ber_om_manniska": False,
                    "inom_amnesomradet": True, "missforstadd": False,
                },
                "cs:customer-research": {
                    "findings": "KB täcker frågan.", "confidence": 0.8,
                    "kb_supports_answer": True, "behover_fortydligande": False,
                },
                "cs:draft-response": {"draft": "Du kan betala med Swish eller kort.", "beslut": "SVARA"},
                "cs:customer-escalation": {"should_escalate": False, "reason": None},
                "cs:kb-article": {"should_create": False},
                "snajp:humanizer-svenska": {"final_reply": "Du kan betala med Swish eller kort."},
            }.get(skill, {})
        )
        payload.update(self.overrides.get(skill, {}))
        message = type("M", (), {"content": json.dumps(payload, ensure_ascii=False)})()
        usage = type("U", (), {"prompt_tokens": 100, "completion_tokens": 20})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


async def _tur(storage, llm, message, *, channel="web"):
    with patch("app.agent.step_runner.get_llm_client", return_value=llm), patch(
        "app.agent.support_agent.classify_cancellation_risk", new=AsyncMock(return_value=(0.0, 0.0))
    ):
        return await run_support_agent(
            storage, TENANT,
            message=message, subject="", channel=channel,
            customer_email="kund@exempel.se", customer_name="Kim Kund", attachments=[],
        )


# -- Renderingen -------------------------------------------------------------


@pytest.mark.parametrize("lage", sorted(support_systemprompt.LAGEN))
@pytest.mark.parametrize("kanal", ["web", "email", "whatsapp", "okand-kanal"])
def test_varje_platshallare_fylls_i_varje_lage_och_kanal(lage, kanal):
    text = support_systemprompt.rendera(foretagsnamn="Cykelboden AB", kanal=kanal, lage=lage)
    assert "{{" not in text and "}}" not in text
    assert "Cykelboden AB" in text
    assert "Om filen" not in text
    # Promptens kärna är kvar ordagrant.
    assert "Vid tveksamhet: eskalera." in text
    assert "## 10. Självkontroll innan du lämnar svaret" in text


def test_okand_platshallare_fäller_hellre_an_att_na_modellen(monkeypatch):
    support_systemprompt.cache_clear()
    monkeypatch.setattr(
        support_systemprompt, "_mall", lambda: "Hej {{FÖRETAGSNAMN}}, {{NY_INSTÄLLNING}}"
    )
    with pytest.raises(support_systemprompt.OkandPlatshallare):
        support_systemprompt.rendera(foretagsnamn="X", kanal="web")


def test_chatt_far_ingen_signatur_mejl_far_avsandaren():
    chatt = support_systemprompt.rendera(foretagsnamn="Cykelboden AB", kanal="web")
    mejl = support_systemprompt.rendera(
        foretagsnamn="Cykelboden AB", kanal="email", avsandare="Cykelboden AB", lage="mejl"
    )
    assert "Signatur: Ingen. Det här är en chatt" in chatt
    assert "\"Vänliga hälsningar,\" och på raden under \"Cykelboden AB\"" in mejl


def test_kundskriven_text_renderas_aldrig_in_i_systemprompten():
    """INV-SEC-009: kunskapsbas, kunddata och tråd pekas ut, kopieras inte in."""
    text = support_systemprompt.rendera(foretagsnamn="X", kanal="web")
    assert "Står i användarmeddelandet under rubriken \"Kunskapsbas\"" in text
    assert "<kunddata>" in text


# -- Chattkedjan --------------------------------------------------------------


@pytest.mark.anyio
async def test_grundprompten_nar_varje_steg_fore_skillen():
    storage = MemoryStorage()
    llm = _LLM(overrides={
        "cs:customer-research": {"kb_supports_answer": False, "behover_fortydligande": False},
    })
    svar = await _tur(storage, llm, "Levererar ni till Island?")
    assert len(llm.calls) >= 4
    for skill, system in llm.system_by_skill.items():
        assert "## GRUNDPROMPT" in system, skill
        assert "## 1. Roll och uppdrag" in system, skill
        assert "## Driftregel" in system or "KÄRNAN av grundprompten" in system, skill
        assert system.index("## GRUNDPROMPT") < system.index(f"styrs av skillen {skill}"), skill
        assert "{{" not in system, skill
    # Hela prompten där svaret skrivs, kärnan i de billigare stegen.
    assert "## 6. Beslutsregler" in llm.system_by_skill["cs:draft-response"]
    assert "## 9. Svarsmallar" in llm.system_by_skill["cs:draft-response"]
    for skill in ("cs:ticket-triage", "cs:customer-research", "snajp:humanizer-svenska"):
        assert "## 9. Svarsmallar" not in llm.system_by_skill[skill], skill
    # Spårvyn ska kunna visa att den nådde fram.
    assert all(steg["grundprompt_chars"] > 1_500 for steg in svar["step_log"] if "skill" in steg)


@pytest.mark.anyio
async def test_kunskapsbasen_far_kall_id():
    storage = MemoryStorage()
    await storage.add_kb_article(
        TENANT, title="Betalsätt", content="Vi tar Swish och kort.", category="betalning"
    )
    llm = _LLM()
    await _tur(storage, llm, "Vilka betalsätt har ni?")
    assert "[KB-1] Betalsätt" in llm.user_by_skill["cs:draft-response"]
    assert "beslut (SVARA, MOTFRÅGA, DELVIS eller ESKALERA)" in llm.user_by_skill["cs:draft-response"]


@pytest.mark.anyio
async def test_delvis_ar_ett_erbjudande_inte_en_overlamning():
    """Driftregeln (2026-10-06): en kunskapslucka lämnas inte över. Svaret
    erbjuder en kollega, och kundens "ja" blir överlämningen."""
    storage = MemoryStorage()
    text = (
        "Du kan betala med Swish eller kort. Om faktura har jag ingen uppgift — "
        "vill du att en kollega tittar på det?"
    )
    llm = _LLM(overrides={
        "cs:draft-response": {
            "draft": text,
            "beslut": "DELVIS",
            "kundens_frågor": [
                {"fråga": "betalsätt", "status": "besvarad", "källor": ["KB-1"]},
                {"fråga": "faktura", "status": "saknar_underlag", "källor": []},
            ],
            "intern_notering": "Kunden vill betala mot faktura, KB-1 saknar det.",
        },
        "snajp:humanizer-svenska": {"final_reply": text},
    })
    svar = await _tur(storage, llm, "Vilka betalsätt har ni, går faktura?")
    assert svar["escalated"] is False
    samtal = await storage.get_chat_state(TENANT, svar["customer_id"])
    assert samtal["erbjod_manniska"] is True

    ja = await _tur(storage, _LLM(), "ja tack")
    assert ja["escalated"] is True
    assert ja["escalation_code"] == "kund_bad_om_manniska"


@pytest.mark.anyio
async def test_eskalera_fran_utkastet_lamnar_over_med_intern_notering():
    storage = MemoryStorage()
    text = "Det här behöver en kollega titta på. Hela samtalet följer med."
    llm = _LLM(overrides={
        "cs:draft-response": {
            "draft": text,
            "beslut": "ESKALERA",
            "kundens_frågor": [{"fråga": "undantag", "status": "eskalerad", "källor": []}],
            "intern_notering": "Kunden vill ha undantag från KB-1.",
        },
        "snajp:humanizer-svenska": {"final_reply": text},
    })
    svar = await _tur(storage, llm, "Kan ni göra ett undantag för mig?")
    assert svar["escalated"] is True
    assert svar["escalation_code"] == "modellbedomning"
    assert svar["reply"].count("kollega") == 1
    assert "Obesvarat: undantag" in svar["escalation_reason"]
    assert "Intern notering: Kunden vill ha undantag" in svar["escalation_reason"]


@pytest.mark.anyio
async def test_svara_med_obesvarad_fraga_raknas_som_delvis():
    storage = MemoryStorage()
    llm = _LLM(overrides={
        "cs:draft-response": {
            "draft": "Du kan betala med Swish eller kort.",
            "beslut": "SVARA",
            "kundens_frågor": [{"fråga": "faktura", "status": "saknar_underlag", "källor": []}],
        },
    })
    svar = await _tur(storage, llm, "Går det att betala mot faktura?")
    assert svar["escalated"] is False
    samtal = await storage.get_chat_state(TENANT, svar["customer_id"])
    assert samtal["erbjod_manniska"] is True


@pytest.mark.anyio
async def test_ai_fragan_besvaras_med_erbjudande_och_lamnas_inte_over():
    storage = MemoryStorage()
    text = "Jag är en AI-assistent. Vill du att jag kopplar in en kollega?"
    llm = _LLM(overrides={
        "cs:ticket-triage": {"ber_om_manniska": True},
        "cs:draft-response": {"draft": text, "beslut": "SVARA"},
        "snajp:humanizer-svenska": {"final_reply": text},
    })
    svar = await _tur(storage, llm, "Pratar jag med en riktig människa eller en bot?")
    assert svar["escalated"] is False
    samtal = await storage.get_chat_state(TENANT, svar["customer_id"])
    assert samtal["erbjod_manniska"] is True


@pytest.mark.anyio
async def test_krisraden_laggs_pa_i_kod_om_modellen_tappade_den():
    storage = MemoryStorage()
    text = "Jag tar det du skriver på allvar. En kollega tar över här."
    llm = _LLM(overrides={
        "cs:draft-response": {"draft": text, "beslut": "ESKALERA"},
        "snajp:humanizer-svenska": {"final_reply": text},
    })
    svar = await _tur(storage, llm, "Jag vill inte leva längre")
    assert svar["escalated"] is True
    assert "ring 112" in svar["reply"]
    assert "90101" in svar["reply"]


@pytest.mark.anyio
async def test_svensk_sokfraga_soks_ocksa_ensam_och_slas_ihop():
    """Skarptest 2026-10-06: "dubbeldebiterad" i den långa frågan hittade
    inte artikeln om dubbeldragning — omformuleringen ensam gör det."""
    storage = MemoryStorage()
    llm = _LLM(overrides={"cs:ticket-triage": {"sokfraga_sv": "dubbeldragning debitering"}})
    svar = await _tur(storage, llm, "Hej, pengarna drogs visst två gånger för min order igår?")
    rubriker = [k["title"] for k in svar["kb_sources"]]
    assert any("Dubbeldragning" in r for r in rubriker), rubriker


@pytest.mark.anyio
async def test_loftesgrinden_gor_ett_kollegalofte_sant():
    """Ett SVARA som ändå lovar att en kollega återkommer: ingen människa hade
    sett ärendet. Grinden lämnar över i stället för att låta löftet ljuga."""
    storage = MemoryStorage()
    text = "Jag har skickat din fråga vidare, en kollega återkommer till dig."
    llm = _LLM(overrides={
        "cs:draft-response": {"draft": text, "beslut": "SVARA"},
        "snajp:humanizer-svenska": {"final_reply": text},
    })
    svar = await _tur(storage, llm, "Kan ni ändra min leveransadress?")
    assert svar["escalated"] is True
    assert svar["escalation_code"] == "modellbedomning"
    samtal = await storage.get_chat_state(TENANT, svar["customer_id"])
    assert samtal["lage"] == "overlamnad"


@pytest.mark.anyio
async def test_kris_eskalerar_och_far_hanvisa_till_112():
    storage = MemoryStorage()
    text = "Jag är ledsen att du har det så. Är du i akut fara, ring 112. En kollega tar över här."
    llm = _LLM(overrides={
        "cs:draft-response": {"draft": text, "beslut": "ESKALERA"},
        "snajp:humanizer-svenska": {"final_reply": text},
    })
    svar = await _tur(storage, llm, "Jag orkar inte mer, jag vill inte leva")
    assert svar["escalated"] is True
    assert "112" in svar["reply"]
    assert svar["faktagrind"]["ok"] is True
    assert "ringa 112" in llm.user_by_skill["cs:draft-response"]
    assert "brådskande" in svar["escalation_reason"]


@pytest.mark.parametrize(
    "text",
    [
        "Ni har dubbeldebiterat mig",
        "Jag blev debiterad två gånger",
        "Fakturan är fel",
        "Jag vill rätta mina personuppgifter",
        "Laddaren gav en elchock",
    ],
)
def test_promptens_nya_eskaleringsamnen_fangas_i_kod(text):
    assert _ar_kansligt(text)


@pytest.mark.parametrize("text", ["När kommer fakturan?", "Kan jag betala mot faktura?"])
def test_vanliga_fakturafragor_eskalerar_inte(text):
    assert not _ar_kansligt(text)


def test_kollegaloften_kanns_igen_men_inte_erbjudanden():
    assert _LOVAR_KOLLEGA.search("Jag har skickat det vidare till en kollega.")
    assert _LOVAR_KOLLEGA.search("En kollega återkommer så snart som möjligt.")
    assert not _LOVAR_KOLLEGA.search("Vill du att jag kopplar in en kollega?")


def test_tolka_beslut_ar_tolerant():
    assert tolka_beslut({})["beslut"] is None
    assert tolka_beslut({"beslut": "motfraga"})["beslut"] == "MOTFRÅGA"
    assert tolka_beslut({"beslut": "nonsens"})["beslut"] is None
    assert tolka_beslut({"kundens_frågor": "inte en lista"})["obesvarade"] == []


def test_kb_kartan_foljer_blockets_numrering():
    assert kb_kartan([{"title": "A"}, {"title": "B"}]) == {"KB-1": "A", "KB-2": "B"}


# -- Mejlinkorgen ------------------------------------------------------------


@pytest.mark.anyio
async def test_mejltriagen_har_grundprompten_som_systemmeddelande():
    svar = MagicMock()
    svar.choices = [MagicMock(message=MagicMock(content=json.dumps({
        "beslut": "SVARA", "kategori": "leverans", "svarsutkast": "Hej Anna, ...",
    })))]
    klient = MagicMock()
    klient.chat.completions.create = AsyncMock(return_value=svar)
    with patch("app.agent.triage.get_llm_client", return_value=klient):
        resultat = await triage_email_llm(
            sender="anna@exempel.se", subject="Leverans", body="När kommer paketet?",
            kb_articles=[{"title": "Frakt", "content": "2-4 vardagar.", "similarity": 0.9}],
            foretagsnamn="Cykelboden AB",
        )
    meddelanden = klient.chat.completions.create.await_args.kwargs["messages"]
    assert meddelanden[0]["role"] == "system"
    assert "kundtjänstagent för **Cykelboden AB**" in meddelanden[0]["content"]
    assert "{{" not in meddelanden[0]["content"]
    assert "[KB-1] Frakt" in meddelanden[1]["content"]
    assert resultat["category"] == "leverans"
    assert resultat["draft_reply"] == "Hej Anna, ..."
    assert resultat["escalate"] is False


def test_mejlets_delvis_eskalerar_inte():
    resultat = tolka_svar(
        {"beslut": "DELVIS", "kategori": "betalning", "svarsutkast": "Hej Maria, ..."}, []
    )
    assert resultat["escalate"] is False
    assert resultat["beslut"] == "DELVIS"


def test_mejlets_eskalera_och_bradska_eskalerar_med_notering():
    resultat = tolka_svar(
        {
            "beslut": "ESKALERA",
            "kategori": "betalning",
            "brådskande": True,
            "kundens_frågor": [{"fråga": "gruppris", "status": "saknar_underlag", "källor": []}],
            "svarsutkast": "Hej Maria, kursen kostar ...",
            "intern_notering": "Gruppris saknas i KB-1.",
            "eskaleringsorsak": "Saknar källa för central fråga",
        },
        [{"title": "Kurspriser"}],
    )
    assert resultat["escalate"] is True
    assert resultat["priority"] == "high"
    assert "KB-1 «Kurspriser»" in resultat["escalation_reason"]
    assert resultat["category"] in CATEGORIES


def test_mejlets_gamla_faltnamn_fungerar_fortfarande():
    resultat = tolka_svar(
        {"category": "leverans", "draft_reply": "Hej!", "escalate": True, "escalation_reason": "x"},
        [],
    )
    assert resultat["draft_reply"] == "Hej!"
    assert resultat["escalate"] is True


@pytest.mark.anyio
async def test_promptens_faltnamn_svarsutkast_godtas_utan_omkorning():
    """Skarptest 2026-10-06: modellen följer avsnitt 11 och skriver
    `svarsutkast`. Formatgrinden körde om hela utkaststeget för det —
    ett extra anrop per ärende."""
    storage = MemoryStorage()
    llm = _LLM(overrides={
        "cs:draft-response": {"svarsutkast": "Du kan betala med Swish eller kort.", "beslut": "SVARA"},
    })
    svar = await _tur(storage, llm, "Vilka betalsätt har ni?")
    assert llm.calls.count("cs:draft-response") == 1
    assert "Swish" in svar["reply"]


def test_exemplen_foljer_inte_med_i_drift_men_kontraktet_gor():
    text = support_systemprompt.rendera(foretagsnamn="X", kanal="web")
    assert "## 12. Exempel" not in text
    assert "## 11. Utdataformat" in text
    assert "## 9. Svarsmallar" in text


@pytest.mark.parametrize(
    ("fore", "efter"),
    [
        ("Vi tar faktura. [KB-1]", "Vi tar faktura."),
        ("Vi tar faktura (KB-1, KB-3).", "Vi tar faktura."),
        ("Enligt KB-2 tar det 2–4 vardagar.", "Enligt tar det 2–4 vardagar."),
        ("Inga ID här.", "Inga ID här."),
    ],
)
def test_kall_id_tvattas_ur_kundtext(fore, efter):
    from app.agent.support_agent import utan_kall_id

    assert utan_kall_id(fore) == efter


def test_erbjudande_om_vidarebefordran_ar_inget_lofte():
    assert not _LOVAR_KOLLEGA.search("Svara på mejlet så skickar jag det vidare.")
    assert _LOVAR_KOLLEGA.search("Jag har skickat din fråga vidare.")


def test_mejlets_kall_id_tvattas_och_erbjudandet_eskalerar_inte():
    resultat = tolka_svar(
        {
            "beslut": "DELVIS",
            "svarsutkast": "Vi tar faktura. [KB-1] Vill du att en kollega tittar på "
            "rabatten? Svara på mejlet så skickar jag det vidare.",
        },
        [{"title": "Om oss"}],
    )
    assert "KB-" not in resultat["draft_reply"]
    assert resultat["escalate"] is False


@pytest.mark.anyio
async def test_felbedomd_research_men_besvarat_utkast_ar_ett_besvarat_arende():
    """Dev 2026-10-06: researchen kallade "Vilka har grundat Snajp?" oklar,
    utkastet svarade ändå. Då gäller utkastet: ingen överlämning och ingen
    misslyckad runda mot motfrågetaket."""
    storage = MemoryStorage()
    llm = _LLM(overrides={
        "cs:customer-research": {"kb_supports_answer": False, "behover_fortydligande": True},
        "cs:customer-escalation": {"should_escalate": True, "reason": "x"},
    })
    svar = await _tur(storage, llm, "Hej! Vilka har grundat Snajp?")
    assert svar["escalated"] is False
    assert svar["svarslage"] == "besvara"
    assert "cs:customer-escalation" not in llm.calls
    samtal = await storage.get_chat_state(TENANT, svar["customer_id"])
    assert samtal["misslyckade_i_rad"] == 0


@pytest.mark.anyio
async def test_kodbeslutad_overlamning_syns_for_kunden():
    storage = MemoryStorage()
    text = "Agenten svarar utifrån din kunskapsbas."
    llm = _LLM(overrides={
        "cs:ticket-triage": {"escalate": True},
        "cs:draft-response": {"draft": text, "beslut": "SVARA"},
        "snajp:humanizer-svenska": {"final_reply": text},
    })
    svar = await _tur(storage, llm, "Hur fungerar agenten?")
    assert svar["escalated"] is True
    assert "kollega" in svar["reply"]


@pytest.mark.anyio
async def test_triagens_escalate_definieras_som_63_amnen():
    llm = _LLM()
    await _tur(MemoryStorage(), llm, "Hur fungerar agenten?")
    assert "Aldrig för en vanlig fråga, en säljfråga" in llm.user_by_skill["cs:ticket-triage"]


def test_slutlig_text_skalar_bort_humaniserarens_arbetsgang():
    from app.agent.support_agent import slutlig_text

    lackt = (
        "Utkast till omskrivning:\nHej, utkastet.\n\n"
        "Vad avslöjar att det här är AI-genererat?\n– Formellt.\n\n"
        "Slutlig version:\nHej, den riktiga texten."
    )
    assert slutlig_text(lackt) == "Hej, den riktiga texten."
    assert slutlig_text("Hej, vanlig text.") == "Hej, vanlig text."


def test_beskrivning_av_produkten_ar_inget_kollegalofte():
    assert not _LOVAR_KOLLEGA.search(
        "Sedan erbjuder den att en kollega tar över. Om du vill det lämnas ärendet över."
    )
    assert not _LOVAR_KOLLEGA.search("A colleague can take a look if you want.")
    assert _LOVAR_KOLLEGA.search("En kollega tar över härifrån.")
    assert _LOVAR_KOLLEGA.search("A colleague will get back to you shortly.")


@pytest.mark.anyio
async def test_lackt_arbetsgang_nar_aldrig_kunden():
    storage = MemoryStorage()
    lackt = "Utkast till omskrivning:\nX\n\nSlutlig version:\nDu kan betala med Swish eller kort."
    llm = _LLM(overrides={"snajp:humanizer-svenska": {"final_reply": lackt}})
    svar = await _tur(storage, llm, "Vilka betalsätt har ni?")
    assert svar["reply"] == "Du kan betala med Swish eller kort."
