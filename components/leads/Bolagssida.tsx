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
  | { fas: "fel"; meddelande: string }
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
  | { fas: "skapar" }
  | { fas: "fel"; meddelande: string }
  | { fas: "klar"; data: EmailStudioData; queueItemId: string | null };

/** Så som `/api/leads/queue` (send_queue join outreach_messages) svarar. */
type KöItem = {
  id: string;
  subject?: string | null;
  body?: string | null;
  prospect_email?: string | null;
  company_name?: string | null;
};

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
    throw new Error(detaljtext ?? k.error ?? `Anropet avvisades (${response.status}).`);
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
  const bäst = lista.find((k) => k.utfall !== "miss") ?? lista[0];
  if (!bäst) return null;
  return bäst.motivering ? `${bäst.etikett}: ${bäst.motivering}` : bäst.etikett;
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
  const svar = await snajpAnrop<{ docs?: { content?: string }[] }>(
    "/leads/context-docs?kind=product_marketing"
  );
  const senaste = svar.docs?.[0]?.content?.trim();
  if (!senaste) {
    throw new Error(
      "Affärskontexten (Vad vi säljer) är inte ifylld ännu. Fyll i den under " +
        "Inställningar, Vad agenterna vet, Affärskontext innan ett utkast kan skapas."
    );
  }
  // OutreachDraftRequest.offer_summary har max_length 2000.
  return senaste.slice(0, 2000);
}

const STATUS_ETIKETT: Record<string, string> = {
  new: "Ny",
  researching: "Research pågår",
  ready: "Redo",
  contacted: "Kontaktad",
  replied: "Svarat",
  meeting: "Möte",
  won: "Vunnen",
  lost: "Förlorad",
  suppressed: "Spärrad"
};

