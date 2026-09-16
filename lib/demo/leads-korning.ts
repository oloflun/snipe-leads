/**
 * Exempelkörningen för /demo/leads. Påhittad, och märkt som påhittad.
 *
 * ## Varför demon numera KAN "köra"
 *
 * Formuläret sa tidigare bara "logga in för att köra" — reglagen visades men
 * ingenting hände, och demons löfte är att man ska få PROVA. Sedan 2026-09-15
 * kan besökaren trigga en färdiggenererad exempelkörning: stegen spelas upp,
 * resultatet fälls ut och utkasten går att redigera.
 *
 * Regeln från LeadsRunForm gäller fortfarande och är löst med märkning, inte
 * bruten: ett fejkat resultat som SER körningsäkta ut vore värst av allt, så
 * varje yta som visar körningen säger att den är skriven i förväg och att
 * ingen modell körs. Samma mönster som bokföringsdemons förskrivna svar och
 * kundtjänstdemons exempelärenden.
 *
 * Bolagen är hittepå. Ingen av dem finns i registret, och adresserna är
 * exempel-domäner som inte går att mejla.
 */

export type Korsteg = {
  text: string;
  /** Hur länge steget "arbetar" innan nästa visas, i millisekunder. */
  varaktighet: number;
};

export type Exempelresultat = {
  bolag: string;
  ort: string;
  signal: string;
  kontakt: string;
  epost: string;
  /** Varför bolaget kvalificerade sig — behovsanalysen i en mening. */
  behov: string;
  amne: string;
  utkast: string;
};

/** Stegen, i den ordning den riktiga körningen loggar dem. */
export const KORSTEG: Korsteg[] = [
  { text: "Letar bolag som matchar målgruppen", varaktighet: 1400 },
  { text: "Läser signaler: nyheter, platsannonser, tillväxt", varaktighet: 1600 },
  { text: "Gör behovsanalys per bolag", varaktighet: 1500 },
  { text: "Skriver personliga utkast", varaktighet: 1300 }
];

export const EXEMPELRESULTAT: Exempelresultat[] = [
  {
    bolag: "Bergsala Verkstad AB",
    ort: "Örebro",
    signal: "Söker två CNC-operatörer och en produktionstekniker",
    kontakt: "Marie Lundvall",
    epost: "marie.lundvall@exempel.se",
    behov:
      "Växande produktion med nyanställningar brukar betyda att kringutrustning och underhåll släpar efter.",
    amne: "Inför utökningen i Örebro",
    utkast:
      "Hej Marie,\n\n" +
      "Jag såg att Bergsala Verkstad tar in både CNC-operatörer och en produktionstekniker. " +
      "När produktionen växer så snabbt brukar underhållssidan vara det som får vänta.\n\n" +
      "Vi hjälper verkstäder i er storlek att hålla maskinparken igång under expansionen, " +
      "utan att binda upp egen personal.\n\n" +
      "Skulle det vara värt ett kort samtal nästa vecka?\n\nVänliga hälsningar"
  },
  {
    bolag: "Norrsken Logistik AB",
    ort: "Sundsvall",
    signal: "Flyttar till ny terminal vid E4 i oktober",
    kontakt: "Peder Sandin",
    epost: "peder.sandin@exempel.se",
    behov:
      "En terminalflytt är ett naturligt tillfälle att se över utrustning och avtal innan allt skruvas fast igen.",
    amne: "Innan flytten till nya terminalen",
    utkast:
      "Hej Peder,\n\n" +
      "Grattis till nya terminalen vid E4:an. En flytt är ofta det bästa tillfället att se över " +
      "det som annars aldrig hinns med, innan allt är fastskruvat och igång.\n\n" +
      "Vi arbetar med logistikbolag i Norrland och kan ta fram ett förslag anpassat efter er nya yta.\n\n" +
      "Har ni tio minuter vecka 41?\n\nVänliga hälsningar"
  },
  {
    bolag: "Lindqvist & Söner Bygg AB",
    ort: "Växjö",
    signal: "Vann ramavtal med kommunen i september",
    kontakt: "Åsa Lindqvist",
    epost: "asa.lindqvist@exempel.se",
    behov:
      "Ett ramavtal ger jämnare beläggning men också hårdare krav på dokumentation och leveranstider.",
    amne: "Ramavtalet med kommunen",
    utkast:
      "Hej Åsa,\n\n" +
      "Såg att ni vann ramavtalet med kommunen, roligt! Med ett ramavtal följer ofta " +
      "hårdare krav på dokumentation och ledtider än i vanliga projekt.\n\n" +
      "Vi stöttar byggbolag i Småland med precis den biten, så att era arbetsledare " +
      "slipper administrationen.\n\n" +
      "Får jag skicka över ett kort förslag?\n\nVänliga hälsningar"
  }
];
