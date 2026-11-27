"use client";

import { useEffect, useRef, useState } from "react";
import NextLink from "next/link";
import { Activity, Clock, Landmark, MailX } from "lucide-react";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { Icon } from "@astryxdesign/core/Icon";
import { MetadataList, MetadataListItem } from "@astryxdesign/core/MetadataList";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { CrmFel, crmAnrop, type Bolag } from "@/lib/crm/api";
import { FALT, uppraknat } from "@/lib/crm/felkoder";
import { REGISTERNAMN, REGISTERSTATUS, type Berikning } from "@/lib/crm/register";
import { useLocale, type Localized } from "@/lib/i18n";

/**
 * Bolagets uppgifter ur SCB:s företagsregister, i fliken Källa: registrets
 * status, när det senast lästes, och knappen som fyller bolagets tomma fält
 * (`POST /v1/companies/{id}/enrich`). Ett fält som redan har ett värde står
 * kvar; säger registret annat står det i utfallet, med valet att skriva över.
 *
 * Bara bolagsnivå (Antons beslut 2026-11-27). En enskild firma och en
 * privatperson slås inte upp: numret hör till en person.
 */
export function Registret({
  bolag,
  etikett,
  sparrvag,
  uppdaterat
}: Readonly<{ bolag: Bolag; etikett: { position: "start"; width: number }; sparrvag: string; uppdaterat?: (b: Bolag) => void }>) {
  const { text } = useLocale();
  const [hamtar, setHamtar] = useState<"fyll" | "skriv" | null>(null);
  const [utfall, setUtfall] = useState<Berikning | null>(null);
  const [fel, setFel] = useState<Localized | null>(null);
  // Skriv över går inte att ångra (historiken bär fältens namn, inte värdena): ett steg till innan det sker.
  const [bekraftar, setBekraftar] = useState(false);
  // Bolaget som visas nu. Ett svar som kommer efter att panelen bytt bolag slängs.
  const visat = useRef(bolag.id);
  visat.current = bolag.id;

  useEffect(() => {
    setUtfall(null);
    setFel(null);
    setHamtar(null);
    setBekraftar(false);
  }, [bolag.id]);

  const person = bolag.private_person || bolag.sole_proprietor;
  const namn = (falt: string[]) => uppraknat(falt.map((f) => (FALT[f] ? text(FALT[f].naken) : f)), text({ sv: "och", en: "and" }));

  async function hamta(skrivOver: boolean) {
    if (hamtar) return;
    const fragat = bolag.id;
    setHamtar(skrivOver ? "skriv" : "fyll");
    setFel(null);
    setBekraftar(false);
    try {
      const svar = await crmAnrop<Berikning>(`/v1/companies/${encodeURIComponent(fragat)}/enrich${skrivOver ? "?overwrite=true" : ""}`, { method: "POST" });
      if (visat.current !== fragat) return;
      setUtfall(svar);
      uppdaterat?.(svar.company);
    } catch (orsak) {
      if (visat.current !== fragat) return;
      setUtfall(null);
      setFel(orsak instanceof CrmFel ? orsak.text : { sv: "Okänt fel.", en: "Unknown error." });
    } finally {
      if (visat.current === fragat) setHamtar(null);
    }
  }

  const status = bolag.registry_status ?? null;
  return (
    <div className="crm-kallkort flex flex-col gap-3 rounded-[16px] p-4">
      <MetadataList label={etikett}>
        <MetadataListItem label={text({ sv: "Register", en: "Registry" })} icon={<Icon icon={Landmark} size="sm" />}>
          {/* Hela namnet ryms inte bredvid etiketten på telefon: där står förkortningen. */}
          <span className="crm-varde">
            <span className="sm:hidden">SCB</span>
            <span className="hidden sm:inline">{text(REGISTERNAMN)}</span>
          </span>
        </MetadataListItem>
        <MetadataListItem label={text({ sv: "Status", en: "Status" })} icon={<Icon icon={Activity} size="sm" />}>
          {status ? (
            <Badge variant={REGISTERSTATUS[status]?.badge ?? "neutral"} label={text(REGISTERSTATUS[status]?.namn ?? { sv: status, en: status })} />
          ) : (
            <span className="crm-varde text-ink-muted">{text({ sv: "Inte hämtad", en: "Not fetched" })}</span>
          )}
        </MetadataListItem>
        {bolag.registry_advertising_block != null ? (
          <MetadataListItem label={text({ sv: "Reklamspärr", en: "Advertising block" })} icon={<Icon icon={MailX} size="sm" />}>
            <span className="crm-varde">{bolag.registry_advertising_block ? text({ sv: "Ja, i registret", en: "Yes, in the registry" }) : text({ sv: "Nej", en: "No" })}</span>
          </MetadataListItem>
        ) : null}
        {bolag.registry_checked_at ? (
          <MetadataListItem label={text({ sv: "Senast hämtad", en: "Last fetched" })} icon={<Icon icon={Clock} size="sm" />}>
            <Timestamp value={bolag.registry_checked_at} format="relative" color="primary" />
          </MetadataListItem>
        ) : null}
      </MetadataList>

      {person ? (
        <p className="text-[0.8125rem] text-ink-muted">
          {text({
            sv: "En enskild firma eller privatperson slås inte upp i registret: numret hör till en person.",
            en: "A sole proprietorship or private person is not looked up in the registry: the number belongs to a person."
          })}
        </p>
      ) : (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <Button
            size="sm"
            variant="secondary"
            label={status ? text({ sv: "Hämta igen", en: "Fetch again" }) : text({ sv: "Hämta ur registret", en: "Fetch from the registry" })}
            isLoading={hamtar === "fyll"}
            isDisabled={!bolag.org_number || hamtar === "skriv"}
            onClick={() => void hamta(false)}
          />
          <span className="text-[0.8125rem] text-ink-muted">
            {bolag.org_number
              ? text({ sv: "Fyller tomma fält. Det du själv skrivit står kvar.", en: "Fills empty fields. What you have written stays." })
              : text({ sv: "Bolaget saknar organisationsnummer.", en: "The company has no organisation number." })}
          </span>
        </div>
      )}

      {/* Det som står på posten och därför finns kvar efter en omladdning. */}
      {status === "deregistered" ? (
        <p className="text-[0.875rem] text-danger">{text({ sv: "Bolaget är avregistrerat i registret.", en: "The company is deregistered in the registry." })}</p>
      ) : null}
      {bolag.registry_advertising_block ? (
        <p className="text-[0.875rem] text-ink2">
          {text({ sv: "Bolaget har reklamspärr i registret. Den stoppar inget här förrän bolaget står i ", en: "The company has an advertising block in the registry. It stops nothing here until the company is in " })}
          <NextLink href={`${sparrvag}?ny=1`} className="underline underline-offset-2">
            {text({ sv: "Spärrar", en: "Blocks" })}
          </NextLink>
          .
        </p>
      ) : null}

      {/* Utfallet av hämtningen. Regionen finns hela tiden och byter bara innehåll, så att beskedet sägs upp. */}
      <div role="status" className="flex flex-col gap-2 empty:-mt-3">
        {fel ? <p className="text-[0.875rem] text-danger">{text(fel)}</p> : null}
        {utfall ? (
          <>
            <p className="text-[0.875rem] text-ink">
              {utfall.filled.length
                ? text({ sv: `Hämtat ur registret: ${namn(utfall.filled)}.`, en: `Fetched from the registry: ${namn(utfall.filled)}.` })
                : text({ sv: "Inget nytt att fylla i.", en: "Nothing new to fill in." })}
            </p>
            {utfall.skipped.length ? (
              bekraftar ? (
                <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                  <p className="min-w-0 flex-1 basis-56 text-[0.875rem] text-ink">
                    {text({
                      sv: `Bolagets ${namn(utfall.skipped)} ersätts med registrets. Det går inte att ångra.`,
                      en: `The company's ${namn(utfall.skipped)} will be replaced with the registry's. This cannot be undone.`
                    })}
                  </p>
                  <Button size="sm" variant="ghost" label={text({ sv: "Avbryt", en: "Cancel" })} onClick={() => setBekraftar(false)} />
                  <Button size="sm" variant="secondary" label={text({ sv: "Skriv över", en: "Overwrite" })} isLoading={hamtar === "skriv"} onClick={() => void hamta(true)} />
                </div>
              ) : (
                <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                  <p className="min-w-0 flex-1 basis-56 text-[0.875rem] text-ink2">
                    {text({
                      sv: `Registret säger annat om ${namn(utfall.skipped)}. Bolagets egna värden står kvar.`,
                      en: `The registry says otherwise about ${namn(utfall.skipped)}. The company's own values stay.`
                    })}
                  </p>
                  <Button size="sm" variant="ghost" label={text({ sv: "Skriv över med registrets", en: "Overwrite with the registry's" })} isDisabled={hamtar != null} onClick={() => setBekraftar(true)} />
                </div>
              )
            ) : null}
            {utfall.protected?.length ? (
              <p className="text-[0.875rem] text-ink2">
                {text({
                  sv: `Registret säger också annat om ${namn(utfall.protected)}, som är ändrat för hand här och aldrig skrivs över. Ändra fältet själv om registret har rätt.`,
                  en: `The registry also says otherwise about ${namn(utfall.protected)}, which was edited by hand here and is never overwritten. Change the field yourself if the registry is right.`
                })}
              </p>
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}
