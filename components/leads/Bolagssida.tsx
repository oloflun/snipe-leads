"use client";

import { AlertTriangle, Send } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { PageShell } from "@/components/AppShell";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { EmptyState, SkeletonRows, btnPrimary } from "@/components/ui";
import type { EmailStudioData } from "@/lib/data/emails";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { sv, useLocale, type Locale, type Localized } from "@/lib/i18n";
import { lasOffertForUtkast } from "@/lib/actions/affarskontext";
import { ICP_ETIKETTER } from "@/lib/leads/icpLabels";
import { kriterier } from "@/lib/prospekt";
import { cn } from "@/lib/utils";

/**
 * Bolagssidan — ETT prospekt, med källorna som motiverade poängen.
 *
 * ## Vad den ersatte
 *
 * `CompanyDetailView` läste `findCompany(id)` ur `lib/mock-data.ts`. Den
 * funktionen faller tillbaka på `companies[0]` när id:t inte finns, alltså
 * Byggkompaniet Syd. Ett klick på ett riktigt prospekt visade därför ett
 * PÅHITTAT bolags researchpromemoria — signaler, källor, storlek, allt — under
 * det riktiga bolagets rubrik. En 404 hade varit ärligare; det här såg
 * komplett ut.
 *
 * ## Poängen redovisas, inte bara siffran
 *
 * `score_breakdown` sparas renderad i databasen (migration 031) av exakt det
 * skäl som gäller här: "84/100" utan motivering går inte att lita på, och
 * poängen kan inte räknas om i efterhand eftersom kundens ICP kan ha ändrats
 * sedan körningen. Därför listas kriterierna som de såg ut DÅ.
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
  orgnr: string | null;
  website: string | null;
  anstallda: number | null;
  score_total: number | null;
  icp_fit: number | null;
  qualified: boolean | null;
  disqualifiers: string[] | null;
  // Avsiktligt otypad: fältet HAR nått hit som en sträng. Se lib/prospekt.ts.
  score_breakdown: unknown;
  created_at: string | null;
};

type Lage =
  | { fas: "laddar" }
  | { fas: "saknas" }
  | { fas: "fel"; meddelande: Localized }
  | { fas: "klar"; prospekt: Prospekt; kallor: string[] };

/**
 * Utkastet till DET HÄR prospektet. Egen state-maskin, skild från `Lage`
 * ovan: sidan kan vara klarladdad utan att vi vet ännu om ett utkast finns.
 *
 * "kontrollerar" täcker både "vi har inte frågat än" och "vi frågar just nu"
 * — samma skäl som SkeletonRows-mönstret i `Lage`, en lucka mellan de två
 * hade gett en flimrande "Skapa utkast"-knapp som hann visas innan svaret om
 * ett befintligt utkast kommit tillbaka.
 */
type UtkastLage =
  | { fas: "kontrollerar" }
  | { fas: "ingen" }
  | { fas: "letar-kontakt" }
  | { fas: "skapar" }
  | { fas: "fel"; meddelande: Localized }
  | { fas: "klar"; data: EmailStudioData; queueItemId: string | null };

/** Så som `/api/leads/queue` (send_queue join outreach_messages) svarar. */
type KöItem = {
  id: string;
  subject?: string | null;
  body?: string | null;
  prospect_email?: string | null;
  company_name?: string | null;
};

