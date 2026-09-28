"""Skopningarna av snajp:humanizer-svenska — på ett ställe.

Hela skillen är 27 081 tecken, och den laddas i fyra steg: leads-utkastet
(outreach V2), leads-reparationen (grounding), supportchattens sista hand och
bokföringsassistentens polering. Tre av dem skriver AFFÄRSTEXT — ett mejl
eller ett chattsvar — och har ingen nytta av exempelblocket (6 851 tecken) eller
registren för rapport, artikel och sociala medier.

`KALLMEJL` är outreach V2:s skopa, uppmätt och domartestad 2026-09-02 (se
kommentaren i app/leads/outreach_playbook.py). Ett arbetat exempel i
måltexttypen HOMOGENISERADE utkasten — exemplet är alltså inte bara en
kostnad utan en risk.

`SVAR` är samma skopa plus två mönster som kan uppstå i ett kundsvar men inte
i ett kallmejl: 14 (kunskapsavgränsning, "inom ramen för mina kunskaper" —
precis vad en supportmodell frestas att skriva när underlaget är tunt) och 16
(punktlistor och emoji — ett chattsvar renderas som text, och en punktlista
där en mening räcker är en AI-signal). Utelämnat: exemplen, registren för
rapport/artikel/socialt och mönster 10 (sociala medier). ~40 % av skillen.
"""

from __future__ import annotations

KALLMEJL: tuple[str, ...] = (
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
)

SVAR: tuple[str, ...] = (
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
    "§ 14. Kunskapsavgränsningsklausuler",
    "§ 15. Kopulaundvikande (utgör/representerar/utgör)",
    "§ 16. Bullet-punkts- och emoji-formatting som AI-signal",
    "§ Affärsskrivande (mejl, offerter, presentationer, intern kommunikation)",
    "§ PROCESS",
    "§ Utdataformat",
    "§ Snabbreferens: Vanliga byten",
)

SVAR_RATIONALE = (
    "Ett kundsvar är affärsskrivande. Utelämnat: exempelblocket, registren för "
    "rapport/artikel/socialt och mönster 10 (sociala medier) — ~40 % av skillen. "
    "Mönstren, rösten, affärsregistret, processen och utdataformatet laddas i sin "
    "helhet."
)
