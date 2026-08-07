/**
 * En kund = en configfil. Ingen kopierad kodbas, inga parallella repon.
 *
 * Snajp bygger INTE om kundens hemsida. Kunden behåller sin egen sajt; det vi
 * levererar är supportchatten, dit besökaren kommer via en länk därifrån.
 * Configen innehåller därför bara det chatten behöver: logotyp, färgtokens,
 * kontaktuppgifter i sidfoten och agentens startfrågor.
 *
 * Juridisk text (villkor, garanti, ångerrätt) hör hemma på kundens egen sajt och
 * i agentens kunskapsbas — aldrig som sidor här. Två kopior av samma villkor
 * hamnar förr eller senare ur synk, och då är vår kopia felaktig.
 */

export type TenantPalette = {
  /** OKLCH utan färgfunktion, t.ex. "0.20 0.018 252" — samma format som globals.css. */
  ink: string;
  ink2: string;
  paper: string;
  paper2: string;
  mineral: string;
  seal: string;
  /** Den enda accenten. DESIGN.md tillåter inte en andra. */
  ochre: string;
  moss: string;
  danger: string;
};

export type TenantLogo = {
  /** Sökväg under /public, t.ex. /tenants/livrustning/logo.png */
  src: string;
  width: number;
  height: number;
  alt: string;
  /**
   * Vilken bakgrund logotypen är gjord för.
   *
   * Detta är inte en smakfråga. Livrustnings logotyp är vit text på
   * transparent — mot vårt varma papper syns bara den röda figuren och
   * företagsnamnet försvinner. `dark` lägger logotypen på ett mörkt fält, precis
   * som kundens egen sajt gör. Kontrollera alltid en ny kunds logotyp mot båda
   * bakgrunderna innan värdet sätts.
   */
  background: "light" | "dark";
};

export type TenantCompany = {
  legalName: string;
  orgNumber: string;
  addresses: string[];
  phones: string[];
  email: string;
  webshop?: string;
};

export type Tenant = {
  slug: string;
  name: string;
  /** Visas i <title>. */
  tagline: string;
  logo: TenantLogo;
  palette: TenantPalette;
  company: TenantCompany;
  /** Kundens egen hemsida — dit "tillbaka"-länken i chatten pekar. */
  website: string;
  /** Env-nyckel för supportbackendens API-nyckel, t.ex. SNAJP_KEY_LIVRUSTNING. */
  supportKeyEnv: string;
  /** Startfrågor i supportchatten. Måste handla om kundens egen verksamhet. */
  supportPrompts: string[];
  /** Hjälptexten över startfrågorna, i chattens tomma läge. */
  supportIntro: string;
};
