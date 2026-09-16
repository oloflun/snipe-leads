/**
 * Exempeldatan för /demo/kvitton. Påhittad, och märkt som påhittad.
 *
 * ## Regeln som gäller här och som inte får brytas
 *
 * Samma som för leads-agentens exempelbolag och den gamla bokföringsdemon:
 * ingen riktig kunddata, och ingen siffra som ser ut att komma från en verklig
 * körning. Mejlen nedan är hittepå, bolagen finns inte, och det står på sidan.
 *
 * ## Samma berättelse som backendens mock-inkorg
 *
 * Mejlen speglar `FEJKMEJL` i snajp-support/app/kvitton/mejl.py — samma
 * avsändare, samma belopp, samma tre flaggade fall (utländsk valuta, otydligt
 * belopp, möjlig dubblett). Det är avsiktligt: den öppna demon och den
 * inloggade testkörningen ska berätta EN historia, inte två som råkar likna
 * varandra. tests/test_demo_kvitton.py räknar om varje summa nedan; går
 * demon och backendens fixturer isär fälls bygget.
 *
 * ## Varför siffrorna är handräknade och står utskrivna
 *
 * Demon kör ingen LLM och anropar ingen backend. Talen är konstanter med
 * facit i kommentaren, och testet räknar om dem — samma mönster som den
 * gamla bokföringsdemon använde och av samma skäl.
 */

export type Demomejl = {
  id: string;
  avsandare: string;
  amne: string;
  /** ÅÅÅÅ-MM-DD */
  datum: string;
  /** En rad ur mejlet som visas i inkorgsvyn — beloppsraden när det finns en. */
  rad: string;
  utfall: "kvitto" | "kvitto_granska" | "ej_kvitto";
  /** Maskinläsbart brutto i SEK, eller null (flaggat/inte kvitto). */
  belopp: string | null;
  /** Utländskt originalbelopp när SEK-beloppet saknas. */
  beloppOriginal?: string;
  momssats?: string;
  kategoriEtikett?: string;
  anmarkning?: string;
};

