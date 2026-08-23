/**
 * Kortformer och testkort — utan "use server", så både växeln och formuläret
 * kan läsa dem.
 *
 * ## Den bärande regeln: BARA testkort accepteras
 *
 * Formuläret tar emot Stripes officiella testnummer och ingenting annat. Det
 * är inte en begränsning som ska lyftas när produkten blir skarp — det är
 * skyddet som gör att den här ytan får existera innan en betalväxel är
 * inkopplad.
 *
 * Skälet: ett kortformulär som tar emot vilket nummer som helst LÄR kunden att
 * skriva sitt riktiga kort här. Gör de det ligger ett PAN i en request mot en
 * server som varken är PCI-granskad eller byggd för att hantera det, och den
 * skadan går inte att ta tillbaka genom att lägga till en varningstext efteråt.
 * Ett fält som bara kan svälja `4242…` kan inte svälja ett riktigt kort.
 *
 * ## Vad som lagras
 *
 * Märke, fyra sista och giltighetstid. Aldrig hela numret, aldrig CVC. Det är
 * exakt vad en riktig växel lämnar tillbaka efter tokenisering, så formen
 * behöver inte ändras den dagen växeln kopplas in — bara källan till värdena.
 */

export type Kortmarke = "Visa" | "Mastercard" | "American Express";

export type Betalsatt = {
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  /** Sant så länge ingen skarp betalväxel är inkopplad. */
  is_test: boolean;
  provider: string;
};

/**
 * Stripes publicerade testnummer. De är avsiktligt kända och kan inte debiteras
 * någon — det är därför de är säkra att skriva i klartext här.
 *
 * Listan är den enda ingången: matchar inte numret exakt avvisas det.
 */
export const TESTKORT: { nummer: string; marke: Kortmarke; not: string }[] = [
  { nummer: "4242424242424242", marke: "Visa", not: "Godkänns alltid" },
  { nummer: "5555555555554444", marke: "Mastercard", not: "Godkänns alltid" },
  { nummer: "378282246310005", marke: "American Express", not: "Godkänns alltid" },
  {
    nummer: "4000000000000002",
    marke: "Visa",
    not: "Nekas av banken — för att se felvägen"
  }
];

/** Kortet som ska NEKAS. Finns för att felvägen ska gå att prova, inte bara lyckas. */
export const NEKAT_TESTKORT = "4000000000000002";

export function bararSiffror(text: string): string {
  return text.replace(/\D/g, "");
}

/** Grupperar i fyror för läsbarhet. Amex grupperas 4-6-5, som på kortet. */
export function formateraKortnummer(text: string): string {
  const siffror = bararSiffror(text).slice(0, 16);
  if (/^3[47]/.test(siffror)) {
    return [siffror.slice(0, 4), siffror.slice(4, 10), siffror.slice(10, 15)]
      .filter(Boolean)
      .join(" ");
  }
  return siffror.replace(/(.{4})/g, "$1 ").trim();
}

export function testkortFor(nummer: string): (typeof TESTKORT)[number] | null {
  const siffror = bararSiffror(nummer);
  return TESTKORT.find((k) => k.nummer === siffror) ?? null;
}

export type Kortfel = string | null;

/**
 * Validerar kortet. Returnerar felmeddelandet, eller null när allt stämmer.
 *
 * Ordningen är medveten: numret kontrolleras FÖRST och mot testlistan, så att
 * den som klistrar in ett riktigt kort får veta det innan formuläret börjar
 * fråga om giltighetstid — och innan något skickas någonstans.
 */
export function kortfel(
  nummer: string,
  manad: string,
  ar: string,
  cvc: string
): Kortfel {
  const siffror = bararSiffror(nummer);
  if (!siffror) return "Fyll i kortnumret.";
  if (!testkortFor(siffror)) {
    return "Bara testkort går att spara här. Använd ett av numren i listan nedan — riktiga kort tas inte emot, och ska inte skrivas in.";
  }

  const m = Number(manad);
  if (!Number.isInteger(m) || m < 1 || m > 12) return "Månaden ska vara 01–12.";

  const a = Number(ar.length === 2 ? `20${ar}` : ar);
  if (!Number.isInteger(a) || a < 2020 || a > 2100) return "Fyll i giltighetsåret, till exempel 2030.";

  const nu = new Date();
  if (a < nu.getFullYear() || (a === nu.getFullYear() && m < nu.getMonth() + 1)) {
    return "Kortet har gått ut.";
  }

  // CVC krävs men SPARAS ALDRIG. Den finns i formuläret för att flödet ska
  // likna det riktiga; värdet lämnar aldrig webbläsaren (se BetalsattForm).
  const c = bararSiffror(cvc);
  if (c.length < 3 || c.length > 4) return "CVC är tre siffror, fyra på Amex.";

  return null;
}

/** Vad som får skickas till servern: aldrig hela numret. */
export type Kortuppgifter = {
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  /** Testkortet som nekas i banksteget, så felvägen går att prova. */
  simuleraNekat: boolean;
};

export function tillKortuppgifter(
  nummer: string,
  manad: string,
  ar: string
): Kortuppgifter | null {
  const kort = testkortFor(nummer);
  if (!kort) return null;
  return {
    brand: kort.marke,
    last4: kort.nummer.slice(-4),
    exp_month: Number(manad),
    exp_year: Number(ar.length === 2 ? `20${ar}` : ar),
    simuleraNekat: kort.nummer === NEKAT_TESTKORT
  };
}
