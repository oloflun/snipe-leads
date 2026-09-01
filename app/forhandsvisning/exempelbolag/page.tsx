"use client";

import { useState } from "react";
import { Exempelbolagslista } from "@/components/leads/LeadsRunForm";
import { ICP_ETIKETTER } from "@/lib/leads/icpLabels";

/**
 * Förhandsvisning av hur en avslutad leads-körning ser ut.
 *
 * ## Varför sidan finns
 *
 * Resultatvyn ligger bakom en inloggning OCH bakom en körning som kostar
 * LLM-anrop. Att granska hur den SER UT krävde alltså ett konto, en tenant med
 * nycklar och en riktig körning — vilket i praktiken betyder att ingen
 * granskar den, och att den vy som visar produktens viktigaste ögonblick är
 * den enda ingen tittar på.
 *
 * Sidan är publik med flit och kan vara det: varje bolag här är påhittat, och
 * ingen rad kommer från någon kunds data. Se `bygg_exempelbolag` i
 * app/leads/exempelbolag.py — org.numren har medvetet fel kontrollsiffra och
 * domänerna ligger under `.example`.
 *
 * ## Vad den INTE är
 *
 * Ingen körning startas härifrån och inget skrivs. Ändras listans utseende i
 * `LeadsRunForm` ändras den här sidan med, eftersom den renderar samma
 * komponent — en kopia hade slutat spegla produkten inom en vecka.
 */


/** Samma form som backendens pitch. Se app/leads/exempelbolag.py. */
function PITCH(namn: string, ort: string, oppning: string, varforNu: string): string {
  return [
    "Hej!",
    `${oppning} i ${ort}. Anledningen att jag hör av mig just nu är att ${varforNu}.`,
    `Vi säljer hjärtstartare och HLR-utbildning till arbetsplatser. I det läge ${namn} är i brukar det vara relevant precis nu, innan rutinerna satt sig.`,
    "Är det något ni tittar på? I så fall svarar jag gärna på hur det brukar se ut — annars säger du bara till, så hör jag inte av mig igen.",
    "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
  ].join("\n\n");
}

const BOLAG = [
  {
    id: "1",
    company_name: "Lundsund Bygg & Partner AB",
    pitch_subject: "Grattis till den nya lokalen",
    pitch_varfor_nu: "en ny lokal ska utrustas från grunden, och den listan skrivs en gång",
    pitch_body: [
      "Hej!",
      "Grattis till den nya lokalen i Umeå. Anledningen att jag hör av mig just nu är att en ny lokal ska utrustas från grunden, och den listan skrivs en gång.",
      "Vi säljer hjärtstartare och HLR-utbildning till arbetsplatser. I det läge Lundsund Bygg & Partner AB är i brukar det vara relevant precis nu, innan rutinerna satt sig.",
      "Är det något ni tittar på? I så fall svarar jag gärna på hur det brukar se ut — annars säger du bara till, så hör jag inte av mig igen.",
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
    ].join("\n\n"),

    contact_name: "Inköpschef",
    orgnr: "556438-7011",
    ort: "Umeå",
    website: "lundsundbyggpartnerab.example",
    anstallda: 13,
    bransch: "Bygg",
    beskrivning: "Bygg i Umeå med 13 anställda. Söker en ny inköpschef sedan i våras."
  },
  {
    id: "2",
    company_name: "Viksund Bygg Gruppen AB",
    pitch_subject: "Grattis till den nya lokalen",
    pitch_varfor_nu: "en ny lokal ska utrustas från grunden, och den listan skrivs en gång",
    pitch_body: [
      "Hej!",
      "Grattis till den nya lokalen i Umeå. Anledningen att jag hör av mig just nu är att en ny lokal ska utrustas från grunden, och den listan skrivs en gång.",
      "Vi säljer hjärtstartare och HLR-utbildning till arbetsplatser. I det läge Viksund Bygg Gruppen AB är i brukar det vara relevant precis nu, innan rutinerna satt sig.",
      "Är det något ni tittar på? I så fall svarar jag gärna på hur det brukar se ut — annars säger du bara till, så hör jag inte av mig igen.",
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
    ].join("\n\n"),

    contact_name: "Inköpschef",
    orgnr: "556859-7318",
    ort: "Umeå",
    website: "viksundbygggruppenab.example",
    anstallda: 14,
    bransch: "Bygg",
    beskrivning:
      "Bygg i Umeå med 14 anställda. Har lagt om sin tjänstesida och lyfter fram service."
  },
  {
    id: "3",
    company_name: "Hammarnäs Bygg Sverige AB",
    pitch_subject: "Grattis till den nya lokalen",
    pitch_varfor_nu: "en ny lokal ska utrustas från grunden, och den listan skrivs en gång",
    pitch_body: [
      "Hej!",
      "Grattis till den nya lokalen i Umeå. Anledningen att jag hör av mig just nu är att en ny lokal ska utrustas från grunden, och den listan skrivs en gång.",
      "Vi säljer hjärtstartare och HLR-utbildning till arbetsplatser. I det läge Hammarnäs Bygg Sverige AB är i brukar det vara relevant precis nu, innan rutinerna satt sig.",
      "Är det något ni tittar på? I så fall svarar jag gärna på hur det brukar se ut — annars säger du bara till, så hör jag inte av mig igen.",
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
    ].join("\n\n"),

    contact_name: "Inköpschef",
    orgnr: "556201-4453",
    ort: "Umeå",
    website: "hammarnasbyggsverigeab.example",
    anstallda: 31,
    bransch: "Bygg",
    beskrivning: "Bygg i Umeå med 31 anställda. Har flyttat till större lokal."
  }
];


