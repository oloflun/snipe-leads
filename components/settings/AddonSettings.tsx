"use client";

import { addonCatalog } from "@/lib/addons";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { mejlaOss } from "@/components/marketing/copy";
import { Rad, Radlista } from "@/components/ui";
import { useLocale } from "@/lib/i18n";

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
  const { text } = useLocale();

  return (
    <div className="grid gap-8">
      {/* Ingen egen ingress här. Sidrubriken ovanför säger redan "Det agenten kan
          göra utöver det som ingår i er plan", och den här upprepade det med
          andra ord — två meningar om samma sak, synligt bredvid varandra i
          samma vy. Sett i pixlar. */}

      <Radlista ariaLabel={text({ sv: "Tilläggstjänster", en: "Add-on services" })}>
        {addonCatalog.map((addon) => {
          const active = addons.includes(addon.key);
          return (
            <Rad key={addon.key} className="min-w-0">
              <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
                <h4 className="min-w-0 break-words text-[17px]">{text(addon.name)}</h4>
                {/* Ochre bara på avvikelsen — här "ingår", som är det
                    ovanliga tillståndet. Ett aktivt tillägg är nyheten;
                    ett låst är utgångsläget och behöver ingen färg. */}
                <span
                  className={
                    active
                      ? "kicker shrink-0 text-warning"
                      : "kicker shrink-0 text-mineral"
                  }
                >
                  {active ? text({ sv: "Ingår", en: "Included" }) : text({ sv: "Tillval", en: "Optional" })}
                </span>
              </div>

              <p className="mt-3 max-w-[64ch] text-[15px] leading-7">{text(addon.what)}</p>

              {!active ? (
                <a
                  href={mejlaOss(text({ sv: `Tillägg: ${addon.name.sv}`, en: `Add-on: ${addon.name.en}` }))}
                  className="mt-4 inline-block text-[13px] underline underline-offset-4 transition hover:text-ochre"
                >
                  {text({ sv: `Hör av dig om ${addon.name.sv.toLowerCase()}`, en: `Get in touch about ${addon.name.en.toLowerCase()}` })}
                </a>
              ) : null}
            </Rad>
          );
        })}
      </Radlista>
    </div>
  );
}
