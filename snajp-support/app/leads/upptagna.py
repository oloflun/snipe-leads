"""Upptagna bolag: det som varken Iris eller en leadslista får hämta igen.

Sebbes beställning 2026-10-06: Iris-leads och leadslistor är två skilda spår.
Iris hittar de kvalificerade bolagen med webbplats och research; listorna är
de mindre kvalificerade, mer "kalla samtal", och ska aldrig dela bolag med
Iris. Kundens egna kunder (en uppladdad CRM-lista, `kalla='crm'`) ska inte
prospekteras alls.

En nyckel per bolag: orgnr när det finns, annars namnet utan bolagsform och
skiljetecken ("Byggarna Berggren AB" och "byggarna berggren" är samma bolag).
Mängden innehåller båda sorterna, så ett register-träff med orgnr fastnar
även när namnet stavats annorlunda i kundens CRM.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Any

#: Bolagsformer som inte skiljer två bolag åt. Sist i namnet stryks de alla
#: ("Volvo AB (publ)", "Bygg HB i likvidation"); först bara AB ("AB Volvo").
_BOLAGSFORMER = {
    "ab", "aktiebolag", "publ", "hb", "handelsbolag", "kb", "kommanditbolag",
    "ek", "för", "ekonomisk", "förening", "ef", "enskild", "firma", "i", "likvidation",
}
_ORGNR = "orgnr:"


def nyckel(namn: str | None) -> str:
    """Bolagsnamnet jämförbart: casefold, skiljetecken bort, bolagsform bort."""
    text = unicodedata.normalize("NFKC", str(namn or "")).casefold().replace("&", " och ")
    ord_ = re.sub(r"[^\w]+", " ", text).split()
    while ord_ and ord_[-1] in _BOLAGSFORMER:
        ord_.pop()
    while ord_ and ord_[0] in ("ab", "aktiebolag"):
        ord_.pop(0)
    return " ".join(ord_) or text.strip()


def orgnr_nyckel(orgnr: str | None) -> str | None:
    siffror = "".join(ch for ch in str(orgnr or "") if ch.isdigit())
    # 12 siffror = sekelprefixet ("16" för juridiska personer) framför.
    if len(siffror) == 12:
        siffror = siffror[2:]
    return f"{_ORGNR}{siffror}" if len(siffror) == 10 else None


def nycklar(uteslut: Iterable[str]) -> set[str]:
    """Normaliserar en blandad mängd: namn blir namnnycklar, `orgnr:`-poster
    står kvar."""
    ut: set[str] = set()
    for post in uteslut:
        if not post:
            continue
        ut.add(post if post.startswith(_ORGNR) else nyckel(post))
    return ut


def bolagsnycklar(bolag: Iterable[dict[str, Any]]) -> set[str]:
    """Nycklarna för rader med `company_name` och (valfritt) `orgnr`."""
    ut: set[str] = set()
    for b in bolag:
        if b.get("company_name"):
            ut.add(nyckel(b["company_name"]))
        o = orgnr_nyckel(b.get("orgnr"))
        if o:
            ut.add(o)
    return ut


def upptagen(sedda: set[str], namn: str | None, orgnr: str | None = None) -> bool:
    o = orgnr_nyckel(orgnr)
    return bool((namn and nyckel(namn) in sedda) or (o and o in sedda))


def samma_bolag(rad: dict[str, Any], namn: str | None, orgnr: str | None = None) -> bool:
    """Samma bolag som raden? Org.nr avgör när båda har ett (två bolag kan
    heta likadant), annars namnet utan bolagsform. Grinden i
    storage.create_prospect (Antons krav 2026-10-08: ett bolag, ett ställe)."""
    a, b = orgnr_nyckel(rad.get("orgnr")), orgnr_nyckel(orgnr)
    if a and b:
        return a == b
    return bool(namn) and nyckel(rad.get("company_name")) == nyckel(namn)


def bara_namn(sedda: Iterable[str]) -> list[str]:
    """Namnposterna, för en prompt som ska få veta vad som redan är taget."""
    return sorted(p for p in sedda if not p.startswith(_ORGNR))


async def hamta(storage: Any, tenant_id: str) -> set[str]:
    """Alla bolag kunden redan har: Iris-prospekt, rader i varje leadslista
    (sökta, kombinerade, importerade) och CRM-kunder."""
    return bolagsnycklar(await storage.lista_upptagna_bolag(tenant_id))
