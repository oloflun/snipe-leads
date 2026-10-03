import type { Locale, Localized } from "@/lib/i18n";

/**
 * Adminytans texter på svenska och engelska.
 *
 * ## Varför de ligger samlade här och inte i komponenterna
 *
 * `lib/i18n.tsx` bär appens GEMENSAMMA copy — navigation, knappar, statusord.
 * Adminytans texter är många, långa och används på ett enda ställe var; hade
 * de lagts i samma ordbok hade den gemensamma ordboken blivit en adminordbok
 * med lite navigation i.
 *
 * Alternativet — `text({ sv: "…", en: "…" })` direkt i JSX — prövades och gör
 * tabellrubriker oläsbara: en rad med nio kolumnrubriker blev nio inbäddade
 * objekt i en map. Här står svenskan och engelskan bredvid varandra, vilket
 * också är det enda sättet att SE att en text saknar sin översättning.
 *
 * Nyckelnamnen är svenska av samma skäl som resten av kodbasen är det.
 */

export const ADMIN: Record<string, Localized> = {
  /* -------------------------------------------------- Översikt */
  oversiktRubrik: { sv: "Översikt", en: "Overview" },
  manadsintakt: { sv: "Månadsintäkt", en: "Monthly revenue" },
  uppskattadKostnad: { sv: "Uppskattad kostnad", en: "Estimated cost" },
  tokensAllaKunder: { sv: "Tokens, alla kunder", en: "Tokens, all customers" },
  marginal: { sv: "Marginal", en: "Margin" },
  ingenIntakt: { sv: "Ingen intäkt att räkna på", en: "No revenue to measure against" },
  intaktMinusToken: { sv: "Intäkt minus tokenkostnad", en: "Revenue minus token cost" },
  kraverAtgard: { sv: "Kräver åtgärd", en: "Needs attention" },

  /* -------------------------------------------------- Kolumner */
  kolKund: { sv: "Kund", en: "Customer" },
  kolPaket: { sv: "Paket", en: "Plan" },
  kolArenden: { sv: "Ärenden", en: "Tickets" },
  kolKorningar: { sv: "Körningar", en: "Runs" },
  kolTokens: { sv: "Tokens", en: "Tokens" },
  kolKostnad: { sv: "Kostnad", en: "Cost" },
  kolMarginal: { sv: "Marginal", en: "Margin" },
  kolFel: { sv: "Fel", en: "Errors" },
  kolSlug: { sv: "Slug", en: "Slug" },
  kolKundSedan: { sv: "Kund sedan", en: "Customer since" },
  kolAvtal: { sv: "Avtal", en: "Contract" },
  kolTrial: { sv: "Trial", en: "Trial" },
  kolSenastAktiv: { sv: "Senast aktiv", en: "Last active" },

  /* -------------------------------------------------- Hälsa */
  halsaBra: { sv: "Bra", en: "Healthy" },
  halsaOk: { sv: "Håll koll", en: "Watch" },
  halsaDalig: { sv: "Åtgärda", en: "Act now" },
  halsaTyst: { sv: "Tyst", en: "Dormant" },
  halsaOkand: { sv: "Okänd", en: "Unknown" },

  /* -------------------------------------------------- Fotnoter, Översikt */
  ingaKunder: {
    sv: "Inga kunder ännu. Tom lista är ett giltigt svar, inte ett fel.",
    en: "No customers yet. An empty list is a valid answer, not a failure."
  },
  seAllaKorningar: { sv: "Se alla körningar", en: "See all runs" },
  perManad: { sv: "/mån", en: "/mo" },
  test: { sv: "test", en: "test" },

  /* -------------------------------------------------- Kunder & Data */
  kunderRubrik: { sv: "Kunder & Data", en: "Customers & Data" },
  kunderIngress: {
    sv: "Alla registrerade kunder med volym, avtal och senaste aktivitet. Klicka på kundnamnet för kontaktpersoner och faktureringsuppgifter. Ekonomin och hälsobedömningen ligger under Översikt.",
    en: "Every registered customer with volume, contract and last activity. Click a customer name for contacts and billing details. Finances and the health assessment live under Overview."
  },
  ingaRegistrerade: {
    sv: "Inga kunder registrerade ännu.",
    en: "No customers registered yet."
  },
  saknas: { sv: "saknas", en: "missing" },
  inget: { sv: "inget", en: "none" },
  profil: { sv: "Profil", en: "Profile" },
  oppnaProfilen: { sv: "Öppna agentprofilen för", en: "Open the agent profile for" },
  profilOchArbetsyta: { sv: "Profil och arbetsyta", en: "Profile and workspace" },

  /* -------------------------------------------------- Statistik */
  statistik: { sv: "Statistik", en: "Statistics" },
  statistikIngress: {
    sv: "Signerade avtal och nya kunder över tid. Försäljningstakten nedan är definierad som nya kunder och signerade avtal per vecka — säg till om den ska mäta något annat.",
    en: "Signed contracts and new customers over time. The sales rate below is defined as new customers and signed contracts per week — say so if it should measure something else."
  },
  avtalIdag: { sv: "Avtal i dag", en: "Contracts today" },
  avtalVeckan: { sv: "Avtal denna vecka", en: "Contracts this week" },
  avtalManaden: { sv: "Avtal denna månad", en: "Contracts this month" },
  avtalAret: { sv: "Avtal i år", en: "Contracts this year" },
  nyaKunder: { sv: "Nya kunder", en: "New customers" },
  signeradeAvtal: { sv: "Signerade avtal", en: "Signed contracts" },
  perVecka12: { sv: "per vecka, senaste 12 veckorna", en: "per week, last 12 weeks" },
  visaSomTabell: { sv: "Visa som tabell", en: "Show as table" },
  vecka: { sv: "Vecka", en: "Week" },

  /* -------------------------------------------------- Fel & eskaleringar */
  felOchEskaleringar: { sv: "Fel & eskaleringar", en: "Errors & escalations" },
  eskaleradeArenden: { sv: "Eskalerade ärenden", en: "Escalated tickets" },
  allaKunderTotalt: { sv: "alla kunder, totalt", en: "all customers, total" },
  handelser: { sv: "Händelser", en: "Events" },
  minst: { sv: "minst ", en: "at least " },
  ggr: { sv: "ggr", en: "times" },
  tillKorningen: { sv: "till körningen", en: "to the run" },
  plattformsniva: { sv: "plattformsnivå", en: "platform level" },

  /* -------------------------------------------------- Händelser */
  filterAlla: { sv: "Alla", en: "All" },
  filterFel: { sv: "Fel", en: "Errors" },
  filterVarningar: { sv: "Varningar", en: "Warnings" },
  filterInfo: { sv: "Info", en: "Info" },
  handelserIngress: {
    sv: "Allt som plattformen loggat, grupperat på källa och orsak. Samma fel hundra gånger är ett problem, inte hundra — antalet står vid raden.",
    en: "Everything the platform has logged, grouped by source and cause. The same error a hundred times is one problem, not a hundred — the count sits on the row."
  },
  ingaHandelser: {
    sv: "Inga händelser. Det är det önskade tillståndet.",
    en: "No events. That is the desired state."
  },
  ingaHandelserFilter: {
    sv: "Inga händelser på den här nivån.",
    en: "No events at this level."
  },
  tekniskaDetaljer: { sv: "Tekniska detaljer", en: "Technical detail" },
  senast: { sv: "Senast", en: "Last seen" },
  forsta: { sv: "första", en: "first" },

  /* -------------------------------------------------- Exempeldata */
  exempel: { sv: "Exempel", en: "Example" },
  exempeldataMarkning: {
    sv: "Exempeldata — arbetsytan har ingen egen aktivitet",
    en: "Example data — this workspace has no activity of its own"
  },

  /* -------------------------------------------------- Sidrubriker och railnamn */
  korningarRubrik: { sv: "Körningar", en: "Runs" },
  korningRubrik: { sv: "Körning", en: "Run" },
  paketRubrik: { sv: "Paket", en: "Packages" },
  paketEtt: { sv: "Paket", en: "Package" },
  testkorningarRubrik: { sv: "Testkörningar", en: "Test runs" },
  agentanvandningRubrik: { sv: "Agentanvändning", en: "Agent usage" },
  kunddataRubrik: { sv: "Kunddata", en: "Customer data" },
  kundprofilRubrik: { sv: "Kundprofil", en: "Customer profile" },
  kunderLank: { sv: "Kunder", en: "Customers" },
  railIris: { sv: "Iris", en: "Iris" },
  railKundtjanst: { sv: "Kundtjänst", en: "Customer service" },
  railKvitton: { sv: "Kvitton", en: "Receipts" },
  leads: { sv: "Leads", en: "Leads" },

  /* -------------------------------------------------- Körningar */
  typIrisResearch: { sv: "Iris, research", en: "Iris, research" },
  typIrisUtskick: { sv: "Iris, utskick", en: "Iris, outreach" },
  typIrisSvar: { sv: "Iris, svar", en: "Iris, replies" },
  typIrisUppfoljning: { sv: "Iris, uppföljning", en: "Iris, follow-up" },
  typDemo: { sv: "Demo", en: "Demo" },
  ingaKorningarMatchar: { sv: "Inga körningar matchar.", en: "No runs match." },
  kolTid: { sv: "Tid", en: "Time" },
  kolTyp: { sv: "Typ", en: "Type" },
  kolPack: { sv: "Pack", en: "Pack" },
  kolLatens: { sv: "Latens", en: "Latency" },
  kolSpar: { sv: "Spår", en: "Trace" },
  steg: { sv: "Steg", en: "Step" },
  stegLista: { sv: "Steg", en: "Steps" },
  eskalerade: { sv: "Eskalerade", en: "Escalated" },
  forsok: { sv: "Försök", en: "Attempts" },
  reasoning: { sv: "Reasoning", en: "Reasoning" },
  thinking: { sv: "Thinking", en: "Thinking" },
  overlay: { sv: "Overlay", en: "Overlay" },
  grundatI: { sv: "Grundat i", en: "Grounded in" },
  systemprompt: { sv: "Systemprompt", en: "System prompt" },
  anvandarmeddelande: { sv: "Användarmeddelande", en: "User message" },
  rasvar: { sv: "Råsvar", en: "Raw output" },
  korningSaknas: { sv: "Körningen finns inte.", en: "The run does not exist." },
  tillbakaKorningar: { sv: "Tillbaka till körningarna", en: "Back to runs" },
  ingenSparning: {
    sv: "Körningen har ingen spårning. Onboardingkörningar (fas A) loggar inga steg.",
    en: "This run has no trace. Onboarding runs (phase A) log no steps."
  },

  /* -------------------------------------------------- Agentanvändning */
  okand: { sv: "okänd", en: "unknown" },
  ut: { sv: "ut", en: "out" },
  aiKostnadUppskattad: { sv: "AI-kostnad, uppskattad", en: "AI cost, estimated" },

  /* -------------------------------------------------- Kund: profil och data */
  kundSaknas: { sv: "Kunden gick inte att hämta.", en: "Could not load the customer." },
  tillbakaKundlistan: { sv: "Tillbaka till kundlistan", en: "Back to the customer list" },
  kundprofilIngress: {
    sv: "Allt som formar den här kundens agent. Ändringar gäller nästa körning. Pågående ärenden kör klart på de regler de startade med.",
    en: "Everything that shapes this customer's agent. Changes apply from the next run. Open tickets finish on the rules they started with."
  },
  agentprofil: { sv: "Agentprofil", en: "Agent profile" },
  bladdraKunder: { sv: "Bläddra mellan kunder", en: "Browse customers" },
  forra: { sv: "Förra:", en: "Previous:" },
  nasta: { sv: "Nästa:", en: "Next:" },
  av: { sv: "av", en: "of" },
  kunskapsbasKolon: { sv: "Kunskapsbas:", en: "Knowledge base:" },
  artiklar: { sv: "artiklar", en: "articles" },
  fackKolon: { sv: "Fack:", en: "Categories:" },
  standard: { sv: "standard", en: "default" },
  instruktionsversionKolon: { sv: "Instruktionsversion:", en: "Instruction version:" },
  ingenGlobalInstruktion: {
    sv: "Ingen global instruktion är sparad. Agenten kör på den incheckade agent-core/AGENTS.md ovanpå det som står här.",
    en: "No global instruction is saved. The agent runs on the checked-in agent-core/AGENTS.md on top of what is here."
  },
  vadAgentenLaserKund: { sv: "Vad agenten läser för den här kunden", en: "What the agent reads for this customer" },
  sparatNastaKorning: { sv: "Sparat. Gäller nästa körning.", en: "Saved. Applies from the next run." },
  kontaktpersoner: { sv: "Kontaktpersoner", en: "Contacts" },
  ingaKontaktpersoner: { sv: "Inga kontaktpersoner ännu.", en: "No contacts yet." },
  laggTillKontaktperson: { sv: "Lägg till kontaktperson", en: "Add contact" },
  laggTill: { sv: "Lägg till", en: "Add" },
  laggerTill: { sv: "Lägger till…", en: "Adding…" },
  kunduppgifter: { sv: "Kunduppgifter", en: "Customer details" },
  sparaKunduppgifter: { sv: "Spara kunduppgifter", en: "Save customer details" },
  saknasStor: { sv: "Saknas", en: "Missing" },
  kontaktNamn: { sv: "Namn", en: "Name" },
  kontaktRoll: { sv: "Roll", en: "Role" },
  kontaktMejl: { sv: "Mejl", en: "Email" },
  kontaktDirektnummer: { sv: "Direktnummer", en: "Direct number" },
  taBort: { sv: "Ta bort", en: "Remove" },
  ingetAndrat: { sv: "Inget ändrat.", en: "Nothing changed." },
  sparatPunkt: { sv: "Sparat.", en: "Saved." },
  kontaktBehoverNamn: { sv: "Kontaktpersonen behöver ett namn.", en: "The contact needs a name." },
  kundeInteSparaKontakt: { sv: "Kunde inte spara kontaktpersonen.", en: "Could not save the contact." },
  kundeInteTaBortKontakt: { sv: "Kunde inte ta bort kontaktpersonen.", en: "Could not remove the contact." },
  kundeInteLaggaTillKontakt: {
    sv: "Kunde inte lägga till kontaktpersonen.",
    en: "Could not add the contact."
  },

  /* -------------------------------------------------- Konvertera testkund */
  flyttaTillRiktigt: { sv: "Flytta till riktigt konto", en: "Move to a real account" },
  malkonto: { sv: "Målkonto", en: "Target account" },
  ingaRiktigaKonton: { sv: "Inga riktiga konton att flytta till", en: "No real accounts to move to" },
  kor: { sv: "Kör…", en: "Running…" },
  visaVadSomFlyttas: { sv: "Visa vad som skulle flyttas", en: "Show what would be moved" },
  skrivOver: { sv: "Skriv över", en: "Overwrite" },
  raderIMaletRaderas: { sv: "rader i målet raderas,", en: "rows in the target are deleted," },
  raderas: { sv: "raderas,", en: "deleted," },
  kopieras: { sv: "kopieras.", en: "copied." },
  rostdokumentKolon: { sv: "Röstdokument:", en: "Voice documents:" },
  fackreglerKolon: { sv: "Fackregler:", en: "Category rules:" },

  /* -------------------------------------------------- Agentinstruktioner */
  hamtarInstruktionerna: { sv: "Hämtar instruktionerna", en: "Loading the instructions" },
  instruktionernaKundeInteHamtas: {
    sv: "Instruktionerna kunde inte hämtas:",
    en: "The instructions could not be loaded:"
  },
  vadAgentenLaserNu: { sv: "Vad agenten läser just nu", en: "What the agent reads right now" },
  lagetKundeInteLasas: { sv: "Läget kunde inte läsas.", en: "The state could not be read." },
  ingenInstruktionSparad: {
    sv: "Ingen instruktion är sparad. Agenten kör på den incheckade",
    en: "No instruction is saved. The agent runs on the checked-in"
  },
  sparad: { sv: "Sparad", en: "Saved" },
  oknatDatum: { sv: "okänt datum", en: "unknown date" },
  struktureradAvModellen: { sv: "strukturerad av modellen", en: "structured by the model" },
  sparadSomDenSkrevs: { sv: "sparad som den skrevs", en: "saved as written" },
  tomtParentes: { sv: "(tomt)", en: "(empty)" },
  policyOchSakerhet: {
    sv: "Här står policy och säkerhet. Ton och röst ställer varje kund in själv.",
    en: "Policy and safety go here. Each customer sets tone and voice themselves."
  },
  dinaInstruktioner: { sv: "Dina instruktioner och din feedback", en: "Your instructions and feedback" },
  tecken: { sv: "tecken", en: "characters" },
  teckenRubrik: { sv: "Tecken", en: "Characters" },
  vadAgentenKommerLasa: { sv: "Vad agenten kommer att läsa", en: "What the agent will read" },
  strukturerasNar: {
    sv: "(struktureras när du förhandsgranskar eller sparar)",
    en: "(structured when you preview or save)"
  },
  redigeradForHand: { sv: "Redigerad för hand, sparas ordagrant.", en: "Edited by hand, saved verbatim." },
  strukturerasAvModellen: { sv: "Struktureras av modellen.", en: "Structured by the model." },
  forhandsgranska: { sv: "Förhandsgranska", en: "Preview" },
  sparar: { sv: "Sparar…", en: "Saving…" },
  spara: { sv: "Spara", en: "Save" },
  sparaOchAktivera: { sv: "Spara och aktivera", en: "Save and activate" },
  historik: { sv: "Historik", en: "History" },
  kalla: { sv: "Källa", en: "Source" },
  status: { sv: "Status", en: "Status" },
  strukturerad: { sv: "Strukturerad", en: "Structured" },
  manuell: { sv: "Manuell", en: "Manual" },
  aktiv: { sv: "Aktiv", en: "Active" },
  kundeInteStrukturera: { sv: "Kunde inte strukturera texten.", en: "Could not structure the text." },
  kundeInteSpara: { sv: "Kunde inte spara.", en: "Could not save." },
  forhandsgranskningEjSparad: {
    sv: "Förhandsgranskning. Ingenting är sparat ännu.",
    en: "Preview. Nothing is saved yet."
  },
  sparatAllaKunder: {
    sv: "Sparat. Gäller nästa körning, för alla kunder.",
    en: "Saved. Applies from the next run, for all customers."
  },

  /* -------------------------------------------------- Paket */
  aktivaKunder: { sv: "Aktiva kunder", en: "Active customers" },
  pausade: { sv: "Pausade", en: "Paused" },
  avslutade: { sv: "Avslutade", en: "Closed" },
  paketvardePerManad: { sv: "Paketvärde per månad", en: "Package value per month" },
  aktivaMedExaktPaket: { sv: "Aktiva kunder med exakt paket", en: "Active customers on an exact package" },
  ingaKunderPaket: {
    sv: "Inga kunder ännu. Raderna dyker upp när första kunden onboardats.",
    en: "No customers yet. Rows appear once the first customer is onboarded."
  },
  kundernasPaket: { sv: "Kundernas paket och kontoläge", en: "Customer packages and account status" },
  pris: { sv: "Pris", en: "Price" },
  hantera: { sv: "Hantera", en: "Manage" },
  prisPaForfragan: { sv: "Pris på förfrågan", en: "Price on request" },
  egetUrval: { sv: "Eget urval:", en: "Custom selection:" },
  ingenArbetsyta: { sv: "Ingen arbetsyta", en: "No workspace" },
  trialTill: { sv: "Trial till", en: "Trial until" },
  ingetAvtal: { sv: "Inget avtal", en: "No contract" },
  ingenKoppladArbetsyta: {
    sv: "Kunden har ingen kopplad arbetsyta, så det finns inget paket att byta här.",
    en: "The customer has no linked workspace, so there is no package to change here."
  },
  nuvarande: { sv: "Nuvarande", en: "Current" },
  valt: { sv: "Valt", en: "Selected" },
  byterPaket: { sv: "Byter paket …", en: "Changing package …" },
  bytTill: { sv: "Byt till", en: "Change to" },
  avbryt: { sv: "Avbryt", en: "Cancel" },
  bytetGallerDirekt: {
    sv: "Bytet gäller direkt: vyer utanför det nya paketet försvinner ur kundens meny, och faktureringen är manuell så nästa faktura skrivs efter det nya paketet.",
    en: "The change applies immediately: views outside the new package disappear from the customer's menu, and billing is manual, so the next invoice follows the new package."
  },
  paketetKundeInteBytas: { sv: "Paketet kunde inte bytas.", en: "The package could not be changed." },
  tillagg: { sv: "Tillägg", en: "Add-ons" },
  hamtarTillaggen: { sv: "Hämtar tilläggen …", en: "Loading add-ons …" },
  kontolage: { sv: "Kontoläge", en: "Account status" },
  kontotOppet: {
    sv: "Kontot är öppet: agenterna, arbetsytan och den publika chatten svarar.",
    en: "The account is open: the agents, the workspace and the public chat respond."
  },
  kontotPausat: {
    sv: "Kontot är pausat: nycklarna avvisas och inget svarar, men allt står orört och väntar. Att öppna igen är ett klick.",
    en: "The account is paused: keys are rejected and nothing responds, but everything stays untouched and waiting. Reopening is one click."
  },
  kontotAvslutat: {
    sv: "Kontot är avslutat: nycklarna avvisas och inget svarar. Ingenting är raderat, så en återaktivering öppnar allt igen.",
    en: "The account is closed: keys are rejected and nothing responds. Nothing is deleted, so reactivating opens everything again."
  },
  pausenLaser: {
    sv: "Pausen låser ute alla agenter, arbetsytan, portalen och chatten i samma ögonblick. Ingenting raderas, och kontot öppnas igen med ett klick här.",
    en: "The pause locks out all agents, the workspace, the portal and the chat at once. Nothing is deleted, and the account reopens with one click here."
  },
  avslutetLaser: {
    sv: "Avslutet låser ute alla agenter, arbetsytan, portalen och chatten i samma ögonblick. Ingenting raderas, men läget är tänkt som ett avslut, inte en paus.",
    en: "Closing locks out all agents, the workspace, the portal and the chat at once. Nothing is deleted, but this state is meant as an ending, not a pause."
  },
  orsakHandelseloggen: { sv: "Orsak, hamnar i händelseloggen", en: "Reason, goes into the event log" },
  platsPausa: { sv: "Kunden vill pausa över sommaren.", en: "The customer wants to pause over the summer." },
  platsAvsluta: { sv: "Kunden har sagt upp avtalet.", en: "The customer has terminated the contract." },
  pausar: { sv: "Pausar …", en: "Pausing …" },
  avslutar: { sv: "Avslutar …", en: "Closing …" },
  pausa: { sv: "Pausa", en: "Pause" },
  avsluta: { sv: "Avsluta", en: "Close" },
  pausaKontot: { sv: "Pausa kontot …", en: "Pause the account …" },
  avslutaKontot: { sv: "Avsluta kontot …", en: "Close the account …" },
  oppnar: { sv: "Öppnar …", en: "Opening …" },
  oppnaKontotIgen: { sv: "Öppna kontot igen", en: "Reopen the account" }
};

