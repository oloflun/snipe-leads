# Session 2026-08-31 — Grok — testlager och inkorg

Standup mot Claudes handoff (exempelbolag + död polling), sedan Antons
skärmbilder och kravlista. Plan godkänd: inga PR:er, push till development
först när allt är verifierat.

## Gjort

- Fas 1: tog bort exempelbolag från `LeadsRunForm`, 403 på exempel-API utanför
  demon, polling via `/leads/jobb/{id}`. Tester gröna.
- Fas 3: Bearbetas i inkorgen, testmail ur tenantens KB.
- Fas 4: undersökningsärende, feedback-grind, kalibreringsblock i testchatt.
- Fas 5 (del): impersonation tvingar `is_test` i `proxyAsTenant`.
- Fas 6: inställningscopy/gruppering.
- Fas 7: Redis-enhetstester gröna, inte live.

## Inte gjort (står i handoffen)

Live-verifiering i webbläsare, push, rensa_exempelbolag mot development,
is_test på mock-inkorg, flytta-formulär, kundväljare, Redis TLS.

<!-- session-state
open_threads: 6
handoffs_pending:
  - HANDOFF-2026-08-31-TESTLAGER-OCH-UI.md
next_session_focus: "Live-verifiera mot web-development, kör rensa_exempelbolag, pusha development när definition of done är grön"
session-state -->
