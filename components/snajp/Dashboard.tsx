"use client";

import {
  CheckCircle2,
  Image as ImageIcon,
  Inbox,
  Loader2,
  Mail,
  RefreshCw,
  Search,
  Send,
  Settings2,
  ShieldAlert,
  UserRound,
  X
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { EjAktiverad, arEjAktiverad } from "@/components/EjAktiverad";
import { Badge, btnPrimary, btnSecondary } from "@/components/ui";
import { mejlaOss } from "@/components/marketing/copy";
import { createDemoSupportApi } from "@/lib/demo/support-inbox";
import { readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

type Classification = {
  category: string;
  priority: string;
  sentiment: number | null;
  confidence: number;
  escalate: boolean;
  escalation_reason?: string | null;
  reasoning?: string;
  kb_sources: { title: string; similarity: number }[];
};

type Draft = {
  id: string;
  content: string;
  status: "pending" | "approved" | "rejected" | "auto_sent";
  auto: boolean;
  confidence: number;
};

type EmailRow = {
  id: string;
  from_email: string;
  from_name: string | null;
  subject: string;
  body_text: string;
  received_at: string;
  status: string;
  classification: Classification | null;
  draft: Draft | null;
  has_image: boolean;
  attachment_count: number;
};

type EmailDetail = EmailRow & {
  attachments: { id: string; filename: string; content_type: string; data_url: string | null; is_image: boolean }[];
  decisions: { event: string; detail: Record<string, unknown>; created_at: string }[];
};

// Måste spegla CATEGORIES i snajp-support/app/config.py. Backenden (som
// deployas från development) klassar numera i garanti och utbildning; utan
// dem här visades facken utan etikett i den här vyn.
const CATEGORY_LABELS: Record<string, string> = {
  teknisk_support: "Teknisk support",
  garanti: "Garanti",
  leverans: "Leverans & frakt",
  utbildning: "Utbildning & användarstöd",
  retur_reklamation: "Reklamation & retur",
  betalning: "Betalning & faktura",
  orderstatus: "Orderstatus",
  ovrigt: "Övrigt"
};

const STATUS_META: Record<string, { label: string; tone: "neutral" | "good" | "warn" | "danger" }> = {
  new: { label: "Ny", tone: "neutral" },
  processing: { label: "Bearbetas", tone: "neutral" },
  awaiting_approval: { label: "Väntar på godkännande", tone: "warn" },
  auto_sent: { label: "Autosvar skickat", tone: "good" },
  sent: { label: "Besvarat", tone: "good" },
  escalated: { label: "Eskalerat", tone: "danger" },
  rejected: { label: "Utkast avvisat", tone: "neutral" },
  taken_over: { label: "Manuellt övertaget", tone: "neutral" },
  failed: { label: "Fel", tone: "danger" }
};

const EVENT_LABELS: Record<string, string> = {
  received: "Mail mottaget",
  classified: "Klassificerat",
  escalated: "Eskalerat till människa",
  draft_created: "Utkast skapat",
  auto_sent: "Autosvar skickat",
  approved_and_sent: "Godkänt & skickat",
  draft_rejected: "Utkast avvisat",
  taken_over: "Manuellt övertaget",
  failed: "Fel vid bearbetning",
  rule_changed: "Regel ändrad"
};

/** Markör så refresh() kan skilja väntläget från riktiga fel utan texttolkning. */
class EjAktiveradFel extends Error {
  constructor() {
    super("Arbetsytan är inte aktiverad ännu.");
    this.name = "EjAktiveradFel";
  }
}

function ConfidenceBar({ value }: Readonly<{ value: number }>) {
  const percent = Math.round(value * 100);
  return (
    <span className="inline-flex items-center gap-2" title={`Konfidens ${percent}%`}>
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-ink/10">
        <span
          className={cn(
            "block h-full rounded-full",
            value >= 0.75 ? "bg-moss" : value >= 0.5 ? "bg-copper" : "bg-danger"
          )}
          style={{ width: `${percent}%` }}
        />
      </span>
      <span className="font-mono text-[11px] text-ink/50">{percent}%</span>
    </span>
  );
}

/**
 * `demo` byter ut backend-anropen mot exempeldata i webbläsaren.
 *
 * Den inloggade vägen går genom requireSnajpTenant(), som härleder tenanten ur
 * SESSIONEN och inte har någon demo-väg — med flit. En anonym besökare får
 * därför alltid 401 på /api/snajp-support/*, och /demo renderade tidigare ett
 * felmeddelande mitt i produktdemon. Grinden står kvar orörd; det är indatan
 * som byts, precis som app/demo/[[...slug]]/page.tsx föreskriver.
 */
export function Dashboard({ demo = false }: Readonly<{ demo?: boolean }>) {
  const vag = useArbetsvag();
  const [emails, setEmails] = useState<EmailRow[]>([]);
  const [categoryCounts, setCategoryCounts] = useState<Record<string, number>>({});
  const [selected, setSelected] = useState<EmailDetail | null>(null);
  const [draftText, setDraftText] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ejAktiverad, setEjAktiverad] = useState(false);
  const [syncInfo, setSyncInfo] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  /**
   * Söktexten som faktiskt ligger till grund för en fråga till backenden.
   *
   * `search` uppdateras vid varje tangenttryck, och `refresh` hänger på den.
   * Utan den här fördröjningen blev "paket" fem anrop genom proxyn till
   * backenden, var och en med en fullständig omrendering av listan medan man
   * skrev — det är den hackighet som märks efter en stunds klickande, och
   * inget som syns i ett enskilt klick.
   */
  const [sokning, setSokning] = useState("");

  useEffect(() => {
    const id = window.setTimeout(() => setSokning(search), 300);
    return () => window.clearTimeout(id);
  }, [search]);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);


  // En instans per monterad vy, så att demons tillstånd inte delas mellan
  // flikar eller återställs vid varje omrendering.
  // Sätts när komponenten avmonteras. Utan den fortsätter pollningen efter
  // att kunden bytt flik, och varje varv sätter state på en borttagen vy.
  const avbrutet = useRef(false);
  useEffect(() => {
    avbrutet.current = false;
    return () => {
      avbrutet.current = true;
    };
  }, []);

  const demoApi = useRef<ReturnType<typeof createDemoSupportApi> | null>(null);
  if (demo && !demoApi.current) {
    demoApi.current = createDemoSupportApi();
  }

  // Generisk med samma tillåtande default som tidigare (helpern returnerade
  // resultatet av response.json(), alltså any). Enda skillnaden är att kroppen
  // numera läses säkert.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const api = useCallback(async <T = any,>(path: string, init?: RequestInit): Promise<T> => {
    if (demo && demoApi.current) {
      return demoApi.current<T>(path, init);
    }

    const response = await fetch(`/api/snajp-support${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init
    });
    // Gemensam väg för hela dashboardens API-anrop — en oskyddad .json() här
    // slog igenom på varje yta som använder helpern.
    const payload =
      (await readJsonBody<T & { offline?: boolean; error?: string; detail?: string }>(response)) ??
      ({} as T & { offline?: boolean; error?: string; detail?: string });
    if (payload.offline) {
      throw new Error(
        payload.error ?? "Tjänsten är inte tillgänglig just nu. Försök igen om en stund."
      );
    }
    if (!response.ok) {
      // Ej aktiverad är ett VÄNTLÄGE, inte ett fel — samma gräns som i
      // Svar/Bolagsregister/Kontakter. Utan den här grenen visades
      // driftinstruktionen ur requireSnajpTenant() i en röd banner för en
      // nyregistrerad kund, i den vy som är supportkundens huvudvy.
      if (arEjAktiverad(response.status, payload)) {
        throw new EjAktiveradFel();
      }
      throw new Error(payload.detail ?? payload.error ?? "Okänt fel");
    }
    return payload;
  }, [demo]);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const params = new URLSearchParams();
      if (sokning) params.set("q", sokning);
      if (statusFilter) params.set("status", statusFilter);
      if (categoryFilter) params.set("category", categoryFilter);
      const data = await api(`/inbox?${params.toString()}`);
      setEmails(data.emails);
      setCategoryCounts(data.category_counts);
    } catch (caught) {
      if (caught instanceof EjAktiveradFel) {
        setEjAktiverad(true);
        return;
      }
      setError(caught instanceof Error ? caught.message : "Kunde inte hämta inkorgen.");
    }
  }, [api, sokning, statusFilter, categoryFilter]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  /**
   * Är en riktig inkorg kopplad?
   *
   * `null` betyder "vet inte än" och renderar ingen knapp alls. Att gissa
   * `true` hade gett samma fel som fanns förut: en knapp som ser tryckbar ut
   * och alltid svarar med ett konfigurationsfel. Att gissa `false` hade dolt
   * knappen ett ögonblick för kunder som HAR en inkorg, vilket blinkar.
   */
  const [inkorgKopplad, setInkorgKopplad] = useState<boolean | null>(null);

  useEffect(() => {
    let avbruten = false;
    void (async () => {
      try {
        const svar = await api<{ kan_synka?: boolean }>("/inbox/mailboxes");
        if (!avbruten) setInkorgKopplad(Boolean(svar?.kan_synka));
      } catch {
        // Ett fel här är inte kundens problem och ska inte visas som ett.
        // Utan svar vet vi inte, och då är rätt beteende att inte lova något:
        // knappen uteblir och texten under säger hur man kopplar en inkorg.
        if (!avbruten) setInkorgKopplad(false);
      }
    })();
    return () => {
      avbruten = true;
    };
  }, [api]);

  const openEmail = useCallback(
    async (id: string) => {
      try {
        const detail = (await api(`/inbox/${id}`)) as EmailDetail;
        setSelected(detail);
        setDraftText(detail.draft?.content ?? "");
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Kunde inte öppna mailet.");
      }
    },
    [api]
  );

  const act = useCallback(
    async (label: string, run: () => Promise<unknown>) => {
      setBusy(label);
      setError(null);
      try {
        await run();
        await refresh();
        if (selected) {
          await openEmail(selected.id);
        }
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Något gick fel.");
      } finally {
        setBusy(null);
      }
    },
    [refresh, openEmail, selected]
  );

  /**
   * Hämtar nya testmail och läser om listan medan agenten arbetar.
   *
   * ## Varför den pollar
   *
   * Backenden svarar numera så fort mailen är inlästa och klassificerar dem i
   * en bakgrundsuppgift — den ändringen gjordes för att knappen annars
   * snurrade i över en minut och dödades av proxyns 60-sekundersgräns. Följden
   * här: ärendena syns direkt men utan fack och utkast, och listan måste läsas
   * om några gånger för att fyllas i.
   *
   * Pollningen är BEGRÄNSAD med flit — åtta försök, växande mellanrum, sedan
   * slut. En obegränsad `setInterval` mot ett API är hur en flik som legat
   * öppen över natten blir en lastgenerator, och den sortens bakgrundsarbete
   * är också vad som får en sida att hacka efter tio minuters klickande.
   */
  const pollaTills = useCallback(
    async (forsok = 8) => {
      for (let i = 0; i < forsok; i += 1) {
        await new Promise((r) => setTimeout(r, 1500 + i * 1000));
        if (avbrutet.current) return;
        await refresh();
      }
    },
    [refresh]
  );

  /**
   * `category` skickas med: står kunden i ett fack ska nya mail hamna DÄR.
   * Utan den bytte varje klick ut hela testinkorgen, och det fack man tittade
   * på kunde få noll nya mail medan de andra fylldes på.
   */
  const seedMock = (kategori: string | null = categoryFilter) =>
    act("seed", async () => {
      const svar = await api<{ kb_tom?: boolean; ingested?: number; processing?: boolean }>(
        "/inbox/mock",
        { method: "POST", body: JSON.stringify(kategori ? { category: kategori } : {}) }
      );
      setSelected(null);
      // `kb_tom` sägs ut. Utan den läser kunden sex eskalerade rader som ett
      // produktfel, när agenterna i själva verket vägrade gissa ur en tom bas —
      // vilket är rätt beteende och fel intryck.
      setSyncInfo(
        svar?.kb_tom
          ? "Testmailen är inlästa. Kunskapsbasen är tom, så agenterna eskalerar allt tills ni lagt in något — det är avsiktligt, de gissar aldrig."
          : `${svar?.ingested ?? 0} nya mail i inkorgen. Agenterna sorterar och skriver utkast nu.`
      );
      if (svar?.processing) void pollaTills();
    });

  const syncInbox = () =>
    act("sync", async () => {
      setSyncInfo(null);
      const result = await api<{ fetched: number; processed: number; connected?: boolean; error?: string }>(
        "/inbox/sync",
        { method: "POST" }
      );
      // `connected: false` är inte ett fel — det är ett svar. Att kasta här
      // gav en röd felruta för ett läge som bara betyder "vi har inte kopplat
      // er inkorg ännu", och den rutan såg ut som en krasch.
      if (result.connected === false) {
        setInkorgKopplad(false);
        setSyncInfo(result.error ?? "Ingen inkorg är kopplad ännu.");
        return;
      }
      if (result.error) {
        throw new Error(result.error);
      }
      setSyncInfo(
        `Synk klar: ${result.fetched} nya mail hämtade, ${result.processed} processade.`
      );
    });

  const approve = () =>
    selected?.draft &&
    act("approve", () =>
      api(`/drafts/${selected.draft!.id}/approve`, {
        method: "POST",
        body: JSON.stringify(
          draftText !== selected.draft!.content ? { edited_content: draftText } : {}
        )
      })
    );

  const reject = () =>
    selected?.draft &&
    act("reject", () =>
      api(`/drafts/${selected.draft!.id}/reject`, { method: "POST", body: "{}" })
    );

  const takeover = () =>
    selected &&
    act("takeover", () => api(`/inbox/${selected.id}/takeover`, { method: "POST" }));

  const totalPending = useMemo(
    () => emails.filter((e) => e.status === "awaiting_approval").length,
    [emails]
  );
  const totalEscalated = useMemo(
    () => emails.filter((e) => e.status === "escalated").length,
    [emails]
  );

  const canReview = selected?.draft?.status === "pending";

  if (ejAktiverad) {
    return <EjAktiverad yta="Kundtjänst" />;
  }

  return (
    <div className="space-y-6">
      {/* Åtgärdsrad */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Alltid alla fack: knappen ska visa hur en hel inkorg ser ut. Det
            fackvisa läget hör till "Uppdatera" bredvid.

            Göms när en riktig inkorg är kopplad. Testmail bland en kunds
            verkliga ärenden är inte en demo, det är skräp i deras inkorg —
            och de har redan sett hur produkten fungerar. */}
        {inkorgKopplad ? null : (
          <button
            type="button"
            onClick={() => void seedMock(null)}
            disabled={busy !== null}
            className={btnPrimary}
          >
            {busy === "seed" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Inbox className="h-4 w-4" />}
            Hämta testmail
          </button>
        )}
        {/* Knappen finns bara när det finns en inkorg att synka. Den satt
            förut alltid framme och svarade "IMAP är inte konfigurerat
            (IMAP_HOST/USER/PASSWORD)" för varje kund — en felutskrift om
            miljövariabler kunden varken kan se eller sätta. */}
        {inkorgKopplad ? (
          <button
            type="button"
            onClick={syncInbox}
            disabled={busy !== null}
            title="Hämtar olästa mail från er kopplade Gmail- eller Outlook-inkorg"
            className={btnSecondary}
          >
            {busy === "sync" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mail className="h-4 w-4" />}
            Synka inkorg
          </button>
        ) : null}
        {/* "Uppdatera" hämtar NYA testmail när inkorgen är en sandlåda: står
            kunden i ett fack fylls det facket på, står de i "Alla" byts hela
            testinkorgen ut.

            MEN bara då. Är en riktig inkorg kopplad betyder "Uppdatera" läs om
            listan, ingenting annat — att skriva in påhittade kundmail bland en
            kunds verkliga ärenden vore att förstöra deras inkorg med en knapp
            som ser ut att bara ladda om. */}
        <button
          type="button"
          onClick={() => (inkorgKopplad ? void refresh() : void seedMock(categoryFilter))}
          disabled={busy !== null}
          title={
            inkorgKopplad
              ? "Läser om inkorgen"
              : categoryFilter
                ? "Hämtar nya testmail till det här facket"
                : "Hämtar nya testmail till alla fack"
          }
          className={btnSecondary}
        >
          {busy === "seed" && !inkorgKopplad ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          Uppdatera
        </button>
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink/35" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Sök avsändare, ämne eller innehåll…"
            className="focus-ring min-h-11 w-full rounded-input bg-paper py-2.5 pl-9 pr-3 text-sm outline-none placeholder:text-ink/35"
          />
        </div>
        <select
          value={statusFilter ?? ""}
          onChange={(event) => setStatusFilter(event.target.value || null)}
          className="focus-ring min-h-11 rounded-input bg-paper px-3 py-2.5 text-sm"
        >
          <option value="">Alla statusar</option>
          {Object.entries(STATUS_META).map(([value, meta]) => (
            <option key={value} value={value}>
              {meta.label}
            </option>
          ))}
        </select>
        {/* Reglerna bor numera under Inställningar, bredvid leads-agentens
            motsvarande kontroll. Se components/settings/SupportRegler.tsx. */}
        {demo ? null : (
          <Link href={vag("/settings/regler")} className={btnSecondary}>
            <Settings2 className="h-4 w-4" />
            Regler
          </Link>
        )}
      </div>

      {error ? (
        <div className="rounded-[8px] border border-danger/25 bg-danger/5 px-4 py-3 text-sm text-ink/80">{error}</div>
      ) : null}
      {syncInfo ? (
        <div className="rounded-[8px] border border-moss/25 bg-moss/5 px-4 py-3 text-sm text-ink/80">{syncInfo}</div>
      ) : null}

      {/* Fack-översikt */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setCategoryFilter(null)}
          className={cn(
            "focus-ring rounded-input border px-3 py-2 text-xs font-semibold transition",
            categoryFilter === null
              ? "border-ochre bg-ochre/10 text-ink"
              : "bg-paper2/60 text-ink/60 hover:text-ink"
          )}
        >
          Alla ({emails.length})
        </button>
        {Object.entries(CATEGORY_LABELS).map(([category, label]) => (
          <button
            key={category}
            type="button"
            onClick={() => setCategoryFilter(categoryFilter === category ? null : category)}
            className={cn(
              "focus-ring rounded-input border px-3 py-2 text-xs font-semibold transition",
              categoryFilter === category
                ? "border-ochre bg-ochre/10 text-ink"
                : "bg-paper2/60 text-ink/60 hover:text-ink"
            )}
          >
            {label} ({categoryCounts[category] ?? 0})
          </button>
        ))}
        <span className="ml-auto flex gap-2">
          {totalPending > 0 ? <Badge tone="warn">{totalPending} väntar på godkännande</Badge> : null}
          {totalEscalated > 0 ? <Badge tone="danger">{totalEscalated} eskalerade</Badge> : null}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        {/* Maillista */}
        <div className={cn("min-w-0", selected ? "xl:col-span-6" : "xl:col-span-12")}>
          {emails.length === 0 ? (
            <div className="rounded-card border border-dashed border-ink/15 bg-paper/45 p-10 text-center">
              <Inbox className="mx-auto h-6 w-6 text-mineral" />
              <h3 className="mt-4 font-semibold">Inkorgen är tom</h3>
              {/* Stod: "koppla en riktig inkorg (Gmail/Outlook via IMAP) i
                  backendens miljövariabler". En instruktion till oss, tryckt i
                  kundens vy — kunden har varken tillgång till backenden eller
                  anledning att veta vad IMAP är. */}
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink/60">
                Klicka på <strong>Hämta testmail</strong> för att fylla den med sex svenska
                exempelärenden och se hur agenterna sorterar och svarar.
              </p>
              {inkorgKopplad ? null : (
                <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-ink/55">
                  Vill ni koppla er riktiga inkorg?{" "}
                  <a
                    href={mejlaOss("Koppla vår inkorg")}
                    className="focus-ring rounded-input underline underline-offset-4 hover:text-ochre"
                  >
                    Hör av er
                  </a>{" "}
                  så kopplar vi Gmail eller Outlook åt er.
                </p>
              )}
            </div>
          ) : (
            <div className="divide-y divide-ink/10 overflow-hidden rounded-card bg-paper">
              {emails.map((email) => {
                const meta = STATUS_META[email.status] ?? STATUS_META.new;
                return (
                  <button
                    key={email.id}
                    type="button"
                    onClick={() => void openEmail(email.id)}
                    className={cn(
                      "focus-ring block w-full px-4 py-3.5 text-left transition hover:bg-ochre/5",
                      selected?.id === email.id ? "bg-ochre/5" : ""
                    )}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="flex items-center gap-2 truncate text-sm font-semibold">
                          {email.subject || "(utan ämne)"}
                          {email.has_image ? <ImageIcon className="h-3.5 w-3.5 shrink-0 text-ink/40" /> : null}
                        </p>
                        <p className="mt-0.5 truncate font-mono text-xs text-ink/45">
                          {email.from_name ? `${email.from_name} · ` : ""}
                          {email.from_email}
                        </p>
                      </div>
                      <Badge tone={meta.tone}>{meta.label}</Badge>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      {email.classification ? (
                        <>
                          <Badge tone="neutral">{CATEGORY_LABELS[email.classification.category]}</Badge>
                          <ConfidenceBar value={email.classification.confidence} />
                          {email.classification.escalate ? (
                            <ShieldAlert className="h-3.5 w-3.5 text-danger" />
                          ) : null}
                        </>
                      ) : (
                        <Badge tone="neutral">Obearbetat</Badge>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Detaljpanel */}
        {selected ? (
          <div className="min-w-0 xl:col-span-6">
            <div className="space-y-5 rounded-card bg-paper p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="break-words font-semibold">{selected.subject || "(utan ämne)"}</h3>
                  <p className="mt-1 font-mono text-xs text-ink/50">
                    {selected.from_name ? `${selected.from_name} · ` : ""}
                    {selected.from_email}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  className="focus-ring rounded-full p-1.5 text-ink/40 hover:text-ink"
                  aria-label="Stäng"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="rounded-input bg-ink/[0.03] p-4 text-sm leading-6 text-ink/75">
                <p className="whitespace-pre-wrap">{selected.body_text}</p>
                {selected.attachments.filter((a) => a.is_image && a.data_url).length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {selected.attachments
                      .filter((a) => a.is_image && a.data_url)
                      .map((a) => (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          key={a.id}
                          src={a.data_url!}
                          alt={a.filename}
                          title={a.filename}
                          className="h-20 max-w-40 rounded-input border border-ink/10 object-cover"
                        />
                      ))}
                  </div>
                ) : null}
              </div>

              {selected.classification ? (
                <div className="rounded-input border border-ink/10 bg-paper2/50 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="neutral">{CATEGORY_LABELS[selected.classification.category]}</Badge>
                    <ConfidenceBar value={selected.classification.confidence} />
                    {typeof selected.classification.sentiment === "number" ? (
                      <Badge
                        tone={
                          selected.classification.sentiment < 0.3
                            ? "danger"
                            : selected.classification.sentiment > 0.6
                              ? "good"
                              : "warn"
                        }
                      >
                        Sentiment {selected.classification.sentiment.toFixed(1)}
                      </Badge>
                    ) : null}
                    {selected.classification.escalate ? (
                      <Badge tone="danger">
                        <ShieldAlert className="h-3 w-3" />
                        Eskalerat
                      </Badge>
                    ) : null}
                  </div>
                  {selected.classification.reasoning ? (
                    <p className="mt-3 text-xs leading-5 text-ink/60">{selected.classification.reasoning}</p>
                  ) : null}
                  {selected.classification.escalation_reason ? (
                    <p className="mt-2 text-xs leading-5 text-danger">
                      {selected.classification.escalation_reason}
                    </p>
                  ) : null}
                  {selected.classification.kb_sources.length > 0 ? (
                    <p className="mt-2 text-xs text-ink/50">
                      Källor: {selected.classification.kb_sources.map((s) => s.title).join(" · ")}
                    </p>
                  ) : null}
                </div>
              ) : null}

              {selected.draft ? (
                <div className="rounded-input border border-moss/20 bg-moss/5 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[0.8125rem] font-medium text-moss">
                      {selected.draft.status === "auto_sent"
                        ? "Autosvar (skickat)"
                        : selected.draft.status === "approved"
                          ? "Skickat svar"
                          : selected.draft.status === "rejected"
                            ? "Avvisat utkast"
                            : "AI-utkast, väntar på godkännande"}
                    </p>
                    <ConfidenceBar value={selected.draft.confidence} />
                  </div>
                  {canReview ? (
                    <textarea
                      value={draftText}
                      onChange={(event) => setDraftText(event.target.value)}
                      rows={8}
                      className="focus-ring mt-3 w-full resize-y rounded-input bg-paper p-3 text-sm leading-6 outline-none"
                    />
                  ) : (
                    <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-ink/75">
                      {selected.draft.content}
                    </p>
                  )}
                  {canReview ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={approve}
                        disabled={busy !== null}
                        className={btnPrimary}
                      >
                        {busy === "approve" ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Send className="h-4 w-4" />
                        )}
                        Godkänn & skicka
                      </button>
                      <button
                        type="button"
                        onClick={reject}
                        disabled={busy !== null}
                        className="focus-ring inline-flex min-h-10 items-center gap-2 rounded-input border border-danger/30 px-4 py-2 text-sm font-semibold text-danger transition hover:bg-danger/10 disabled:opacity-40"
                      >
                        <X className="h-4 w-4" />
                        Avvisa
                      </button>
                      <button
                        type="button"
                        onClick={takeover}
                        disabled={busy !== null}
                        className="focus-ring inline-flex min-h-10 items-center gap-2 rounded-input border border-ink/15 px-4 py-2 text-sm font-semibold text-ink/70 transition hover:text-ink disabled:opacity-40"
                      >
                        <UserRound className="h-4 w-4" />
                        Ta över ärendet
                      </button>
                    </div>
                  ) : null}
                </div>
              ) : null}

              {selected.decisions.length > 0 ? (
                <div>
                  <p className="text-[0.8125rem] font-medium text-ink/45">Beslutslogg</p>
                  <ol className="mt-3 space-y-2 border-l border-ink/10 pl-4">
                    {selected.decisions.map((decision, index) => (
                      <li key={index} className="relative text-xs leading-5 text-ink/65">
                        <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-ochre" />
                        <span className="font-semibold text-ink/80">
                          {EVENT_LABELS[decision.event] ?? decision.event}
                        </span>
                        {decision.detail?.reasoning ? <>. {String(decision.detail.reasoning)}</> : null}
                        {decision.detail?.reason ? <>. {String(decision.detail.reason)}</> : null}
                        {decision.detail?.why_not_auto ? <>. {String(decision.detail.why_not_auto)}</> : null}
                        {decision.detail?.note ? <>. {String(decision.detail.note)}</> : null}
                      </li>
                    ))}
                  </ol>
                </div>
              ) : null}

              {selected.status === "sent" || selected.status === "auto_sent" ? (
                <p className="flex items-center gap-2 text-xs text-ink/50">
                  <CheckCircle2 className="h-4 w-4 text-moss" />
                  Ärendet är besvarat och stängt i CRM:et.
                </p>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