/** Inkorgen, i den ordning skanningen läser den. */
export const MEJL: Demomejl[] = [
  {
    id: "m1",
    avsandare: "Nordvik Drivmedel AB",
    amne: "Kvitto från Nordvik Drivmedel",
    datum: "2026-09-02",
    rad: "Diesel 41,2 l · Totalt: 623,50 kr",
    utfall: "kvitto",
    belopp: "623.50",
    momssats: "0.25",
    kategoriEtikett: "Drivmedel"
  },
  {
    id: "m2",
    avsandare: "Bistro Linnea",
    amne: "Ditt kvitto från Bistro Linnea",
    datum: "2026-09-04",
    rad: "Lunch 2 personer · Totalt: 486,00 kr",
    utfall: "kvitto",
    belopp: "486.00",
    momssats: "0.12",
    kategoriEtikett: "Representation"
  },
  {
    id: "m3",
    avsandare: "Skrivbo Kontorsvaror AB",
    amne: "Kvitto och orderbekräftelse #48213",
    datum: "2026-09-05",
    rad: "Papper, pärmar, toner · Totalt: 1 245,00 kr",
    utfall: "kvitto",
    belopp: "1245.00",
    momssats: "0.25",
    kategoriEtikett: "Kontorsmateriel"
  },
  {
    id: "m4",
    avsandare: "Skrivbo Kontorsvaror AB",
    amne: "Kvitto #48213 (kopia)",
    datum: "2026-09-06",
    rad: "Samma köp, skickat igen",
    utfall: "kvitto_granska",
    belopp: null,
    kategoriEtikett: "Kontorsmateriel",
    anmarkning: "Möjlig dubblett av kvitto #48213 — räknas inte förrän du godkänt det."
  },
  {
    id: "m5",
    avsandare: "Figmara Inc.",
    amne: "Your Figmara receipt",
    datum: "2026-09-08",
    rad: "1 editor seat · Total: $45.00 USD",
    utfall: "kvitto_granska",
    belopp: null,
    beloppOriginal: "45.00 USD",
    kategoriEtikett: "Prenumerationer",
    anmarkning: "Utländsk valuta — beloppet räknas inte om automatiskt."
  },
  {
    id: "m6",
    avsandare: "Branschnytt",
    amne: "Nyhetsbrev v.37: tre trender i höst",
    datum: "2026-09-08",
    rad: "Veckans nyhetsbrev",
    utfall: "ej_kvitto",
    belopp: null
  },
  {
    id: "m7",
    avsandare: "Taxi Mälardalen",
    amne: "Kvitto på din resa",
    datum: "2026-09-09",
    rad: "Arlanda–Stockholm City · Totalt: 289,00 kr",
    utfall: "kvitto",
    belopp: "289.00",
    momssats: "0.06",
    kategoriEtikett: "Resor & transport"
  },
  {
    id: "m8",
    avsandare: "Svenska Tåglinjer AB",
    amne: "Kvitto — din biljett Stockholm–Göteborg",
    datum: "2026-09-10",
    rad: "2 kl · Totalt: 745,00 kr",
    utfall: "kvitto",
    belopp: "745.00",
    momssats: "0.06",
    kategoriEtikett: "Resor & transport"
  },
  {
    id: "m9",
    avsandare: "Molnlagring Norr AB",
    amne: "Kvitto på din prenumeration, september",
    datum: "2026-09-11",
    rad: "Molnlagring Bas · Totalt: 199,00 kr",
    utfall: "kvitto",
    belopp: "199.00",
    momssats: "0.25",
    kategoriEtikett: "Prenumerationer"
  },
  {
    id: "m10",
    avsandare: "Stadshotellet Örebro",
    amne: "Kvitto för din vistelse",
    datum: "2026-09-12",
    rad: "1 natt inkl. frukost · Totalt: 1 890,00 kr",
    utfall: "kvitto",
    belopp: "1890.00",
    momssats: "0.12",
    kategoriEtikett: "Logi"
  },
  {
    id: "m11",
    avsandare: "Parkera Nu AB",
    amne: "Kvitto parkering, zon 314",
    datum: "2026-09-13",
    rad: "Beloppet dras via appen",
    utfall: "kvitto_granska",
    belopp: null,
    kategoriEtikett: "Övrigt",
    anmarkning: "Inget totalbelopp gick att läsa ur mejlet."
  },
  {
    id: "m12",
    avsandare: "Anna Lindqvist",
    amne: "Möte på torsdag?",
    datum: "2026-09-14",
    rad: "Passar torsdag kl 10?",
    utfall: "ej_kvitto",
    belopp: null
  },
  {
    id: "m13",
    avsandare: "Verktygsboden Nord AB",
    amne: "Kvitto på ditt köp",
    datum: "2026-09-15",
    rad: "Borrmaskin, bitssats · Totalt: 2 340,00 kr",
    utfall: "kvitto",
    belopp: "2340.00",
    momssats: "0.25",
    kategoriEtikett: "Verktyg & förbrukning"
  }
];

/**
 * Sammanfattningen — summan av mejlen ovan, handräknad.
 *
 * Facit (bara kvitton med utfall "kvitto"):
 *   totalt = 623,50 + 486,00 + 1 245,00 + 289,00 + 745,00 + 199,00
 *          + 1 890,00 + 2 340,00                       = 7 817,50
 *   moms   = 124,70 + 52,07 + 249,00 + 16,36 + 42,17 + 39,80
 *          + 202,50 + 468,00                           = 1 194,60
 *   (momsen per kvitto är brutto × sats ÷ (1 + sats), öresavrundad)
 */
