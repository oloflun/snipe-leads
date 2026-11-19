"use client";

import Link from "next/link";
import { JuridiskSida } from "@/components/marketing/JuridiskSida";
import { BOLAG } from "@/lib/bolag";
import { useLocale, type Localized } from "@/lib/i18n";
import { TEMA_COOKIE } from "@/lib/tema";

/**
 * Cookiesidans text på svenska och engelska. Sidan (page.tsx) är en
 * serverkomponent för tenant-grindens skull; språkvalet bor i klienten.
 * Den engelska texten är en översättning av den svenska, inte en egen lydelse.
 *
 * Sidan ska stämma med koden post för post (kartläggningen 2026-11-17). Varje
 * ny kaka, lagringsnyckel eller registrering i besökarens webbläsare ska in
 * här i samma ändring som den läggs till:
 * - kakor: lib/tema.ts, lib/routes.ts (SCOPE_COOKIE), lib/vy.ts, Auth.js
 *   (lib/auth.ts, standardnamnen ur @auth/core)
 * - lagring: lib/i18n.tsx, components/InstalleraApp.tsx,
 *   components/snajp/SupportChat.tsx, components/crm/CrmDemo.tsx,
 *   components/demo/DemoBesok.tsx, lib/leads/struktur.ts,
 *   components/leads/LeadsRunForm.tsx, components/kvitton/KvittoYta.tsx,
 *   lib/leads/utskicksjobb.ts
 * - service worker: public/sw.js
 * - demolänken: app/prova/[token]/route.ts och migration 116
 * - kundernas chatt: public/widget.js och components/snajp/EmbedYta.tsx
 */
