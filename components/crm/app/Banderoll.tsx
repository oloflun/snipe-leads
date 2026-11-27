"use client";

import { useState } from "react";
import { Eye, FlaskConical, Glasses } from "lucide-react";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { Icon } from "@astryxdesign/core/Icon";
import { Spinner } from "@astryxdesign/core/Spinner";
import { useSkaletsAtgarder } from "@/components/crm/app/Skalet";
import { mejlaOss } from "@/components/marketing/copy";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { useLocale } from "@/lib/i18n";

/**
 * Banderollen (NYTT MÖNSTER, SK-076 till SK-079, AD-009): en fast rad överst i
 * bladet som säger i vilket läge man tittar, på varje vy, eftersom skalet bär den.
 *
 * - **Kundbesök** (`impersonation`): "Du testar som <kund>", i ockra, med
 *   Avsluta besöket. Kundbesöket visar kundens riktiga uppgifter i exakt samma
 *   gränssnitt som den egna arbetsytan; utan banderollen går lägena inte att skilja.
 * - **Läsroll** (`arLasare`): lugn och neutral. Läsaren gör inget fel; raden
 *   förklarar varför knappar är avstängda.
 * - **Vybyte** (menyns Admin och Demo, `vybyte` i Skalet.tsx): förloppet, och
 *   felet med Försök igen när server actionen inte bytte.
 * - **Demo**: en demoarbetsyta (`isDemo`) får begränsningen och Kontakta oss,
 *   adminens demovy (`vy === "demo"`) bara märkningen.
 *
 * Ritregel, inte grind: spärrarna sitter i proxyn och i `aktivVy()`. Nästa
 * läge som behöver en rad överst lägger en gren här, inte en egen ruta i vyn.
 * Formen: Astryx `Banner` som sektion, en rad på bred skärm (crm.css: .crm-banderoll).
 */
export function Banderoll() {
  const { text } = useLocale();
  const { impersonation, arLasare, isDemo, vy } = useDashboard();
  const { bytVy, vybyte, bytVyMedBesked, glomVybyte } = useSkaletsAtgarder();
  const [avslutar, setAvslutar] = useState(false);
  const [fel, setFel] = useState(false);

  // Vyväxeln i menyn (Admin, Demo): förloppet och felet, före läget man lämnar.
  if (vybyte) {
    const mal = vybyte.varde === "demo" ? text({ sv: "Demo", en: "Demo" }) : text({ sv: "Admin", en: "Admin" });
    return (
      <div role="status" className="crm-banderoll">
        {vybyte.lage === "pagar" ? (
          <Banner
            status="info"
            container="section"
            icon={<Spinner size="sm" label={text({ sv: "Byter vy", en: "Switching view" })} />}
            title={text({ sv: `Byter till ${mal}.`, en: `Switching to ${mal}.` })}
          />
        ) : (
          <Banner
            status="error"
            container="section"
            title={text({ sv: `Vyn gick inte att byta till ${mal}.`, en: `The view could not be switched to ${mal}.` })}
            description={text({ sv: "Ladda om sidan och försök igen. Har du loggats ut, logga in igen.", en: "Reload the page and try again. If you have been signed out, sign in again." })}
            endContent={
              <>
                <Button size="sm" variant="secondary" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => bytVyMedBesked(vybyte.varde)} />
                <Button size="sm" variant="ghost" label={text({ sv: "Stäng", en: "Close" })} onClick={glomVybyte} />
              </>
            }
          />
        )}
      </div>
    );
  }

  if (impersonation) {
    return (
      <div role="status" className="crm-banderoll crm-banderoll-besok">
        <Banner
          status="warning"
          container="section"
          icon={<Icon icon={Eye} size="sm" color="inherit" />}
          title={
            <>
              {text({ sv: "Du testar som ", en: "You are testing as " })}
              <strong className="font-semibold">{impersonation.namn}</strong>.
            </>
          }
          description={
            fel
              ? text({ sv: "Besöket gick inte att avsluta. Försök igen.", en: "The visit could not be ended. Try again." })
              : text({
                  sv: "Allt du kör här är test och syns inte på kundens riktiga profil. Inga skärmdumpar.",
                  en: "Everything you run here is a test and is not visible on the customer's real profile. No screenshots."
                })
          }
          endContent={
            <Button
              size="sm"
              variant="secondary"
              label={text({ sv: "Avsluta besöket", en: "End the visit" })}
              isLoading={avslutar}
              onClick={async () => {
                setAvslutar(true);
                setFel(false);
                const bytt = await bytVy("admin").catch(() => false);
                // Lyckat byte laddar om sidan; annars står knappen kvar med beskedet.
                if (!bytt) {
                  setAvslutar(false);
                  setFel(true);
                }
              }}
            />
          }
        />
      </div>
    );
  }

  if (arLasare) {
    return (
      <div role="status" className="crm-banderoll crm-banderoll-lasroll">
        <Banner
          status="info"
          container="section"
          icon={<Icon icon={Glasses} size="sm" color="inherit" />}
          title={text({ sv: "Du har läsbehörighet.", en: "You have read access." })}
          description={text({
            sv: "Du ser allt som händer i arbetsytan, men kan inte ändra något.",
            en: "You see everything that happens in the workspace, but cannot change anything."
          })}
        />
      </div>
    );
  }

  if (isDemo || vy === "demo") {
    // Adminens demovy bär bara märkningen; en demoarbetsyta också begränsningen och vägen ut.
    const arbetsyta = isDemo && vy !== "demo";
    return (
      <div role="status" className="crm-banderoll crm-banderoll-demo">
        <Banner
          status="warning"
          container="section"
          icon={<Icon icon={FlaskConical} size="sm" color="inherit" />}
          title={text({ sv: "Demo", en: "Demo" })}
          description={
            arbetsyta
              ? text({ sv: "Du testar Snajp med ett begränsat antal körningar.", en: "You are trying Snajp with a limited number of runs." })
              : undefined
          }
          endContent={arbetsyta ? <Button size="sm" variant="secondary" label={text({ sv: "Kontakta oss", en: "Contact us" })} href={mejlaOss()} /> : undefined}
        />
      </div>
    );
  }

  return null;
}
