"use client";

import {
  CheckCircle2,
  Image as ImageIcon,
  Inbox,
  Loader2,
  Mail,
  RefreshCw,
  Scissors,
  Search,
  Send,
  Settings2,
  ShieldAlert,
  Smile,
  Sparkles,
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
  /** Pilotflaggorna (migration 071): mailet ber om pris/offert respektive
   * uttrycker utbildningsintresse. Oberoende av facket. */
  offertforfragan?: boolean;
  utbildningsintresse?: boolean;
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
  is_test?: boolean;
  /** Manuell avbockning (migration 071). Null/undefined = ohanterad. */
  hanterad_at?: string | null;
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
  failed: { label: "Fel", tone: "danger" },
  // Eskaleringslarm och notiser från Snajp (migration 078). Egen flik,
  // aldrig ett utkast — se processor.ar_snajp_notis.
  att_hantera: { label: "Att hantera", tone: "warn" }
};

const EVENT_LABELS: Record<string, string> = {
  received: "Mail mottaget",
  notis: "Larm från Snajp, flyttat till Att hantera",
  classified: "Klassificerat",
  escalated: "Eskalerat till människa",
  draft_created: "Utkast skapat",
  auto_sent: "Autosvar skickat",
  approved_and_sent: "Godkänt & skickat",
  draft_rejected: "Utkast avvisat",
  taken_over: "Manuellt övertaget",
  failed: "Fel vid bearbetning",
  rule_changed: "Regel ändrad",
  befordrad: "Flyttad till ärenden"
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
      <span className="font-mono text-[11px] text-ink-subtle">{percent}%</span>
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
export function Dashboard({
  demo = false,
  lager = "arenden",
  onMeta
}: Readonly<{
  demo?: boolean;
  lager?: "arenden" | "testmail" | "att_hantera";
  onMeta?: (meta: { visar_test_i_arenden: boolean }) => void;
}>) {
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
  /** Klientfilter: visa bara mail utan hanterad-stämpel. Listan är redan
   * hämtad (max 50 rader), så det behövs ingen serverresa för filtret. */
  const [baraOhanterade, setBaraOhanterade] = useState(false);
  /** True medan bakgrundsklassningen av nyss hämtade testmail pågår. */
  const [bearbetas, setBearbetas] = useState(false);
  /** Demo-/testkonton visar testmail under Ärenden. null = inte hämtat än. */
  const [visarTestIArenden, setVisarTestIArenden] = useState<boolean | null>(null);
  const onMetaRef = useRef(onMeta);
  onMetaRef.current = onMeta;


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
      if (lager === "testmail") params.set("is_test", "true");
      // "Att hantera" är en egen status, inte ett filter i listan: fliken
      // visar BARA larmen, och huvudlistan utesluter dem (backenden).
      if (lager === "att_hantera") params.set("status", "att_hantera");
      const data = await api(`/inbox?${params.toString()}`);
      setEmails(data.emails);
      setCategoryCounts(data.category_counts);
      if (typeof data.visar_test_i_arenden === "boolean") {
        setVisarTestIArenden(data.visar_test_i_arenden);
        onMetaRef.current?.({ visar_test_i_arenden: data.visar_test_i_arenden });
      }
    } catch (caught) {
      if (caught instanceof EjAktiveradFel) {
        setEjAktiverad(true);
        return;
      }
      setError(caught instanceof Error ? caught.message : "Kunde inte hämta inkorgen.");
    }
  }, [api, sokning, statusFilter, categoryFilter, lager]);

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
      setBearbetas(true);
      try {
        for (let i = 0; i < forsok; i += 1) {
          await new Promise((r) => setTimeout(r, 1500 + i * 1000));
          if (avbrutet.current) return;
          await refresh();
        }
      } finally {
        if (!avbrutet.current) setBearbetas(false);
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
      const result = await api<{
        fetched: number;
        processed: number;
        connected?: boolean;
        processing?: boolean;
        error?: string;
      }>("/inbox/sync", { method: "POST" });
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
      // Backenden svarar när mailen är HÄMTADE; klassificering och utkast
      // körs i bakgrunden (samma mönster som testmailen). Listan läses om
      // medan agenten arbetar, annars ser nya rader ut att sakna fack.
      setSyncInfo(
        result.fetched === 0
          ? "Synk klar: inga nya olästa mail i inkorgen."
          : `${result.fetched} nya mail hämtade. Agenten sorterar och skriver utkast nu.`
      );
      if (result.processing) void pollaTills();
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

  /**
   * Skriver om texten i rutan i vald riktning (Förbättra/Kortare/Mer
   * personlig). Egen väg i stället för act(): act() läser om listan och
   * ärendet, och en omhämtning här hade skrivit över precis den text kunden
   * just fick omformulerad. Inget skickas och det sparade utkastet rörs inte
   * — det som godkänns är som alltid innehållet i rutan.
   */
  const omformulera = async (lage: string) => {
    if (!selected?.draft) return;
    setBusy(`omformulera-${lage}`);
    setError(null);
    try {
      const svar = await api<{ content?: string }>(
        `/drafts/${selected.draft.id}/omformulera`,
        { method: "POST", body: JSON.stringify({ lage, content: draftText }) }
      );
      if (svar?.content) setDraftText(svar.content);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Kunde inte skriva om utkastet.");
    } finally {
      setBusy(null);
    }
  };

  const reject = () =>
    selected?.draft &&
    act("reject", () =>
      api(`/drafts/${selected.draft!.id}/reject`, { method: "POST", body: "{}" })
    );

  const takeover = () =>
    selected &&
    act("takeover", () => api(`/inbox/${selected.id}/takeover`, { method: "POST" }));

  const flyttaTillArenden = () =>
    selected &&
    act("befordra", async () => {
      await api(`/inbox/${selected.id}/befordra`, { method: "POST" });
      setSelected(null);
    });

  /** Avbockningen (migration 071) — skild från status: en medarbetare ska
   * kunna bocka av ett eskalerat mail som lösts i telefon. */
  const vaxlaHanterad = () =>
    selected &&
    act("hanterad", () =>
      api(`/inbox/${selected.id}/hanterad`, {
        method: "POST",
        body: JSON.stringify({ hanterad: !selected.hanterad_at })
      })
    );

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
        {inkorgKopplad || lager === "att_hantera" || (lager === "arenden" && visarTestIArenden === false) ? null : (
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
          onClick={() =>
            inkorgKopplad || lager === "att_hantera" || (lager === "arenden" && visarTestIArenden === false)
              ? void refresh()
              : void seedMock(categoryFilter)
          }
          disabled={busy !== null}
          title={
            inkorgKopplad || lager === "att_hantera" || (lager === "arenden" && visarTestIArenden === false)
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
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Sök avsändare, ämne eller innehåll…"
            className="focus-ring min-h-11 w-full rounded-input bg-paper py-2.5 pl-9 pr-3 text-sm outline-none placeholder:text-ink/35"
          />
        </div>
        {lager === "att_hantera" ? null : (
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
        )}
        {/* Reglerna bor numera under Inställningar, bredvid leads-agentens
            motsvarande kontroll. Se components/settings/SupportRegler.tsx. */}
        {demo || lager === "att_hantera" ? null : (
          <Link href={vag("/settings/regler")} className={btnSecondary}>
            <Settings2 className="h-4 w-4" />
            Regler
          </Link>
        )}
      </div>

      {error ? (
        <div className="rounded-[8px] border border-danger/25 bg-danger/5 px-4 py-3 text-sm text-ink-muted">{error}</div>
      ) : null}
      {syncInfo ? (
        <div
          className={
            syncInfo.includes("Kunskapsbasen är tom")
              ? "rounded-[8px] border border-ochre/40 bg-ochre/10 px-4 py-3 text-sm text-ink-muted"
              : "rounded-[8px] border border-moss/25 bg-moss/5 px-4 py-3 text-sm text-ink-muted"
          }
        >
          {syncInfo}
        </div>
      ) : null}

      {/* Fack-översikt. Bara fack som HAR ärenden visas (plus det valda):
          nio chips där sju står på (0) var den största delen av bruset i
          inkorgen (kundtest 2026-09-22). Summeringen till höger är text, inte
          fler färgade rutor. Döljs i Att hantera: larmen har inga fack. */}
      {lager === "att_hantera" ? null : (
        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { id: null as string | null, label: "Alla", antal: emails.length },
            ...Object.entries(CATEGORY_LABELS)
              .map(([id, label]) => ({ id: id as string | null, label, antal: categoryCounts[id] ?? 0 }))
              .filter((f) => f.antal > 0 || categoryFilter === f.id)
          ].map((f) => (
            <button
              key={f.id ?? "alla"}
              type="button"
              onClick={() => setCategoryFilter(f.id === null || categoryFilter === f.id ? null : f.id)}
              className={cn(
                "focus-ring rounded-full px-3 py-1.5 text-[0.8125rem] font-medium transition",
                categoryFilter === f.id
                  ? "bg-ink text-paper"
                  : "text-ink-muted hover:bg-paper2/70 hover:text-ink"
              )}
            >
              {f.label}
              <span className={cn("ml-1.5 tabular-nums", categoryFilter === f.id ? "text-paper-muted" : "text-ink-subtle")}>
                {f.antal}
              </span>
            </button>
          ))}
          <span aria-hidden className="mx-1 h-4 w-px bg-ink/15" />
          <button
            type="button"
            onClick={() => setBaraOhanterade((v) => !v)}
            className={cn(
              "focus-ring rounded-full px-3 py-1.5 text-[0.8125rem] font-medium transition",
              baraOhanterade ? "bg-ink text-paper" : "text-ink-muted hover:bg-paper2/70 hover:text-ink"
            )}
          >
            Bara ohanterade
          </button>
          {totalPending > 0 || totalEscalated > 0 ? (
            <span className="ml-auto text-[0.8125rem] text-ink-muted">
              {[
                totalPending > 0 ? `${totalPending} väntar på dig` : null,
                totalEscalated > 0 ? `${totalEscalated} eskalerade` : null
              ]
                .filter(Boolean)
                .join(" · ")}
            </span>
          ) : null}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        {/* Maillista */}
        <div className={cn("min-w-0", selected ? "xl:col-span-6" : "xl:col-span-12")}>
          {emails.length === 0 ? (
            <div className="rounded-card border border-dashed border-ink/15 bg-paper/45 p-10 text-center">
              <Inbox className="mx-auto h-6 w-6 text-mineral" />
              <h3 className="mt-4 font-semibold">
                {lager === "att_hantera" ? "Inget att hantera" : "Inkorgen är tom"}
              </h3>
              {/* Stod: "koppla en riktig inkorg (Gmail/Outlook via IMAP) i
                  backendens miljövariabler". En instruktion till oss, tryckt i
                  kundens vy — kunden har varken tillgång till backenden eller
                  anledning att veta vad IMAP är. */}
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink-muted">
                {lager === "att_hantera" ? (
                  <>
                    Här hamnar eskaleringar och larm när ett ärende lämnas över till er. De får
                    aldrig ett AI-utkast.
                  </>
                ) : lager === "testmail" || visarTestIArenden !== false ? (
                  <>
                    Klicka på <strong>Hämta testmail</strong> för att skicka testärenden mot
                    den här profilens kunskapsbas och se hur agenten svarar.
                  </>
                ) : (
                  <>Inga ärenden ännu. När en inkorg är kopplad hamnar kundmailen här.</>
                )}
              </p>
              {inkorgKopplad || lager === "att_hantera" ? null : (
                <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-ink-subtle">
                  Vill ni koppla er riktiga inkorg? Koppla Gmail, Outlook eller iCloud
                  under{" "}
                  <Link
                    href="/settings/mailboxes"
                    className="focus-ring rounded-input underline underline-offset-4 hover:text-ochre"
                  >
                    Inställningar → Inkorgar
                  </Link>
                  , så hämtas era olästa kundmail hit.
                </p>
              )}
            </div>
          ) : (
            /* Två rader text och EN tyst status (kundtest 2026-09-22: sex
               etiketter per rad — fack, Offert, Utbildning, konfidensstapel,
               sköld, statusruta — gjorde inkorgen svårläst). Fack och flaggor
               står som text i metaraden; konfidensen och motiveringen finns
               kvar i detaljpanelen, där de faktiskt läses. */
            <div className="divide-y divide-ink/10 overflow-hidden rounded-card bg-paper">
              {(baraOhanterade ? emails.filter((e) => !e.hanterad_at) : emails).map((email) => {
                const meta = STATUS_META[email.status] ?? STATUS_META.new;
                const lasesNu = bearbetas && !email.classification;
                const statusText = lasesNu ? "Agenten läser…" : meta.label;
                const prick = lasesNu
                  ? "bg-ink/25"
                  : { neutral: "bg-ink/25", good: "bg-moss", warn: "bg-ochre", danger: "bg-danger" }[meta.tone];
                const detaljer = [
                  email.from_name || email.from_email,
                  email.classification ? CATEGORY_LABELS[email.classification.category] : null
                ].filter(Boolean);
                return (
                  <button
                    key={email.id}
                    type="button"
                    onClick={() => void openEmail(email.id)}
                    className={cn(
                      "focus-ring grid w-full grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-4 px-4 py-3 text-left transition hover:bg-paper2/50",
                      selected?.id === email.id ? "bg-paper2/70" : ""
                    )}
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      <span className={cn("truncate text-sm", email.hanterad_at ? "font-medium text-ink-muted" : "font-semibold")}>
                        {email.subject || "(utan ämne)"}
                      </span>
                      {email.has_image ? <ImageIcon className="h-3.5 w-3.5 shrink-0 text-ink-subtle" /> : null}
                      {email.is_test ? <span className="kicker shrink-0 text-mineral">Test</span> : null}
                    </span>
                    <span className="flex items-center gap-1.5 whitespace-nowrap text-[0.8125rem] text-ink-muted">
                      {email.hanterad_at ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-moss" aria-label="Hanterat" />
                      ) : (
                        <span aria-hidden className={cn("h-1.5 w-1.5 rounded-full", prick)} />
                      )}
                      {statusText}
                    </span>
                    <span className="col-span-2 mt-0.5 flex min-w-0 items-center gap-1.5 text-[0.8125rem] text-ink-subtle">
                      <span className="truncate">{detaljer.join(" · ")}</span>
                      {email.classification?.offertforfragan ? (
                        <span className="shrink-0 font-medium text-warning">· Offert</span>
                      ) : null}
                      {email.classification?.utbildningsintresse ? (
                        <span className="shrink-0 font-medium text-moss">· Utbildning</span>
                      ) : null}
                    </span>
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
                  <p className="mt-1 font-mono text-xs text-ink-subtle">
                    {selected.from_name ? `${selected.from_name} · ` : ""}
                    {selected.from_email}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  className="focus-ring rounded-full p-1.5 text-ink-subtle hover:text-ink"
                  aria-label="Stäng"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="rounded-input bg-ink/[0.03] p-4 text-sm leading-6 text-ink-muted">
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

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void vaxlaHanterad()}
                  disabled={busy !== null}
                  className={btnSecondary}
                >
                  {busy === "hanterad" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <CheckCircle2
                      className={cn("h-4 w-4", selected.hanterad_at ? "text-moss" : "")}
                    />
                  )}
                  {selected.hanterad_at ? "Markera som ohanterat" : "Markera som hanterat"}
                </button>
                {selected.is_test ? (
                  <button
                    type="button"
                    onClick={() => void flyttaTillArenden()}
                    disabled={busy !== null}
                    className={btnSecondary}
                  >
                    {busy === "befordra" ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    Flytta till ärenden
                  </button>
                ) : null}
              </div>

              {!selected.classification && bearbetas ? (
                <p className="text-sm leading-6 text-ink-subtle">Agenten läser mailet och skriver ett utkast…</p>
              ) : null}

              {selected.classification ? (
                <div className="rounded-input border border-ink/10 bg-paper2/50 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="neutral">{CATEGORY_LABELS[selected.classification.category]}</Badge>
                    {selected.classification.offertforfragan ? (
                      <Badge tone="warn">Offertförfrågan</Badge>
                    ) : null}
                    {selected.classification.utbildningsintresse ? (
                      <Badge tone="good">Utbildningsintresse</Badge>
                    ) : null}
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
                    <p className="mt-3 text-xs leading-5 text-ink-muted">{selected.classification.reasoning}</p>
                  ) : null}
                  {selected.classification.escalation_reason ? (
                    <p className="mt-2 text-xs leading-5 text-danger">
                      {selected.classification.escalation_reason}
                    </p>
                  ) : null}
                  {selected.classification.kb_sources.length > 0 ? (
                    <p className="mt-2 text-xs text-ink-subtle">
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
                    <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-ink-muted">
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
                        className="focus-ring inline-flex min-h-10 items-center gap-2 rounded-input border border-ink/15 px-4 py-2 text-sm font-semibold text-ink-muted transition hover:text-ink disabled:opacity-40"
                      >
                        <UserRound className="h-4 w-4" />
                        Ta över ärendet
                      </button>
                      {/* Omformuleringarna, avskilda med en tunn linje: de
                          ändrar bara texten i rutan, aldrig ärendets
                          tillstånd. Samma trio som support-portalens inkorg. */}
                      <span aria-hidden className="mx-0.5 hidden self-center h-5 w-px bg-ink/15 sm:block" />
                      {(
                        [
                          ["forbattra", "Förbättra", Sparkles],
                          ["kortare", "Kortare", Scissors],
                          ["personligare", "Mer personlig", Smile]
                        ] as const
                      ).map(([lage, etikett, Ikon]) => (
                        <button
                          key={lage}
                          type="button"
                          onClick={() => void omformulera(lage)}
                          disabled={busy !== null}
                          title={`Skriv om utkastet: ${etikett.toLowerCase()}. Inget skickas förrän du godkänner.`}
                          className="focus-ring inline-flex min-h-10 items-center gap-1.5 rounded-input border border-ink/15 px-3 py-2 text-[0.8125rem] font-semibold text-ink-muted transition hover:text-ink disabled:opacity-40"
                        >
                          {busy === `omformulera-${lage}` ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Ikon className="h-3.5 w-3.5" />
                          )}
                          {etikett}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}

              {selected.decisions.length > 0 ? (
                <div>
                  <p className="text-[0.8125rem] font-medium text-ink-subtle">Beslutslogg</p>
                  <ol className="mt-3 space-y-2 border-l border-ink/10 pl-4">
                    {selected.decisions.map((decision, index) => (
                      <li key={index} className="relative text-xs leading-5 text-ink-muted">
                        <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-ochre" />
                        <span className="font-semibold text-ink-muted">
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
                <p className="flex items-center gap-2 text-xs text-ink-subtle">
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
