"use client";

import { AlertTriangle } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { kriterier } from "@/lib/prospekt";
import {
  Badge,
  Cell,
  Rad,
  Radlista,
  SkeletonRows,
  Tabell,
  Tomt,
  btnLiten,
  btnSecondary,
  etikett,
  flik,
  flikAktiv,
  flikInaktiv,
  meta,
  tabellRad
} from "@/components/ui";
import { EjAktiverad, arEjAktiverad } from "@/components/EjAktiverad";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { offertForUtkast } from "@/lib/leads/offert";
import { cn } from "@/lib/utils";
import { sv, useLocale, type Localized } from "@/lib/i18n";

/** Text vi inte skrivit själva (backendens fel, ett undantag): samma på båda språken. */
function ordagrant(m: string): Localized {
  return { sv: m, en: m };
}

/**
 * Bolagsregistret — kundens EGNA prospekt.
 *
 * ## Vad det ersatte
 *
 * Vyn renderade `companies` ur `lib/mock-data.ts`: Byggkompaniet Syd, Ateljé
 * Måltid, Nordic Sweat Studios och två till, med påhittade kontaktpersoner och
 * mejladresser — för varje INLOGGAD kund, på både /dashboard/leads och
 * /dashboard/companies. En ny kund som öppnade fliken fick intrycket att
 * agenterna redan hittat fem bolag åt dem.
 *
 * Det är samma fel som Email Studio hade (b5277d1) och som analysvyn hade:
 * exempeldata omärkt i en betald yta. Skillnaden mellan de tre var bara vilken
 * flik man råkade öppna.
 *
 * ## Regler
 *
 * Prospekten hämtas ur `/leads/prospects`, som är tenant-skopad ur sessionen.
 * Tom lista är TOM — inga exempelbolag som platshållare, eftersom det var just
 * den vänligheten som blev lögnen. Ett trasigt anrop säger att det är trasigt.
 *
 * Statusordet översätts. Tabellen visade tidigare våra interna värden
 * ("recommended", "queued") oöversatta i en kundvänd vy; kolumnen togs bort
 * helt av det skälet. Den är tillbaka nu när orden är på svenska.
 */

type Prospekt = {
  id: string;
  company_name: string;
  contact_name: string | null;
  contact_email: string | null;
  status: string;
  /** 'example' för de sex påhittade bolagen (se exempelbolag.py). Redan i svaret. */
  origin?: string | null;
  ort: string | null;
  sni: string | null;
  website: string | null;
  orgnr: string | null;
  score_total: number | null;
  icp_fit: number | null;
  qualified: boolean | null;
  disqualifiers: string[] | null;
  // Avsiktligt otypad: fältet HAR nått hit som en sträng. Se lib/prospekt.ts.
  score_breakdown: unknown;
};

type Lage =
  | { fas: "laddar" }
  | { fas: "ejAktiverad" }
  | { fas: "fel"; meddelande: Localized }
  | { fas: "klar"; prospekt: Prospekt[] };

/**
 * Riktningen ett "Flytta"-klick betyder just nu — se docstringen på
 * `flyttaOverValda` för var den kommer ifrån.
 */
type Riktning = "till_test" | "till_skarp";

/** Utfallet av ETT flytta-försök — visas rad för rad efter "Flytta". */
type Utfallsrad = {
  id: string;
  company_name: string;
  ok: boolean;
  /** Avgör om resultatraden ska visa ifyllnadsformuläret (bara till_skarp
   *  kan 422:a på saknade fält — till_test har inga förutsättningar). */
  riktning: Riktning;
  /** Bara satt när ok=false. Backendens 422-lista, redan på svenska. */
  saknas?: Localized[];
};

/** Svaret /befordra och /degradera ger, tolkat oavsett statuskod (se readJsonBody). */
type BefordraSvar = {
  detail?: { message?: string; saknas?: string[] } | string;
};

/** Utfallet av ETT "Skapa utkast"-försök. Samma radmönster som Utfallsrad,
 *  men utan ifyllnad — ett utkast som inte gick att skapa ska bara förklaras. */
type UtkastRad = {
  id: string;
  company_name: string;
  ok: boolean;
  meddelande?: Localized;
};

/** Backendens statusvärden, på svenska. Speglar check-villkoret i migration 010. */
const STATUS_ETIKETT: Record<string, Localized> = {
  new: { sv: "Ny", en: "New" },
  researching: { sv: "Research pågår", en: "Researching" },
  ready: { sv: "Redo", en: "Ready" },
  contacted: { sv: "Kontaktad", en: "Contacted" },
  replied: { sv: "Svarat", en: "Replied" },
  meeting: { sv: "Möte", en: "Meeting" },
  won: { sv: "Vunnen", en: "Won" },
  lost: { sv: "Förlorad", en: "Lost" },
  suppressed: { sv: "Spärrad", en: "Blocked" }
};

/** Status som betyder att något väntar på kunden — bär ochre, resten är neutrala. */
const AKTIV_STATUS = new Set(["ready", "replied", "meeting"]);

