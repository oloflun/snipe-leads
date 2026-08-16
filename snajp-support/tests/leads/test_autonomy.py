"""Autonominivån: EN regel, två anropsplatser.

Regeln avgör om ett mejl går till en riktig mottagare utan att en människa
sett det. Den bor i app/leads/autonomy.py och anropas från
leads_tools.queue_outreach_draft och scheduler.process_due_item — testerna
här mäter regeln själv, de två anropsplatserna har egna tester.
"""

from __future__ import annotations

import pytest

from app.leads.autonomy import (
    DEFAULT_AUTONOMY,
    LEVELS,
    MEETING_REQUIRES_HANDOFF,
    UnknownAutonomyError,
    allowed_action,
    describe,
    normalize,
)


def test_defaulten_ar_draft():
    """Ett fel ska bli ett dåligt utkast, inte ett skickat mejl."""
    assert DEFAULT_AUTONOMY == "draft"
    assert allowed_action(None, 0) == "queue"


@pytest.mark.parametrize(
    "trasigt",
    [None, "", "DRAFT", "aggressive", 3, {"autonomy": "meeting"}, ["meeting"]],
)
def test_okant_varde_faller_till_draft(trasigt):
    """Fail-closed. Motsatt val gör ett skrivfel i en jsonb-nyckel till ett
    utskickat mejl."""
    assert normalize(trasigt) == "draft"
    assert allowed_action(trasigt, 0) == "queue"


def test_draft_koar_aven_uppfoljningar():
    """En kund som valt draft har inte valt 'draft utom vid tredje mejlet'."""
    assert [allowed_action("draft", i) for i in range(4)] == ["queue"] * 4


def test_first_contact_skickar_bara_forsta():
    assert allowed_action("first_contact", 0) == "send"
    assert allowed_action("first_contact", 1) == "queue"
    assert allowed_action("first_contact", 7) == "queue"


def test_meeting_skickar_forsta():
    assert allowed_action("meeting", 0) == "send"


def test_meeting_koar_uppfoljningar_tills_handoff_ar_pakopplad():
    """handoff.py saknar produktionsanropare. Att låta agenten driva tråden
    vidare utan den betyder att den skriver mot ett svar den inte kan tolka."""
    if MEETING_REQUIRES_HANDOFF:
        assert allowed_action("meeting", 1) == "queue"
    else:
        assert allowed_action("meeting", 1) == "send"


def test_negativt_sekvensindex_ar_ett_fel_inte_ett_tyst_utskick():
    with pytest.raises(UnknownAutonomyError):
        allowed_action("first_contact", -1)


@pytest.mark.parametrize("level", LEVELS)
def test_varje_niva_har_en_beskrivning_kunden_kan_lasa(level):
    text = describe(level)
    assert text and text[0].isupper() and text.endswith(".")
    # Ingen intern vokabulär i en text kunden ska fatta beslut på.
    assert "send_queue" not in text
    assert "sequence_index" not in text


def test_nivaerna_ar_stigande_i_befogenhet():
    """Ordningen i LEVELS är inte kosmetisk — UI:t renderar den som en
    segmenterad kontroll där vänster är försiktigast.

    draft köar allt; de tre övriga får skicka första kontakten.
    """
    sends_first = [allowed_action(level, 0) == "send" for level in LEVELS]
    assert sends_first == [False, True, True, True]


def test_bara_auto_send_skickar_uppfoljningar_sjalvt():
    """Det är HELA skillnaden mellan auto_send och nivåerna under den. Utan
    det här testet kan `meeting` glida till att bete sig som auto_send utan
    att någon märker det förrän en uppföljning gått ut."""
    uppfoljning = [allowed_action(level, 1) == "send" for level in LEVELS]
    assert uppfoljning == [False, False, False, True]
