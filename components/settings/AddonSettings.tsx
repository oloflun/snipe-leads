"use client";

import { addonCatalog } from "@/lib/addons";
import { useDashboard } from "@/components/dashboard/DashboardContext";

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
    <div className="grid gap-8">
      {/* Ingen egen ingress här. Sidrubriken ovanför säger redan "Det agenten kan
          göra utöver det som ingår i er plan", och den här upprepade det med
          andra ord — två meningar om samma sak, synligt bredvid varandra i
          samma vy. Sett i pixlar. */}

      <ul className="grid gap-px">
        {addonCatalog.map((addon) => {
          const active = addons.includes(addon.key);
          return (
            <li key={addon.key} className="min-w-0 border-t border-ink/15 py-6">
              <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
                <h4 className="min-w-0 break-words text-[17px]">{addon.name}</h4>
                {/* Ochre bara på avvikelsen — här "ingår", som är det
                    ovanliga tillståndet. Ett aktivt tillägg är nyheten;
                    ett låst är utgångsläget och behöver ingen färg. */}
                <span
                  className={
                    active
                      ? "kicker shrink-0 text-ochre"
                      : "kicker shrink-0 text-mineral"
                  }
                >
                  {active ? "Ingår" : "Tillval"}
                </span>
              </div>

              <p className="mt-3 max-w-[64ch] text-[15px] leading-7">{addon.what}</p>

              {!active ? (
                <>
                  <p className="mt-2 max-w-[64ch] text-[14px] leading-6 text-mineral">
                    {addon.why}
                  </p>
                  <a
                    href={`mailto:Snajpsupport@gmail.com?subject=${encodeURIComponent(`Tillägg: ${addon.name}`)}`}
                    className="mt-4 inline-block text-[13px] underline underline-offset-4 transition hover:text-ochre"
                  >
                    Hör av dig om {addon.name.toLowerCase()}
                  </a>
                </>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
