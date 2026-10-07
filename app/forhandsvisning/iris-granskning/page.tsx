"use client";

import { useState } from "react";
import { IrisGranskning } from "@/components/leads/IrisGranskning";

/**
 * Förhandsvisning av Iris › Granskning (2026-10-07): utkastet med signaturen
 * och loggan under textrutan, och AI-knapparna, med syntetiska svar i stället
 * för backenden.
 *
 * Ingenting här når en databas eller en modell. `fetch` mot
 * `/api/snajp-support/...` och `/api/email-studio` fångas i sidan och svarar
 * med påhittade, uppenbart syntetiska värden — samma mönster som
 * /forhandsvisning/kundinstallningar.
 */

const SIGNATUR = {
  namn: "Sebastian Bergman",
  titel: "Snajp Support | AI för leads och kundtjänst",
  telefon: "+46 70 000 00 00",
  epost: "exempel@snajp.example",
  ort: "Umeå & Göteborg",
  webb: "www.snajp.se",
  bolag: "Snajp AB"
};

const SIGNATURTEXT = [
  [SIGNATUR.namn, SIGNATUR.titel, SIGNATUR.telefon, SIGNATUR.epost].join("\n"),
  [SIGNATUR.ort, SIGNATUR.webb].join("\n"),
  SIGNATUR.bolag
].join("\n\n");

const FOT = [
  "--",
  "Snajp AB, org.nr 559000-0000",
  "Exempelgatan 1, 903 26 Umeå",
  "",
  "Du får det här mejlet därför att din adress är hämtad ur offentliga företagsuppgifter och vi bedömer att erbjudandet är relevant för din verksamhet. Ändamålet är att ta en första affärskontakt.",
  "",
  "Vill du inte få fler mejl från oss: https://snajp.example/avregistrera/exempel"
].join("\n");

const BRODTEXT =
  "Hej,\n\nNi rekryterar två snickare till det nya kontoret i Holmsund. När en byggfirma växer så snabbt brukar orderboken behöva fyllas på i samma takt.\n\nSnajp hittar bolag som passar er kundprofil och skriver ett första mejl som ni granskar innan det går iväg.\n\nHör av er om ni vill se två konkreta exempel.\n\nVänliga hälsningar,";

function kö() {
  const logga = `${window.location.origin}/epost/snajp-logga.png`;
  return {
    items: [
      {
        id: "forhandsvisning-1",
        subject: "Nya kontoret i Holmsund",
        body: `${BRODTEXT}\n${SIGNATURTEXT}\n\n${FOT}`,
        brodtext: BRODTEXT,
        svans: `${SIGNATURTEXT}\n\n${FOT}`,
        prospect_email: "info@provbygget.example",
        company_name: "Provbygget",
        lagesbeskrivning: "Bygger om kök och badrum åt bostadsrättsföreningar i Umeå.",
        signaler: ["rekryterar två snickare", "nytt kontor i Holmsund"]
      }
    ],
    signatur: { ...SIGNATUR, logotyp_url: logga, text: SIGNATURTEXT }
  };
}

const FORBATTRAD =
  "Hej,\n\nTvå nya snickare och ett kontor i Holmsund på kort tid. Då brukar frågan snart bli var nästa uppdrag kommer ifrån.\n\nSnajp hittar bolag som passar er kundprofil och skriver första mejlet åt er, som ni godkänner innan det skickas.\n\nHör av er om ni vill se två exempel från Umeå.\n\nVänliga hälsningar,";

function svar(kropp: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(kropp), { status: 200, headers: { "Content-Type": "application/json" } })
  );
}

function installeraFetch() {
  if (typeof window === "undefined" || (window as { __forhandsvisning?: boolean }).__forhandsvisning) return;
  (window as { __forhandsvisning?: boolean }).__forhandsvisning = true;
  const riktig = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (url.includes("/api/email-studio")) {
      return svar({
        success: true,
        data: {
          new_version: FORBATTRAD,
          explanation: "Exempelsvar i förhandsvisningen: öppningen börjar i signalen, uppmaningen är kvar.",
          subject_suggestions: ["Holmsund och nästa uppdrag"]
        }
      });
    }
    if (!url.includes("/api/snajp-support/")) return riktig(input, init);
    if (url.endsWith("/leads/queue")) return svar(kö());
    return svar({});
  };
}

export default function IrisGranskningForhandsvisning() {
  const [redo] = useState(() => {
    installeraFetch();
    return true;
  });
  if (!redo) return null;
  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <IrisGranskning />
    </main>
  );
}