const T = {
  tjanstenSvararInte: {
    sv: "Tjänsten svarar inte. Försök igen om en minut.",
    en: "The service is not responding. Try again in a minute."
  },
  tomtSvar: { sv: "Backenden svarade utan innehåll.", en: "The backend replied without content." },
  kundeInteNaServern: { sv: "Kunde inte nå servern.", en: "Could not reach the server." },
  utkastTogForLang: { sv: "Utkastet tog för lång tid.", en: "The draft took too long." },
  utkastKundeInte: { sv: "Utkastet kunde inte skrivas.", en: "The draft could not be written." },
  utkastInteKlart: {
    sv: "Utkastet blev inte klart. Försök igen om en stund.",
    en: "The draft was not finished. Try again in a moment."
  },
  ingenKontaktadress: {
    sv: "Iris hittade ingen kontaktadress på bolagets sajt. Försök igen om en stund, eller komplettera bolaget med en adress.",
    en: "Iris found no contact address on the company's site. Try again in a moment, or add an address to the company."
  },
  hamtarBolaget: { sv: "Hämtar bolaget…", en: "Loading the company…" },
  bolagetFinnsInte: { sv: "Bolaget finns inte", en: "Company not found" },
  ingetSadantBolag: { sv: "Hittade inget sådant bolag", en: "No such company found" },
  tillBolagen: { sv: "Till bolagen", en: "Back to companies" },
  bolagetKundeInte: { sv: "Bolaget kunde inte hämtas", en: "Could not load the company" },
  forsokIgen: { sv: "Försök igen", en: "Try again" },
  score: { sv: "Score", en: "Score" },
  diskvalificerad: { sv: "diskvalificerad", en: "disqualified" },
  kvalificerad: { sv: "kvalificerad", en: "qualified" },
  anstallda: { sv: "Anställda", en: "Employees" },
  orgnrSaknas: { sv: "org.nr saknas", en: "no org. no." },
  kallor: { sv: "Källor", en: "Sources" },
  status: { sv: "Status", en: "Status" },
  saRaknades: { sv: "Så räknades poängen", en: "How the score was calculated" },
  vikt: { sv: "vikt", en: "weight" },
  ingenMotivering: { sv: "Ingen poängmotivering sparad.", en: "No score reasoning saved." },
  kontakt: { sv: "Kontakt", en: "Contact" },
  ingenKontaktperson: { sv: "Ingen kontaktperson hittad", en: "No contact person found" },
  ingaKallor: { sv: "Inga källor sparade.", en: "No sources saved." },
  mejlutkast: { sv: "Mejlutkast", en: "Email draft" },
  loggaIn: { sv: "Logga in för att skapa utkast", en: "Log in to create drafts" },
  ingetUtkast: { sv: "Inget utkast ännu.", en: "No draft yet." },
  skapaUtkast: { sv: "Skapa utkast", en: "Create draft" },
  letarKontakt: {
    sv: "Iris letar kontaktadress på bolagets sajt … Det tar ungefär en minut, och utkastet skrivs direkt efteråt.",
    en: "Iris is looking for a contact address on the company's site … It takes about a minute, and the draft is written right after."
  },
  skriverUtkastet: { sv: "Skriver utkastet…", en: "Writing the draft…" },
  andringarSparasInte: {
    sv: "Ändringar ovan sparas inte. Godkänn skickar det sparade utkastet.",
    en: "Changes above are not saved. Approve sends the saved draft."
  },
  godkant: { sv: "Godkänt. Utkastet ligger nu i sändkön.", en: "Approved. The draft is now in the send queue." },
  godkanner: { sv: "Godkänner…", en: "Approving…" },
  godkannOchSkicka: { sv: "Godkänn och skicka", en: "Approve and send" },
  godkannIGranskning: { sv: "Godkänn i Iris › Granskning.", en: "Approve in Iris › Review." },
  skrivAutomatiskt: { sv: "Skriv utkast automatiskt framöver", en: "Write drafts automatically from now on" },
  redanPa: { sv: "(redan på)", en: "(already on)" },
  skickaAutomatiskt: {
    sv: "…och skickar automatiskt, utan granskning?",
    en: "…and send automatically, without review?"
  },
  sparat: { sv: "Sparat.", en: "Saved." },
  exempel: { sv: "Exempel", en: "Example" }
} satisfies Record<string, Localized>;

/** Samma text på båda språken: serverns egna felmeddelanden, som redan är färdiga. */
function samma(text: string): Localized {
  return { sv: text, en: text };
}

/**
 * Språket för fetch-hjälparen, som anropas utanför komponenten och inte kan
 * använda useLocale. LocaleProvider (lib/i18n.tsx) håller `<html lang>` i takt
 * med valet, så attributet är samma källa som hooken läser.
 */
function sprak(): Locale {
  return typeof document !== "undefined" && document.documentElement.lang === "en" ? "en" : "sv";
}

/**
 * Anrop mot snajp-support med läsbar felhantering.
 *
 * Speglar `anropa()` i LeadsRunForm.tsx med flit i stället för att delas: en
 * gemensam modul hade krävt att båda formen och den här sidan importerade
 * samma hjälpfunktion för en sak som är fem rader, och skillnaden mellan de
 * två anropsplatserna (formulärets `LeadsSvar & { error }`-typ mot den här
 * sidans specifika svarsformer) hade ändå tvingat fram generics på båda
 * ställena. Går de isär i framtiden är det värt att bryta ut då.
 */
