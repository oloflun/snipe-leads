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
  /**
   * Nyckeln bor PER ARBETSYTA i databasen, inte i en miljövariabel.
   *
   * Gäller tenants som skapas i drift och därför inte har någon configfil —
   * testarbetsytorna är det första fallet (migration 040). För dem är
   * `supportKeyEnv` fel väg: den pekar på en DELAD nyckel, alltså en delad
   * kunskapsbas, vilket är exakt det egna tenants finns för att undvika.
   */
  perWorkspaceKey?: boolean;
  /**
   * Chattwidgetens PUBLIKA nyckel — det enda som står i kundens snippet.
   *
   * Publik per definition (den ligger i kundens HTML), så den ger ingen
   * åtkomst: den löser bara upp vilken tenants PUBLIKA chatt som visas,
   * precis som sluggen i /chat/<slug>. Slumpad ändå, så att /embed inte blir
   * en katalog man kan räkna upp med gissade slugs. Saknas fältet har kunden
   * ingen widget — /embed svarar 404.
   */
  publicKey?: string;
  /**
   * Domäner som får bädda in widgeten (CSP frame-ancestors, sätts i
   * proxy.ts). Skyddet om nyckeln sprids: webbläsaren vägrar rendera
   * iframen på en domän som inte står här. 'self' läggs alltid till, så
   * vår egen testsida fungerar. Fullständiga origins med schema.
   */
  embedOrigins?: string[];
  /**
   * Widgetens egen inbjudan: pratbubblan som dyker upp bredvid knappen och
   * FRÅGAR om den får hjälpa till, i stället för att vänta på ett klick.
   *
   * Mönstret är Skatteverkets ("Frågor?" / "Chatta med mig!"), som är den
   * chattbot flest svenskar har sett — en rad i fetstil och en inbjudan under.
   * Utseendet är däremot vårt: deras tecknade figur hör till deras varumärke,
   * och chatten bär Snajps formspråk med kundens logotyp (se livrustning.ts).
   *
   * Texten bor HÄR och inte i public/widget.js därför att skriptet är
   * gemensamt för alla kunder: en hårdkodad mening där hade blivit fel för
   * varannan kund. Saknas fältet visas ingen bubbla alls — knappen ensam är
   * ett fullgott läge, och en kund som inte vill bli påkallad ska slippa.
   */
  widgetInbjudan?: { rubrik: string; text: string };
};
