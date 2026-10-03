/**
 * Textkvalitet — TS-spegel av den deterministiska putsningen i
 * snajp-support/app/textkvalitet.py. Används av Email Studio-routen så att
 * samma riskfria rättningar görs oavsett vilken sida av stacken som
 * producerade texten: blankstegsstädning, mellanslag före skiljetecken,
 * hängande hälsningar och en kurerad lista entydiga felstavningar.
 *
 * Ändrar ALDRIG fakta: länkar, e-postadresser och organisationsnummer
 * maskeras undan innan rättningarna och sätts tillbaka ordagrant.
 * Håll FELSTAVNINGAR i synk med Python-modulen — testet
 * scripts/granska_ui_texter.py använder samma lista.
 */

export const FELSTAVNINGAR: Record<string, string> = {
  abbonemang: "abonnemang",
  abonemang: "abonnemang",
  aggresiv: "aggressiv",
  aggresivt: "aggressivt",
  annulera: "annullera",
  defenitivt: "definitivt",
  definitift: "definitivt",
  egentligtvis: "egentligen",
  epost: "e-post",
  epostadress: "e-postadress",
  "följdaktligen": "följaktligen",
  "förmodeligen": "förmodligen",
  iallafall: "i alla fall",
  intresant: "intressant",
  intresanta: "intressanta",
  intressangt: "intressant",
  medans: "medan",
  nogrann: "noggrann",
  nogrant: "noggrant",
  orginal: "original",
  orginell: "originell",
  paralell: "parallell",
  paralellt: "parallellt",
  proffesionell: "professionell",
  proffesionellt: "professionellt",
  professionel: "professionell",
  rekomendera: "rekommendera",
  rekomenderar: "rekommenderar",
  rekomendation: "rekommendation",
  resturang: "restaurang",
  sammarbete: "samarbete",
  sammarbeta: "samarbeta",
  sucessivt: "successivt",
  tillsammas: "tillsammans",
  ursprunligen: "ursprungligen",
  "överaskande": "överraskande",
  "överaskning": "överraskning",
};

const SKYDDAT = /(https?:\/\/\S+|www\.\S+|[\w.+-]+@[\w-]+\.[\w.-]+|\b\d{6}-\d{4}\b)/g;

/** Deterministisk, riskfri putsning av en kundsynlig text. */
export function putsaText(text: string): string {
  if (!text) return text;

  const skyddade: string[] = [];
  let t = text.replace(SKYDDAT, (m) => {
    skyddade.push(m);
    return `\u0000${skyddade.length - 1}\u0000`;
  });

  t = t.replace(/ /g, " ");
  t = t.replace(/[ \t]+([,.!?;:])/g, "$1");
  t = t.replace(/[ \t]{2,}/g, " ");
  t = t.replace(/\n{3,}/g, "\n\n");

  const monster = new RegExp(
    `\\b(${Object.keys(FELSTAVNINGAR).join("|")})\\b`,
    "gi"
  );
  t = t.replace(monster, (ord) => {
    const ratt = FELSTAVNINGAR[ord.toLowerCase()];
    if (!ratt) return ord;
    return ord[0] === ord[0].toUpperCase()
      ? ratt[0].toUpperCase() + ratt.slice(1)
      : ratt;
  });

  skyddade.forEach((segment, i) => {
    t = t.replace(`\u0000${i}\u0000`, segment);
  });

  return t
    .split("\n")
    .map((rad) => rad.replace(/[ \t]+$/, ""))
    .join("\n")
    .trim();
}