async function snajpAnrop<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/snajp-support${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init
  });
  const kropp = (await readJsonBody<T & { error?: string; detail?: unknown }>(response)) ?? ({} as T);
  if (!response.ok) {
    const k = kropp as { error?: string; detail?: unknown };
    // Pydantics 422 lägger en LISTA av valideringsfel i `detail`; en 503/422
    // från en handskriven HTTPException lägger en STRÄNG där. Ett rakt
    // `new Error(detail)` renderar "[object Object]" för listfallet.
    const detaljtext = Array.isArray(k.detail)
      ? k.detail
          .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
          .join("; ")
      : typeof k.detail === "string"
        ? k.detail
        : undefined;
    const avvisat: Localized = {
      sv: `Anropet avvisades (${response.status}).`,
      en: `The request was rejected (${response.status}).`
    };
    throw new Error(detaljtext ?? k.error ?? avvisat[sprak()]);
  }
  return kropp;
}

/** Kriterierna som redan visas under "Så räknades poängen", som forskningsunderlag. */
function byggForskningssammanfattning(p: Prospekt): string {
  return kriterier(p.score_breakdown)
    .map((k) => `${k.etikett} (${k.utfall})${k.motivering ? `: ${k.motivering}` : ""}`)
    .join("\n")
    .slice(0, 8000);
}

/** Den starkaste träffen som "signalen" i Email Studio-kontexten. Ingen träff, inget påhitt. */
function harledSignal(p: Prospekt): string | null {
  const lista = kriterier(p.score_breakdown);
  const bast = lista.find((k) => k.utfall !== "miss") ?? lista[0];
  if (!bast) return null;
  return bast.motivering ? `${bast.etikett}: ${bast.motivering}` : bast.etikett;
}

function byggEmailStudioData(
  p: Prospekt,
  subject: string,
  body: string,
  offerSummary: string | null,
  queueItemId: string | null
): EmailStudioData {
  return {
    source: "database",
    // Rörs inte: business_contexts-tabellen `EmailStudioData.businessContext`
    // normalt bär hör till en helt annan databas (Next-appens egen, se
    // lib/workspace.ts) än prospektet (snajp-support). `offer` bär
    // erbjudandetexten i stället, hämtad ur snajp-supports
    // product_marketing-dokument — se hamtaOffertsammanfattning nedan.
    businessContext: null,
    email: {
      id: queueItemId ?? p.id,
      subject,
      body,
      variantLength: "medium",
      variantType: "cold_outreach",
      status: "draft",
      companyId: p.id,
      contactId: null,
      companyName: p.company_name,
      signal: harledSignal(p),
      offer: offerSummary,
      cta: null,
      contactName: p.contact_name
    }
  };
}

/**
 * Erbjudandetexten `offer_summary` kräver. Prospektet självt bär ingen —
 * det är inte prospektets fält, det är TENANTENS (vad DE säljer). Källan är
 * kontextdokumentet `product_marketing`, samma dokument agentens egen
 * kontextpaket (`build_context_pack`) läser.
 *
 * Kastar med ett läsbart fel i stället för att skicka en tom eller påhittad
 * sträng till outreach/draft — se rapportens avsnitt om saknat UI-data.
 */
async function hamtaOffertsammanfattning(): Promise<string> {
  return lasOffertForUtkast();
}

async function pollaLeadsJobb(jobId: string, locale: Locale): Promise<{
  status?: string;
  error?: string;
  result?: {
    body?: string;
    subject?: string;
    escalated?: boolean;
    escalation_reason?: string | null;
    queue_item_id?: string | null;
  };
}> {
  for (let forsok = 0; forsok < 90; forsok += 1) {
    await new Promise((r) => setTimeout(r, forsok < 5 ? 800 : 2000));
    const jobb = await snajpAnrop<{
      status?: string;
      error?: string;
      result?: {
        body?: string;
        subject?: string;
        escalated?: boolean;
        escalation_reason?: string | null;
        queue_item_id?: string | null;
      };
    }>("/leads/jobb/" + encodeURIComponent(jobId), { method: "GET" });
    if (jobb.status === "completed" || jobb.status === "failed") {
      return jobb;
    }
  }
  return { status: "timeout", error: T.utkastTogForLang[locale] };
}

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

