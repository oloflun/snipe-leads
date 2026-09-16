/**
 * Exempeldatan för /demo/bokforing. Påhittad, och märkt som påhittad.
 *
 * ## Regeln som gäller här och som inte får brytas
 *
 * Samma som för leads-agentens exempelbolag och kundtjänstens exempelärenden:
 * ingen riktig kunddata, och ingen siffra som ser ut att komma från en verklig
 * körning. Underlagen nedan är hittepå, bolagen finns inte, och det står på
 * sidan.
 *
 * ## Varför siffrorna är HANDRÄKNADE och står utskrivna
 *
 * Demon kör ingen LLM och anropar ingen backend. Den kunde ha räknat med
 * `math.ts` i webbläsaren, men det hade varit en andra uträkning vid sidan av
 * `bookkeeping/math.py` — och den enda som märker när de glider isär är en
 * besökare som räknar efter.
 *
 * I stället är talen skrivna som konstanter med facit i kommentaren, och
 * `tests/test_demo_bokforing.py` räknar om dem. Går de isär fälls testet, inte
 * besökaren.
 *
 * ## Varför det är TRE underlag sedan 2026-09-15
 *
 * Ett enda kostnadskvitto visade bara halva produkten: perioden hade varken
 * intäkter eller utgående moms, och besökaren kunde inte VÄLJA något — demon
 * lästes, den provades inte. Nu väljer besökaren underlag (en obetald
 * leverantörsfaktura, en skickad kundfaktura, ett kortbetalt kvitto) och ser
 * varje väg genom avläsning och verifikat. Perioden summerar alla tre.
 *
 * Tre vägar är valda för att de konterar OLIKA: skuld (2440), fordran (1510)
 * och direktbetalning (1930). En fjärde variant hade visat samma sak igen.
 *
 * ## Varför chatten svarar utan att köra en modell
 *
 * Besökaren väljer fråga och får svar — samtalet drivs alltså av den som läser.
 * Men inget LLM-anrop görs: sidan är publik och anonym, och en körning per
 * besökare kostar pengar och kan svara olika varje gång. Samma avvägning som
 * gjorde Email Studios demoläge `simulated: true`.
 *
 * Svaren är grundade i exakt de siffror som står ovanför dem, vilket är precis
 * vad INV-BOOK-003 kräver av det riktiga svaret. Skillnaden är att grinden här
 * är ett TEST och inte en körning — se FRAGOR längre ned.
 */

export type Avlast = { falt: string; varde: string; kalla: string };
export type Verifikatrad = { konto: string; kontonamn: string; debet?: string; kredit?: string };

export type Demounderlag = {
  /** Nyckeln besökaren väljer på. */
  id: string;
  /** Knappetiketten i väljaren. */
  etikett: string;
  filnamn: string;
  motpart: string;
  datum: string;
  /** Brutto, maskinläsbart — testet räknar netto och moms ur det. */
  brutto: string;
  momssats: string;
  kategori: string;
  riktning: "kostnad" | "intakt";
  /** En rad som förklarar vad som är särskilt med just den här vägen. */
  poang: string;
  avlasning: Avlast[];
  verifikat: Verifikatrad[];
};

/**
 * Underlagen besökaren kan "ladda upp".
 *
 * Kontona kommer ur BAS-delmängden i `bookkeeping/kontoplan.py`:
 * 5611 drivmedel, 6110 kontorsmateriel, 3001 försäljning 25 %,
 * 2641 ingående moms, 2611 utgående moms, 2440 leverantörsskulder,
 * 1510 kundfordringar, 1930 företagskonto.
 */
