-- ÅTERSTÄLLD UR LIGGAREN 2026-08-16. Tillägg till 018_rpc_hardening som
-- aldrig fick en egen repo-fil.
--
-- Rådgivaren flaggar current_workspace_id för mutable search_path. Den är
-- security definer och anropas inifrån varje workspace-scopad RLS-policy, så
-- en injicerad search_path hade kunnat byta ut vilka tabeller den läser.

alter function public.current_workspace_id() set search_path = public, pg_temp;
