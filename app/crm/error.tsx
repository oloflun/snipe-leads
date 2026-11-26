"use client";

import { useEffect } from "react";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { Sida } from "@/components/crm/app/Sida";
import { useLocale } from "@/lib/i18n";

/**
 * Felgränsen för CRM:ets vyer. Den ritas inuti skalet (app/crm/layout.tsx), så
 * navigeringen står kvar och användaren kan gå vidare till en annan vy. Som
 * app/error.tsx återges inte felmeddelandet: det kan bära interna detaljer.
 * `digest` är Nexts opaka referens och säker att visa.
 */
export default function CrmFel({ error, reset }: Readonly<{ error: Error & { digest?: string }; reset: () => void }>) {
  const { text } = useLocale();

  useEffect(() => {
    console.error("CRM error boundary caught:", error);
  }, [error]);

  return (
    <Sida rubrik={text({ sv: "Något gick fel", en: "Something went wrong" })} utfyllnad="sida">
      <div className="flex flex-col gap-4 pt-4">
        <Banner
          status="error"
          container="card"
          title={text({ sv: "Vyn kunde inte visas", en: "The view could not be shown" })}
          description={text({
            sv: "Felet är loggat på vår sida. Prova igen, eller välj en annan vy i menyn. Hjälper inte det, mejla kontakt@snajp.se.",
            en: "The error has been logged on our side. Try again, or pick another view in the menu. If that does not help, email kontakt@snajp.se."
          })}
          endContent={<Button size="sm" variant="primary" label={text({ sv: "Försök igen", en: "Try again" })} onClick={reset} />}
        />
        {error.digest ? (
          <p className="text-[0.8125rem] text-ink-muted">
            {text({ sv: "Felkod", en: "Error code" })} <code className="crm-kod">{error.digest}</code>
          </p>
        ) : null}
      </div>
    </Sida>
  );
}
