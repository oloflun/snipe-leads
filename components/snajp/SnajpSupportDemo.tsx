"use client";

import { useState } from "react";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { InboxTriage } from "./InboxTriage";
import { IntegrationSection } from "./IntegrationSection";
import { SupportChat } from "./SupportChat";

const tabs = [
  { id: "chat", label: { sv: "Chatta med agenten", en: "Chat with the agent" } },
  { id: "inbox", label: { sv: "Inkorg-triage", en: "Inbox triage" } },
  { id: "integration", label: { sv: "Integration & API", en: "Integration & API" } }
] as const;

type TabId = (typeof tabs)[number]["id"];

const highlights = [
  {
    title: { sv: "Sorterar i fack", en: "Sorts into queues" },
    body: {
      sv: "Teknisk support, leverans, betalning, retur & reklamation, konto — varje ärende klassas och prioriteras automatiskt.",
      en: "Technical support, delivery, payment, returns & claims, account — every case is classified and prioritised automatically."
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
      sv: "Återbetalningar, juridik, GDPR och arga kunder lämnas alltid vidare — med komplett ärendehistorik.",
      en: "Refunds, legal matters, GDPR and angry customers are always handed over — with the full case history."
    }
  }
];

export function SnajpSupportDemo() {
  const { text } = useLocale();
  const [tab, setTab] = useState<TabId>("chat");

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
