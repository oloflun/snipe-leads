"""JobTech-källan söker på KUNDENS målgrupp, inte på Snajps egen köpsignal.

Uppmätt 2026-09-15 som kunden Nordform Kontor (säljer skrivbord): källan
sökte "kundtjänst Stockholm Göteborg" oavsett branscher, och alla fem bolagen
i körningen var bolag som rekryterade kundtjänst. All HTTP mockas.
"""

from __future__ import annotations

import httpx

from app.leads.sources.jobtech import JobTechSource, ar_formedlare, sokord_for

_RIKTIG_CLIENT = httpx.Client

NORDFORM = {
    "industries": ["IT-konsulter", "redovisningsbyråer"],
    "geography": ["Stockholm", "Göteborg"],
    "roles": ["VD", "kontorschef"],
    "must_have": ["Växer, rekryterar, flyttar till nytt kontor"],
}


def _fanga_fragor(monkeypatch, hits=None):
    fragor: list[str] = []

    def handler(request):
        fragor.append(request.url.params["q"])
        return httpx.Response(200, json={"hits": hits or []})

    def fabrik(**kwargs):
        return _RIKTIG_CLIENT(transport=httpx.MockTransport(handler))

    monkeypatch.setattr("app.leads.sources.jobtech.httpx.Client", fabrik)
    return fragor


def test_branscherna_ar_sokorden_inte_kundtjanst(monkeypatch):
    fragor = _fanga_fragor(monkeypatch)
    JobTechSource().search(NORDFORM)
    assert fragor == [
        "IT-konsulter Stockholm Göteborg",
        "redovisningsbyråer Stockholm Göteborg",
    ]
    assert not any("kundtjänst" in f or "kundservice" in f or "innesälj" in f for f in fragor)


def test_roller_blir_aldrig_sokord(monkeypatch):
    """'VD Stockholm' ger rekryteringsfirmor och storbolag som söker en VD."""
    fragor = _fanga_fragor(monkeypatch)
    assert JobTechSource().search({"roles": ["VD"], "geography": ["Stockholm"]}) == []
    assert fragor == [], "utan bransch eller kort nischord ska källan inte fråga alls"


def test_kort_nischord_anvands_utan_bransch():
    assert sokord_for({"must_have": ["tandläkare"]}) == ["tandläkare"]


def test_leadslistans_meningstitel_blir_inget_sokord():
    """Listans titel hamnar i must_have. En hel mening som annonsfråga ger
    slumpträffar — då söker källan inte, och Gemini tolkar fritexten."""
    titel = (
        "IT-konsulter och redovisningsbyråer i Stockholm, 10–49 anställda, "
        "som växer eller flyttar till nytt kontor"
    )
    assert sokord_for({"must_have": [titel]}) == []


def test_bemannings_och_rekryteringsbolag_filtreras(monkeypatch):
    hits = [
        {"employer": {"name": "ACADEMIC WORK SWEDEN AB"}},
        {"employer": {"name": "Rekryteringshuset i Sverige AB"}},
        {"employer": {"name": "Kraftsam Rekrytering & Bemanning AB"}},
        {"employer": {"name": "Randstad AB"}},
        {"employer": {"name": "evolvit Accounting AB"}, "workplace_address": {"municipality": "Stockholm"}},
    ]
    _fanga_fragor(monkeypatch, hits)
    traffar = JobTechSource().search({"industries": ["redovisningsbyrå"]})
    assert [p.company_name for p in traffar] == ["evolvit Accounting AB"]


def test_formedlare_kanns_igen_utan_att_fanga_vanliga_bolag():
    assert ar_formedlare("MT Search & Recruit AB")
    assert ar_formedlare("Experis AB")
    assert not ar_formedlare("SysPartner Consulting AB")
    assert not ar_formedlare("Nordkap Moduler AB")
