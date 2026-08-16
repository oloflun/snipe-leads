-- ÅTERSTÄLLD UR LIGGAREN 2026-08-16. Ingen repo-fil har någonsin funnits;
-- ändringen kördes via Management-API:t och existerade bara i databasen.
--
-- Varför den betyder något: `segment_ab_aggregate()` returnerar aggregerad
-- statistik över segment. Utan den här återkallelsen kan `anon` — alltså vem
-- som helst med den publika nyckeln — anropa den direkt via PostgREST.

revoke execute on function segment_ab_aggregate() from anon, authenticated;
