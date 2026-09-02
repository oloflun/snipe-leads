"use client";

import { useState } from "react";
import { Exempelbolagslista } from "@/components/leads/LeadsRunForm";

/**
 * Exempellistan som EGEN komponent, med sina data.
 *
 * Datat bodde inline i /forhandsvisning/exempelbolag. När listan skulle visas
 * bredvid körningsformuläret på fler ytor (adminens Testkörningar, kundens
 * leads-vy) fanns två vägar: kopiera de tre bolagen till varje yta, eller
 * flytta dem hit EN gång. Kopior av exempeldata glider isär precis som
 * formulärkopior gjorde (se LeadsRunForm:s docstring) — därför bor bolagen
 * här och alla ytor renderar samma komponent.
 *
 * Allt är påhittat och kan aldrig mejlas: org.numren har medvetet fel
 * kontrollsiffra och domänerna ligger under `.example` (RFC 2606). Se
 * app/leads/exempelbolag.py — samma regel som backendens generator.
 *
 * "Uppdatera" växlar mellan två fasta urval. I produkten hämtar knappen ett
 * nytt urval från backenden (`fro` i ExempelbolagRequest); fördröjningen här
 * motsvarar det anropet så att knappens läge går att se.
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
    pitch_body: PITCH(
      "Lundsund Bygg & Partner AB",
      "Umeå",
      "Grattis till den nya lokalen",
      "en ny lokal ska utrustas från grunden, och den listan skrivs en gång"
    ),
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
    pitch_body: PITCH(
      "Viksund Bygg Gruppen AB",
      "Umeå",
      "Grattis till den nya lokalen",
      "en ny lokal ska utrustas från grunden, och den listan skrivs en gång"
    ),
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
    pitch_body: PITCH(
      "Hammarnäs Bygg Sverige AB",
      "Umeå",
      "Grattis till den nya lokalen",
      "en ny lokal ska utrustas från grunden, och den listan skrivs en gång"
    ),
    contact_name: "Inköpschef",
    orgnr: "556201-4453",
    ort: "Umeå",
    website: "hammarnasbyggsverigeab.example",
    anstallda: 31,
    bransch: "Bygg",
    beskrivning: "Bygg i Umeå med 31 anställda. Har flyttat till större lokal."
  }
];

/** Ett andra urval, så att "Uppdatera" går att prova. */
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
    beskrivning:
      "Tillverkning i Jönköping med 37 anställda. Rekryterar till produktionen — tre annonser ute.",
    pitch_subject: "Rekryterar till produktionen — en fråga",
    pitch_varfor_nu: "fler i produktionen betyder fler som ska introduceras, utrustas och hållas med",
    pitch_body: PITCH(
      "Granstrand Tillverkning AB",
      "Jönköping",
      "Jag såg att ni rekryterar till produktionen",
      "fler i produktionen betyder fler som ska introduceras, utrustas och hållas med"
    )
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
    beskrivning:
      "Logistik i Örebro med 22 anställda. Har bytt affärssystem och skriver om det på sin blogg.",
    pitch_subject: "Bytt affärssystem — en fråga",
    pitch_varfor_nu: "ett systembyte är det enda tillfället på flera år då rutiner faktiskt görs om",
    pitch_body: PITCH(
      "Sjöhaga Logistik Gruppen AB",
      "Örebro",
      "Jag såg att ni bytt affärssystem",
      "ett systembyte är det enda tillfället på flera år då rutiner faktiskt görs om"
    )
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
    beskrivning:
      "Fastighet i Västerås med 14 anställda. Har lagt om sin tjänstesida och lyfter fram service.",
    pitch_subject: "Er nya tjänstesida — en fråga",
    pitch_varfor_nu: "när servicelöftet skärps blir det som håller det uppe plötsligt en fråga för er",
    pitch_body: PITCH(
      "Almnäs Fastighet AB",
      "Västerås",
      "Jag läste er nya tjänstesida",
      "när servicelöftet skärps blir det som håller det uppe plötsligt en fråga för er"
    )
  }
];

export function ExempelbolagDemo() {
  const [omgang, setOmgang] = useState(0);
  const [hamtar, setHamtar] = useState(false);
  const bolag = omgang % 2 === 0 ? BOLAG : ANDRA_OMGANGEN;

  function uppdatera() {
    setHamtar(true);
    window.setTimeout(() => {
      setOmgang((n) => n + 1);
      setHamtar(false);
    }, 450);
  }

  return <Exempelbolagslista bolag={bolag} onUppdatera={uppdatera} uppdaterar={hamtar} />;
}
