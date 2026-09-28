"use client";

import { useState } from "react";
import { flik, flikAktiv, flikInaktiv, rubrikPanel } from "@/components/ui";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { Dashboard } from "./Dashboard";
import { InboxTriage } from "./InboxTriage";
import { IntegrationSection } from "./IntegrationSection";
import { SupportChat } from "./SupportChat";

const tabs = [
  { id: "dashboard", label: { sv: "Dashboard", en: "Dashboard" } },
  { id: "chat", label: { sv: "Live-chatt (preview)", en: "Live chat (preview)" } },
  { id: "inbox", label: { sv: "Snabb-triage", en: "Quick triage" } },
  { id: "integration", label: { sv: "Integration & API", en: "Integration & API" } }
] as const;

type TabId = (typeof tabs)[number]["id"];

const highlights = [
  {
    title: { sv: "Sorterar i fack", en: "Sorts into queues" },
    body: {
      sv: "Teknisk support, garanti, leverans, utbildning, reklamation, betalning och orderstatus. Varje ärende klassas och prioriteras automatiskt.",
      en: "Technical support, warranty, delivery, training, claims, payment and order status. Every case is classified and prioritised automatically."
    }
  },
  {
    title: { sv: "Hittar aldrig på", en: "Never makes things up" },
    body: {
      sv: "Svaren grundas enbart i er kunskapsbas via semantisk sökning. Saknas svar eskaleras ärendet till en människa.",
      en: "Replies are grounded solely in your knowledge base via semantic search. If no answer exists, the case escalates to a human."
    }
  },
  {
    title: { sv: "Ser vad kunden ser", en: "Sees what the customer sees" },
    body: {
      sv: "Skärmdumpar på felmeddelanden och bilder på skadade paket tolkas direkt och styr ärendet till rätt fack.",
      en: "Screenshots of error messages and photos of damaged parcels are interpreted directly and route the case correctly."
    }
  },
  {
    title: { sv: "Vet när människor behövs", en: "Knows when humans are needed" },
    body: {
      sv: "Återbetalningar, juridik, GDPR och arga kunder lämnas alltid vidare, med komplett ärendehistorik.",
      en: "Refunds, legal matters, GDPR and angry customers are always handed over, with the full case history."
    }
  }
];

export function SnajpSupportDemo() {
  const { text } = useLocale();
  const [tab, setTab] = useState<TabId>("dashboard");

  return (
    <div className="space-y-12">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {highlights.map((item) => (
          <div key={item.title.sv} className="rounded-[10px] border border-ink/12 bg-paper p-5 shadow-hairline">
            <h3 className={rubrikPanel}>{text(item.title)}</h3>
            <p className="mt-2 text-[0.9375rem] leading-6 text-ink-muted">{text(item.body)}</p>
          </div>
        ))}
      </div>

      <div>
        <div className="flex flex-wrap gap-2">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              aria-pressed={tab === item.id}
              className={cn(flik, tab === item.id ? flikAktiv : flikInaktiv)}
            >
              {text(item.label)}
            </button>
          ))}
        </div>

        <div className="mt-8">
          {tab === "dashboard" ? <Dashboard /> : null}
          {tab === "chat" ? (
            <div className="mx-auto max-w-3xl">
              <SupportChat />
            </div>
          ) : null}
          {tab === "inbox" ? <InboxTriage /> : null}
          {tab === "integration" ? <IntegrationSection /> : null}
        </div>
      </div>
    </div>
  );
}
