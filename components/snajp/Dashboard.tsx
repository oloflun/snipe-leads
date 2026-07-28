"use client";

import {
  CheckCircle2,
  ChevronDown,
  ClipboardCopy,
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
import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui";
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

type Rule = { category: string; label: string; mode: "auto" | "draft" | "escalate" };

const CATEGORY_LABELS: Record<string, string> = {
  teknisk_support: "Teknisk support",
  leverans: "Leverans",
  betalning: "Betalning",
  retur_reklamation: "Retur & reklamation",
  orderstatus: "Orderstatus",
  konto: "Konto",
  ovrigt: "Övrigt"
};

const STATUS_META: Record<string, { label: string; tone: "neutral" | "good" | "warn" | "danger" }> = {
  new: { label: "Ny", tone: "neutral" },
  processing: { label: "Bearbetas", tone: "neutral" },
  awaiting_approval: { label: "Utkast", tone: "warn" },
  approved: { label: "Godkänt", tone: "good" },
  auto_sent: { label: "Skickat (auto)", tone: "good" },
  sent: { label: "Skickat", tone: "good" },
  escalated: { label: "Eskalerat", tone: "danger" },
  rejected: { label: "Avvisat", tone: "neutral" },
  taken_over: { label: "Övertaget manuellt", tone: "neutral" },
  failed: { label: "Fel", tone: "danger" }
};

const EVENT_LABELS: Record<string, string> = {
  received: "Mail mottaget",
  classified: "Klassificerat",
  escalated: "Eskalerat till människa",
  draft_created: "Utkast skapat",
  auto_sent: "Autosvar skickat",
  auto_send_blocked: "Autoskick stoppat — kräver godkännande",
  approved_and_sent: "Godkänt och skickat till kund",
  approved_no_send: "Godkänt utan utskick",
  send_failed: "Utskicket misslyckades",
  draft_rejected: "Utkast avvisat",
  taken_over: "Manuellt övertaget",
  failed: "Fel vid bearbetning",
  rule_changed: "Regel ändrad"
};

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

export function Dashboard() {
  const [emails, setEmails] = useState<EmailRow[]>([]);
  const [categoryCounts, setCategoryCounts] = useState<Record<string, number>>({});
  const [selected, setSelected] = useState<EmailDetail | null>(null);
  const [draftText, setDraftText] = useState("");
  const [rules, setRules] = useState<Rule[]>([]);
  const [rulesOpen, setRulesOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [syncInfo, setSyncInfo] = useState<string | null>(null);
  const [health, setHealth] = useState<{ can_send_email: boolean; auto_send_enabled: boolean } | null>(null);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const api = useCallback(async (path: string, init?: RequestInit) => {
    const response = await fetch(`/api/snajp-support${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init
    });
    const payload = await response.json();
    if (payload.offline) {
      throw new Error(payload.error);
    }
    if (!response.ok) {
      throw new Error(payload.detail ?? payload.error ?? "Okänt fel");
    }
    return payload;
  }, []);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const params = new URLSearchParams();
      if (search) params.set("q", search);
      if (statusFilter) params.set("status", statusFilter);
      if (categoryFilter) params.set("category", categoryFilter);
      const data = await api(`/inbox?${params.toString()}`);
      setEmails(data.emails);
      setCategoryCounts(data.category_counts);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Kunde inte hämta inkorgen.");
    }
  }, [api, search, statusFilter, categoryFilter]);

  const loadRules = useCallback(async () => {
    try {
      setRules((await api("/rules")).rules);
    } catch {
      /* reglerna är inte kritiska för listan */
    }
  }, [api]);

  useEffect(() => {
    void refresh();
    void loadRules();
    // Avgör om utskick är möjligt, så knappen inte lovar mer än den kan hålla.
    fetch("/api/snajp-support/health")
      .then((r) => r.json())
      .then((h) => setHealth({ can_send_email: !!h.can_send_email, auto_send_enabled: !!h.auto_send_enabled }))
      .catch(() => setHealth(null));
  }, [refresh, loadRules]);

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

  const seedMock = () =>
    act("seed", async () => {
      await api("/inbox/mock", { method: "POST" });
      setSelected(null);
    });

  const syncInbox = () =>
    act("sync", async () => {
      setSyncInfo(null);
      const result = await api("/inbox/sync", { method: "POST" });
      if (result.error) {
        throw new Error(result.error);
      }
      setSyncInfo(
        `Synk klar: ${result.fetched} nya mail hämtade, ${result.processed} processade.`
      );
    });

  const approve = (send: boolean) =>
    selected?.draft &&
    act(send ? "approve" : "approveNoSend", async () => {
      setSyncInfo(null);
      const body: Record<string, unknown> = { send };
      if (draftText !== selected.draft!.content) {
        body.edited_content = draftText;
      }
      const result = await api(`/drafts/${selected.draft!.id}/approve`, {
        method: "POST",
        body: JSON.stringify(body)
      });
      setSyncInfo(
        result.delivered
          ? `Svaret är skickat till ${selected.from_email}.`
          : "Godkänt. Inget mail skickades — kopiera texten och skicka den själv."
      );
    });

  const reject = () =>
    selected?.draft &&
    act("reject", () =>
      api(`/drafts/${selected.draft!.id}/reject`, { method: "POST", body: "{}" })
    );

  const takeover = () =>
    selected &&
    act("takeover", () => api(`/inbox/${selected.id}/takeover`, { method: "POST" }));

  const setRule = (category: string, mode: string) =>
    act("rule", async () => {
      await api("/rules", { method: "PUT", body: JSON.stringify({ category, mode }) });
      await loadRules();
    });

  const totalPending = useMemo(
    () => emails.filter((e) => e.status === "awaiting_approval").length,
    [emails]
  );
  const totalEscalated = useMemo(
    () => emails.filter((e) => e.status === "escalated").length,
    [emails]
  );

  const canReview = selected?.draft?.status === "pending";

  return (
    <div className="space-y-6">
      {/* Åtgärdsrad */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={seedMock}
          disabled={busy !== null}
          className="focus-ring inline-flex min-h-11 items-center gap-2 rounded-[7px] bg-ink px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-copper hover:text-ink disabled:opacity-40"
        >
          {busy === "seed" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Inbox className="h-4 w-4" />}
          Hämta testmail
        </button>
        <button
          type="button"
          onClick={syncInbox}
          disabled={busy !== null}
          title="Hämtar olästa mail från kopplad Gmail/Outlook-inkorg (IMAP)"
          className="focus-ring inline-flex min-h-11 items-center gap-2 rounded-[7px] border border-ink/12 bg-paper2/70 px-4 py-2.5 text-sm font-semibold text-ink/70 transition hover:border-ochre hover:text-ink disabled:opacity-40"
        >
          {busy === "sync" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mail className="h-4 w-4" />}
          Synka inkorg
        </button>
        <button
          type="button"
          onClick={() => void refresh()}
          className="focus-ring inline-flex min-h-11 items-center gap-2 rounded-[7px] border border-ink/12 bg-paper2/70 px-4 py-2.5 text-sm font-semibold text-ink/70 transition hover:border-ochre hover:text-ink"
        >
          <RefreshCw className="h-4 w-4" />
          Uppdatera
        </button>
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink/35" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Sök avsändare, ämne eller innehåll…"
            className="focus-ring min-h-11 w-full rounded-[7px] border border-ink/12 bg-paper py-2.5 pl-9 pr-3 text-sm outline-none placeholder:text-ink/35"
          />
        </div>
        <select
          value={statusFilter ?? ""}
          onChange={(event) => setStatusFilter(event.target.value || null)}
          className="focus-ring min-h-11 rounded-[7px] border border-ink/12 bg-paper px-3 py-2.5 text-sm"
        >
          <option value="">Alla statusar</option>
          {Object.entries(STATUS_META).map(([value, meta]) => (
            <option key={value} value={value}>
              {meta.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => setRulesOpen((open) => !open)}
          className="focus-ring inline-flex min-h-11 items-center gap-2 rounded-[7px] border border-ink/12 bg-paper2/70 px-4 py-2.5 text-sm font-semibold text-ink/70 transition hover:border-ochre hover:text-ink"
        >
          <Settings2 className="h-4 w-4" />
          Regler
          <ChevronDown className={cn("h-3.5 w-3.5 transition", rulesOpen ? "rotate-180" : "")} />
        </button>
      </div>

      {rulesOpen ? (
        <div className="rounded-[10px] border border-ink/12 bg-paper p-5 shadow-hairline">
          <p className="kicker text-mineral">Autosvarsregler per fack</p>
          <p className="mt-2 max-w-[70ch] text-sm leading-6 text-ink/60">
            <strong>Utkast</strong> = svaret väntar på ditt godkännande (default). <strong>Auto</strong> = skickas
            direkt om konfidensen är hög och tonen inte är negativ. <strong>Eskalera</strong> = alltid till människa.
            Pengar, juridik, GDPR och arga kunder eskaleras alltid, oavsett regel.
          </p>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {rules.map((rule) => (
              <div key={rule.category} className="flex items-center justify-between gap-2 rounded-[7px] border border-ink/10 bg-paper2/50 px-3 py-2.5">
                <span className="text-sm font-medium">{rule.label}</span>
                <select
                  value={rule.mode}
                  onChange={(event) => void setRule(rule.category, event.target.value)}
                  className="focus-ring rounded-[6px] border border-ink/12 bg-paper px-2 py-1.5 text-xs"
                >
                  <option value="draft">Utkast</option>
                  <option value="auto">Auto</option>
                  <option value="escalate">Eskalera</option>
                </select>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {error ? (
        <div className="rounded-[8px] border border-danger/25 bg-danger/5 px-4 py-3 text-sm text-ink/80">{error}</div>
      ) : null}
      {syncInfo ? (
        <div className="rounded-[8px] border border-moss/25 bg-moss/5 px-4 py-3 text-sm text-ink/80">{syncInfo}</div>
      ) : null}

      {/* Pilotläge: gör det omöjligt att missförstå vad agenten får göra själv. */}
      {health ? (
        <div className="flex flex-wrap items-center gap-2 rounded-[8px] border border-ink/10 bg-paper2/50 px-4 py-2.5 text-xs text-ink/65">
          <Badge tone={health.auto_send_enabled ? "warn" : "good"}>
            {health.auto_send_enabled ? "Autosvar PÅ" : "Granskningsläge"}
          </Badge>
          <span>
            {health.auto_send_enabled
              ? "Agenten kan skicka svar automatiskt enligt reglerna nedan."
              : "Inget skickas utan att du godkänt det — agenten skriver bara utkast."}
          </span>
          {health.can_send_email ? null : (
            <span className="text-danger">
              · Utskick är inte konfigurerat, så svar kan bara godkännas och kopieras.
            </span>
          )}
        </div>
      ) : null}

      {/* Fack-översikt */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setCategoryFilter(null)}
          className={cn(
            "focus-ring rounded-[7px] border px-3 py-2 text-xs font-semibold transition",
            categoryFilter === null
              ? "border-ochre bg-ochre/10 text-ink"
              : "border-ink/12 bg-paper2/60 text-ink/60 hover:text-ink"
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
              "focus-ring rounded-[7px] border px-3 py-2 text-xs font-semibold transition",
              categoryFilter === category
                ? "border-ochre bg-ochre/10 text-ink"
                : "border-ink/12 bg-paper2/60 text-ink/60 hover:text-ink"
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
            <div className="rounded-[10px] border border-dashed border-ink/15 bg-paper/45 p-10 text-center">
              <Inbox className="mx-auto h-6 w-6 text-mineral" />
              <h3 className="mt-4 font-semibold">Inkorgen är tom</h3>
              <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink/60">
                Klicka på <strong>Hämta testmail</strong> för att seeda sex svenska kundmail, eller koppla en riktig
                inkorg (Gmail/Outlook via IMAP) i backendens miljövariabler.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-ink/10 overflow-hidden rounded-[10px] border border-ink/12 bg-paper shadow-hairline">
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
            <div className="space-y-5 rounded-[10px] border border-ink/12 bg-paper p-5 shadow-lift">
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

              <div className="rounded-[7px] bg-ink/[0.03] p-4 text-sm leading-6 text-ink/75">
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
                          className="h-20 max-w-40 rounded-[6px] border border-ink/10 object-cover"
                        />
                      ))}
                  </div>
                ) : null}
              </div>

              {selected.classification ? (
                <div className="rounded-[7px] border border-ink/10 bg-paper2/50 p-4">
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
                <div className="rounded-[7px] border border-moss/20 bg-moss/5 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <p className="kicker text-moss">
                      {selected.draft.status === "auto_sent"
                        ? "Autosvar (skickat)"
                        : selected.draft.status === "approved"
                          ? selected.status === "sent"
                            ? "Skickat till kunden"
                            : "Godkänt — inte skickat"
                          : selected.draft.status === "rejected"
                            ? "Avvisat utkast"
                            : "AI-utkast — granska innan det skickas"}
                    </p>
                    <ConfidenceBar value={selected.draft.confidence} />
                  </div>
                  {canReview ? (
                    <textarea
                      value={draftText}
                      onChange={(event) => setDraftText(event.target.value)}
                      rows={8}
                      className="focus-ring mt-3 w-full resize-y rounded-[7px] border border-ink/12 bg-paper p-3 text-sm leading-6 outline-none"
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
                        onClick={() => approve(true)}
                        disabled={busy !== null || health?.can_send_email === false}
                        title={
                          health?.can_send_email === false
                            ? "Utskick är inte konfigurerat — använd Godkänn utan att skicka"
                            : `Skickar svaret till ${selected.from_email}`
                        }
                        className="focus-ring inline-flex min-h-10 items-center gap-2 rounded-[7px] bg-ink px-4 py-2 text-sm font-semibold text-paper transition hover:bg-moss disabled:opacity-40"
                      >
                        {busy === "approve" ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Send className="h-4 w-4" />
                        )}
                        Godkänn &amp; skicka
                      </button>
                      <button
                        type="button"
                        onClick={() => approve(false)}
                        disabled={busy !== null}
                        title="Markerar som godkänt utan att skicka mail — du hanterar utskicket själv"
                        className="focus-ring inline-flex min-h-10 items-center gap-2 rounded-[7px] border border-ink/15 px-4 py-2 text-sm font-semibold text-ink/70 transition hover:border-moss hover:text-ink disabled:opacity-40"
                      >
                        {busy === "approveNoSend" ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <CheckCircle2 className="h-4 w-4" />
                        )}
                        Godkänn utan att skicka
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          void navigator.clipboard?.writeText(draftText);
                          setSyncInfo("Svarstexten är kopierad till urklipp.");
                        }}
                        className="focus-ring inline-flex min-h-10 items-center gap-2 rounded-[7px] border border-ink/15 px-4 py-2 text-sm font-semibold text-ink/70 transition hover:border-ochre hover:text-ink"
                      >
                        <ClipboardCopy className="h-4 w-4" />
                        Kopiera text
                      </button>
                      <button
                        type="button"
                        onClick={reject}
                        disabled={busy !== null}
                        className="focus-ring inline-flex min-h-10 items-center gap-2 rounded-[7px] border border-danger/30 px-4 py-2 text-sm font-semibold text-danger transition hover:bg-danger/10 disabled:opacity-40"
                      >
                        <X className="h-4 w-4" />
                        Avvisa
                      </button>
                      <button
                        type="button"
                        onClick={takeover}
                        disabled={busy !== null}
                        className="focus-ring inline-flex min-h-10 items-center gap-2 rounded-[7px] border border-ink/15 px-4 py-2 text-sm font-semibold text-ink/70 transition hover:border-ochre hover:text-ink disabled:opacity-40"
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
                  <p className="kicker text-mineral">Beslutslogg</p>
                  <ol className="mt-3 space-y-2 border-l border-ink/10 pl-4">
                    {selected.decisions.map((decision, index) => (
                      <li key={index} className="relative text-xs leading-5 text-ink/65">
                        <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-ochre" />
                        <span className="font-semibold text-ink/80">
                          {EVENT_LABELS[decision.event] ?? decision.event}
                        </span>
                        {decision.detail?.reasoning ? <> — {String(decision.detail.reasoning)}</> : null}
                        {decision.detail?.reason ? <> — {String(decision.detail.reason)}</> : null}
                        {decision.detail?.why_not_auto ? <> — {String(decision.detail.why_not_auto)}</> : null}
                        {decision.detail?.note ? <> — {String(decision.detail.note)}</> : null}
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
