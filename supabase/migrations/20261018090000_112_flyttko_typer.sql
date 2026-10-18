-- 112: Flyttloggen tar emot alla flytttyper (Sebbe 2026-10-18).
--
-- 085 tillät bara 'mejl' och 'korning'. Enstaka leads ('prospekt', 2026-10-06)
-- och leadslistor ('lista', 2026-10-18) flyttas genom samma väg
-- (app/api/admin_flytt.py), och kvittot efter en lyckad flytt föll på
-- check-villkoret: development svarade 500 trots att main tagit emot paketet.
-- Tabellen finns i båda miljöerna (samma schema), men bara development skriver.
alter table public.dev_flytt_ko drop constraint if exists dev_flytt_ko_typ_check;
alter table public.dev_flytt_ko
  add constraint dev_flytt_ko_typ_check check (typ in ('mejl', 'korning', 'prospekt', 'lista'));