/** Ett andra urval, så att "Uppdatera" går att prova här också. */
const ANDRA_OMGANGEN = [
  {
    id: "4",
    company_name: "Granstrand Tillverkning AB",
    contact_name: "Inköpschef",
    orgnr: "556744-1288",
    ort: "Jönköping",
    website: "granstrandtillverkningab.example",
    anstallda: 37,
    bransch: "Tillverkning",
    beskrivning: "Tillverkning i Jönköping med 37 anställda. Rekryterar till produktionen — tre annonser ute.",
    pitch_subject: "Rekryterar till produktionen — en fråga",
    pitch_varfor_nu: "fler i produktionen betyder fler som ska introduceras, utrustas och hållas med",
    pitch_body: PITCH("Granstrand Tillverkning AB", "Jönköping", "Jag såg att ni rekryterar till produktionen", "fler i produktionen betyder fler som ska introduceras, utrustas och hållas med")
  },
  {
    id: "5",
    company_name: "Sjöhaga Logistik Gruppen AB",
    contact_name: "Platschef",
    orgnr: "556019-5473",
    ort: "Örebro",
    website: "sjohagalogistikgruppenab.example",
    anstallda: 22,
    bransch: "Logistik",
    beskrivning: "Logistik i Örebro med 22 anställda. Har bytt affärssystem och skriver om det på sin blogg.",
    pitch_subject: "Bytt affärssystem — en fråga",
    pitch_varfor_nu: "ett systembyte är det enda tillfället på flera år då rutiner faktiskt görs om",
    pitch_body: PITCH("Sjöhaga Logistik Gruppen AB", "Örebro", "Jag såg att ni bytt affärssystem", "ett systembyte är det enda tillfället på flera år då rutiner faktiskt görs om")
  },
  {
    id: "6",
    company_name: "Almnäs Fastighet AB",
    contact_name: "VD",
    orgnr: "556352-9061",
    ort: "Västerås",
    website: "almnasfastighetab.example",
    anstallda: 14,
    bransch: "Fastighet",
    beskrivning: "Fastighet i Västerås med 14 anställda. Har lagt om sin tjänstesida och lyfter fram service.",
    pitch_subject: "Er nya tjänstesida — en fråga",
    pitch_varfor_nu: "när servicelöftet skärps blir det som håller det uppe plötsligt en fråga för er",
    pitch_body: PITCH("Almnäs Fastighet AB", "Västerås", "Jag läste er nya tjänstesida", "när servicelöftet skärps blir det som håller det uppe plötsligt en fråga för er")
  }
];

/** Samma etiketter som formuläret använder — se ICP_ETIKETTER. */
const ÖVERSKRIVNINGAR: [string, string][] = [
  [ICP_ETIKETTER.industries.label, "Bygg"],
  [ICP_ETIKETTER.geography.label, "Umeå"],
  [ICP_ETIKETTER.roles.label, "inköpschef"],
  [ICP_ETIKETTER.deal_breakers.label, "Under 10 anställda"]
];

export default function Page() {
  const [omgang, setOmgang] = useState(0);
  const [hamtar, setHamtar] = useState(false);
  const bolag = omgang % 2 === 0 ? BOLAG : ANDRA_OMGANGEN;

  // Här är urvalet två fasta listor. I produkten hämtar knappen ett nytt urval
  // från backenden, som slumpar ett frö per anrop — se `fro` i
  // ExempelbolagRequest. Fördröjningen finns för att knappens läge ska gå att
  // se; den motsvarar anropet.
  function uppdatera() {
    setHamtar(true);
    window.setTimeout(() => {
      setOmgang((n) => n + 1);
      setHamtar(false);
    }, 450);
  }

  return (
    <main className="min-h-screen bg-paper py-10 text-ink">
      <div className="mx-auto max-w-[900px] space-y-6 px-4 md:px-6">
        <header>
          <p className="text-[0.8125rem] font-medium text-ink/45">Förhandsvisning</p>
          <h1 className="mt-1 text-[1.5rem] font-semibold leading-tight tracking-[-0.02em]">
            Så ser en avslutad körning ut
          </h1>
          <p className="mt-2 max-w-[68ch] text-[0.9375rem] leading-[1.6] text-ink/65">
            Samma komponenter som kundens leads-vy renderar efter en körning. Alla bolag här är
            påhittade — sidan startar ingen körning och skriver ingenting.
          </p>
          <p className="mt-3 max-w-[68ch] rounded-card bg-paper2/60 p-4 text-[0.9375rem] leading-[1.6] text-ink/70">
            <strong className="font-semibold">Klicka på ett bolag</strong> för att öppna utkastet.
            Där finns Email Studios alla åtgärder — Kortare, Skriv om, Förbättra, Personalisera,
            Översätt, A/B-varianter, Uppföljning och Analysera — och du kan skriva om texten själv
            innan du provar dem. <em>Skicka test</em> skickar ingenting.
          </p>
        </header>

        <div className="rounded-card bg-paper2/60 p-5">
          <p className="text-[15px]">
            <strong className="font-semibold">3</strong> bolag i körningen · bara research ·
            testkörning
          </p>
          <dl className="mt-4 grid gap-x-8 gap-y-3 sm:grid-cols-2">
            {ÖVERSKRIVNINGAR.map(([etikett, värde]) => (
              <div key={etikett} className="border-t border-ink/10 pt-2">
                <dt className="text-[12px] font-medium uppercase tracking-[0.04em] text-ink/45">
                  {etikett}
                </dt>
                <dd className="mt-1 text-[14px] leading-6 text-ink/80">{värde}</dd>
              </div>
            ))}
          </dl>
        </div>

        <Exempelbolagslista bolag={bolag} onUppdatera={uppdatera} uppdaterar={hamtar} />
      </div>
    </main>
  );
}
