-- 076: Stripe-abonnemanget bort — kunderna faktureras manuellt av oss.
--
-- Migration 075 (billing_subscriptions + stripe_synka_abonnemang) kördes mot
-- development 2026-09-21 och återkallades samma dag: beslutet är att kunderna
-- faktureras av oss personligen och kontaktar oss för allt som rör betalning.
-- Ingen kortbetalning, ingen betalväxel.
--
-- Filen för 075 är borttagen ur katalogen. Den här migrationen städar bort det
-- 075 hann skapa, så att development-databasen åter speglar produktionen.
-- Mot main (där 075 aldrig kördes) är den en no-op.

drop function if exists public.stripe_synka_abonnemang(
  uuid, text, text, text, text, timestamptz, boolean, boolean, text[]
);
drop table if exists public.billing_subscriptions;
