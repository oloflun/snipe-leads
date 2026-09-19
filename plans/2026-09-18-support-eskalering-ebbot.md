# Support-agentens kvalitet enligt Ebbot-modellen

## Scope
- Research av Ebbots publika produkt och demochatt (godkänd av Sebbe innan kod).
- Eskalering: fasta triggers i kod, sömlös överlämning i samma chattfönster, hela historiken till medarbetaren, ton och trösklar per kund.
- Uttrycklig osäkerhet, proaktivt nästa steg, faktagrind mot kunskapsbasen, svar på kundens språk.
- Inga visuella ändringar på hemsidan utöver det som krävs för funktionen (Sebbes gräns).
- Utanför scope, gjort av annan session: kanaler och integrationer (`snipe-36u`).

## Completed
- [x] Ebbot-research och riktning, godkänd 2026-09-18
- [x] Fasta eskaleringstriggers med orsakskod (`support_regler.py`, `support_agent.py`), INV-ESC-001
- [x] Samtalsläge per kund, migration 066 (körd mot development, och mot main enligt torrkörning)
- [x] Medarbetarens sida: `overlamning.py`, `/api/chattar`, portalvyn Chattar
- [x] Chattfönstret: pollning av medarbetarens svar och återställning vid omladdning
- [x] Regler per kund: `/api/support/config` och panelen `SupportEskalering.tsx`
- [x] Faktagrind med tre nivåer (`support_faktagrind.py`), plus rättningar för klockslag, tusentalskomma och enhet
- [x] Svar på kundens språk, fasta texter på svenska och engelska
- [x] Härdning av de nya ytorna (fel, laddning, långa länkar, höger-till-vänster-text, tangentbord)
- [x] Kundtest på dev med riktig modell, sex fel hittade och rättade (tillsammans med kanalsessionen)
- [x] Release-PR #22 development → main skapad och beskriven

## In Progress
- [ ] PR #22 väntar på Antons merge (migrationer 066–068 och `INTEGRATION_NYCKEL` klara i main)

## Remaining
- [ ] `verify_railway.py` efter mergen
- [ ] `snipe-v60`: notis till kundföretagets medarbetare vid eskalering
- [ ] `snipe-njh`: obesvarad överlämning ska synas i Chattar även efter 24 timmar
- [ ] `snipe-pgz`: rate limit för `POST /api/chat/samtal`

## Deferred
- Fasta repliker på fler språk än svenska och engelska
- Påhoppsspärrens svar på andra språk än svenska
- Granskning av portalens inloggade vyer på dev (kräver Sebbes inloggning)

## Blockers
- Produktionen kräver Antons godkännande och merge av PR #22.

## Next Steps
- Efter Antons merge: `python scripts/verify_railway.py`.
- Nästa byggsteg: `snipe-v60`.
