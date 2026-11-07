/**
 * Allt här är påhittat. Bolagen följer demons mönster (uppdiktade ortsled +
 * bransch, domäner under .example som aldrig kan registreras), personerna
 * är bara förnamn och svaren är skrivna för filmen. Inga riktiga bolag,
 * inga riktiga personer.
 */

const STAMMAR = [
  "Lundsund", "Viksund", "Hammarnäs", "Ekvalla", "Tallheden", "Granåsa", "Sjöbrinka",
  "Almtorpa", "Björkmyra", "Stenvika", "Mossbacka", "Kvarnlida", "Rönnhaga", "Lindhult",
  "Hagsätra", "Fjällmo", "Ängsvik", "Dalbo", "Norrhede", "Sandlund", "Vesslinge",
  "Högtorp", "Klövhammar", "Bergsjö", "Tunaberga"
];

const LED = [
  "Bygg & Partner AB", "Byggrupp AB", "Entreprenad AB", "Snickeri AB", "Tak & Fasad AB",
  "Måleri AB", "El & Bygg AB", "Markarbeten AB", "Byggservice AB", "Plåt AB"
];

const ORTER = ["Göteborg", "Mölndal", "Partille", "Kungsbacka", "Lerum", "Kungälv", "Härryda"];

export type Lead = { bolag: string; ort: string; niva: "A" | "B"; kontakt: string };

const NAMN = ["Karin", "Mikael", "Sara", "Johan", "Anna", "Erik", "Lena", "Daniel", "Maria", "Peter", "Eva", "Anders"];

export const LEADS: Lead[] = Array.from({ length: 50 }, (_, i) => ({
  bolag: `${STAMMAR[i % STAMMAR.length]} ${LED[(i * 7) % LED.length]}`,
  ort: ORTER[(i * 3) % ORTER.length],
  niva: i % 3 === 2 ? "B" : "A",
  kontakt: NAMN[i % NAMN.length]
}));

export const UTKAST = {
  bolag: "Lundsund Bygg & Partner AB",
  till: "karin@lundsundbygg.example",
  amne: "Nya lokalen i Mölndal",
  delar: [
    { text: "Hej Karin,\n\n" },
    { text: "Såg att ni precis flyttat in i nya lokaler i Mölndal.", markera: true },
    {
      text:
        " Grattis!\n\nVi hjälper byggföretag i Göteborg att få in fler förfrågningar, utan att kvällarna går åt till offerter.\n\nHar du tio minuter i veckan?"
    }
  ]
};

export type Svar = { namn: string; bolag: string; text: string; ton: "ochre" | "moss" | "bla" };

const SVARSTEXTER = [
  "Låter intressant. Har du tid på torsdag?",
  "Skicka gärna mer info, vi tittar på det i veckan.",
  "Vi har faktiskt precis pratat om det här. Ring mig.",
  "Ja tack, boka in ett möte.",
  "Kan ni visa en demo nästa vecka?",
  "Bra timing. Vad kostar det?",
  "Vidarebefordrar till min kollega, hon ringer dig.",
  "Intressant! Fredag förmiddag passar.",
  "Vi behöver precis det här inför våren.",
  "Hör av dig på måndag så pratar vi."
];

export const SVAR: Svar[] = Array.from({ length: 30 }, (_, i) => {
  const lead = LEADS[(i * 11) % LEADS.length];
  return {
    namn: lead.kontakt,
    bolag: lead.bolag,
    text: SVARSTEXTER[i % SVARSTEXTER.length],
    ton: (["ochre", "moss", "bla"] as const)[i % 3]
  };
});

export const FRISKRIVNING = "Illustration med påhittade exempel";
