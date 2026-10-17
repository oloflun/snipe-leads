import type { Saljrad } from "@/lib/leads/saljlista";

/**
 * Exempelbolagen i säljlistans demo ("Utforska i demo" på Leads › Listor,
 * Sebbes beställning 2026-10-06). Bolagen är påhittade — `.example`-domäner
 * och orgnr i 5560-serien som inte pekar på riktiga bolag, samma regel som
 * lib/demo/iris-exempel.ts.
 *
 * Statusfärgerna är med flit blandade så att demon visar hela paletten:
 * grönt (sålt), blått (väntar på signering), rött (nej), gult (ej svar) och
 * rader utan färg. Anteckningarna är på svenska — det är svenska säljsamtal
 * som demonstreras, samma val som Iris-exemplen.
 */
export const SALJLISTA_EXEMPEL: readonly Saljrad[] = [
  {
    id: "00000000-0000-4000-9000-000000000001",
    foretagsnamn: "Lundsund Byggpartner AB",
    orgnr: "556001-7281",
    kontaktperson: "Karin Lindqvist",
    kontaktnummer: "070-412 38 51",
    kontaktmail: "karin.lindqvist@lundsundbyggpartnerab.example",
    senast_kontaktad: "2026-10-05",
    anteckningar: "Avtal klart, startar med supportagenten i november.",
    status: "salt",
    created_at: "2026-10-05 09:10:00+00",
    updated_at: ""
  },
  {
    id: "00000000-0000-4000-9000-000000000002",
    foretagsnamn: "Viksund Bygggruppen AB",
    orgnr: "556002-4190",
    kontaktperson: "Mats Viklund",
    kontaktnummer: "08-410 233 17",
    kontaktmail: "mats@viksundbygggruppenab.example",
    senast_kontaktad: "2026-10-02",
    anteckningar: "Offert skickad, väntar på VD:s underskrift.",
    status: "signering",
    created_at: "2026-10-04 14:00:00+00",
    updated_at: ""
  },
  {
    id: "00000000-0000-4000-9000-000000000003",
    foretagsnamn: "Granstrand Tillverkning AB",
    orgnr: "556003-9034",
    kontaktperson: "Elin Granstrand",
    kontaktnummer: "031-712 90 44",
    kontaktmail: "elin@granstrandtillverkningab.example",
    senast_kontaktad: "2026-09-29",
    anteckningar: "Nöjda med nuvarande leverantör, återkom om ett år.",
    status: "nej",
    created_at: "2026-10-04 09:00:00+00",
    updated_at: ""
  },
  {
    id: "00000000-0000-4000-9000-000000000004",
    foretagsnamn: "Sjöhaga Logistikgruppen AB",
    orgnr: "556004-2817",
    kontaktperson: "Jonas Sjöberg",
    kontaktnummer: "070-991 24 08",
    kontaktmail: "",
    senast_kontaktad: "2026-10-06",
    anteckningar: "Ringde två gånger, inget svar. Testa efter lunch.",
    status: "ej_svar",
    created_at: "2026-10-03 15:30:00+00",
    updated_at: ""
  },
  {
    id: "00000000-0000-4000-9000-000000000005",
    foretagsnamn: "Almnäs Fastighet AB",
    orgnr: "556005-6629",
    kontaktperson: "Sara Almgren",
    kontaktnummer: "08-662 48 90",
    kontaktmail: "sara.almgren@almnasfastighetab.example",
    senast_kontaktad: "2026-10-03",
    anteckningar: "Vill se en demo av chatten. Bokat torsdag kl 14.",
    status: "",
    created_at: "2026-10-03 10:00:00+00",
    updated_at: ""
  },
  {
    id: "00000000-0000-4000-9000-000000000006",
    foretagsnamn: "Hammarnäs Bygg Sverige AB",
    orgnr: "556006-3412",
    kontaktperson: "Peter Hammar",
    kontaktnummer: "070-233 81 67",
    kontaktmail: "peter@hammarnasbyggsverigeab.example",
    senast_kontaktad: "2026-09-30",
    anteckningar: "Prisfrågan avgör. Skickade paketöversikten.",
    status: "signering",
    created_at: "2026-10-02 13:20:00+00",
    updated_at: ""
  },
  {
    id: "00000000-0000-4000-9000-000000000007",
    foretagsnamn: "Norrvik El & Installation AB",
    orgnr: "556007-5583",
    kontaktperson: "Anna Norrby",
    kontaktnummer: "090-311 72 25",
    kontaktmail: "anna@norrvikelinstallationab.example",
    senast_kontaktad: "2026-09-26",
    anteckningar: "Växeln kopplade fel, be om Anna direkt nästa gång.",
    status: "ej_svar",
    created_at: "2026-10-02 09:40:00+00",
    updated_at: ""
  },
  {
    id: "00000000-0000-4000-9000-000000000008",
    foretagsnamn: "Ekbacka Redovisning AB",
    orgnr: "556008-1945",
    kontaktperson: "Oskar Ek",
    kontaktnummer: "031-144 09 62",
    kontaktmail: "oskar@ekbackaredovisningab.example",
    senast_kontaktad: "2026-09-24",
    anteckningar: "Kör igång med leads + support. Onboarding bokad.",
    status: "salt",
    created_at: "2026-10-01 11:00:00+00",
    updated_at: ""
  },
  {
    id: "00000000-0000-4000-9000-000000000009",
    foretagsnamn: "Tallhöjden Måleri AB",
    orgnr: "556009-7230",
    kontaktperson: "Lisa Tall",
    kontaktnummer: "070-518 42 93",
    kontaktmail: "",
    senast_kontaktad: null,
    anteckningar: "Tips från Ekbacka. Inte ringt än.",
    status: "",
    created_at: "2026-10-01 08:30:00+00",
    updated_at: ""
  },
  {
    id: "00000000-0000-4000-9000-000000000010",
    foretagsnamn: "Bergfors Maskinuthyrning AB",
    orgnr: "556010-8864",
    kontaktperson: "Henrik Bergfors",
    kontaktnummer: "0920-141 58 03",
    kontaktmail: "henrik@bergforsmaskinuthyrningab.example",
    senast_kontaktad: "2026-09-19",
    anteckningar: "Har ingen egen support i dag, mejlen svämmar över.",
    status: "",
    created_at: "2026-09-30 16:10:00+00",
    updated_at: ""
  },
  {
    id: "00000000-0000-4000-9000-000000000011",
    foretagsnamn: "Strandvalls VVS AB",
    orgnr: "556011-2308",
    kontaktperson: "Maria Strandvall",
    kontaktnummer: "070-804 17 36",
    kontaktmail: "maria@strandvallsvvsab.example",
    senast_kontaktad: "2026-09-17",
    anteckningar: "För små just nu, max fem mejl i veckan.",
    status: "nej",
    created_at: "2026-09-30 09:00:00+00",
    updated_at: ""
  },
  {
    id: "00000000-0000-4000-9000-000000000012",
    foretagsnamn: "Kvarnlyckans Bageri AB",
    orgnr: "556012-9471",
    kontaktperson: "Amir Kassem",
    kontaktnummer: "040-233 95 14",
    kontaktmail: "amir@kvarnlyckansbageriab.example",
    senast_kontaktad: "2026-10-01",
    anteckningar: "Upptagen i produktionen, ring före kl 9.",
    status: "ej_svar",
    created_at: "2026-09-29 14:45:00+00",
    updated_at: ""
  },
  {
    id: "00000000-0000-4000-9000-000000000013",
    foretagsnamn: "Idre Fjällservice AB",
    orgnr: "556013-5126",
    kontaktperson: "Gunilla Idre",
    kontaktnummer: "0253-410 77 89",
    kontaktmail: "gunilla@idrefjallserviceab.example",
    senast_kontaktad: "2026-09-12",
    anteckningar: "Säsongstopp i december — vill ha allt uppe innan dess.",
    status: "",
    created_at: "2026-09-26 10:30:00+00",
    updated_at: ""
  },
  {
    id: "00000000-0000-4000-9000-000000000014",
    foretagsnamn: "Rosendal Trädgårdsanläggning AB",
    orgnr: "556014-6017",
    kontaktperson: "Björn Rosendal",
    kontaktnummer: "070-672 50 41",
    kontaktmail: "bjorn@rosendaltradgardab.example",
    senast_kontaktad: "2026-09-08",
    anteckningar: "Ringer själv tillbaka efter semestern, vecka 42.",
    status: "",
    created_at: "2026-09-25 13:00:00+00",
    updated_at: ""
  }
];
