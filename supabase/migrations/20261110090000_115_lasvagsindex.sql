-- 115: index för leadsvyernas läsvägar (stabilitetsarbetet fas 2, 2026-11-10).
--
-- Uppmätt i development: send_queue hade lästs sekventiellt 1,37 miljoner
-- gånger. Varje vy som visar utkastens läge slog upp trådens senaste köpost
-- per tråd, och send_queue har bara index på (status, scheduled_at). Hos den
-- största kunden var det 3 184 genomläsningar och 1,8 s per anrop.
--
-- Frågan för hela kunden läser sedan 2026-11-10 tabellen en gång i stället
-- (storage.utkast_lagen), så vyerna är snabba även utan de här indexen. De
-- behövs för uppslagen per tråd och per prospekt, som finns kvar på ett
-- tiotal ställen (sändvägen, kampanjernas poster, ett prospekts utkast).
--
-- Additiv och idempotent. Tabellerna är små (tusental rader), så indexen
-- byggs på ett ögonblick och utan `concurrently`.

-- Trådens senaste köpost: where thread_id = $1 order by created_at desc.
create index if not exists send_queue_trad_idx
  on public.send_queue (thread_id, created_at desc);

-- Granskningskön och förfallna utskick per kund.
create index if not exists send_queue_kund_status_idx
  on public.send_queue (tenant_id, status, scheduled_at);

-- Kundens trådar, och ett prospekts tråd (find_outreach_thread, utkast_lagen).
create index if not exists outreach_threads_kund_prospekt_idx
  on public.outreach_threads (tenant_id, prospect_id, created_at);

-- Skickade mejl, nyast först (list_skickade).
create index if not exists outreach_messages_skickade_idx
  on public.outreach_messages (tenant_id, sent_at desc)
  where direction = 'outbound' and sent_at is not null;

-- Prospektlistan, nyast först med stabil ordning (list_prospects).
create index if not exists prospects_kund_skapad_idx
  on public.prospects (tenant_id, created_at desc, id);
