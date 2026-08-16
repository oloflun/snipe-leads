-- Prospekttabellen kan inte hålla den data nischtargetingen bygger på.
--
-- Uppmätt mot produktionsschemat: `public.prospects` har company_name,
-- contact_name, contact_email, language_state, status, icp_fit, qualified och
-- disqualifiers. Alltså INGET av
--
--     orgnr · ort · postnr · sni · hemsida · anställda · omsättning
--
-- vilket är exakt de sju fält `app/leads/sources/base.Prospect` producerar och
-- `app/leads/scoring.py` dömer på.
--
-- Två konsekvenser utan den här migrationen, båda tysta:
--
--  1. En CSV-körning kan hitta rätt bolag men bara spara namnet och adressen.
--     Nästa körning måste göra om hela urvalet, och granskningsvyn kan inte
--     visa VARFÖR ett bolag valdes — score_breakdown pekar på fält som inte
--     finns i databasen.
--
--  2. `send_guard` regel 5:s karens per företag har ingen företagsnyckel att
--     räkna på. Utan org.nr faller den tillbaka på e-postdomänen, och ett
--     bolag som byter kontaktperson hade kunnat få ett nytt kallmejl dagen
--     efter — vilket är precis det regeln finns för att förhindra.
--
-- Fälten är alla nullbara. En källa som inte kan fylla i dem ska fungera ändå;
-- scoringen skiljer redan på "okänd" och "stämmer inte" och behöver NULL för
-- att kunna göra det.

alter table public.prospects
  add column if not exists orgnr text,
  add column if not exists ort text,
  add column if not exists postnr text,
  add column if not exists sni text,
  add column if not exists website text,
  add column if not exists anstallda integer,
  add column if not exists omsattning bigint,
  -- Hela score_breakdown som jsonb. Att spara den RENDERADE motiveringen och
  -- inte bara siffran är poängen: en användare som ser "84/100" utan att veta
  -- varför litar inte på listan, och poängen går inte att räkna om i efterhand
  -- eftersom kundens ICP kan ha ändrats sedan körningen.
  add column if not exists score_breakdown jsonb not null default '[]'::jsonb,
  add column if not exists score_total integer;

-- Företagsnyckeln send_guard:s karensregel slår upp på. Genererad i stället
-- för skriven av koden: två kodvägar som räknar fram samma nyckel är två
-- tillfällen att räkna fram den olika, och den skillnaden syns först när ett
-- dubbelutskick redan gått.
--
-- Samma prioritetsordning som app/leads/send_guard.foretagsnyckel():
-- org.nr först (överlever domänbyte), e-postdomänen som andrahandsval.
alter table public.prospects
  add column if not exists foretagsnyckel text
  generated always as (
    coalesce(
      nullif(regexp_replace(coalesce(orgnr, ''), '\D', '', 'g'), ''),
      nullif(lower(split_part(coalesce(contact_email, ''), '@', 2)), '')
    )
  ) stored;

create index if not exists prospects_foretagsnyckel_idx
  on public.prospects (tenant_id, foretagsnyckel);

-- Geografifiltret slår upp på postnummerprefix (se app/leads/geo.py).
create index if not exists prospects_postnr_idx
  on public.prospects (tenant_id, left(postnr, 3));

comment on column public.prospects.foretagsnyckel is
  'Genererad. Identiteten send_guard regel 5 räknar karens på — org.nr först, '
  'e-postdomän som fallback. Får INTE skrivas av koden: två uträkningar är två '
  'tillfällen att räkna olika.';
