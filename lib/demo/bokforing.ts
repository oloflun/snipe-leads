/**
 * Exempeldatan för /demo/bokforing. Påhittad, och märkt som påhittad.
 *
 * ## Regeln som gäller här och som inte får brytas
 *
 * Samma som för leads-agentens exempelbolag och kundtjänstens exempelärenden:
 * ingen riktig kunddata, och ingen siffra som ser ut att komma från en verklig
 * körning. Drivmedelsfakturan nedan är hittepå, bolaget finns inte, och det
 * står på sidan.
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

/** Underlaget besökaren "laddar upp". */
export const EXEMPELKVITTO = {
  filnamn: "drivmedel-2026-08-14.pdf",
  motpart: "Nordvik Drivmedel AB",
  datum: "2026-08-14",
  /** Brutto. 1 250,00 kr inklusive 25 % moms. */
  brutto: "1250.00",
  momssats: "0.25",
  kategori: "drivmedel",
  riktning: "kostnad"
} as const;

/**
 * Avläsningen, fält för fält.
 *
 * `kalla` finns för att visa att varje fält STOD på underlaget. Ett fält utan
 * källa är ett gissat fält, och gissade fält går till granskning i produkten.
 */
export const AVLASNING: Avlast[] = [
  { falt: "Datum", varde: "2026-08-14", kalla: "Fakturadatum 2026-08-14" },
  { falt: "Motpart", varde: "Nordvik Drivmedel AB", kalla: "Nordvik Drivmedel AB, 556xxx-xxxx" },
  { falt: "Totalbelopp", varde: "1 250,00 kr", kalla: "Att betala 1 250,00" },
  { falt: "Momssats", varde: "25 %", kalla: "Moms 25 % 250,00" },
  { falt: "Kategori", varde: "Drivmedel", kalla: "Diesel, 62,3 l" }
];

/**
 * Verifikatet. Netto 1000,00 + moms 250,00 = brutto 1250,00.
 *
 * Kontona kommer ur BAS-delmängden i `bookkeeping/kontoplan.py`:
 * 5611 drivmedel, 2641 ingående moms, 2440 leverantörsskuld.
 *
 * Debet 1000,00 + 250,00 = 1250,00 = kredit 1250,00. Balanserar.
 */
export const VERIFIKAT: Verifikatrad[] = [
  { konto: "5611", kontonamn: "Drivmedel för personbilar", debet: "1000.00" },
  { konto: "2641", kontonamn: "Ingående moms", debet: "250.00" },
  { konto: "2440", kontonamn: "Leverantörsskulder", kredit: "1250.00" }
];

/**
 * Periodrapporten för augusti i exemplet.
 *
 * Handräknat facit, och det enda underlaget är kvittot ovan:
 *   kostnader        = netto            = 1000,00
 *   ingående moms    = moms             =  250,00
 *   intäkter         = inga underlag    =    0,00
 *   utgående moms    = inga underlag    =    0,00
 *   resultat         = 0 - 1000         = -1000,00
 *   moms att betala  = utg - ing        =  -250,00  (fordran på Skatteverket)
 */
export const PERIOD = {
  fran: "2026-08-01",
  till: "2026-08-31",
  status: "klar",
  summor: {
    intakter: "0.00",
    kostnader: "1000.00",
    utgaende_moms: "0.00",
    ingaende_moms: "250.00",
    resultat_fore_skatt: "-1000.00",
    moms_att_betala: "-250.00"
  },
  antal_underlag: 1,
  antal_verifikat: 1
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
 * Varje svar bär BARA belopp som står i PERIOD ovan. Det är inte en stilistisk
 * regel utan samma krav som INV-BOOK-003 ställer på det riktiga svaret: ett tal
 * som inte hämtats fälls innan kunden ser det.
 *
 * Skillnaden mot produkten är att grinden här är ett TEST i stället för en
 * körning — `tests/test_demo_bokforing.py` läser svaren och jämför varje
 * kronbelopp mot periodrapporten. Ett påhittat tal fäller bygget, inte
 * besökaren.
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
    fraga: "Hur mycket har jag i utgående moms hittills i augusti?",
    svar:
      "Ingen alls — utgående moms är 0,00 kr för 2026-08-01 till 2026-08-31. " +
      "Du har ingen registrerad försäljning i perioden, bara ett kostnadsunderlag.\n\n" +
      "Däremot har du 250,00 kr i INGÅENDE moms från drivmedelsfakturan, alltså " +
      "moms du får tillbaka. Kostnaden exklusive moms är 1 000,00 kr."
  },
  {
    fraga: "Vad är skillnaden på ingående och utgående moms?",
    svar:
      "Utgående moms är den du lägger på när du SÄLJER — den är en skuld till " +
      "Skatteverket. Ingående moms är den du betalar när du KÖPER, och den får " +
      "du dra av.\n\n" +
      "På deklarationen kvittas de mot varandra. Är den ingående större får du " +
      "tillbaka mellanskillnaden, vilket är läget i din period just nu.\n\n" +
      "Hur just din deklaration ska fyllas i bör du stämma av med en " +
      "redovisningskonsult — jag förklarar begreppen, jag ger inte skatteråd."
  },
  {
    fraga: "Vilket konto hamnar drivmedlet på?",
    svar:
      "5611, Drivmedel för personbilar. Momsen bokas separat på 2641, ingående " +
      "moms, och skulden till leverantören på 2440.\n\n" +
      "Jag valde kategorin utifrån vad som stod på underlaget. Kontot valde " +
      "koden ur BAS-kontoplanen, vilket är varför verifikatet balanserar av " +
      "konstruktion."
  },
  {
    fraga: "Går perioden ihop?",
    svar:
      "Ja. Ett underlag, ett verifikat, och debet är lika med kredit. " +
      "Resultatet före skatt är -1 000,00 kr, och du har 250,00 kr att få " +
      "tillbaka i moms.\n\n" +
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
