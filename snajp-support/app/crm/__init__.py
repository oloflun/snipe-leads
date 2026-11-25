"""Snajp CRM: bolag, personer och kundsynken in (migration 153).

Antons beställning 2026-11-24, efter demon för Buddy: kunddatan ska synkas in
över ett API i stället för att laddas upp som lista, och kunderna ska gå att
hantera i Snajp. Koden är Snajps egen (docs/BESLUT.md 2026-11-25).

Modulerna:

- `falt`      normalisering och validering efter svensk standard
              (organisationsnummer, momsnummer, telefon, postnummer).
- `adaptrar`  källsystemens format in till den kanoniska modellen, med en
              fältmappning som kunden kan justera per anslutning.
- `lagring`   tabellerna crm_*. Egen modul i samma mönster som
              app/integrationer/lagring.py: Postgres via storage._scoped,
              och en dict på minneslagret i testsviten.
- `synk`      själva synken: hitta rätt post, slå ihop utan dubbletter,
              avgör konflikter fält för fält och för liggaren.
- `nycklar`   API-nycklar med omfång.

Ett bolag i CRM:et är samma bolag som i leads: nyckeln är organisationsnumret
(app/leads/upptagna.py: orgnr_nyckel), och varje levande CRM-bolag utesluts ur
Iris-körningar och listbyggen (storage.lista_upptagna_bolag).
"""
