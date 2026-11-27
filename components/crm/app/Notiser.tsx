"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { Button } from "@astryxdesign/core/Button";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { List, ListItem } from "@astryxdesign/core/List";
import { Popover } from "@astryxdesign/core/Popover";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { HStack, StackItem } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { Prick, useSkrivratt } from "@/components/crm/app/kit";
import { navpost } from "@/lib/crm/navigering";
import { useLocale } from "@/lib/i18n";
import { klassText, meddelaNotiser, notisEtikett, useNotisantal, type Notis } from "@/lib/leads/konversationer";
import { leadsAnrop } from "@/lib/leads/suite";

/**
 * Notiserna i skalet (NYTT MÖNSTER, SK-064, SK-171, AD-005): olästa svar,
 * svarsutkast och möten hos Iris.
 *
 * Två delar som läser samma tal:
 * - räknaren på menyposten Leads (registret: `raknare: "leadsnotiser"`), i ockra
 *   som `crm-railtal`, och
 * - klockan i sidhuvudet (`NotisKlocka`), som öppnar listan med Markera alla som lästa.
 *
 * Talet hämtas av `useNotisantal` (lib/leads/konversationer.ts), samma krok som
 * dagens app: vid start, varje minut när fliken syns och direkt när något i Leads
 * ändrats. Listan är databasens (migration 149), så den står kvar efter en
 * omladdning. Av i demoarbetsytor och för arbetsytor utan Leads.
 *
 * Nästa vy som visar notiser återanvänder `useNotiser()` och `NotisKlocka`.
 */

type Notislage = { pa: boolean; antal: number; bas: string };

const Kontext = createContext<Notislage>({ pa: false, antal: 0, bas: "/crm" });

export function NotisKalla({ pa, bas, children }: Readonly<{ pa: boolean; bas: string; children: React.ReactNode }>) {
  const antal = useNotisantal(pa);
  return <Kontext.Provider value={{ pa, antal, bas }}>{children}</Kontext.Provider>;
}

export const useNotiser = () => useContext(Kontext);

/** Talet som text: över 99 står det 99+, som i dagens räknare. */
export const notistal = (antal: number) => (antal > 99 ? "99+" : String(antal));

/**
 * Vart en notis leder: konversationen. Tills CRM:et har vyn Konversationer
 * (registret: `iris/konversationer`) öppnas den i dagens Leads.
 */
function notisMal(n: Notis, bas: string): string {
  const trad = n.thread_id ? `trad=${encodeURIComponent(n.thread_id)}` : "";
  return navpost("iris/konversationer")?.byggd
    ? `${bas}/iris/konversationer${trad ? `?${trad}` : ""}`
    : `/dashboard/leads?vy=konversationer${trad ? `&${trad}` : ""}`;
}

/** Klockan i sidhuvudet med antalet olästa, och listan den öppnar. */
export function NotisKlocka() {
  const { text } = useLocale();
  const { pa, antal, bas } = useNotiser();
  const skriv = useSkrivratt();
  const [oppen, setOppen] = useState(false);
  const [notiser, setNotiser] = useState<Notis[] | null>(null);
  const [fel, setFel] = useState(false);
  const [markerar, setMarkerar] = useState(false);
  const [besked, setBesked] = useState("");

  const hamta = useCallback(async () => {
    try {
      const svar = await leadsAnrop<{ notiser: Notis[] }>("/leads/notiser?limit=30");
      setNotiser(svar.notiser);
      setFel(false);
    } catch {
      setFel(true);
      setNotiser((nu) => nu ?? []);
    }
  }, []);

  useEffect(() => {
    if (oppen) void hamta();
  }, [oppen, hamta]);

  if (!pa) return null;

  async function allaLasta() {
    setMarkerar(true);
    try {
      await leadsAnrop("/leads/notiser/last", { method: "POST", body: JSON.stringify({}) });
      meddelaNotiser();
      await hamta();
      setBesked(text({ sv: "Alla notiser är markerade som lästa.", en: "All notifications are marked as read." }));
    } catch {
      setBesked(text({ sv: "Notiserna gick inte att markera som lästa. Försök igen.", en: "The notifications could not be marked as read. Try again." }));
    } finally {
      setMarkerar(false);
    }
  }

  const olasta = notiser?.some((n) => !n.last) ?? false;
  const etikett =
    antal === 1
      ? text({ sv: "Notiser, 1 oläst", en: "Notifications, 1 unread" })
      : text({ sv: `Notiser, ${notistal(antal)} olästa`, en: `Notifications, ${notistal(antal)} unread` });

  const innehall = (
    <div className="flex max-h-[min(70dvh,32rem)] flex-col gap-2">
      <HStack gap={3} vAlign="center">
        <StackItem size="fill">
          <Text as="h2" weight="semibold">
            {text({ sv: "Notiser", en: "Notifications" })}
          </Text>
        </StackItem>
        {olasta ? (
          <Button
            size="sm"
            variant="ghost"
            label={text({ sv: "Markera alla som lästa", en: "Mark all as read" })}
            isLoading={markerar}
            isDisabled={!skriv.far}
            tooltip={skriv.skal ?? undefined}
            onClick={() => void allaLasta()}
          />
        ) : null}
      </HStack>
      {fel ? (
        <Text color="secondary" className="text-danger">
          {text({ sv: "Notiserna gick inte att hämta. Försök igen om en stund.", en: "The notifications could not be loaded. Try again in a moment." })}
        </Text>
      ) : null}
      <div className="-mx-1 min-h-0 overflow-y-auto">
        {notiser === null ? (
          <div role="status" aria-label={text({ sv: "Hämtar notiserna", en: "Loading the notifications" })} className="flex flex-col gap-3 p-2">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} width={`${70 - i * 12}%`} height={12} radius="rounded" index={i} />
            ))}
          </div>
        ) : notiser.length === 0 ? (
          <p className="px-2 py-3 text-[0.875rem] text-ink-muted">
            {text({ sv: "Inga notiser än. Nya svar, utkast och möten hamnar här.", en: "No notifications yet. New replies, drafts and meetings land here." })}
          </p>
        ) : (
          <List hasDividers density="compact">
            {notiser.map((n) => {
              const delar = [n.company_name, n.klass ? klassText(n.klass, text) : null].filter(Boolean).join(" · ");
              return (
                <ListItem
                  key={n.id}
                  href={notisMal(n, bas)}
                  label={
                    <>
                      {text(notisEtikett(n))}
                      {n.last ? null : <span className="sr-only">{text({ sv: ", oläst", en: ", unread" })}</span>}
                    </>
                  }
                  description={delar || undefined}
                  startContent={
                    <span className={n.last ? "invisible inline-flex" : "inline-flex"}>
                      <Prick ton="ockra" />
                    </span>
                  }
                  endContent={<Timestamp value={n.tid} format="relative" hasTooltip={false} />}
                />
              );
            })}
          </List>
        )}
      </div>
    </div>
  );

  return (
    <span className="relative inline-flex">
      <Popover
        label={text({ sv: "Notiser", en: "Notifications" })}
        content={innehall}
        isOpen={oppen}
        onOpenChange={setOppen}
        placement="below"
        alignment="end"
        width={384}
        padding={3}
      >
        <IconButton label={etikett} icon={<Icon icon={Bell} size="sm" />} variant="ghost" size="md" />
      </Popover>
      {antal > 0 ? (
        <span aria-hidden className="crm-railtal crm-klocktal tabular-nums">
          {notistal(antal)}
        </span>
      ) : null}
      <span role="status" className="sr-only">
        {besked}
      </span>
    </span>
  );
}
