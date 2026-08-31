# Session 2026-08-31 — Grok — testlager, inkorg, isolering

Standup mot Claudes handoff, Antons skärmbilder, plan godkänd. Första
leveransen pushad så deployen gick att testa. Resten av de öppna punkterna
byggda och pushade i samma dag.

## Gjort

- Fas 1: exempelbolag bara i demon, polling via `/leads/jobb/{id}`.
- Fas 3: Bearbetas, testmail ur tenantens KB.
- Fas 4: undersökningsärende, feedback-grind, kalibrering.
- Fas 5: impersonation tvingar is_test på skrivningar, inte på GET.
- Fas 6: inställningscopy/gruppering.
- Fas 2: `is_test` på ss_emails/ss_tickets (057 kört mot development),
  Testmail-flik, Flytta till ärenden, ifyllnad vid befordra, Byt kund,
  konvertera testkund i admin.
- Fas 7: Redis EU + shadow mätt. TLS av, inte påslaget.
- 21 exempelbolag raderade från Snajp-tenanten.

## Inte gjort

Browser-QA mot den nya deployen. Redis TLS (`scripts/redis_tls_pa.py --apply`).
INV-API-001 oauth.ts. Railway auto-deploytrigger.

<!-- session-state
open_threads: 3
handoffs_pending:
  - HANDOFF-2026-08-31-TESTISOLERING.md
next_session_focus: "Live-verifiera Testmail-flik, Byt kund och flytta-ifyllnad mot web-development. Redis TLS är Antons apply."
session-state -->