const T = {
  rubrik: { sv: "Cookies", en: "Cookies" },
  uppdaterad: { sv: "Senast uppdaterad:", en: "Last updated:" },
  ingress: {
    sv: "Här står allt som snajp.se sparar i din webbläsare: kakor, poster i webbläsarens lagring och appens offlinesida. Det mesta sparas först när du loggar in eller gör ett val. Vi använder inga analys- eller marknadsföringskakor. Den som följer en personlig demolänk i ett mejl får däremot sitt klick och besök registrerat, och det beskriver vi längre ned.",
    en: "This page lists everything snajp.se stores in your browser: cookies, entries in the browser's storage and the app's offline page. Most of it is stored only when you sign in or make a choice. We use no analytics or marketing cookies. Anyone who follows a personal demo link in an email does, however, have their click and visit recorded, and we describe that further down."
  },
  livslangd: { sv: "Livslängd:", en: "Lifetime:" },

  kakor: { sv: "Kakor", en: "Cookies" },
  kakorIntro: {
    sv: "Alla kakor nedan sätts av snajp.se och behövs för något du själv har valt eller bett om: att vara inloggad, ditt tema eller din vy i arbetsytan.",
    en: "All the cookies below are set by snajp.se and are needed for something you have chosen or asked for yourself: being signed in, your theme or your view in the workspace."
  },
  tema: {
    sv: "ditt val av ljust eller mörkt tema. Sätts först när du väljer tema i inställningarna och innehåller bara temats namn.",
    en: "your choice of light or dark theme. Set only when you choose a theme in the settings, and contains only the name of the theme."
  },
  temaTid: { sv: "ett år.", en: "one year." },
  session: {
    sv: "håller dig inloggad. På https heter den __Secure-authjs.session-token.",
    en: "keeps you signed in. Over https it is named __Secure-authjs.session-token."
  },
  sessionTid: {
    sv: "30 dagar efter att du senast använde tjänsten, eller tills du loggar ut.",
    en: "30 days after you last used the service, or until you sign out."
  },
  csrf: {
    sv: "skyddar inloggningen mot förfalskade anrop från andra webbplatser. På https heter den __Host-authjs.csrf-token.",
    en: "protects the sign-in against forged requests from other websites. Over https it is named __Host-authjs.csrf-token."
  },
  callback: {
    sv: "vilken sida du ska tillbaka till efter inloggningen. På https heter den __Secure-authjs.callback-url.",
    en: "which page to return you to after signing in. Over https it is named __Secure-authjs.callback-url."
  },
  webblasarenStangs: { sv: "tills du stänger webbläsaren.", en: "until you close the browser." },
  pkce: {
    sv: "sätts bara när du loggar in med Google eller Microsoft, och säkrar att inloggningen kommer tillbaka från rätt ställe. På https heter den __Secure-authjs.pkce.code_verifier.",
    en: "set only when you sign in with Google or Microsoft, and makes sure the sign-in comes back from the right place. Over https it is named __Secure-authjs.pkce.code_verifier."
  },
  pkceTid: { sv: "15 minuter.", en: "15 minutes." },
  scope: {
    sv: "vilken produkt (Leads, Support eller Bokföring) du senast valde i arbetsytan.",
    en: "which product (Leads, Support or Bookkeeping) you last chose in the workspace."
  },
  vy: {
    sv: "sätts bara för Snajps egen personal och anger vilken vy som är aktiv.",
    en: "set only for Snajp's own staff, and records which view is active."
  },
  vyTid: { sv: "30 dagar.", en: "30 days." },

  lagring: { sv: "Webbläsarens lagring", en: "The browser's storage" },
  lagringIntro: {
    sv: "Vissa val sparas i webbläsarens lokala lagring (localStorage), som ligger kvar tills du rensar webbläsarens data för snajp.se, eller i sessionslagringen (sessionStorage), som försvinner när du stänger fliken. Inget av det skickas till oss av sig självt.",
    en: "Some choices are stored in the browser's local storage (localStorage), which stays until you clear the browser's data for snajp.se, or in session storage (sessionStorage), which disappears when you close the tab. None of it is sent to us on its own."
  },
  lokal: { sv: "localStorage", en: "localStorage" },
  sessionslagring: { sv: "sessionStorage", en: "sessionStorage" },
  locale: {
    sv: "ditt språkval. Sparas när du byter språk.",
    en: "your language choice. Stored when you switch language."
  },
  installation: {
    sv: "att du har tackat nej till att installera Snajp som app, så att frågan inte kommer tillbaka.",
    en: "that you have declined to install Snajp as an app, so that the question does not come back."
  },
  demoSession: {
    sv: "en slumpad identitet för chatten på våra produktsidor, så att samtalet hänger ihop medan fliken är öppen. Själva samtalet sparas hos oss, knutet till den identiteten.",
    en: "a random identity for the chat on our product pages, so that the conversation holds together while the tab is open. The conversation itself is stored with us, linked to that identity."
  },
  crm: {
    sv: "CRM-demons inställningar och den kundlista du själv laddar upp i demon. Sparas när demon öppnas. Listan stannar i din webbläsare och skickas inte till oss.",
    en: "the CRM demo's settings and any customer list you upload to the demo yourself. Stored when the demo is opened. The list stays in your browser and is not sent to us."
  },
  inloggadLagring: {
    sv: "När du är inloggad sparas dessutom några arbetsval och pågående jobb, så att du ser förloppet igen efter en omladdning:",
    en: "When you are signed in, a few working choices and ongoing jobs are also stored, so that you see the progress again after a reload:"
  },
  struktur: {
    sv: "vilken utkaststruktur du senast valde.",
    en: "which draft structure you last chose."
  },
  korning: {
    sv: "en pågående leadskörning.",
    en: "an ongoing leads run."
  },
  pagaende: {
    sv: "en pågående kvittoskanning eller ett pågående utskick.",
    en: "an ongoing receipt scan or an ongoing send."
  },
  testchatt: {
    sv: "en slumpad identitet för testchatten i arbetsytan.",
    en: "a random identity for the test chat in the workspace."
  },

  app: { sv: "Appens offlinesida", en: "The app's offline page" },
  appText: {
    sv: "När du besöker snajp.se registreras en service worker i din webbläsare. Den sparar offlinesidan och appens ikoner i webbläsarens cache (snajp-v4), så att Snajp går att installera som app och visar en begriplig sida när nätet är borta. Den sparar inga uppgifter om dig och aldrig innehåll ur arbetsytan. Den ligger kvar tills du rensar webbläsarens data för snajp.se.",
    en: "When you visit snajp.se, a service worker is registered in your browser. It stores the offline page and the app's icons in the browser's cache (snajp-v4), so that Snajp can be installed as an app and shows a readable page when the network is down. It stores no data about you and never any content from the workspace. It stays until you clear the browser's data for snajp.se."
  },

  demolank: { sv: "Demolänken i mejl som skickas med Snajp", en: "The demo link in emails sent with Snajp" },
  demolank1: {
    sv: "Mejl som skickas med Snajp kan innehålla en länk till en demo (snajp.se/prova/…). Länken är unik för varje mottagare och därmed knuten till den som fick mejlet. När du följer länken registrerar vi:",
    en: "Emails sent with Snajp may contain a link to a demo (snajp.se/prova/…). The link is unique to each recipient and is therefore linked to the person who received it. When you follow the link, we record:"
  },
  klick: {
    sv: "ett klick: när länken öppnades och vilken webbläsare som öppnade den (user agent). Klick som ser ut att komma från ett e-postskydd som öppnar länkar automatiskt märks som det.",
    en: "a click: when the link was opened and which browser opened it (user agent). Clicks that appear to come from an email security filter that opens links automatically are marked as such."
  },
  besok: {
    sv: "ett besök: när du första gången skrollar, klickar eller trycker på en tangent på demosidan. Det registreras bara när länken leder till en demo på snajp.se. En post i sessionslagringen (demobesok: följt av länkens kod) gör att besöket räknas en gång, och den försvinner när du stänger fliken.",
    en: "a visit: the first time you scroll, click or press a key on the demo page. It is recorded only when the link leads to a demo on snajp.se. An entry in session storage (demobesok: followed by the link's code) makes sure the visit is counted once, and it disappears when you close the tab."
  },
  demolank2: {
    sv: "Registreringen innehåller ingen IP-adress, och ingen kaka sätts. Syftet är att avsändaren ska se om mottagaren har tittat på demon. Avsändaren är Snajp eller det företag som skickade mejlet med Snajp, och det är avsändaren som ser registreringen. Den sparas tillsammans med mejlkonversationen och raderas när den raderas. Vill du se demon utan att bli registrerad kan du gå direkt till",
    en: "The record contains no IP address, and no cookie is set. The purpose is to let the sender see whether the recipient has looked at the demo. The sender is Snajp or the company that sent the email with Snajp, and it is the sender who sees the record. It is kept together with the email conversation and deleted when the conversation is deleted. To see the demo without being recorded, go directly to"
  },
  demolank3: {
    sv: "i stället för att följa länken. Hur uppgifterna behandlas står i",
    en: "instead of following the link. How the data is processed is described in the"
  },

  kunder: { sv: "Chatten på våra kunders webbplatser", en: "The chat on our customers' websites" },
  kunderText: {
    sv: "Ett företag som har Snajps chatt på sin egen webbplats får två poster i sessionslagringen, och båda försvinner när du stänger fliken: snajp.widget.inbjudan.avfardad, på företagets webbplats, som minns att du stängt chattens inbjudan, och snajp.embed.session. följt av företagets namn, i chattfönstret som laddas från Snajp, som håller ihop samtalet. Företaget är personuppgiftsansvarigt för chatten och ska informera om den på sin webbplats.",
    en: "A company that has Snajp's chat on its own website gets two entries in session storage, and both disappear when you close the tab: snajp.widget.inbjudan.avfardad, on the company's website, which remembers that you closed the chat's invitation, and snajp.embed.session. followed by the company's name, in the chat window loaded from Snajp, which holds the conversation together. The company is the data controller for the chat and should inform about it on its website."
  },

  bokning: { sv: "Bokningskalendern", en: "The booking calendar" },
  bokningText: {
    sv: "När sidan Boka demo visar Cal.coms kalender laddas den i en ram från cal.com, och Cal.com kan då sätta egna kakor. Ramen laddas bara på den sidan.",
    en: "When the Book a demo page shows Cal.com's calendar, it is loaded in a frame from cal.com, and Cal.com may then set its own cookies. The frame is loaded only on that page."
  },

  inte: { sv: "Det vi inte gör", en: "What we do not do" },
  inteText: {
    sv: "Vi använder inga analys- eller marknadsföringskakor och inga spårningsskript från andra företag, och vi delar ingenting med annonsnätverk. Typsnitten hämtas från vår egen server. Lägger vi till analys- eller marknadsföringskakor visas en samtyckesruta innan de sätts.",
    en: "We use no analytics or marketing cookies and no tracking scripts from other companies, and we share nothing with ad networks. The fonts are served from our own server. If we add analytics or marketing cookies, a consent prompt will be shown before they are set."
  },
  policyLank: { sv: "integritetspolicyn", en: "privacy policy" }
} satisfies Record<string, Localized>;

