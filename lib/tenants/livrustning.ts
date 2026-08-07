import type { Tenant } from "./types";

/**
 * Livrustning AB — utbildning i HLR, första hjälpen, brand och krisstöd.
 *
 * Kunden behåller livrustning.se. Vi levererar supportchatten, dit deras
 * besökare kommer via en länk från den sajten eller i ett mejl.
 *
 * Paletten matchar inte deras grafiska profil och ska inte göra det — chatten
 * bär Snajps formspråk med kundens logotyp. Accenten är petrol snarare än rött
 * eller grönt eftersom de färgerna är upptagna av --danger och --moss, och för
 * ett bolag som utbildar i livräddning får accenten inte kunna förväxlas med
 * ett larm eller en bekräftelse.
 */
export const livrustning: Tenant = {
  slug: "livrustning",
  name: "Livrustning AB",
  tagline: "Utbildning i hjärt-lungräddning, första hjälpen, brand och krisstöd",
  website: "https://livrustning.se",
  supportKeyEnv: "SNAJP_KEY_LIVRUSTNING",

  logo: {
    src: "/tenants/livrustning/logo.png",
    width: 264,
    height: 70,
    alt: "Livrustning — kunskap för säkerhets skull",
    // Vit ordbild på transparent. Mot papper syns bara den röda figuren och
    // företagsnamnet försvinner — därför mörkt fält, som på kundens egen sajt.
    background: "dark"
  },

  palette: {
    ink: "0.19 0.020 250",
    ink2: "0.30 0.018 250",
    paper: "0.970 0.005 85",
    paper2: "0.935 0.008 85",
    mineral: "0.54 0.014 250",
    seal: "0.38 0.030 235",
    ochre: "0.48 0.105 215",
    moss: "0.45 0.075 145",
    danger: "0.53 0.190 27"
  },

  company: {
    legalName: "Livrustning AB",
    orgNumber: "556824-9022",
    addresses: [
      "Rudsjövägen 112, 131 47 Nacka, Sverige",
      "Kurskontor: Hökaren 49, 907 88 Täfteå"
    ],
    phones: ["08-972247", "070-733 32 54"],
    email: "kontakt@livrustning.se",
    webshop: "hjartstartarbutiken.com"
  },

  supportIntro:
    "Beskriv ditt ärende — kursbokning, en beställd hjärtstartare, faktura eller något annat.",
  supportPrompts: [
    "Hur lång är garantin på en hjärtstartare?",
    "Kan jag ångra mitt köp och hur gör jag i så fall?",
    "Vad kostar frakten och hur snabbt kommer varan?",
    "Vi är 15 personer på kontoret — hur bokar vi en HLR-kurs?",
    "Vad ingår i eHLR och kan den göras på distans?"
  ]
};
