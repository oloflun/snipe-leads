"""Reguljära uttryck som körs på mejltext ska ta linjär tid (kodskanningen 2026-11-17).

Uttrycken nedan körs på utkast, supportsvar och bolagsnamn. Texten kommer från
en modell som läst inkommande mejl och hämtade webbsidor, eller från en
människa som redigerat utkastet, så längden och innehållet styrs inte av oss.
Före rättningen tog vart och ett av fallen nedan sekunder på en rad om några
tiotusen tecken (kvadratisk backtracking) och blockerade arbetaren under tiden.

Varje test kör en lång, enformig sträng av det slag som gav den kvadratiska
tiden och kräver att den går fort. Gränsen är generös mot en långsam CI-maskin
men långt under den tid den gamla formen tog.
"""

from __future__ import annotations

import re
import time

from app.leads import halsning, outreach_playbook, signatur, text_delta, tilltal
from app.textkvalitet import putsa

N = 20_000
GRANS_SEKUNDER = 0.5


def _tid(f) -> float:
    start = time.perf_counter()
    f()
    return time.perf_counter() - start


def test_putsa_blanksteg_fore_skiljetecken_ar_linjar():
    assert _tid(lambda: putsa("a" + "\t" * N + "x")) < GRANS_SEKUNDER


def test_putsa_tar_fortfarande_bort_blanksteg_fore_skiljetecken():
    text, _ = putsa("Hej ,\nTack  \t. Vi hörs !")
    assert text == "Hej,\nTack. Vi hörs!"


def test_meningsdelningen_ar_linjar_pa_langa_skiljeteckensrader():
    assert _tid(lambda: text_delta.split_sentences("a" + "!" * N + "a")) < GRANS_SEKUNDER


def test_meningsdelningen_delar_som_forut():
    text = "Hej!!! Vi ses. Tack?! Bra"
    spans = text_delta.split_sentences(text)
    assert [text[a:b] for a, b in spans] == ["Hej!!! ", "Vi ses. ", "Tack?! ", "Bra"]


def test_anonym_halsning_ar_linjar():
    assert _tid(lambda: outreach_playbook.tilltala_med_ni("hej" + " " * N + "x")) < GRANS_SEKUNDER


def test_anonym_halsning_kanns_igen_som_forut():
    for rad in ("Hej,", "hej !", "Hejsan ,  ", "God dag", "  hallå!"):
        assert outreach_playbook._ANONYM_HALSNING.match(rad), rad
    assert not outreach_playbook._ANONYM_HALSNING.match("Hej Anna,")
    assert not outreach_playbook._ANONYM_HALSNING.match("Hej,,")


def test_avslutningsfrasen_ar_linjar():
    assert _tid(lambda: signatur._AVSLUTNING.search("\nmvh" + "\t" * N + "x")) < GRANS_SEKUNDER


def test_avslutningsfrasen_kanns_igen_som_forut():
    for text in ("Tack\nMvh,", "Tack\n  Med vänliga hälsningar !", "Thanks\nBest regards\t,\t", "Tack\nhälsningar"):
        assert signatur._AVSLUTNING.search(text), text
    assert not signatur._AVSLUTNING.search("Tack\nmvh,,")


def test_pronomenlaget_efter_radbrytningar_ar_linjart():
    assert _tid(lambda: tilltal._pronomen("\n" * N + "x")) < GRANS_SEKUNDER


def test_pronomenlaget_efter_skiljetecken_ar_som_forut():
    for fore in ("Tack för sist. ", "Hej!\n", "Fråga:  ", "Rad ett\n  \t", ""):
        assert tilltal._pronomen(fore) == (0, "Ni"), repr(fore)
    assert tilltal._pronomen("Vi tror att ")[1] != "Ni"


def test_bolagsnamnet_ar_linjart_pa_ett_orimligt_langt_namn():
    assert _tid(lambda: halsning.snyggt_bolagsnamn("a" + " AB" * N)) < GRANS_SEKUNDER


def test_bolagsnamnet_putsas_som_forut():
    assert halsning.snyggt_bolagsnamn("HORTLAX RÖR AB") == "Hortlax Rör"
    assert halsning.snyggt_bolagsnamn("B Flemströms Gräv & Last i Luleå AB") == "B Flemströms Gräv & Last"


def test_den_gamla_formen_var_kvadratisk():
    """Kontrollen av själva mätningen: den gamla formen av uttrycket i putsa
    tar mätbart längre tid på samma sträng. Utan den här raden kunde testerna
    ovan vara gröna för att strängen inte träffade det dåliga fallet."""
    gammal = re.compile(r"[ \t]+([,.!?;:])")
    assert _tid(lambda: gammal.sub(r"\1", "a" + "\t" * 4000 + "x")) > _tid(lambda: putsa("a" + "\t" * 4000 + "x"))
