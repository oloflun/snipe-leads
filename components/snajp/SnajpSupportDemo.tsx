"use client";

import { useState } from "react";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { Dashboard } from "./Dashboard";
import { IntegrationSection } from "./IntegrationSection";
import { KnowledgeBase } from "./KnowledgeBase";
import { SupportChat } from "./SupportChat";

const tabs = [
  { id: "dashboard", label: { sv: "Inkorg & triage", en: "Inbox & triage" } },
  { id: "kb", label: { sv: "Kunskapsbas", en: "Knowledge base" } },
  { id: "chat", label: { sv: "Live-chatt", en: "Live chat" } },
  { id: "integration", label: { sv: "Integration & API", en: "Integration & API" } }
] as const;

type TabId = (typeof tabs)[number]["id"];

const highlights = [
  {
    title: { sv: "Sorterar i åtta fack", en: "Sorts into eight queues" },
    body: {
      sv: "Teknisk support, garanti, leverans, utbildning, reklamation, betalning och orderstatus — varje mail klassas med konfidens.",
      en: "Technical support, warranty, delivery, training, claims, payment and order status — each email classified with a confidence score."
    }
  },
  {
    title: { sv: "Hittar aldrig på", en: "Never makes things up" },
    body: {
      sv: "Svaren bygger enbart på er kunskapsbas. Saknas underlag skrivs inget svar — ärendet går till en människa.",
      en: "Replies draw solely on your knowledge base. Without grounding it writes nothing — the case goes to a human."
    }
  },
  {
    title: { sv: "Ni godkänner varje svar", en: "You approve every reply" },
    body: {
      sv: "Agenten skriver utkast, ni granskar och skickar. Inget lämnar systemet utan att någon tryckt godkänn.",
      en: "The agent drafts, you review and send. Nothing leaves the system until a person approves it."
    }
  },
  {
    title: { sv: "Vet när människor behövs", en: "Knows when humans are needed" },
    body: {
      sv: "Återbetalningar, juridik, GDPR och ärenden som rör en inträffad incident lämnas alltid vidare.",
      en: "Refunds, legal matters, GDPR and anything touching a real incident are always handed over."
    }
  }
];

// apiBase avgör VILKEN arbetsyta datan hämtas från — utseendet är detsamma.
// "/api/snajp-demo" = publik demo (låst till demo-tenanten), "/api/snajp-support"
// = den inloggade kundens egen tenant.
export function SnajpSupportDemo({
  apiBase = "/api/snajp-support"
}: Readonly<{ apiBase?: string }>) {
  const { text } = useLocale();
  const [tab, setTab] = useState<TabId>("dashboard");

  return (
    <div className="space-y-12">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {highlights.map((item, index) => (
          <div key={item.title.sv} className="rounded-[10px] border border-ink/12 bg-paper p-5 shadow-hairline">
            <span className="kicker text-mineral">0{index + 1}</span>
            <h3 className="mt-3 font-semibold">{text(item.title)}</h3>
            <p className="mt-2 text-sm leading-6 text-ink/62">{text(item.body)}</p>
          </div>
        ))}
      </div>

      <div>
        <div className="flex flex-wrap gap-2 border-b border-ink/12 pb-px">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              className={cn(
                "focus-ring -mb-px border-b-2 px-4 py-3 text-sm font-semibold transition",
                tab === item.id
                  ? "border-ochre text-ink"
                  : "border-transparent text-ink/50 hover:text-ink"
              )}
            >
              {text(item.label)}
            </button>
          ))}
        </div>

        <div className="mt-8">
          {tab === "dashboard" ? <Dashboard apiBase={apiBase} /> : null}
          {tab === "kb" ? <KnowledgeBase apiBase={apiBase} /> : null}
          {tab === "chat" ? (
            <div className="mx-auto max-w-3xl">
              <SupportChat apiBase={apiBase} />
            </div>
          ) : null}
          {tab === "integration" ? <IntegrationSection /> : null}
        </div>
      </div>
    </div>
  );
}