export const UNDERLAG: Demounderlag[] = [
  {
    id: "drivmedel",
    etikett: "Leverantörsfaktura, obetald",
    filnamn: "drivmedel-2026-08-14.pdf",
    motpart: "Nordvik Drivmedel AB",
    datum: "2026-08-14",
    /** Brutto. 1 250,00 kr inklusive 25 % moms: netto 1000,00 + moms 250,00. */
    brutto: "1250.00",
    momssats: "0.25",
    kategori: "drivmedel",
    riktning: "kostnad",
    poang:
      "Obetald faktura: skulden bokas på 2440 tills betalningen syns, inte mot kontot.",
    avlasning: [
      { falt: "Datum", varde: "2026-08-14", kalla: "Fakturadatum 2026-08-14" },
      { falt: "Motpart", varde: "Nordvik Drivmedel AB", kalla: "Nordvik Drivmedel AB, 556xxx-xxxx" },
      { falt: "Totalbelopp", varde: "1 250,00 kr", kalla: "Att betala 1 250,00" },
      { falt: "Momssats", varde: "25 %", kalla: "Moms 25 % 250,00" },
      { falt: "Kategori", varde: "Drivmedel", kalla: "Diesel, 62,3 l" },
      // Sjunde fältet (migration 062). Det står här för att det är fältet som
      // FÖRKLARAR kreditraden: 2440 och inte 1930. Utan raden ser besökaren
      // en leverantörsskuld dyka upp ur ingenstans, och demon visade en
      // kontering produkten inte kunde motivera.
      { falt: "Betalstatus", varde: "Obetald", kalla: "Förfallodatum 2026-09-13" }
    ],
    /** Debet 1000,00 + 250,00 = kredit 1250,00. Balanserar. */
    verifikat: [
      { konto: "5611", kontonamn: "Drivmedel för personbilar", debet: "1000.00" },
      { konto: "2641", kontonamn: "Ingående moms", debet: "250.00" },
      { konto: "2440", kontonamn: "Leverantörsskulder", kredit: "1250.00" }
    ]
  },
  {
    id: "kundfaktura",
    etikett: "Kundfaktura, skickad",
    filnamn: "faktura-1042-almgrens.pdf",
    motpart: "Almgrens Måleri AB",
    datum: "2026-08-19",
    /** Brutto. 18 750,00 kr inklusive 25 % moms: netto 15 000,00 + moms 3 750,00. */
    brutto: "18750.00",
    momssats: "0.25",
    kategori: "forsaljning",
    riktning: "intakt",
    poang:
      "En intäkt vänder allt: fordran på 1510, försäljningen på 3001 och momsen blir utgående.",
    avlasning: [
      { falt: "Datum", varde: "2026-08-19", kalla: "Fakturadatum 2026-08-19" },
      { falt: "Motpart", varde: "Almgrens Måleri AB", kalla: "Almgrens Måleri AB, 559xxx-xxxx" },
      { falt: "Totalbelopp", varde: "18 750,00 kr", kalla: "Att betala 18 750,00" },
      { falt: "Momssats", varde: "25 %", kalla: "Varav moms 25 % 3 750,00" },
      { falt: "Kategori", varde: "Försäljning", kalla: "Konsultarbete vecka 32-33" },
      { falt: "Betalstatus", varde: "Obetald", kalla: "Förfallodatum 2026-09-18" }
    ],
    /** Debet 18750,00 = kredit 15000,00 + 3750,00. Balanserar. */
    verifikat: [
      { konto: "1510", kontonamn: "Kundfordringar", debet: "18750.00" },
      { konto: "3001", kontonamn: "Försäljning inom Sverige, 25 % moms", kredit: "15000.00" },
      { konto: "2611", kontonamn: "Utgående moms på försäljning inom Sverige, 25 %", kredit: "3750.00" }
    ]
  },
  {
    id: "kontorsmateriel",
    etikett: "Kvitto, betalt med kort",
    filnamn: "kvitto-kontorsmateriel-2026-08-27.pdf",
    motpart: "Skrivbo Kontorsvaror AB",
    datum: "2026-08-27",
    /** Brutto. 495,00 kr inklusive 25 % moms: netto 396,00 + moms 99,00. */
    brutto: "495.00",
    momssats: "0.25",
    kategori: "kontorsmateriel",
    riktning: "kostnad",
    poang:
      "Redan betalt: ingen skuld uppstår, kreditsidan är företagskontot 1930 direkt.",
    avlasning: [
      { falt: "Datum", varde: "2026-08-27", kalla: "Kvittodatum 2026-08-27 14:32" },
      { falt: "Motpart", varde: "Skrivbo Kontorsvaror AB", kalla: "Skrivbo Kontorsvaror AB, 556xxx-xxxx" },
      { falt: "Totalbelopp", varde: "495,00 kr", kalla: "Totalt 495,00" },
      { falt: "Momssats", varde: "25 %", kalla: "Moms 25 % 99,00" },
      { falt: "Kategori", varde: "Kontorsmateriel", kalla: "Pärmar, papper, tonerkassett" },
      { falt: "Betalstatus", varde: "Betald", kalla: "Kort ****1274, godkänt" }
    ],
    /** Debet 396,00 + 99,00 = kredit 495,00. Balanserar. */
    verifikat: [
      { konto: "6110", kontonamn: "Kontorsmateriel", debet: "396.00" },
      { konto: "2641", kontonamn: "Ingående moms", debet: "99.00" },
      { konto: "1930", kontonamn: "Företagskonto / checkräkningskonto", kredit: "495.00" }
    ]
  }
];

/**
 * Periodrapporten för augusti i exemplet — summan av de TRE underlagen ovan.
 *
 * Handräknat facit:
 *   intäkter         = 15000,00                      = 15000,00
 *   kostnader        = 1000,00 + 396,00              =  1396,00
 *   utgående moms    = 3750,00                       =  3750,00
 *   ingående moms    = 250,00 + 99,00                =   349,00
 *   resultat         = 15000,00 - 1396,00            = 13604,00
 *   moms att betala  = 3750,00 - 349,00              =  3401,00
 */