function segment(p: Prospekt): string {
  return [p.sni, p.ort].filter(Boolean).join(" · ") || "–";
}

/**
 * Signalen: det starkaste kriteriet som faktiskt slog in.
 *
 * `score_breakdown` sparas RENDERAD (migration 031) just för att en poäng utan
 * motivering inte går att lita på — och den motiveringen är det närmaste en
 * "signal" prospektet har. Diskvalificerare vinner över den: att ett bolag
 * sorterats bort är viktigare än varför det nästan platsade.
 */
function signal(p: Prospekt): string {
  if (p.disqualifiers?.length) {
    return p.disqualifiers[0];
  }
  const träff = kriterier(p.score_breakdown).find(
    (k) => k.motivering && k.utfall !== "saknas"
  );
  return träff?.motivering ?? "–";
}

/** Tomt värde i en tabellcell är "–" (tankstreck), aldrig em-streck. */
function poang(p: Prospekt): string {
  if (typeof p.score_total === "number") return String(p.score_total);
  if (typeof p.icp_fit === "number") return String(Math.round(p.icp_fit * 100));
  return "–";
}

/** Knapptexten SKA säga vilken riktning som gäller — se docstringen på
 *  `flyttaOverValda`. Fel riktning tyst i en knapptext är precis den sortens
 *  fel som gör att någon flyttar ett riktigt prospekt in i testytan, eller
 *  tvärtom, utan att märka det. */
function flyttaKnappText(riktning: Riktning, antal: number): Localized {
  return riktning === "till_test"
    ? { sv: `Flytta till testytan (${antal})`, en: `Move to the test area (${antal})` }
    : { sv: `Flytta till skarpa listan (${antal})`, en: `Move to the live list (${antal})` };
}

/**
 * Erbjudandetexten `offer_summary` kräver — TENANTENS text, inte prospektets
 * (registrets `Prospekt`-typ bär den inte). Speglar `hamtaOffertsammanfattning`
 * i Bolagssida.tsx med flit i stället för att delas: samma resonemang som
 * `snajpAnrop`-dubbleringen där, se den docstringen.
 */
async function hamtaOffertsammanfattning(): Promise<string> {
  // Samma källa som Inställningar → Affärskontext, inte context-docs som
  // kan vara tomma eller 503 medan formuläret är ifyllt.
  return offertForUtkast();
}

type LeadsJobbSvar = {
  status?: string;
  error?: string;
  result?: {
    body?: string;
    escalated?: boolean;
    escalation_reason?: string | null;
    draft_note?: string;
    prospect_id?: string;
  };
  /** Ett fel vi själva formulerat (timeout, felstatus), på båda språken. */
  fel?: Localized;
};

async function pollaLeadsJobb(jobId: string): Promise<LeadsJobbSvar> {
  for (let forsok = 0; forsok < 90; forsok += 1) {
    await new Promise((r) => setTimeout(r, forsok < 5 ? 800 : 2000));
    const response = await fetch("/api/snajp-support/leads/jobb/" + encodeURIComponent(jobId), {
      cache: "no-store"
    });
    const kropp = await readJsonBody<LeadsJobbSvar>(response).catch(() => null);
    if (!response.ok) {
      const detalj = extraheraFelmeddelande((kropp as { detail?: unknown } | null)?.detail);
      return {
        status: "failed",
        fel: detalj
          ? ordagrant(detalj)
          : { sv: `Jobbet svarade ${response.status}.`, en: `The job responded ${response.status}.` }
      };
    }
    if (kropp?.status === "completed" || kropp?.status === "failed") {
      return kropp;
    }
  }
  return { status: "timeout", fel: { sv: "Körningen tog för lång tid.", en: "The run took too long." } };
}

/** Poängmotiveringen som forskningsunderlag åt utkastet — samma källa som
 *  "Signal"-kolumnen redan visar. Speglar Bolagssida.tsx:s variant. */
function byggForskningssammanfattning(p: Prospekt): string {
  return kriterier(p.score_breakdown)
    .map((k) => `${k.etikett} (${k.utfall})${k.motivering ? `: ${k.motivering}` : ""}`)
    .join("\n")
    .slice(0, 8000);
}

/** Pydantics 422 lägger en LISTA i `detail`, en handskriven HTTPException en
 *  STRÄNG — samma distinktion som `snajpAnrop` i Bolagssida.tsx gör. */
function extraheraFelmeddelande(detail: unknown): string | undefined {
  if (Array.isArray(detail)) {
    return detail
      .map((d) =>
        d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)
      )
      .join("; ");
  }
  return typeof detail === "string" ? detail : undefined;
}

