-- Del F step 12 / A2b: Snajp som sin egen tenant. Snajp ÄR SaaS med
-- prenumerationer, vilket gör mk:churn-prevention direkt tillämplig som
-- den är (utan att skrivas om, till skillnad från snajp:retention-
-- conversation) — ett bra testfall för att skillen fungerar innan den
-- används som policygenerator åt andra kunder.
--
-- Fast UUID, samma mönster som Nordlys Handel (003) och public-demo (011).
-- Detta skapar BARA tenant-raden. Att faktiskt köra onboarding
-- (mk:product-marketing, mk:customer-research, mk:churn-prevention på
-- Snajp självt) är ett live-steg som kräver en riktig LLM-nyckel — samma
-- "kvarstår hos dig"-status som branch protection i plan Del L6.

insert into ss_tenants (id, slug, name)
values ('00000000-0000-4000-a000-000000000002', 'snajp', 'Snajp')
on conflict (slug) do nothing;