export function CookiesSida() {
  const { text } = useLocale();
  const tid = (varde: Localized) => (
    <>
      {" "}
      {text(T.livslangd)} {text(varde)}
    </>
  );

  return (
    <JuridiskSida
      rubrik={text(T.rubrik)}
      ingress={text(T.ingress)}
      uppdaterad={{ etikett: text(T.uppdaterad), datum: BOLAG.uppdaterad.cookies }}
    >
      <h2>{text(T.kakor)}</h2>
      <p>{text(T.kakorIntro)}</p>
      <ul>
        <li>
          <strong>{TEMA_COOKIE}</strong>: {text(T.tema)}
          {tid(T.temaTid)}
        </li>
        <li>
          <strong>authjs.session-token</strong>: {text(T.session)}
          {tid(T.sessionTid)}
        </li>
        <li>
          <strong>authjs.csrf-token</strong>: {text(T.csrf)}
          {tid(T.webblasarenStangs)}
        </li>
        <li>
          <strong>authjs.callback-url</strong>: {text(T.callback)}
          {tid(T.webblasarenStangs)}
        </li>
        <li>
          <strong>authjs.pkce.code_verifier</strong>: {text(T.pkce)}
          {tid(T.pkceTid)}
        </li>
        <li>
          <strong>snajp.scope</strong>: {text(T.scope)}
          {tid(T.temaTid)}
        </li>
        <li>
          <strong>snajp.vy</strong>: {text(T.vy)}
          {tid(T.vyTid)}
        </li>
      </ul>

      <h2>{text(T.lagring)}</h2>
      <p>{text(T.lagringIntro)}</p>
      <ul>
        <li>
          <strong>snajp.locale</strong> ({text(T.lokal)}): {text(T.locale)}
        </li>
        <li>
          <strong>snajp.installation.avvisad</strong> ({text(T.lokal)}): {text(T.installation)}
        </li>
        <li>
          <strong>snajp.demo.session</strong> ({text(T.sessionslagring)}): {text(T.demoSession)}
        </li>
        <li>
          <strong>snajp-demo-crm</strong> ({text(T.lokal)}): {text(T.crm)}
        </li>
      </ul>
      <p>{text(T.inloggadLagring)}</p>
      <ul>
        <li>
          <strong>snajp:leads-struktur</strong> ({text(T.lokal)}): {text(T.struktur)}
        </li>
        <li>
          <strong>snipra:korning:kund</strong>, <strong>snipra:korning:admin</strong> ({text(T.lokal)}):{" "}
          {text(T.korning)}
        </li>
        <li>
          <strong>snajp:kvittoskanning</strong>, <strong>snajp:utskick:…</strong> ({text(T.sessionslagring)}):{" "}
          {text(T.pagaende)}
        </li>
        <li>
          <strong>snajp.testchatt.session</strong> ({text(T.sessionslagring)}): {text(T.testchatt)}
        </li>
      </ul>

      <h2>{text(T.app)}</h2>
      <p>{text(T.appText)}</p>

      <h2 id="demolank">{text(T.demolank)}</h2>
      <p>{text(T.demolank1)}</p>
      <ul>
        <li>{text(T.klick)}</li>
        <li>{text(T.besok)}</li>
      </ul>
      <p>
        {text(T.demolank2)} <Link href="/demo">snajp.se/demo</Link> {text(T.demolank3)}{" "}
        <Link href="/integritetspolicy#demolank">{text(T.policyLank)}</Link>.
      </p>

      <h2>{text(T.kunder)}</h2>
      <p>{text(T.kunderText)}</p>

      <h2>{text(T.bokning)}</h2>
      <p>{text(T.bokningText)}</p>

      <h2>{text(T.inte)}</h2>
      <p>{text(T.inteText)}</p>
    </JuridiskSida>
  );
}
