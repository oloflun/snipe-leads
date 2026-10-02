-- 083: Lägesbeskrivning och signaler på prospektraden (plan del C, 2026-10-02).
--
-- Antons krav 2026-10-01: varje lead Iris presenterar MÅSTE bära en
-- lägesbeskrivning (vad bolaget gör, vad som hänt senast med källa, vad som
-- matchar profilen, varför nu), signaler och en kontaktperson med roll och
-- telefon eller mejl. Mejlet utgår sedan från just det läget.
--
-- lagesbeskrivning: modellens 4–6 meningar, ur källmaterialet (overlayen
--   leads-research-v2). Tom = inte leverbart (app/api/leads.py::_leverbarhet).
-- signaler: trigger_events ur researchen (rekrytering, expansion, ny ort …),
--   bara det källmaterialet faktiskt visar.
alter table public.prospects
  add column if not exists lagesbeskrivning text,
  add column if not exists signaler jsonb;