/** `ADMIN`-uppslagning för ett känt språk. Kortare än `text(ADMIN.x)` i JSX. */
export function a(nyckel: keyof typeof ADMIN, locale: Locale): string {
  return ADMIN[nyckel][locale];
}

/**
 * Ett besked som redan är färdig text (backendens felmeddelande, en
 * anmärkning från servern) i samma form som en översatt text. Felstate i
 * adminkomponenterna bär `Localized`, så att fallbacktexterna byter språk;
 * backendens egna ord har bara ett språk och visas som de kom.
 */
export function ordagrant(text: string): Localized {
  return { sv: text, en: text };
}

/**
 * TIDSZONEN ÄR SPIKAD, och det är inte en detalj.
 *
 * Vyerna som kallar de här funktionerna är klientkomponenter, och en
 * klientkomponent renderas TVÅ gånger: en gång på servern (SSR) och en gång i
 * webbläsaren (hydrering). Servern kör i UTC, webbläsaren i besökarens zon. En
 * tidsstämpel som `2026-08-26T23:30:00Z` blir då 26 augusti på servern och 27
 * augusti i Stockholm — olika text på samma rad, alltså en hydreringskrock.
 *
 * `Europe/Stockholm` och inte besökarens zon: det ÄR besökarens zon här (en
 * intern driftvy för ett svenskt bolag), och en fast zon är det enda som gör
 * de två renderingarna identiska. Bonus: raderna visar numera lokal tid i
 * stället för den råa UTC-strängen den gamla vyn skrev ut.
 */
const TIDSZON = "Europe/Stockholm";

/**
 * Datum enligt språkvalet.
 *
 * `sv-SE` ger 2026-08-29 och `en-GB` ger 29/08/2026 — INTE `en-US`, som hade
 * gett 8/29/2026. En intern driftvy läses av folk som skriver datum bakifrån,
 * och den amerikanska ordningen är den enda som går att missläsa som en annan
 * giltig dag.
 */
export function datum(varde: string | null | undefined, locale: Locale): string {
  if (!varde) return "—";
  const d = new Date(varde);
  return Number.isNaN(d.getTime())
    ? "—"
    : d.toLocaleDateString(locale === "sv" ? "sv-SE" : "en-GB", { timeZone: TIDSZON });
}

/** Tidsstämpel i listor: datum och klockslag, utan sekunder och utan T. */
export function tidpunkt(varde: string, locale: Locale): string {
  const d = new Date(varde);
  if (Number.isNaN(d.getTime())) return varde.slice(0, 19).replace("T", " ");
  return d.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB", {
    timeZone: TIDSZON,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

/** Tusentalsavgränsat heltal enligt språkvalet. */
export function antal(varde: number, locale: Locale): string {
  return varde.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB");
}