export function Bolagsregister({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { text } = useLocale();
  const [lage, setLage] = useState<Lage>({ fas: "laddar" });
  const vag = useArbetsvag();

  const hamta = useCallback(async (tyst = false) => {
    if (!tyst) setLage({ fas: "laddar" });

    if (demo) {
      const svar = demoOversiktSvar("/leads/prospects") as { prospects?: Prospekt[] } | undefined;
      setLage({ fas: "klar", prospekt: svar?.prospects ?? [] });
      return;
    }

    try {
      const response = await fetch("/api/snajp-support/leads/prospects", { cache: "no-store" });
      // response.ok före tolkningen: en sovande backend svarar med HTML, och
      // `.json()` på den ger kunden webbläsarens råa felmeddelande.
      if (response.status === 409) {
        // Kroppen måste läsas ÄVEN vid felstatus här: koden bor i den, och
        // 409 betyder två olika saker (se arEjAktiverad).
        const kropp = await readJsonBody<unknown>(response).catch(() => null);
        if (arEjAktiverad(response.status, kropp)) {
          setLage({ fas: "ejAktiverad" });
          return;
        }
      }
      if (!response.ok) {
        setLage({
          fas: "fel",
          meddelande:
            response.status >= 500
              ? {
                  sv: "Tjänsten svarar inte just nu. Den vaknar ur viloläge och kan ta upp till en minut.",
                  en: "The service is not responding right now. It is waking from sleep mode and can take up to a minute."
                }
              : {
                  sv: `Kunde inte hämta bolagen (status ${response.status}).`,
                  en: `Could not fetch the companies (status ${response.status}).`
                }
        });
        return;
      }
      const kropp = await readJsonBody<{ prospects?: Prospekt[]; offline?: boolean }>(response);
      if (!kropp || kropp.offline) {
        setLage({ fas: "fel", meddelande: { sv: "Backenden svarade utan innehåll.", en: "The backend replied without content." } });
        return;
      }
      setLage({ fas: "klar", prospekt: kropp.prospects ?? [] });
    } catch (error) {
      setLage({
        fas: "fel",
        meddelande:
          error instanceof Error
            ? ordagrant(error.message)
            : { sv: "Kunde inte nå servern.", en: "Could not reach the server." }
      });
    }
  }, [demo]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  useEffect(() => {
    const lyssna = () => {
      void hamta(true);
    };
    window.addEventListener("snipra:leads-korning-klar", lyssna);
    return () => window.removeEventListener("snipra:leads-korning-klar", lyssna);
  }, [hamta]);

  // Fas 3 §4: kryssrutor + "Flytta över valda". Bara i den riktiga vyn — demot
  // visar en statisk ögonblicksbild (demoOversiktSvar) utan riktiga id:n, och
  // ett POST mot ett påhittat id hade bara gett 404 utan att kunden lärt sig
  // något om funktionen.
  const [valda, setValda] = useState<Set<string>>(new Set());
  const [flyttar, setFlyttar] = useState(false);
  const [utfall, setUtfall] = useState<Utfallsrad[] | null>(null);
  const [ifyllnad, setIfyllnad] = useState<
    Record<string, { orgnr: string; website: string; contact_email: string }>
  >({});

  // Fas 2 §3, 2.4-UI: testkörningar döljs som default. Exempelbolag räknas
  // INTE hit — de är produktens tomläge och ska synas även med växeln av.
  //
  // `visaTest` bär ÄVEN läget "Flytta" ska tolka riktningen ur (se
  // flyttaOverValda nedan). Ingen egen `läge`-flagga behövdes: den här är
  // redan svaret på "vilken yta tittar kunden på just nu", och det är exakt
  // frågan riktningen ska svara på. DashboardContext/lib/vy.ts äger ett HELT
  // annat läge (adminens admin/demo/kund-yta — VEM som tittar, inte VILKEN
  // datayta den här tabellen visar) och har inget att säga om riktningen.
  const [visaTest, setVisaTest] = useState(false);
  const [genererarUtkast, setGenererarUtkast] = useState(false);
  const [processarOm, setProcessarOm] = useState(false);
  const [utkastResultat, setUtkastResultat] = useState<UtkastRad[] | null>(null);

  const vaxlaVal = useCallback((id: string) => {
    setValda((forra) => {
      const nasta = new Set(forra);
      if (nasta.has(id)) {
        nasta.delete(id);
      } else {
        nasta.add(id);
      }
      return nasta;
    });
  }, []);

  /**
   * "Flytta"-knappens riktning följer var kunden STÅR i tabellen — den är
   * inget eget reglage. `visaTest` säger redan vilken yta som är synlig
   * (testkörningar dolda som default = skarpt läge, framplockade = testläge,
   * se useState ovan), och det är precis den frågan riktningen ska svara på.
   *
   * Skarpt läge (visaTest=false, default): bara riktiga prospekt syns och går
   * att markera, så "Flytta" för dem TILL testytan (`/degradera`). Det gör
   * prospektet OSKICKBART — send-guardens spärr noll (scheduler.py) blockerar
   * varje utskick där origin är 'test' eller 'example', och det är hela
   * poängen: ett prospekt som hamnat fel ska aldrig kunna mejlas av misstag.
   *
   * Testläge (visaTest=true): test/exempel syns också, och "Flytta" gör vad
   * den alltid gjort — flyttar DEM till den skarpa listan (`/befordra`), och
   * blir därmed skickbara. Se den endpointens docstring för samma regel åt
   * andra hållet.
   */
  const flyttaOverValda = useCallback(async (ids?: Set<string>) => {
    if (lage.fas !== "klar") return;
    const riktning: Riktning = visaTest ? "till_skarp" : "till_test";
    // Ett snapshot av VILKA som är markerade just nu — valda kan ändras under
    // await-kedjan om kunden hinner klicka mer, men resultatlistan ska svara
    // på det urval knappen faktiskt kördes med.
    const markering = ids ?? valda;
    const kandidater = lage.prospekt.filter((p) => markering.has(p.id));
    if (!kandidater.length) return;

    setFlyttar(true);
    setUtfall(null);
    try {
      const resultat: Utfallsrad[] = [];
      for (const p of kandidater) {
        const arTestEllerExempel = p.origin === "test" || p.origin === "example";
        if (riktning === "till_skarp" ? !arTestEllerExempel : arTestEllerExempel) {
          // till_skarp: redan i kundens riktiga lista. till_test: redan
          // oskickbar. Båda hoppas över TYST, ingen rad i resultatlistan —
          // en markerad-men-redan-rätt rad är inget fel.
          continue;
        }
        try {
          // Ifyllnaden gäller bara till_skarp: /degradera tar ingen kropp,
          // och att bli oskickbar har inga fält att fylla i.
          const extra = riktning === "till_skarp" ? ifyllnad[p.id] : undefined;
          const vagsegment = riktning === "till_skarp" ? "befordra" : "degradera";
          const response = await fetch(
            `/api/snajp-support/leads/prospects/${p.id}/${vagsegment}`,
            {
              method: "POST",
              headers: extra ? { "Content-Type": "application/json" } : undefined,
              body: extra
                ? JSON.stringify({
                    orgnr: extra.orgnr || undefined,
                    website: extra.website || undefined,
                    contact_email: extra.contact_email || undefined
                  })
                : undefined
            }
          );
          if (response.ok) {
            resultat.push({ id: p.id, company_name: p.company_name, ok: true, riktning });
            continue;
          }
          const kropp = await readJsonBody<BefordraSvar>(response).catch(() => null);
          const detalj = kropp?.detail;
          const saknas =
            detalj && typeof detalj === "object" && Array.isArray(detalj.saknas)
              ? detalj.saknas
              : [];
          resultat.push({
            id: p.id,
            company_name: p.company_name,
            ok: false,
            riktning,
            saknas: saknas.length
              ? saknas.map(ordagrant)
              : [
                  typeof detalj === "string"
                    ? ordagrant(detalj)
                    : {
                        sv: `Kunde inte flytta (status ${response.status}).`,
                        en: `Could not move (status ${response.status}).`
                      }
                ]
          });
        } catch (error) {
          resultat.push({
            id: p.id,
            company_name: p.company_name,
            ok: false,
            riktning,
            saknas: [ordagrant(felmeddelande(error))]
          });
        }
      }
      setUtfall(resultat);
      setValda(new Set());
      await hamta();
    } finally {
      setFlyttar(false);
    }
  }, [lage, valda, hamta, ifyllnad, visaTest]);

  /**
   * "Skapa utkast för valda" — samma kedja som Bolagssidans "Skapa utkast"
   * (POST /leads/outreach/draft), körd per markerat prospekt i tur och
   * ordning. Oberoende av flytta-riktningen ovan: att skriva ett utkast
   * ändrar ingen origin och rör inte send-guarden.
   *
   * En rad utan mottagaradress kan aldrig bli ett utkast — det stoppas HÄR,
   * innan anropet görs, så att den raden syns som "saknar adress" i stället
   * för att hela satsen misslyckas på fältet som saknades för just den raden.
   */
  const skapaUtkastForValda = useCallback(async () => {
    if (lage.fas !== "klar") return;
    const kandidater = lage.prospekt.filter((p) => valda.has(p.id));
    if (!kandidater.length) return;

    setGenererarUtkast(true);
    setUtkastResultat(null);
    try {
      let offerSummary: string;
      try {
        offerSummary = await hamtaOffertsammanfattning();
      } catch (fel) {
        // Ett hinder som gäller HELA arbetsytan (ingen affärskontext ifylld)
        // — alla markerade rader delar samma orsak, inte en per prospekt.
        setUtkastResultat(
          kandidater.map((p) => ({
            id: p.id,
            company_name: p.company_name,
            ok: false,
            meddelande: ordagrant(felmeddelande(fel))
          }))
        );
        return;
      }

      const resultat: UtkastRad[] = [];
      for (const p of kandidater) {
        if (!p.contact_email) {
          resultat.push({
            id: p.id,
            company_name: p.company_name,
            ok: false,
            meddelande: { sv: "Prospektet saknar en mottagaradress.", en: "The prospect has no recipient address." }
          });
          continue;
        }
        try {
          const response = await fetch("/api/snajp-support/leads/outreach/draft", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              prospect_id: p.id,
              prospect_email: p.contact_email,
              company_name: p.company_name,
              offer_summary: offerSummary,
              // Instruktion till modellen, inte text på skärmen: alltid svenska.
              brief: sv({
                sv: `Skriv ett kort, personligt första mejl till kontaktpersonen på ${p.company_name}. Utgå ifrån poängmotiveringen i researchunderlaget och håll dig till det som redan är känt. Ingen hype, inga superlativ, ren text. Utkastet ska köas för granskning, inte skickas.`,
                en: `Write a short, personal first email to the contact at ${p.company_name}. Start from the score rationale in the research and stick to what is already known. No hype, no superlatives, plain text. The draft is queued for review, not sent.`
              }),
              research_summary: byggForskningssammanfattning(p)
            })
          });
          const kropp = await readJsonBody<{
            job_id?: string;
            fase?: string;
            escalated?: boolean;
            escalation_reason?: string | null;
            body?: string;
            detail?: unknown;
          }>(response).catch(() => null);
          if (response.status === 202 && kropp?.job_id) {
            const klart = await pollaLeadsJobb(kropp.job_id);
            const utkast = klart.result;
            if (klart.status === "completed" && utkast && !utkast.escalated && utkast.body) {
              resultat.push({ id: p.id, company_name: p.company_name, ok: true });
              continue;
            }
            const jobbText = klart.error || utkast?.escalation_reason || utkast?.draft_note;
            resultat.push({
              id: p.id,
              company_name: p.company_name,
              ok: false,
              meddelande:
                klart.fel ??
                (jobbText ? ordagrant(jobbText) : { sv: "Kunde inte skapa utkast.", en: "Could not create a draft." })
            });
            continue;
          }
          if (response.ok && kropp && !kropp.escalated && kropp.body) {
            resultat.push({ id: p.id, company_name: p.company_name, ok: true });
            continue;
          }
          const backendFel = kropp?.escalation_reason || extraheraFelmeddelande(kropp?.detail);
          const meddelande: Localized = backendFel
            ? ordagrant(backendFel)
            : {
                sv: `Kunde inte skapa utkast (status ${response.status}).`,
                en: `Could not create a draft (status ${response.status}).`
              };
          resultat.push({ id: p.id, company_name: p.company_name, ok: false, meddelande });
        } catch (error) {
          resultat.push({
            id: p.id,
            company_name: p.company_name,
            ok: false,
            meddelande: ordagrant(felmeddelande(error))
          });
        }
      }
      setUtkastResultat(resultat);
    } finally {
      setGenererarUtkast(false);
    }
  }, [lage, valda]);

  const processaOmValda = useCallback(async () => {
    if (lage.fas !== "klar") return;
    const kandidater = lage.prospekt.filter((p) => valda.has(p.id));
    if (!kandidater.length) return;

    setProcessarOm(true);
    setUtkastResultat(null);
    try {
      try {
        await hamtaOffertsammanfattning();
      } catch (fel) {
        setUtkastResultat(
          kandidater.map((p) => ({
            id: p.id,
            company_name: p.company_name,
            ok: false,
            meddelande: ordagrant(felmeddelande(fel))
          }))
        );
        return;
      }

      const response = await fetch("/api/snajp-support/leads/prospects/processa-om", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prospect_ids: kandidater.map((p) => p.id),
          scope: "research_and_draft"
        })
      });
      const kropp = await readJsonBody<{
        jobs?: { job_id: string; prospect_id?: string }[];
        detail?: unknown;
      }>(response).catch(() => null);
      if (!response.ok || !kropp?.jobs?.length) {
        const backendFel = extraheraFelmeddelande(kropp?.detail);
        const orsak: Localized = backendFel
          ? ordagrant(backendFel)
          : {
              sv: `Kunde inte bearbeta om (status ${response.status}).`,
              en: `Could not reprocess (status ${response.status}).`
            };
        setUtkastResultat(
          kandidater.map((p) => ({ id: p.id, company_name: p.company_name, ok: false, meddelande: orsak }))
        );
        return;
      }
      const namn = new Map(kandidater.map((p) => [p.id, p.company_name]));
      const resultat: UtkastRad[] = [];
      for (const jobb of kropp.jobs) {
        const namnRad = namn.get(jobb.prospect_id ?? "") ?? jobb.prospect_id ?? text({ sv: "Bolag", en: "Company" });
        const klart = await pollaLeadsJobb(jobb.job_id);
        const id = jobb.prospect_id ?? jobb.job_id;
        if (klart.status === "completed") {
          const note = klart.result?.draft_note;
          resultat.push({
            id,
            company_name: namnRad,
            ok: !note,
            meddelande: note ? ordagrant(note) : undefined
          });
        } else {
          resultat.push({
            id,
            company_name: namnRad,
            ok: false,
            meddelande:
              klart.fel ??
              (klart.error ? ordagrant(klart.error) : { sv: "Bearbetningen misslyckades.", en: "Processing failed." })
          });
        }
      }
      setUtkastResultat(resultat);
      await hamta(true);
    } catch (error) {
      setUtkastResultat(
        kandidater.map((p) => ({
          id: p.id,
          company_name: p.company_name,
          ok: false,
          meddelande: ordagrant(felmeddelande(error))
        }))
      );
    } finally {
      setProcessarOm(false);
    }
  }, [lage, valda, hamta, text]);

  if (lage.fas === "laddar") {
    return <SkeletonRows />;
  }

  if (lage.fas === "ejAktiverad") {
    return <EjAktiverad yta={text({ sv: "Företag", en: "Companies" })} />;
  }

  if (lage.fas === "fel") {
    return (
      <div className="flex items-start gap-3 border-y border-ochre/40 bg-ochre/10 px-4 py-4">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />
        <div className="min-w-0">
          <p className="text-[0.9375rem] font-medium text-ink">{text({ sv: "Bolagen kunde inte hämtas", en: "The companies could not be fetched" })}</p>
          <p className="mt-1 text-[0.9375rem] text-ink-muted">{text(lage.meddelande)}</p>
          <button type="button" onClick={() => void hamta()} className={cn(btnSecondary, btnLiten, "mt-3")}>
            {text({ sv: "Försök igen", en: "Try again" })}
          </button>
        </div>
      </div>
    );
  }

  // "Formuläret ovan" som den gamla tomtexten pekade på finns inte längre här
  // (Discovery.tsx togs bort) — körningen startas från Iris.
  if (!lage.prospekt.length) {
    return (
      <Tomt>
        {text({
          sv: "Inga bolag ännu. Kör Iris för att hitta bolag som matchar er målgrupp.",
          en: "No companies yet. Run Iris to find companies that match your target group."
        })}
      </Tomt>
    );
  }

  // Fas 2 §3, 2.4-UI: testkörningar döljs som default, exempelbolag aldrig.
  const antalTest = lage.prospekt.filter((p) => p.origin === "test").length;
  const synliga = lage.prospekt.filter((p) => visaTest || p.origin !== "test");
  // Se docstringen på flyttaOverValda: visaTest ÄR läget knappen tolkar.
  const riktning: Riktning = visaTest ? "till_skarp" : "till_test";

  return (
    <>
      {(antalTest > 0 || (!demo && valda.size > 0)) && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          {!demo && valda.size > 0 ? (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={flyttar}
                onClick={() => void flyttaOverValda()}
                className={cn(btnSecondary, btnLiten)}
              >
                {flyttar ? text({ sv: "Flyttar…", en: "Moving…" }) : text(flyttaKnappText(riktning, valda.size))}
              </button>
              <button
                type="button"
                disabled={genererarUtkast || processarOm}
                onClick={() => void skapaUtkastForValda()}
                className={cn(btnSecondary, btnLiten)}
              >
                {genererarUtkast
                  ? text({ sv: "Skapar utkast…", en: "Creating drafts…" })
                  : text({ sv: `Skapa utkast för valda (${valda.size})`, en: `Create drafts for selected (${valda.size})` })}
              </button>
              <button
                type="button"
                disabled={genererarUtkast || processarOm}
                onClick={() => void processaOmValda()}
                className={cn(btnSecondary, btnLiten)}
              >
                {processarOm
                  ? text({ sv: "Bearbetar om…", en: "Reprocessing…" })
                  : text({ sv: `Bearbeta om (${valda.size})`, en: `Reprocess (${valda.size})` })}
              </button>
            </div>
          ) : (
            <span />
          )}
          {antalTest > 0 ? (
            // Ett filter i arbetsflödet, inte en inställningsväxel: samma
            // flikspråk som vyflikarna, markerad när testkörningarna syns.
            // Etiketten står still — en switch byter läge, inte namn.
            <button
              type="button"
              role="switch"
              aria-checked={visaTest}
              onClick={() => setVisaTest((v) => !v)}
              className={cn(flik, visaTest ? flikAktiv : flikInaktiv)}
            >
              {text({ sv: `Visa testkörningar (${antalTest})`, en: `Show test runs (${antalTest})` })}
            </button>
          ) : null}
        </div>
      )}

      {utfall && utfall.length > 0 ? (
        <ul className="mb-5 space-y-3 border-y border-ink/15 py-4">
          {utfall.map((rad) => (
            <li key={rad.id} className="text-[0.9375rem] leading-6">
              <span className="font-medium text-ink">{rad.company_name}</span>{" "}
              {rad.ok ? (
                <span className="text-moss">
                  {rad.riktning === "till_skarp"
                    ? text({ sv: "flyttades över till den riktiga listan.", en: "was moved to the live list." })
                    : text({
                        sv: "flyttades till testytan och kan inte längre skickas.",
                        en: "was moved to the test area and can no longer be sent."
                      })}
                </span>
              ) : (
                <span className="text-danger">
                  {text({ sv: "kunde inte flyttas:", en: "could not be moved:" })}{" "}
                  {rad.saknas?.map((s) => text(s)).join(" ")}
                </span>
              )}
              {!rad.ok && rad.riktning === "till_skarp" ? (
                <Ifyllnad
                  id={rad.id}
                  varden={ifyllnad[rad.id] ?? { orgnr: "", website: "", contact_email: "" }}
                  disabled={flyttar}
                  onChange={(varden) =>
                    setIfyllnad((forra) => ({ ...forra, [rad.id]: varden }))
                  }
                  onSubmit={() => void flyttaOverValda(new Set([rad.id]))}
                />
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      {utkastResultat && utkastResultat.length > 0 ? (
        <ul className="mb-5 space-y-2 border-y border-ink/15 py-4">
          {utkastResultat.map((rad) => (
            <li key={rad.id} className="text-[0.9375rem] leading-6">
              <span className="font-medium text-ink">{rad.company_name}</span>{" "}
              {rad.ok ? (
                <span className="text-moss">
                  {text({ sv: "utkast skapat och köat för granskning.", en: "draft created and queued for review." })}
                </span>
              ) : (
                <span className="text-danger">
                  {text({ sv: "inget utkast:", en: "no draft:" })} {rad.meddelande ? text(rad.meddelande) : null}
                </span>
              )}
            </li>
          ))}
        </ul>
      ) : null}

      {synliga.length === 0 ? (
        <Tomt>
          {text({
            sv: `Alla ${antalTest} bolag är just nu testkörningar och döljs. Slå på "Visa testkörningar" ovan för att se dem.`,
            en: `All ${antalTest} companies right now are test runs and are hidden. Turn on "Show test runs" above to see them.`
          })}
        </Tomt>
      ) : (
        <>
          {/* Tabell från md och upp, rader under. Sex kolumner krympta till
              375px blir ~40px styck och därmed oläsliga — se DESIGN.md
              App-familjen.

              `Tabell` ur components/ui.tsx: kolumnlistan byggs med samma
              villkor som cellerna (demo saknar kryssrutor), så colgroup och
              celler kan aldrig peka på olika kolumner. Bredderna summerar
              till 100 % bredvid kryssrutans fasta 44px. */}
          <div className="hidden md:block">
            <Tabell
              ariaLabel={text({ sv: "Bolag", en: "Companies" })}
              minBredd={900}
              kolumner={[
                ...(!demo ? [{ rubrik: text({ sv: "Välj", en: "Select" }), bredd: "44px", srOnly: true }] : []),
                { rubrik: text({ sv: "Bolag", en: "Company" }), bredd: "24%" },
                { rubrik: text({ sv: "Segment", en: "Segment" }), bredd: "14%" },
                { rubrik: text({ sv: "Kontakt", en: "Contact" }), bredd: "18%" },
                { rubrik: text({ sv: "Signal", en: "Signal" }), bredd: "24%" },
                { rubrik: text({ sv: "Poäng", en: "Score" }), bredd: "8%", hoger: true },
                { rubrik: text({ sv: "Status", en: "Status" }), bredd: "12%", hoger: true }
              ]}
            >
              {synliga.map((p) => (
                <tr key={p.id} className={tabellRad}>
                  {!demo ? (
                    <Cell>
                      <input
                        type="checkbox"
                        checked={valda.has(p.id)}
                        onChange={() => vaxlaVal(p.id)}
                        aria-label={text({ sv: `Välj ${p.company_name}`, en: `Select ${p.company_name}` })}
                        className="h-4 w-4 accent-ochre"
                      />
                    </Cell>
                  ) : null}
                  <Cell titel>
                    {/* Ingen länk i demon. Bolagssidan ligger under /dashboard,
                        alltså bakom inloggningen — en besökare som klickar hade
                        mötts av en inloggningsruta mitt i en demo. */}
                    <div className="flex flex-wrap items-center gap-2">
                      {demo ? (
                        <span className="font-semibold">{p.company_name}</span>
                      ) : (
                        <Link href={vag(`/dashboard/companies/${p.id}`)} className="focus-ring font-semibold">
                          {p.company_name}
                        </Link>
                      )}
                      {/* Ett påhittat bolag ska inte gå att ta för en riktig
                          AI-körning — samma Badge som statusen. */}
                      {p.origin === "example" ? <Badge>{text({ sv: "Exempel", en: "Example" })}</Badge> : null}
                      {p.origin === "test" ? <Badge>{text({ sv: "Test", en: "Test" })}</Badge> : null}
                    </div>
                    {/* truncate: i en fast tabell är det cellen som ger med
                        sig, aldrig kolumnen. */}
                    {p.website ? <p className={cn(meta, "mt-1 truncate")}>{p.website}</p> : null}
                  </Cell>
                  <Cell className="text-ink-muted">{segment(p)}</Cell>
                  <Cell>
                    <p>{p.contact_name ?? "–"}</p>
                    {p.contact_email ? (
                      <p className={cn(meta, "mt-1 break-all")}>{p.contact_email}</p>
                    ) : null}
                  </Cell>
                  {/* Två rader i tabellen — hela motiveringen står på
                      bolagssidan, och i title för den som pekar. */}
                  <Cell className="leading-6 text-ink-muted">
                    <span className="line-clamp-2" title={signal(p)}>
                      {signal(p)}
                    </span>
                  </Cell>
                  <Cell hoger>
                    <span className="font-semibold">{poang(p)}</span>
                  </Cell>
                  <Cell hoger>
                    <StatusOrd status={p.status} />
                  </Cell>
                </tr>
              ))}
            </Tabell>
          </div>

          <Radlista className="md:hidden">
            {synliga.map((p) => (
              <Rad key={p.id}>
                <div className="flex items-baseline justify-between gap-3">
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    {!demo ? (
                      <input
                        type="checkbox"
                        checked={valda.has(p.id)}
                        onChange={() => vaxlaVal(p.id)}
                        aria-label={text({ sv: `Välj ${p.company_name}`, en: `Select ${p.company_name}` })}
                        className="h-4 w-4 shrink-0 accent-ochre"
                      />
                    ) : null}
                    {demo ? (
                      <span className="min-w-0 text-[0.9375rem] font-semibold">{p.company_name}</span>
                    ) : (
                      <Link
                        href={vag(`/dashboard/companies/${p.id}`)}
                        className="focus-ring min-w-0 text-[0.9375rem] font-semibold"
                      >
                        {p.company_name}
                      </Link>
                    )}
                    {p.origin === "example" ? <Badge>{text({ sv: "Exempel", en: "Example" })}</Badge> : null}
                  </div>
                  <span className="num shrink-0 text-[0.9375rem] font-semibold">{poang(p)}</span>
                </div>
                <p className={cn(meta, "mt-1")}>{segment(p)}</p>
                <p className="mt-2 line-clamp-2 text-[0.9375rem] leading-6 text-ink-muted">{signal(p)}</p>
                <div className="mt-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                  <span className="text-[0.9375rem] text-ink-muted">{p.contact_name ?? text({ sv: "Ingen kontakt", en: "No contact" })}</span>
                  <StatusOrd status={p.status} />
                </div>
              </Rad>
            ))}
          </Radlista>
        </>
      )}
    </>
  );
}

function Ifyllnad({
  id,
  varden,
  disabled,
  onChange,
  onSubmit
}: Readonly<{
  id: string;
  varden: { orgnr: string; website: string; contact_email: string };
  disabled: boolean;
  onChange: (varden: { orgnr: string; website: string; contact_email: string }) => void;
  onSubmit: () => void;
}>) {
  const { text } = useLocale();
  return (
    <form
      className="mt-3 grid gap-2 sm:grid-cols-3"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <label className={cn(etikett, "block")}>
        {text({ sv: "Organisationsnummer", en: "Company registration number" })}
        <input
          name={`${id}-orgnr`}
          value={varden.orgnr}
          onChange={(event) => onChange({ ...varden, orgnr: event.target.value })}
          placeholder="556824-9022"
          className="focus-ring mt-1 block min-h-11 w-full rounded-input bg-paper2 px-3 text-sm text-ink"
        />
      </label>
      <label className={cn(etikett, "block")}>
        {text({ sv: "Webbplats", en: "Website" })}
        <input
          name={`${id}-website`}
          value={varden.website}
          onChange={(event) => onChange({ ...varden, website: event.target.value })}
          placeholder={text({ sv: "https://bolaget.se", en: "https://company.com" })}
          className="focus-ring mt-1 block min-h-11 w-full rounded-input bg-paper2 px-3 text-sm text-ink"
        />
      </label>
      <label className={cn(etikett, "block")}>
        {text({ sv: "E-post", en: "Email" })}
        <input
          name={`${id}-email`}
          value={varden.contact_email}
          onChange={(event) => onChange({ ...varden, contact_email: event.target.value })}
          placeholder={text({ sv: "info@bolaget.se", en: "info@company.com" })}
          className="focus-ring mt-1 block min-h-11 w-full rounded-input bg-paper2 px-3 text-sm text-ink"
        />
      </label>
      <div className="sm:col-span-3">
        <button type="submit" disabled={disabled} className={cn(btnSecondary, btnLiten)}>
          {text({ sv: "Spara och flytta", en: "Save and move" })}
        </button>
      </div>
    </form>
  );
}

/** Status som Badge: det som väntar på kunden bär ochre-tonen, resten är neutralt. */
function StatusOrd({ status }: Readonly<{ status: string }>) {
  const { text } = useLocale();
  return (
    <Badge tone={AKTIV_STATUS.has(status) ? "warn" : "neutral"}>
      {STATUS_ETIKETT[status] ? text(STATUS_ETIKETT[status]) : status}
    </Badge>
  );
}