export const SAMMANFATTNING = {
  fran: "2026-09-01",
  till: "2026-09-30",
  antal: 11,
  antalKlara: 8,
  antalGranska: 3,
  totalt: "7817.50",
  moms: "1194.60",
  perKategori: [
    { etikett: "Verktyg & förbrukning", antal: 1, summa: "2340.00" },
    { etikett: "Logi", antal: 1, summa: "1890.00" },
    { etikett: "Kontorsmateriel", antal: 1, summa: "1245.00" },
    { etikett: "Resor & transport", antal: 2, summa: "1034.00" },
    { etikett: "Drivmedel", antal: 1, summa: "623.50" },
    { etikett: "Representation", antal: 1, summa: "486.00" },
    { etikett: "Prenumerationer", antal: 1, summa: "199.00" }
  ]
} as const;

/** Textsammanfattningen bredvid resultatet. Bara tal som står ovanför. */
export const SAMMANFATTNINGSTEXT =
  "Agenten hittade 11 kvitton i perioden 1–30 september, varav 8 lästes av " +
  "komplett på totalt 7 817,50 kr. Mest pengar gick till verktyg & förbrukning " +
  "(2 340,00 kr) och logi (1 890,00 kr). Den ingående momsen i de " +
  "avlästa kvittona är 1 194,60 kr. 3 kvitton flaggades för manuell granskning: " +
  "en möjlig dubblett, ett kvitto i utländsk valuta och ett utan läsbart belopp. " +
  "De räknas inte in i summorna förrän du godkänt dem.";

/**
 * Frågorna besökaren kan ställa, och svaren.
 *
 * Konstanter, inte en modell — sidan är publik och anonym. Varje krontal i
 * svaren finns i SAMMANFATTNING eller i ett mejl ovanför; testet kontrollerar
 * det, vilket är samma krav som INV-BOOK-003 ställer på det riktiga svaret.
 * Den sista frågan visar var rådgivningsgränsen går, med flit.
 */
export type Demofraga = { fraga: string; svar: string };

export const FRAGOR: Demofraga[] = [
  {
    fraga: "Hur mycket la vi på resor den här månaden?",
    svar:
      "2 924,00 kr på resor den här månaden. Transporten står för 1 034,00 kr: " +
      "taxin från Arlanda på 289,00 kr och tågbiljetten Stockholm–Göteborg på " +
      "745,00 kr.\n\n" +
      "Resten är hotellnatten i Örebro på 1 890,00 kr, som ligger under logi."
  },
  {
    fraga: "Vilka kvitton flaggades för granskning?",
    svar:
      "Tre stycken. Kopian av kvitto #48213 från Skrivbo Kontorsvaror är en " +
      "möjlig dubblett av ett kvitto som redan är inläst. Figmara-kvittot är på " +
      "45.00 USD och räknas inte om till kronor automatiskt. Parkeringskvittot " +
      "saknar läsbart belopp.\n\n" +
      "Ingen av dem räknas in i summorna förrän du godkänt dem — det är så " +
      "dubbletter aldrig blir dubbla kostnader."
  },
  {
    fraga: "Hur mycket ingående moms finns i kvittona?",
    svar:
      "1 194,60 kr, ur de 8 kvitton som lästes av komplett. Momsen räknas ur " +
      "varje kvittos totalbelopp och sats — den största posten är borrmaskinen " +
      "från Verktygsboden med 468,00 kr.\n\n" +
      "Exakt vad som får dras av i deklarationen stämmer du av med en " +
      "redovisningskonsult."
  },
  {
    fraga: "Ska jag dra av lunchen på Bistro Linnea?",
    svar:
      "Det svarar jag inte på. Om en viss kostnad är avdragsgill i just din " +
      "verksamhet är en bedömning som binder dig mot Skatteverket, och den ska " +
      "en auktoriserad redovisningskonsult göra.\n\n" +
      "Jag kan däremot visa att kvittot är på 486,00 kr och ligger i kategorin " +
      "representation, så att underlaget är klart när du ställer frågan till " +
      "rätt person."
  }
];
