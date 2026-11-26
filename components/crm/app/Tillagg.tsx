"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Blocks } from "lucide-react";
import { Button } from "@astryxdesign/core/Button";
import { Card } from "@astryxdesign/core/Card";
import { Icon } from "@astryxdesign/core/Icon";
import { Objektikon } from "@/components/crm/app/kit";
import { Sida } from "@/components/crm/app/Sida";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { CrmFel, TILLAGG_SAKNAS, crmAnrop, type Jag } from "@/lib/crm/api";
import { useLocale } from "@/lib/i18n";

/** Arbetsytans tillgång till CRM:et: okänd tills `/v1/me` svarat, sedan ja eller saknas. */
export type Tillgang = "okand" | "ja" | "saknas";

const Kontext = createContext<Tillgang>("okand");

/** Tillgången som skalet avgjort. Vyer som vill veta läser den här, de frågar inte själva. */
export const useTillgang = () => useContext(Kontext);

/**
 * Avgör på ETT ställe om arbetsytan når CRM:et (snajp-support/app/crm/tillgang.py:
 * tillägget, eller en provperiod som inte gått ut). Skalet frågar `/v1/me` en
 * gång; dessutom svarar varje CRM-anrop 403 `addon_missing` om tillgången
 * upphör mitt i ett besök (provperioden tar slut), och `crmAnrop` säger då till
 * här. Utfallet delas genom en kontext.
 */
export function TillgangKalla({ children }: Readonly<{ children: React.ReactNode }>) {
  const [tillgang, setTillgang] = useState<Tillgang>("okand");

  useEffect(() => {
    let aktuell = true;
    crmAnrop<Jag>("/v1/me")
      .then(() => aktuell && setTillgang((t) => (t === "saknas" ? t : "ja")))
      .catch((e) => {
        if (!aktuell) return;
        // Bara beskedet om tillägget stänger CRM:et; andra fel visar varje vy själv.
        if (e instanceof CrmFel && e.kod === TILLAGG_SAKNAS) setTillgang("saknas");
        else setTillgang((t) => (t === "saknas" ? t : "ja"));
      });
    const saknas = () => setTillgang("saknas");
    window.addEventListener(TILLAGG_SAKNAS, saknas);
    return () => {
      aktuell = false;
      window.removeEventListener(TILLAGG_SAKNAS, saknas);
    };
  }, []);

  return <Kontext.Provider value={tillgang}>{children}</Kontext.Provider>;
}

/**
 * Helsidan i skalets form när tillägget saknas: vad Snajp CRM är, att det är ett
 * tillägg som ingår fritt under provperioden, och vägen vidare. Plattformsadmin
 * får veta var tillägget slås på; en kund att höra av sig till Snajp.
 */
export function TillaggSaknas() {
  const { text } = useLocale();
  const admin = useDashboard().isPlatformAdmin;

  return (
    <Sida rubrik="Snajp CRM" utfyllnad="sida">
      <div className="pt-4">
        <Card padding={8} className="crm-kort">
          <section aria-labelledby="crm-tillagg-rubrik" className="mx-auto flex max-w-[36rem] flex-col items-center gap-4 py-6 text-center">
            <Objektikon ikon={Blocks} ton="ockra" storlek={32} />
            <h2 id="crm-tillagg-rubrik" className="font-sans text-[1.0625rem] font-semibold tracking-normal text-ink">
              {text({ sv: "Snajp CRM är inte påslaget för arbetsytan", en: "Snajp CRM is not turned on for this workspace" })}
            </h2>
            <div className="flex flex-col gap-3 text-[0.9375rem] leading-relaxed text-ink2">
                <p>
                  {text({
                    sv: "Snajp CRM samlar era bolag, kontaktpersoner och synken från ert CRM eller ekonomisystem på ett ställe. Det är ett tillägg till Snajp och ingår fritt under provperioden.",
                    en: "Snajp CRM gathers your companies, contacts and the sync from your CRM or accounting system in one place. It is an add-on to Snajp and is included free during the trial."
                  })}
                </p>
                <p>
                  {admin
                    ? text({
                        sv: "Arbetsytan har varken tillägget eller en pågående provperiod. Slå på tillägget under Admin, kunden, Tillägg.",
                        en: "The workspace has neither the add-on nor an ongoing trial. Turn the add-on on under Admin, the customer, Add-ons."
                      })
                    : text({
                        sv: "Arbetsytan har varken tillägget eller en pågående provperiod. Hör av er till Snajp på kontakt@snajp.se, så slår vi på det.",
                        en: "The workspace has neither the add-on nor an ongoing trial. Contact Snajp at kontakt@snajp.se and we will turn it on."
                      })}
                </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 pt-2">
              {admin ? (
                <Button variant="primary" label={text({ sv: "Till kunderna i Admin", en: "Go to customers in Admin" })} endContent={<Icon icon={ArrowRight} size="sm" />} href="/admin/kunder" />
              ) : (
                <Button variant="primary" label={text({ sv: "Mejla Snajp", en: "Email Snajp" })} href="mailto:kontakt@snajp.se" />
              )}
              <Button variant="secondary" label={text({ sv: "Till arbetsytan", en: "Back to workspace" })} icon={<Icon icon={ArrowLeft} size="sm" />} href="/dashboard" />
            </div>
          </section>
        </Card>
      </div>
    </Sida>
  );
}
