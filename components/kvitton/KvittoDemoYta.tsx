"use client";

import { useState } from "react";
import { KvittoDemo } from "@/components/kvitton/KvittoDemo";
import { KvittoFlikar, type KvittoFlik } from "@/components/kvitton/KvittoFlikar";
import { KvittoOversikt } from "@/components/kvitton/KvittoOversikt";

/**
 * /demo/kvitton: Översikten först (demodata ur lib/demo/kvitto-oversikt.ts),
 * skanningen under fliken bredvid — samma två flikar som arbetsytans KvittoVy.
 * KvittoDemo ensam är fortfarande produktsidans demo (ProductPage).
 */
export function KvittoDemoYta({ visaDrift = false }: Readonly<{ visaDrift?: boolean }>) {
  const [vald, setVald] = useState<KvittoFlik>("oversikt");
  return (
    <div>
      <KvittoFlikar vald={vald} onValj={setVald} etiketter={{ kvitton: { sv: "Skanningen", en: "Scanning" } }} />
      <div className="mt-6">
        {vald === "oversikt" ? <KvittoOversikt demo visaDrift={visaDrift} onOppnaKvitton={() => setVald("kvitton")} /> : <KvittoDemo />}
      </div>
    </div>
  );
}