export function Bolagssida({ id, demo = false }: Readonly<{ id: string; demo?: boolean }>) {
  const { locale, text } = useLocale();
  const [lage, setLage] = useState<Lage>({ fas: "laddar" });
  const [utkastLage, setUtkastLage] = useState<UtkastLage>({ fas: "kontrollerar" });
  // "Godkänn och skicka"-knappen och uppföljningsfrågan efteråt — skilda från
  // utkastLage för att ett lyckat godkännande inte ska tvinga hela
  // draft-sektionen (editorn inkluderad) att montera om.
  const [godkant, setGodkant] = useState(false);
  const [godkannBusy, setGodkannBusy] = useState(false);
  const [godkannFel, setGodkannFel] = useState<string | null>(null);
  // Uppföljningsfrågan (5.6). "Skriver utkast automatiskt" har ingen lägre
  // nivå att stänga av mot i backenden (draft ÄR golvet, se
  // app/leads/autonomy.py) — kryssrutan står därför fast förkryssad och
  // skickar ingen egen PUT. "Skickar automatiskt" är den enda som faktiskt
  // ändrar autonomy, och den kan gå från true till false igen om backendens
  // kan_aktivera_auto_send-grind avvisar valet.
  const [autoSkicka, setAutoSkicka] = useState(false);
  const [autonomiSparar, setAutonomiSparar] = useState(false);
  const [autonomiFel, setAutonomiFel] = useState<string | null>(null);
  const [autonomiSparad, setAutonomiSparad] = useState(false);
  const vag = useArbetsvag();

  /**
   * 5.5: läsvägen som ska hindra en omladdning från att tappa ett utkast.
   *
   * GET /leads/prospects/{id}/utkast (byggd i samma fas) svarar med senaste
   * utkastet för prospektet + kö-id:t när det väntar på granskning. Kö-id:t
   * kan vara null för ett redan godkänt/avvisat utkast — då visas texten
   * men godkännandeknappen får ingenting att peka på, vilket är rätt.
   */
  const kontrolleraBefintligtUtkast = useCallback(async (p: Prospekt) => {
    setUtkastLage({ fas: "kontrollerar" });
    try {
      const svar = await snajpAnrop<{
        utkast?: { id: string; subject?: string | null; body?: string | null } | null;
        queue_item_id?: string | null;
      }>(`/leads/prospects/${p.id}/utkast`);
      if (!svar.utkast?.body) {
        setUtkastLage({ fas: "ingen" });
        return;
      }
      // Erbjudandetexten är inte en del av utkastsvaret. Ett misslyckat
      // hämtningsförsök här ska inte dölja ett utkast som faktiskt finns —
      // bara lämna "offer" tomt i editorns kontext.
      const offerSummary = await hamtaOffertsammanfattning().catch(() => null);
      setUtkastLage({
        fas: "klar",
        data: byggEmailStudioData(
          p,
          svar.utkast.subject || `Till ${p.company_name}`,
          svar.utkast.body,
          offerSummary,
          svar.utkast.id
        ),
        queueItemId: svar.queue_item_id ?? null
      });
    } catch {
      // Läsvägen är inte kritisk för vyn — samma resonemang som
      // LeadsControls: ett fel här ska inte hindra "Skapa utkast" från att
      // visas.
      setUtkastLage({ fas: "ingen" });
    }
  }, []);

  const hamta = useCallback(async () => {
    setLage({ fas: "laddar" });
    setUtkastLage({ fas: "kontrollerar" });
    setGodkant(false);
    setGodkannFel(null);
    setAutoSkicka(false);
    setAutonomiSparad(false);
    setAutonomiFel(null);

    if (demo) {
      // Demon har ingen egen bolagssida-endpoint; prospektet plockas ur samma
      // lista som registret visar. Hittas det inte är det ett riktigt "saknas"
      // och inte ett tyst första-bolag — det var hela buggen.
      const svar = demoOversiktSvar("/leads/prospects") as { prospects?: Prospekt[] } | undefined;
      const träff = svar?.prospects?.find((p) => p.id === id);
      if (träff) {
        setLage({ fas: "klar", prospekt: träff, kallor: [] });
        // Demoprospekten bär inga färdiga utkast (se lib/demo/oversikt.ts) —
        // ett påstått befintligt utkast här hade varit precis den sortens
        // påhitt DESIGN.md:s hederlighetsregel förbjuder.
        setUtkastLage({ fas: "ingen" });
      } else {
        setLage({ fas: "saknas" });
      }
      return;
    }

    try {
      const response = await fetch(
        `/api/snajp-support/leads/prospects/${encodeURIComponent(id)}`,
        { cache: "no-store" }
      );
      if (response.status === 404) {
        setLage({ fas: "saknas" });
        return;
      }
      if (!response.ok) {
        setLage({
          fas: "fel",
          meddelande:
            response.status >= 500
              ? T.tjanstenSvararInte
              : {
                  sv: `Kunde inte hämta bolaget (status ${response.status}).`,
                  en: `Could not load the company (status ${response.status}).`
                }
        });
        return;
      }
      const kropp = await readJsonBody<{
        prospect?: Prospekt;
        sources?: string[];
        offline?: boolean;
      }>(response);
      if (!kropp?.prospect || kropp.offline) {
        setLage({ fas: "fel", meddelande: T.tomtSvar });
        return;
      }
      setLage({ fas: "klar", prospekt: kropp.prospect, kallor: kropp.sources ?? [] });
      void kontrolleraBefintligtUtkast(kropp.prospect);
    } catch (error) {
      setLage({
        fas: "fel",
        meddelande: error instanceof Error ? samma(error.message) : T.kundeInteNaServern
      });
    }
  }, [id, demo, kontrolleraBefintligtUtkast]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  /** 5.2/5.3: "Skapa utkast" — anropar den riktiga kedjan, inte studions egen route. */
  const skapaUtkast = useCallback(async () => {
    if (lage.fas !== "klar") return;
    let p = lage.prospekt;
    if (!p.contact_email) {
      // Ingen återvändsgränd ("Mottagaradress saknas."): starta kontaktjakten
      // — processa-om kör researchen som skrapar bolagets kontakt-/om-oss-
      // sidor och skriver kontaktfälten — och fortsätt själv när adressen
      // finns. Samma flöde som tvillingen IrisBolag.tsx.
      setUtkastLage({ fas: "letar-kontakt" });
      try {
        await snajpAnrop("/leads/prospects/processa-om", {
          method: "POST",
          body: JSON.stringify({ prospect_ids: [p.id], scope: "research" })
        });
        let hittad: Prospekt | null = null;
        for (let forsok = 0; forsok < 24 && !hittad; forsok += 1) {
          await new Promise((r) => setTimeout(r, 5_000));
          const kropp = await snajpAnrop<{ prospect?: Prospekt }>(
            `/leads/prospects/${encodeURIComponent(p.id)}`
          );
          if (kropp.prospect?.contact_email) hittad = kropp.prospect;
        }
        if (!hittad) {
          setUtkastLage({ fas: "fel", meddelande: T.ingenKontaktadress });
          return;
        }
        p = hittad;
        setLage({ fas: "klar", prospekt: hittad, kallor: lage.kallor });
      } catch (cause) {
        setUtkastLage({ fas: "fel", meddelande: samma(felmeddelande(cause)) });
        return;
      }
    }

    setUtkastLage({ fas: "skapar" });
    try {
      const offerSummary = await hamtaOffertsammanfattning();
      const koat = await snajpAnrop<{
        job_id?: string;
        fase?: string;
        escalated?: boolean;
        escalation_reason?: string | null;
        subject?: string;
        body?: string;
        queue_item_id?: string | null;
      }>("/leads/outreach/draft", {
        method: "POST",
        body: JSON.stringify({
          prospect_id: p.id,
          prospect_email: p.contact_email,
          company_name: p.company_name,
          offer_summary: offerSummary,
          // Agentens instruktion, inte copy: alltid svenska, så att mejlet till
          // det svenska bolaget blir svenskt oavsett gränssnittets språk.
          brief: sv({
            sv: `Skriv ett kort, personligt första mejl till kontaktpersonen på ${p.company_name}. Utgå ifrån poängmotiveringen i researchunderlaget och håll dig till det som redan är känt. Ingen hype, inga superlativ, ren text. Utkastet ska köas för granskning, inte skickas.`,
            en: `Write a short, personal first email to the contact person at ${p.company_name}. Start from the score reasoning in the research and stick to what is already known. No hype, no superlatives, plain text. The draft is queued for review, not sent.`
          }),
          research_summary: byggForskningssammanfattning(p),
          // OutreachDraftRequest.research_evidence har max_length 60 poster.
          research_evidence: lage.kallor.slice(0, 60)
        })
      });

      let svar = koat;
      if (koat.job_id && (koat.fase === "skriver" || !koat.body)) {
        const klart = await pollaLeadsJobb(koat.job_id, locale);
        if (klart.status !== "completed" || !klart.result) {
          throw new Error(klart.error || text(T.utkastKundeInte));
        }
        svar = klart.result;
      }

      if (svar.escalated || !svar.body) {
        setUtkastLage({
          fas: "fel",
          meddelande: svar.escalation_reason ? samma(svar.escalation_reason) : T.utkastInteKlart
        });
        return;
      }

      setUtkastLage({
        fas: "klar",
        data: byggEmailStudioData(
          p,
          svar.subject || `Till ${p.company_name}`,
          svar.body,
          offerSummary,
          svar.queue_item_id ?? null
        ),
        queueItemId: svar.queue_item_id ?? null
      });
    } catch (cause) {
      setUtkastLage({ fas: "fel", meddelande: samma(felmeddelande(cause)) });
    }
  }, [lage, locale, text]);

  /** 5.6: "Godkänn och skicka" — släpper utkastet till schemaläggaren. */
  const godkannOchSkicka = useCallback(async () => {
    if (utkastLage.fas !== "klar" || !utkastLage.queueItemId) return;
    setGodkannBusy(true);
    setGodkannFel(null);
    try {
      await snajpAnrop(`/leads/queue/${encodeURIComponent(utkastLage.queueItemId)}/approve`, {
        method: "POST"
      });
      setGodkant(true);
    } catch (cause) {
      setGodkannFel(felmeddelande(cause));
    } finally {
      setGodkannBusy(false);
    }
  }, [utkastLage]);

  /**
   * Uppföljningsfrågans andra kryssruta. Reaktivt avstängd i stället för
   * proaktivt: `GET /api/leads/config` exponerar inte kan_aktivera_auto_send
   * -beslutet i dag (bara PUT-handlern kontrollerar det, se rapporten) — så
   * i stället för att gissa oss till om valet är tillåtet, försöker vi och
   * visar backendens egna hinder-text om den säger nej.
   */
  const hanteraAutoSkicka = useCallback(async (nästa: boolean) => {
    setAutoSkicka(nästa);
    setAutonomiSparar(true);
    setAutonomiFel(null);
    setAutonomiSparad(false);
    try {
      await snajpAnrop("/leads/config", {
        method: "PUT",
        body: JSON.stringify({ autonomy: nästa ? "auto_send" : "draft" })
      });
      setAutonomiSparad(true);
    } catch (cause) {
      setAutonomiFel(felmeddelande(cause));
      setAutoSkicka(false);
    } finally {
      setAutonomiSparar(false);
    }
  }, []);

  if (lage.fas === "laddar") {
    return (
      <PageShell title={text(T.hamtarBolaget)}>
        <SkeletonRows />
      </PageShell>
    );
  }

  if (lage.fas === "saknas") {
    return (
      <PageShell title={text(T.bolagetFinnsInte)}>
        <EmptyState title={text(T.ingetSadantBolag)} />
        <Link href={vag("/dashboard/companies")} className={cn(btnPrimary, "mt-6")}>
          {text(T.tillBolagen)}
        </Link>
      </PageShell>
    );
  }

  if (lage.fas === "fel") {
    return (
      <PageShell title={text(T.bolagetKundeInte)}>
        <div className="flex items-start gap-3 border-y border-ochre/40 bg-ochre/10 px-4 py-4">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />
          <div className="min-w-0">
            <p className="text-sm text-ink-muted">{text(lage.meddelande)}</p>
            <button
              type="button"
              onClick={() => void hamta()}
              className="focus-ring mt-3 inline-flex min-h-9 items-center rounded-input bg-paper2 px-3 text-[13px] font-medium"
            >
              {text(T.forsokIgen)}
            </button>
          </div>
        </div>
      </PageShell>
    );
  }

  const { prospekt: p, kallor } = lage;
  const poang =
    typeof p.score_total === "number"
      ? `${p.score_total}/100`
      : typeof p.icp_fit === "number"
        ? `${Math.round(p.icp_fit * 100)}/100`
        : "—";

  return (
    <PageShell
      title={p.company_name}
      action={
        // Länken till den frikopplade Email-studion är BORTA (Fas 4,
        // 2026-08-29): mejlutkastet renderas numera inline i den här sidan,
        // se sektionen "Mejlutkast" nedan. Kvar i action-sloten står bara
        // märkningen — samma stil som statusetiketterna i Bolagsregister
        // (kicker/mineral), inte en egen badgestil.
        p.origin === "example" ? <span className="kicker text-mineral">{text(T.exempel)}</span> : null
      }
    >
      {/* Vad kickern och beskrivningen bar: bransch/ort och webbplats,
          nu en rad i brödtextstorlek direkt under rubriken (F-016). */}
      {[p.sni, p.ort].filter(Boolean).join(" · ") || p.website ? (
        <p className="-mt-1 mb-8 text-[0.9375rem] text-ink-muted">
          {[p.sni, p.ort].filter(Boolean).join(" · ")}
          {p.website ? (p.sni || p.ort ? " · " : "") + p.website : ""}
        </p>
      ) : null}

      <div className="grid grid-cols-12 gap-x-8 gap-y-10">
        <dl className="col-span-12 grid grid-cols-12 gap-x-8 gap-y-8">
          <Matt
            label={text(T.score)}
            value={poang}
            detail={p.qualified === false ? text(T.diskvalificerad) : text(T.kvalificerad)}
          />
          <Matt
            label={text(T.anstallda)}
            value={p.anstallda == null ? "—" : String(p.anstallda)}
            detail={p.orgnr ? text({ sv: `org.nr ${p.orgnr}`, en: `org. no. ${p.orgnr}` }) : text(T.orgnrSaknas)}
          />
          <Matt label={text(T.kallor)} value={String(kallor.length)} />
          <Matt label={text(T.status)} value={STATUS_ETIKETT[p.status]?.[locale] ?? p.status} />
        </dl>

        <section className="col-span-12 md:col-span-7">
          <h2 className="kicker text-mineral">{text(T.saRaknades)}</h2>
          {kriterier(p.score_breakdown).length ? (
            <ul className="mt-5 divide-y divide-ink/15 border-y border-ink/15">
              {kriterier(p.score_breakdown).map((k, i) => (
                <li key={`${k.nyckel ?? k.etikett}-${i}`} className="py-4">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <p className="text-[15px] font-medium">{k.etikett}</p>
                    <span
                      className={cn(
                        "kicker",
                        k.hart && k.utfall === "miss" ? "text-danger" : "text-mineral"
                      )}
                    >
                      {k.utfall}
                      {typeof k.vikt === "number" ? ` · ${text(T.vikt)} ${k.vikt}` : ""}
                    </span>
                  </div>
                  {k.motivering ? (
                    <p className="mt-1.5 max-w-[65ch] text-[15px] leading-6 text-ink-muted">
                      {k.motivering}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-5 border-y border-ink/15 py-4 text-[15px] text-ink-muted">
              {text(T.ingenMotivering)}
            </p>
          )}

          {p.disqualifiers?.length ? (
            <div className="mt-8">
              <h2 className="kicker text-mineral">{ICP_ETIKETTER.deal_breakers.label}</h2>
              <ul className="mt-4 space-y-2">
                {p.disqualifiers.map((skäl) => (
                  <li key={skäl} className="border-l-2 border-danger pl-3 text-[15px] text-ink-muted">
                    {skäl}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>

        <section className="col-span-12 md:col-span-5">
          <h2 className="kicker text-mineral">{text(T.kontakt)}</h2>
          <div className="mt-4 border-y border-ink/15 py-4">
            <p className="text-[15px]">{p.contact_name ?? text(T.ingenKontaktperson)}</p>
            {p.contact_email ? (
              <p className="mt-1 break-all text-sm text-ink-muted">{p.contact_email}</p>
            ) : null}
          </div>

          <h2 className="kicker mt-8 text-mineral">{text(T.kallor)}</h2>
          {kallor.length ? (
            <ul className="mt-4 space-y-2">
              {kallor.map((url) => (
                <li key={url}>
                  <a
                    href={url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="focus-ring break-all text-sm text-ink-muted underline decoration-ink/25 underline-offset-4"
                  >
                    {url}
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-[15px] text-ink-muted">{text(T.ingaKallor)}</p>
          )}
        </section>

        {/* Fas 4 (2026-08-29): Email-studion flyttade in i leaden. Ersätter
            den gamla "Skriv mejl ↗"-länken till den frikopplade, generiska
            studion — den kunde bara visa E-Tech-exemplet, oavsett vilket
            bolag man tittade på. */}
        <section className="col-span-12 border-t border-ink/15 pt-8">
          <h2 className="kicker text-mineral">{text(T.mejlutkast)}</h2>

          {demo ? (
            <div className="mt-5 rounded-card bg-paper2/60 p-5">
              <Link href="/login" className={btnPrimary}>
                {text(T.loggaIn)}
              </Link>
            </div>
          ) : (
            <div className="mt-5">
              {utkastLage.fas === "kontrollerar" ? (
                <div className="h-16 animate-pulse border-t border-ink/15 bg-ink/[0.03]" />
              ) : null}

              {utkastLage.fas === "ingen" ? (
                <div>
                  <p className="text-[15px] leading-7 text-ink-muted">{text(T.ingetUtkast)}</p>
                  <button type="button" onClick={() => void skapaUtkast()} className={cn(btnPrimary, "mt-4")}>
                    {text(T.skapaUtkast)}
                  </button>
                </div>
              ) : null}

              {utkastLage.fas === "letar-kontakt" ? (
                <p className="text-[14px] leading-6 text-ink-subtle">
                  {text(T.letarKontakt)}
                </p>
              ) : null}

              {utkastLage.fas === "skapar" ? (
                <p className="text-[14px] text-ink-subtle">{text(T.skriverUtkastet)}</p>
              ) : null}

              {utkastLage.fas === "fel" ? (
                <div className="flex items-start gap-3 border-y border-ochre/40 bg-ochre/10 px-4 py-4">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />
                  <div className="min-w-0">
                    <p className="text-sm text-ink-muted">{text(utkastLage.meddelande)}</p>
                    <button
                      type="button"
                      onClick={() => void skapaUtkast()}
                      className="focus-ring mt-3 inline-flex min-h-9 items-center rounded-input bg-paper2 px-3 text-[13px] font-medium"
                    >
                      {text(T.forsokIgen)}
                    </button>
                  </div>
                </div>
              ) : null}

              {utkastLage.fas === "klar" ? (
                <div>
                  <EmailStudioEditor data={utkastLage.data} compact />

                  {/* Redigeringar ovan lever bara i webbläsaren. Ingen väg
                      sparar dem tillbaka till outreach_messages innan
                      godkännande — se rapportens avsnitt om saknad
                      sparväg. Utan raden hade knappen sett ut att skicka det
                      som står i fälten just nu, vilket den inte gör. */}
                  <p className="mt-4 max-w-[65ch] text-[13px] leading-6 text-ink-subtle">
                    {text(T.andringarSparasInte)}
                  </p>

                  <div className="mt-5 border-t border-ink/15 pt-5">
                    {godkant ? (
                      <p role="status" className="text-[15px] text-moss">
                        {text(T.godkant)}
                      </p>
                    ) : (
                      <>
                        <button
                          type="button"
                          disabled={godkannBusy || !utkastLage.queueItemId}
                          onClick={() => void godkannOchSkicka()}
                          className={cn(btnPrimary, "disabled:cursor-wait disabled:opacity-60")}
                        >
                          <Send className="h-4 w-4" aria-hidden />
                          {godkannBusy ? text(T.godkanner) : text(T.godkannOchSkicka)}
                        </button>
                        {!utkastLage.queueItemId ? (
                          <p className="mt-3 text-[13px] leading-6 text-ink-subtle">
                            {text(T.godkannIGranskning)}
                          </p>
                        ) : null}
                        {godkannFel ? (
                          <p role="alert" className="mt-3 max-w-[65ch] text-[14px] text-danger">
                            {godkannFel}
                          </p>
                        ) : null}
                      </>
                    )}

                    {/* 5.6: uppföljningsfrågan, bara efter ett lyckat godkännande. */}
                    {godkant ? (
                      <div className="mt-6 max-w-[65ch] space-y-4 rounded-card bg-paper2/60 p-5">
                        <label className="flex items-start gap-3">
                          <input
                            type="checkbox"
                            checked
                            readOnly
                            disabled
                            className="mt-1 h-4 w-4 accent-ochre"
                          />
                          <span className="text-[14px] leading-6 text-ink-muted">
                            {text(T.skrivAutomatiskt)}{" "}
                            <span className="text-ink-subtle">{text(T.redanPa)}</span>
                          </span>
                        </label>

                        <label className="flex items-start gap-3">
                          <input
                            type="checkbox"
                            checked={autoSkicka}
                            disabled={autonomiSparar}
                            onChange={(event) => void hanteraAutoSkicka(event.target.checked)}
                            className="mt-1 h-4 w-4 accent-ochre disabled:cursor-wait"
                          />
                          <span className="text-[14px] leading-6 text-ink-muted">
                            {text(T.skickaAutomatiskt)}
                          </span>
                        </label>

                        {autonomiFel ? (
                          <p role="alert" className="text-[13px] leading-6 text-danger">
                            {autonomiFel}
                          </p>
                        ) : null}
                        {autonomiSparad ? (
                          <p role="status" className="text-[13px] text-moss">
                            {text(T.sparat)}
                          </p>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </section>
      </div>
    </PageShell>
  );
}

function Matt({
  label,
  value,
  detail
}: Readonly<{ label: string; value: string; detail?: string }>) {
  return (
    <div className="col-span-6 border-t border-ink/15 pt-4 md:col-span-3">
      <dt className="kicker text-mineral">{label}</dt>
      <dd className="num mt-3 text-[1.75rem] font-semibold tabular-nums tracking-[-0.02em]">
        {value}
      </dd>
      {detail ? <p className="mt-2 text-[14px] leading-6 text-ink-muted">{detail}</p> : null}
    </div>
  );
}