export const PERIOD = {
  fran: "2026-08-01",
  till: "2026-08-31",
  status: "klar",
  summor: {
    intakter: "15000.00",
    kostnader: "1396.00",
    utgaende_moms: "3750.00",
    ingaende_moms: "349.00",
    resultat_fore_skatt: "13604.00",
    moms_att_betala: "3401.00"
  },
  antal_underlag: 3,
  antal_verifikat: 3
} as const;

/**
 * Frågorna besökaren kan ställa, och svaren.
 *
 * ## Varför de är KONSTANTER och ändå ett riktigt samtal
 *
 * Besökaren väljer fråga och svaret kommer fram — samtalet drivs alltså av den
 * som läser, inte av en inspelning som rullar. Men ingen modell körs, av skälet
 * som står i filens docstring.
 *
 * ## Varför det inte är fusk
 *
 * Varje svar bär BARA belopp som står i PERIOD eller i ett verifikat ovan —
 * alltså siffror som redan står på sidan. Det är inte en stilistisk regel utan
 * samma krav som INV-BOOK-003 ställer på det riktiga svaret: ett tal som inte
 * hämtats fälls innan kunden ser det.
 *
 * Skillnaden mot produkten är att grinden här är ett TEST i stället för en
 * körning — `tests/test_demo_bokforing.py` läser svaren och jämför varje
 * kronbelopp mot rapporten och verifikaten. Ett påhittat tal fäller bygget,
 * inte besökaren.
 *
 * ## Varför den sista frågan finns
 *
 * "Ska jag dra av den här middagen?" ligger på fel sida gränsen, och svaret
 * visar var gränsen går. Att bara demonstrera det agenten KAN hade gett en demo
 * som lovar mer än produkten håller.
 */
export type Demofraga = { fraga: string; svar: string };

export const FRAGOR: Demofraga[] = [
  {
    fraga: "Hur mycket moms ska jag betala för augusti?",
    svar:
      "3 401,00 kr, preliminärt. Utgående moms på din försäljning är " +
      "3 750,00 kr, och du får dra av 349,00 kr i ingående moms från dina två " +
      "inköp.\n\n" +
      "Skillnaden, 3 401,00 kr, är det som ska redovisas till Skatteverket för " +
      "perioden. Exakt hur deklarationen fylls i stämmer du av med en " +
      "redovisningskonsult."
  },
  {
    fraga: "Vad är skillnaden på ingående och utgående moms?",
    svar:
      "Utgående moms är den du lägger på när du SÄLJER — den är en skuld till " +
      "Skatteverket. I din period är den 3 750,00 kr, från kundfakturan. " +
      "Ingående moms är den du betalar när du KÖPER, och den får du dra av — " +
      "hos dig 349,00 kr.\n\n" +
      "På deklarationen kvittas de mot varandra, och mellanskillnaden är det " +
      "du betalar eller får tillbaka.\n\n" +
      "Hur just din deklaration ska fyllas i bör du stämma av med en " +
      "redovisningskonsult — jag förklarar begreppen, jag ger inte skatteråd."
  },
  {
    fraga: "Varför hamnade drivmedlet på 2440 och kvittot på 1930?",
    svar:
      "Betalstatusen avgör. Drivmedelsfakturan är obetald, så motkontot är " +
      "2440, leverantörsskulder — skulden finns kvar tills betalningen syns. " +
      "Kontorskvittot är redan betalt med kort, så där krediteras " +
      "företagskontot 1930 direkt.\n\n" +
      "Kostnaden bokas på sitt eget konto i båda fallen: 5611 för drivmedlet " +
      "och 6110 för kontorsmaterielen. Kontona kommer ur BAS-kontoplanen, " +
      "vilket är varför verifikaten balanserar av konstruktion."
  },
  {
    fraga: "Går perioden ihop?",
    svar:
      "Ja. Tre underlag, tre verifikat, och debet är lika med kredit i varje. " +
      "Resultatet före skatt är 13 604,00 kr: intäkter på 15 000,00 kr minus " +
      "kostnader på 1 396,00 kr.\n\n" +
      "Hade den inte gått ihop hade jag visat bristerna i stället för summorna. " +
      "Trovärdiga tal för en period som inte stämmer är värre än inga tal alls."
  },
  {
    fraga: "Ska jag dra av den här middagen?",
    svar:
      "Det svarar jag inte på. Om en viss kostnad är avdragsgill i just din " +
      "verksamhet är en bedömning som binder dig mot Skatteverket, och den ska " +
      "en auktoriserad redovisningskonsult göra.\n\n" +
      "Jag kan däremot förklara vad representation är för något, och visa vilket " +
      "konto en representationskostnad brukar hamna på."
  }
];
