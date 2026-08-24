"use client";

import { Fragment, useRef } from "react";
import type { ProductKey } from "@/lib/routes";
import { productKeys } from "@/lib/routes";
import { useLocale } from "@/lib/i18n";
import { productCopy, shared } from "@/components/marketing/copy";
import { cn } from "@/lib/utils";

/**
 * The signature control. It is literally the second word of the wordmark, so the
 * page reads "Snajp Leads / Support" and the live product is the italic one.
 *
 * Italic carries meaning here rather than decoration: it marks the word that
 * changes. That is the only italic DESIGN.md allows outside the hero, and this
 * IS the hero.
 */
export function ProductSwitch({
  value,
  onChange,
  tone = "ink",
  brytEfter
}: Readonly<{
  value: ProductKey;
  onChange: (next: ProductKey) => void;
  tone?: "ink" | "paper";
  /**
   * Tvinga en radbrytning EFTER den här produkten.
   *
   * Med tre produkter ryms inte raden i hjältebildens 219px-kolumn, och den
   * naturliga brytningen lade "Bokföring" ensamt på rad två — alltså under
   * "Leads" i stället för bredvid "Support". Här styrs brytpunkten i stället:
   * "Leads /" på första raden, "Support / Bokföring" på den andra.
   */
  brytEfter?: ProductKey;
}>) {
  const { text } = useLocale();
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  function onKeyDown(event: React.KeyboardEvent<HTMLButtonElement>) {
    const index = productKeys.indexOf(value);
    let next: ProductKey | null = null;

    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      next = productKeys[(index + 1) % productKeys.length];
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      next = productKeys[(index - 1 + productKeys.length) % productKeys.length];
    } else if (event.key === "Home") {
      next = productKeys[0];
    } else if (event.key === "End") {
      next = productKeys[productKeys.length - 1];
    }

    if (next) {
      event.preventDefault();
      onChange(next);
      refs.current[next]?.focus();
    }
  }

  return (
    // `flex flex-wrap` i stället för `inline`: brytpunkten ska vara vald, inte
    // upphittad av radbrytningen. Se `brytEfter`.
    <span role="tablist" aria-label={text(shared.switchLabel)} className="flex flex-wrap items-baseline">
      {productKeys.map((key, index) => {
        const selected = key === value;
        return (
          <Fragment key={key}>
            {/* Snedstrecket följer sitt eget ord i stället för att inleda
                nästa. Annars hade en bruten rad börjat med "/ Support". */}
            <span className="inline-flex items-baseline whitespace-nowrap">
            <button
              ref={(node) => {
                refs.current[key] = node;
              }}
              type="button"
              role="tab"
              id={`product-tab-${key}`}
              aria-selected={selected}
              aria-controls={`product-panel-${key}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(key)}
              onKeyDown={onKeyDown}
              className={cn(
                "focus-ring inline-flex min-h-11 items-center rounded-input transition-colors duration-200 ease-out",
                selected
                  ? tone === "paper"
                    ? "italic-disp text-paper"
                    : "italic-disp text-ink"
                  : tone === "paper"
                    ? "text-paper/40 hover:text-paper/75"
                    : "text-ink/25 hover:text-ink/60 active:text-ink/70"
              )}
            >
              {text(productCopy[key].word)}
            </button>
            {index < productKeys.length - 1 ? (
              <span aria-hidden="true" className={cn("mx-1 md:mx-2", tone === "paper" ? "text-paper/30" : "text-ink/20")}>
                /
              </span>
            ) : null}
            </span>
            {/* Radbrytningen i en flex-rad: ett tomt element med hela radens
                bredd och ingen höjd. Raden det hamnar på blir noll hög, så
                det syns ingen lucka. */}
            {brytEfter === key ? <span aria-hidden="true" className="h-0 basis-full" /> : null}
          </Fragment>
        );
      })}
    </span>
  );
}
