"use client";

import { addonCatalog } from "@/lib/addons";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { mejlaOss } from "@/components/marketing/copy";
import { Badge, Rad, Radlista, rubrikPanel } from "@/components/ui";
import { cn } from "@/lib/utils";

/**
 * Tilläggstjänsterna, aktiva och låsta i samma lista.
 *
 * Ett låst tillägg renderas som ett ruled kort med vad det är och varför det
 * inte ingår — inte som en gråad menyrad. Ett tillägg som bara är osynligt
 * säljer ingenting: den som inte vet att bildanalys finns frågar aldrig efter
 * den, och den som ser en gråad rad utan förklaring läser det som en bugg.
 *
 * Skälet står med. Ett tillägg utan skäl läser som godtycke, och då är nästa
 * fråga "kan ni inte bara slå på det" i stället för "vad kostar det".
 */
export function AddonSettings() {
  const { addons } = useDashboard();

  return (
    // Ingen ingress. Sidan hade en i form av sidrubrikens beskrivning, och den
    // här komponenten en till med samma innehåll i andra ord; båda är borta
    // (F-016). Raden bär namn, status, vad tillägget gör och, för det som inte
    // ingår, skälet och vägen dit.
    <Radlista ariaLabel="Tilläggstjänster">
      {addonCatalog.map((addon) => {
        const active = addons.includes(addon.key);
        return (
          <Rad key={addon.key} className="min-w-0">
            <div className="flex min-w-0 flex-wrap items-center justify-between gap-x-6 gap-y-2">
              <h2 className={cn(rubrikPanel, "min-w-0 break-words")}>{addon.name}</h2>
              {/* Färg bara på avvikelsen: "Ingår" är det ovanliga tillståndet.
                  Ett låst tillägg är utgångsläget och får den neutrala brickan. */}
              <Badge tone={active ? "good" : "neutral"}>{active ? "Ingår" : "Tillval"}</Badge>
            </div>

            <p className="mt-2 max-w-[64ch] text-[0.9375rem] leading-6 text-ink">{addon.what}</p>

            {!active ? (
              <>
                <p className="mt-1 max-w-[64ch] text-[0.9375rem] leading-6 text-ink-muted">
                  {addon.why}
                </p>
                <a
                  href={mejlaOss(`Tillägg: ${addon.name}`)}
                  className="focus-ring mt-3 inline-flex min-h-11 items-center rounded-input text-[0.9375rem] underline underline-offset-4 transition hover:text-ochre"
                >
                  Hör av dig om {addon.name.toLowerCase()}
                </a>
              </>
            ) : null}
          </Rad>
        );
      })}
    </Radlista>
  );
}