export function Bolagssida({ id, demo = false }: Readonly<{ id: string; demo?: boolean }>) {
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
              ? "Tjänsten svarar inte just nu. Den vaknar ur viloläge och kan ta upp till en minut."
              : `Kunde inte hämta bolaget (status ${response.status}).`
        });
        return;
      }
      const kropp = await readJsonBody<{
        prospect?: Prospekt;
        sources?: string[];
        offline?: boolean;
      }>(response);
      if (!kropp?.prospect || kropp.offline) {
        setLage({ fas: "fel", meddelande: "Backenden svarade utan innehåll." });
        return;
      }
      setLage({ fas: "klar", prospekt: kropp.prospect, kallor: kropp.sources ?? [] });
      void kontrolleraBefintligtUtkast(kropp.prospect);
    } catch (error) {
      setLage({
        fas: "fel",
        meddelande: error instanceof Error ? error.message : "Kunde inte nå servern."
      });
    }
  }, [id, demo, kontrolleraBefintligtUtkast]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  /** 5.2/5.3: "Skapa utkast" — anropar den riktiga kedjan, inte studions egen route. */
  const skapaUtkast = useCallback(async () => {
    if (lage.fas !== "klar") return;
    const p = lage.prospekt;
    if (!p.contact_email) {
      setUtkastLage({
        fas: "fel",
        meddelande:
          "Prospektet saknar en mottagaradress. Lägg till en kontaktkälla med adress innan ett utkast kan skapas."
      });
      return;
    }

    setUtkastLage({ fas: "skapar" });
    try {
      const offerSummary = await hamtaOffertsammanfattning();
      const svar = await snajpAnrop<{
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
          brief:
            `Skriv ett kort, personligt första mejl till kontaktpersonen på ${p.company_name}. ` +
            "Utgå ifrån poängmotiveringen i researchunderlaget och håll dig till det som redan är " +
            "känt. Ingen hype, inga superlativ, ren text. Utkastet ska köas för granskning, inte skickas.",
          research_summary: byggForskningssammanfattning(p),
          // OutreachDraftRequest.research_evidence har max_length 60 poster.
          research_evidence: lage.kallor.slice(0, 60)
        })
      });

      if (svar.escalated || !svar.body) {
        setUtkastLage({
          fas: "fel",
          meddelande:
            svar.escalation_reason ||
            "Agenten lämnade över till en människa i stället för att skriva klart utkastet. Försök igen om en stund."
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
      setUtkastLage({ fas: "fel", meddelande: felmeddelande(cause) });
    }
  }, [lage]);

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
      <PageShell title="Hämtar bolaget…">
        <SkeletonRows />
      </PageShell>
    );
  }

  if (lage.fas === "saknas") {
    return (
      <PageShell kicker="Företag" title="Bolaget finns inte">
        <EmptyState
          title="Hittade inget sådant bolag"
          body="Prospektet finns inte i din arbetsyta. Det kan ha tagits bort, eller så pekar länken fel."
        />
        <Link href={vag("/dashboard/companies")} className={cn(btnPrimary, "mt-6")}>
          Till bolagen
        </Link>
      </PageShell>
    );
  }

  if (lage.fas === "fel") {
    return (
      <PageShell kicker="Företag" title="Bolaget kunde inte hämtas">
        <div className="flex items-start gap-3 border-y border-ochre/40 bg-ochre/10 px-4 py-4">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-ochre" aria-hidden />
          <div className="min-w-0">
            <p className="text-sm text-ink/70">{lage.meddelande}</p>
            <button
              type="button"
              onClick={() => void hamta()}
              className="focus-ring mt-3 inline-flex min-h-9 items-center rounded-input bg-paper2 px-3 text-[13px] font-medium"
            >
              Försök igen
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
      kicker={[p.sni, p.ort].filter(Boolean).join(" · ") || "Företag"}
      title={p.company_name}
      description={p.website ?? undefined}
      action={
        // Länken till den frikopplade Email-studion är BORTA (Fas 4,
        // 2026-08-29): mejlutkastet renderas numera inline i den här sidan,
        // se sektionen "Mejlutkast" nedan. Kvar i action-sloten står bara
        // märkningen — samma stil som statusetiketterna i Bolagsregister
        // (kicker/mineral), inte en egen badgestil.
        p.origin === "example" ? <span className="kicker text-mineral">Exempel</span> : null
      }
    >
      <div className="grid grid-cols-12 gap-x-8 gap-y-10">
        <dl className="col-span-12 grid grid-cols-12 gap-x-8 gap-y-8">
          <Matt label="Score" value={poang} detail={p.qualified === false ? "diskvalificerad" : "kvalificerad"} />
          <Matt
            label="Anställda"
            value={p.anstallda == null ? "—" : String(p.anstallda)}
            detail={p.orgnr ? `org.nr ${p.orgnr}` : "org.nr saknas"}
          />
          <Matt label="Källor" value={String(kallor.length)} detail="provenienskällor" />
          <Matt label="Status" value={STATUS_ETIKETT[p.status] ?? p.status} detail="nuvarande läge" />
        </dl>

        <section className="col-span-12 md:col-span-7">
          <h2 className="kicker text-mineral">Så räknades poängen</h2>
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
                      {typeof k.vikt === "number" ? ` · vikt ${k.vikt}` : ""}
                    </span>
                  </div>
                  {k.motivering ? (
                    <p className="mt-1.5 max-w-[65ch] text-[15px] leading-6 text-ink/70">
                      {k.motivering}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-5 border-y border-ink/15 py-4 text-[15px] text-ink/60">
              Ingen poängmotivering sparad för det här bolaget. Den skrivs vid körningen — ett
              prospekt som lagts till för hand har ingen.
            </p>
          )}

          {p.disqualifiers?.length ? (
            <div className="mt-8">
              <h2 className="kicker text-mineral">Diskvalificerare</h2>
              <ul className="mt-4 space-y-2">
                {p.disqualifiers.map((skäl) => (
                  <li key={skäl} className="border-l-2 border-danger pl-3 text-[15px] text-ink/75">
                    {skäl}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>

        <section className="col-span-12 md:col-span-5">
          <h2 className="kicker text-mineral">Kontakt</h2>
          <div className="mt-4 border-y border-ink/15 py-4">
            <p className="text-[15px]">{p.contact_name ?? "Ingen kontaktperson hittad"}</p>
            {p.contact_email ? (
              <p className="mt-1 break-all text-sm text-ink/60">{p.contact_email}</p>
            ) : null}
          </div>

          <h2 className="kicker mt-8 text-mineral">Källor</h2>
          {kallor.length ? (
            <ul className="mt-4 space-y-2">
              {kallor.map((url) => (
                <li key={url}>
                  <a
                    href={url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="focus-ring break-all text-sm text-ink/70 underline decoration-ink/25 underline-offset-4"
                  >
                    {url}
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-[15px] text-ink/60">
              Inga källor sparade. Utan minst en källa får agenten inte skriva ett utkast — se
              provenienskravet i leads-agentens regler.
            </p>
          )}
        </section>

        {/* Fas 4 (2026-08-29): Email-studion flyttade in i leaden. Ersätter
            den gamla "Skriv mejl ↗"-länken till den frikopplade, generiska
            studion — den kunde bara visa E-Tech-exemplet, oavsett vilket
            bolag man tittade på. */}
        <section className="col-span-12 border-t border-ink/15 pt-8">
          <h2 className="kicker text-mineral">Mejlutkast</h2>

          {demo ? (
            <div className="mt-5 rounded-card bg-paper2/60 p-5">
              <p className="max-w-[65ch] text-[15px] leading-7 text-ink/70">
                Ett utkast kostar LLM-anrop mot er egen granskningskö och kräver därför ett
                konto. Här visar vi var det hade legat, inte ett påhittat resultat.
              </p>
              <Link href="/login" className={cn(btnPrimary, "mt-4")}>
                Logga in för att skapa utkast
              </Link>
            </div>
          ) : (
            <div className="mt-5">
              {utkastLage.fas === "kontrollerar" ? (
                <div className="h-16 animate-pulse border-t border-ink/15 bg-ink/[0.03]" />
              ) : null}

              {utkastLage.fas === "ingen" ? (
                <div>
                  <p className="max-w-[65ch] text-[15px] leading-7 text-ink/70">
                    Inget utkast ännu. Ett klick skriver ett första mejl utifrån poängmotiveringen
                    och källorna ovan, sedan väntar det på din granskning i kön.
                  </p>
                  <button type="button" onClick={() => void skapaUtkast()} className={cn(btnPrimary, "mt-4")}>
                    Skapa utkast
                  </button>
                </div>
              ) : null}

              {utkastLage.fas === "skapar" ? (
                <p className="text-[14px] text-ink/55">Skriver utkastet…</p>
              ) : null}

              {utkastLage.fas === "fel" ? (
                <div className="flex items-start gap-3 border-y border-ochre/40 bg-ochre/10 px-4 py-4">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-ochre" aria-hidden />
                  <div className="min-w-0">
                    <p className="text-sm text-ink/70">{utkastLage.meddelande}</p>
                    <button
                      type="button"
                      onClick={() => void skapaUtkast()}
                      className="focus-ring mt-3 inline-flex min-h-9 items-center rounded-input bg-paper2 px-3 text-[13px] font-medium"
                    >
                      Försök igen
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
                  <p className="mt-4 max-w-[65ch] text-[13px] leading-6 text-ink/50">
                    Godkänn skickar utkastet som det sparades i granskningskön. Ändringar i
                    fälten ovan uppdaterar bara den här vyn tills en sparväg finns.
                  </p>

                  <div className="mt-5 border-t border-ink/15 pt-5">
                    {godkant ? (
                      <p role="status" className="text-[15px] text-moss">
                        Godkänt. Utkastet ligger nu i sändkön.
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
                          {godkannBusy ? "Godkänner…" : "Godkänn och skicka"}
                        </button>
                        {!utkastLage.queueItemId ? (
                          <p className="mt-3 max-w-[65ch] text-[13px] leading-6 text-ink/50">
                            Det här utkastet saknar ett kö-id och kan inte godkännas härifrån.
                            Se granskningskön under Leads-inställningarna.
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
                          <span className="text-[14px] leading-6 text-ink/70">
                            Vill du att agenten skriver utkast automatiskt framöver?{" "}
                            <span className="text-ink/45">
                              Redan på. Utan mänsklig granskning lämnar inget huset ändå.
                            </span>
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
                          <span className="text-[14px] leading-6 text-ink/70">
                            …och skickar automatiskt, utan granskning?
                          </span>
                        </label>

                        {autonomiFel ? (
                          <p role="alert" className="text-[13px] leading-6 text-danger">
                            {autonomiFel}
                          </p>
                        ) : null}
                        {autonomiSparad ? (
                          <p role="status" className="text-[13px] text-moss">
                            Sparat.
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
}: Readonly<{ label: string; value: string; detail: string }>) {
  return (
    <div className="col-span-6 border-t border-ink/15 pt-4 md:col-span-3">
      <dt className="kicker text-mineral">{label}</dt>
      <dd className="num mt-3 text-[1.75rem] font-semibold tabular-nums tracking-[-0.02em]">
        {value}
      </dd>
      <p className="mt-2 text-[14px] leading-6 text-ink/65">{detail}</p>
    </div>
  );
}
