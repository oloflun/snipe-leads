"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Dashboard } from "./Dashboard";
import { KnowledgeBase } from "./KnowledgeBase";

const API_BASE = "/api/kundtjanst";

const tabs = [
  { id: "inbox", label: "Inkorg" },
  { id: "kb", label: "Kunskapsbas" }
] as const;

type TabId = (typeof tabs)[number]["id"];

export function PilotWorkspace() {
  const [tab, setTab] = useState<TabId>("inbox");

  return (
    <div>
      <div className="flex flex-wrap gap-2 border-b border-ink/12 pb-px">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={cn(
              "focus-ring -mb-px border-b-2 px-4 py-3 text-sm font-semibold transition",
              tab === item.id ? "border-ochre text-ink" : "border-transparent text-ink/50 hover:text-ink"
            )}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="mt-8">
        {tab === "inbox" ? <Dashboard mode="pilot" apiBase={API_BASE} /> : null}
        {tab === "kb" ? <KnowledgeBase apiBase={API_BASE} /> : null}
      </div>
    </div>
  );
}
