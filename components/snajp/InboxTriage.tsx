"use client";

import { ChevronDown, Inbox, Loader2, ShieldAlert, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

type SampleEmail = { from: string; subject: string; body: string };

type TriageResult = SampleEmail & {
  category: string;
  category_label: string;
  priority: string;
  sentiment: number;
  escalate: boolean;
  escalation_reason?: string | null;
  draft_reply: string;
  simulation?: boolean;
};

const sampleEmails: SampleEmail[] = [
  {
    from: "anna.lindqvist@mail.se",
    subject: "Kan inte logga in",
    body: "Hej! Jag försöker logga in på mitt konto men får bara felmeddelande. Har försökt återställa lösenordet men inget mail kommer. Kan ni hjälpa mig?"
  },
  {
    from: "johan.berg@mail.se",
    subject: "Var är mitt paket?",
    body: "Beställde för en vecka sedan och spårningen har inte uppdaterats på fyra dagar. Leveransen skulle ta 2–4 vardagar. När kommer paketet?"
  },
  {
    from: "sara.nystrom@mail.se",
    subject: "Dubbeldragning på kortet",
    body: "Jag ser två dragningar på exakt samma belopp för min beställning. Har ni debiterat mig dubbelt? Vill gärna få det utrett."
  },
  {
    from: "erik.holm@mail.se",
    subject: "Trasig vara — kräver återbetalning",
    body: "Vasen kom fram i tusen bitar trots bubbelplast. Helt oacceptabelt!! Jag vill ha pengarna tillbaka omgående, annars anmäler jag er till ARN."
  },
  {
    from: "maria.ek@mail.se",
    subject: "Radera mina uppgifter",
    body: "Hej, jag vill radera mitt konto och alla personuppgifter ni har om mig enligt GDPR. Hur går jag tillväga?"
  },
  {
    from: "lars.strand@mail.se",
    subject: "Rabattkoden funkar inte?",
    body: "Försökte använda välkomstkoden i kassan men den gick inte igenom. Är den bara för första köpet eller vad gäller?"
  }
];

const categoryOrder = [
  "teknisk_support",
  "leverans",
  "betalning",
  "retur_reklamation",
  "konto",
  "ovrigt"
];

export function InboxTriage({
  apiBase = "/api/snajp-support"
}: Readonly<{ apiBase?: string }>) {
  const { text } = useLocale();
  const [results, setResults] = useState<TriageResult[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  const grouped = useMemo(() => {
    if (!results) {
      return [];
    }
    return categoryOrder
      .map((category) => ({
        category,
        label: results.find((r) => r.category === category)?.category_label ?? category,
        items: results.filter((r) => r.category === category)
      }))
      .filter((group) => group.items.length > 0);
  }, [results]);

  const runTriage = async () => {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`${apiBase}/triage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ emails: sampleEmails })
      });
      const payload = await response.json();
      if (payload.offline) {
        setError(payload.error);
        return;
      }
      if (!response.ok) {
        throw new Error(payload.error ?? "Okänt fel");
      }
      setResults(payload.results as TriageResult[]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Något gick fel — försök igen.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <p className="max-w-[58ch] text-sm leading-6 text-ink/65">
          {text({
            sv: "Sex osorterade kundmail ligger i inkorgen. Ett klick — Snajp-Support läser, sorterar dem i rätt fack, bedömer ton och prioritet, och skriver färdiga svarsutkast.",
            en: "Six unsorted customer emails sit in the inbox. One click — Snajp-Support reads them, files them into the right queue, scores tone and priority, and drafts ready replies."
          })}
        </p>
        <button
          type="button"
          onClick={() => void runTriage()}
          disabled={busy}
          className="focus-ring inline-flex min-h-11 items-center gap-2 rounded-[7px] bg-ink px-5 py-2.5 text-sm font-semibold text-paper transition hover:bg-copper hover:text-ink disabled:opacity-40"
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {text({ sv: "Sortera inkorgen", en: "Sort the inbox" })}
        </button>
      </div>

      {error ? (
        <div className="rounded-[8px] border border-danger/25 bg-danger/5 px-4 py-3 text-sm text-ink/80">
          {error}
        </div>
      ) : null}

      {!results ? (
        <div className="divide-y divide-ink/10 rounded-[10px] border border-ink/12 bg-paper shadow-hairline">
          <div className="flex items-center gap-2 bg-paper2/60 px-5 py-3">
            <Inbox className="h-4 w-4 text-mineral" />
            <span className="kicker text-mineral">
              {text({ sv: "Inkorg · 6 olästa", en: "Inbox · 6 unread" })}
            </span>
          </div>
          {sampleEmails.map((email) => (
            <div key={email.from} className="grid grid-cols-12 gap-x-4 px-5 py-4">
              <span className="col-span-12 truncate font-mono text-xs text-ink/50 md:col-span-3">
                {email.from}
              </span>
              <span className="col-span-12 mt-1 text-sm font-semibold md:col-span-3 md:mt-0">
                {email.subject}
              </span>
              <span className="col-span-12 mt-1 truncate text-sm text-ink/55 md:col-span-6 md:mt-0">
                {email.body}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
          {grouped.map((group) => (
            <div key={group.category} className="rounded-[10px] border border-ink/12 bg-paper shadow-hairline">
              <div className="flex items-center justify-between border-b border-ink/10 bg-paper2/60 px-4 py-3">
                <span className="kicker text-mineral">{group.label}</span>
                <Badge tone="neutral">{group.items.length}</Badge>
              </div>
              <div className="divide-y divide-ink/10">
                {group.items.map((item) => {
                  const id = `${item.from}-${item.subject}`;
                  const open = openId === id;
                  return (
                    <div key={id} className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => setOpenId(open ? null : id)}
                        className="focus-ring flex w-full items-start justify-between gap-2 text-left"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold">{item.subject}</p>
                          <p className="truncate font-mono text-xs text-ink/45">{item.from}</p>
                        </div>
                        <ChevronDown
                          className={cn("mt-1 h-4 w-4 shrink-0 text-ink/40 transition", open ? "rotate-180" : "")}
                        />
                      </button>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        <Badge tone={item.sentiment < 0.3 ? "danger" : item.sentiment > 0.6 ? "good" : "warn"}>
                          Sentiment {item.sentiment.toFixed(1)}
                        </Badge>
                        <Badge tone={item.priority === "high" ? "warn" : "neutral"}>
                          {item.priority === "high"
                            ? text({ sv: "Hög prio", en: "High prio" })
                            : item.priority === "low"
                              ? text({ sv: "Låg prio", en: "Low prio" })
                              : text({ sv: "Normal prio", en: "Normal prio" })}
                        </Badge>
                        {item.escalate ? (
                          <Badge tone="danger">
                            <ShieldAlert className="h-3 w-3" />
                            {text({ sv: "Till människa", en: "To human" })}
                          </Badge>
                        ) : (
                          <Badge tone="good">{text({ sv: "Autosvar klart", en: "Auto-reply ready" })}</Badge>
                        )}
                      </div>
                      {open ? (
                        <div className="mt-3 space-y-3">
                          <div className="rounded-[7px] bg-ink/[0.03] p-3 text-xs leading-5 text-ink/65">
                            {item.body}
                          </div>
                          {item.escalation_reason ? (
                            <p className="text-xs leading-5 text-danger">{item.escalation_reason}</p>
                          ) : null}
                          <div className="rounded-[7px] border border-moss/20 bg-moss/5 p-3">
                            <p className="kicker mb-2 text-moss">
                              {text({ sv: "AI-utkast", en: "AI draft" })}
                            </p>
                            <p className="whitespace-pre-wrap text-xs leading-5 text-ink/80">
                              {item.draft_reply}
                            </p>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
