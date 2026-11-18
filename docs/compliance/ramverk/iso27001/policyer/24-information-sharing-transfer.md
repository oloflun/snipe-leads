# Information Sharing & Transfer

| | |
|---|---|
| Status | **UTKAST 2026-11-17, inte godkänd** |
| Ägare | Anton |
| Godkänns av | Anton |
| Granskningsintervall | Årligen (mallens `frequency: yearly`) |
| Ramverkets mall | `frk_pt_685e46557bc14fbddea6468a` (avdelning `it`) |
| Täcker kontroller | Data Masking (`frk_ct_6849c343d7fbe4e71446ce78`), Data Privacy (`frk_ct_684071e280c4e0f777b957f7`), Secure Data Transfer (`frk_ct_68406fc94e08f884cc085ded`) |
| Täcker krav | A.5.14, A.6.6, A.8.10, A.8.11, A.8.12, A.8.33 |

## Syfte

Kunddata ska bara flyttas över skyddade kanaler, till mottagare med avtal, och i så liten mängd som möjligt.

## Omfattning

All överföring av kunddata och interna uppgifter: mellan tjänsterna, till leverantörer, mellan miljöerna, och till kunder och registrerade.

## Godkända sätt

- HTTPS till leverantörer och kunder. Redis utan TLS är ett avsteg (P23).
- Registerutdrag och export till en registrerad lämnas som krypterad fil eller via kundens egen kanal, aldrig som bilaga i klartext (G04).
- Inga fysiska medier.

## Delning med andra

- Kunddata går bara till leverantörer som godkänts enligt `../../gdpr/policyer/06-vendor-third-party-risk.md` och har avtal. **Avsteg i dag:** kundmejl till TypeSafe utan avtal (`../../../BESLUTSUNDERLAG-2026-11-17.md` A2), och produktionsdata genom GitHubs runners var tionde minut utan DPA (`.github/workflows/synk.yml`; JA #11).
- Den som får se kunddata utanför driften (jurist, revisor, ny medarbetare) skriver först på ett sekretessavtal.
- Länkar till testmiljön och skärmdumpar med kunddata delas inte med utomstående (`DEPLOY.md:170-171`).

## Minimering och maskering

- Personnummer maskeras före Vertex (`snajp-support/app/moderation/maskering.py`). Adresser och telefonnummer tas bort före Jev (`snajp-support/app/leads/jev.py:63-77`).
- Webbplatsbedömningen lämnar bara plattformsadmin och två namngivna kunder (`CLAUDE.md`). Listkopior saknar fälten (`snajp-support/app/api/admin_listor.py:LISTRADSFALT`).
- **Testdata (krav A.8.33):** `development` får produktionens persondata oförändrad. Det är det största avsteget från minimeringen. Anton beslutar om minimering eller pseudonymisering (JA #16), [FYLL: datum].

## Överföring till tredjeland

Mekanism per leverantör (DPF, SCC) står i `../../../leverantorsgranskning.md` och `docs/registerforteckning.md`. Överföringar utan mekanism (TypeSafe, ScrapeGraphAI, GitHub Free) ska stoppas eller avtalas (JA #3, #10, #11).

## Logg över överföringar

Mallen kräver logg över varje utgående överföring av Begränsad data. Snajps vanliga överföringar sker i kod till kända leverantörer och syns i registerförteckningen. Manuella överföringar (utdrag, exporter, dumpar) loggas i `../../../loggar/overforingar.md` med datum, vem, mottagare, innehåll och kanal. Loggen finns inte; införs [FYLL: datum]. Sparas i ett år.

## Mätning

Varje kvartal: stickprov i loggen, och kontroll att inga nya leverantörer får kunddata utan avtal.

## Undantag

En okrypterad överföring av data med låg klassning kräver Antons ja.

## Brister

En överföring utan avtal eller skydd behandlas som incident (G03).

## Förbättring

Lägg till verktyg för säker delning när behovet uppstår.
