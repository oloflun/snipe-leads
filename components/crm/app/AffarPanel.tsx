"use client";

import { useEffect, useState } from "react";
import {
  Building2,
  CalendarCheck,
  CalendarClock,
  CalendarPlus,
  CircleSlash,
  Clock,
  Handshake,
  History,
  LayoutGrid,
  Milestone,
  Pencil,
  Percent,
  Trash2,
  UserRound,
  Users,
  Wallet,
  type LucideIcon
} from "lucide-react";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { Drawer, DrawerHeader } from "@astryxdesign/core/Drawer";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { MetadataList, MetadataListItem } from "@astryxdesign/core/MetadataList";
import { Selector } from "@astryxdesign/core/Selector";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { HStack } from "@astryxdesign/core/Stack";
import { Tab, TabList } from "@astryxdesign/core/TabList";
import { Text } from "@astryxdesign/core/Text";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import type { Affarsfalt } from "@/components/crm/app/AffarFormular";
import { Tidslinje } from "@/components/crm/app/Tidslinje";
import { Personchip, Postchip, Prick, tonklass, useSmal, type Ton } from "@/components/crm/app/kit";
import { belopp, sannolikhet, type Affar, type Affarssteg, type Stegtyp } from "@/lib/crm/affar";
import { crmAnrop, type Person } from "@/lib/crm/api";
import { useLocale, type Localized } from "@/lib/i18n";

type Flik = "oversikt" | "historik";

const ETIKETT_BRED = { position: "start" as const, width: 160 };
const ETIKETT_SMAL = { position: "start" as const, width: 136 };

/** Stegets färg: öppet blått, vunnet mossa, förlorat mineral. Samma i tavlans huvud och i panelen. */
export const STEGTON: Record<Stegtyp, { ton: Ton; badge: "blue" | "green" | "neutral" }> = {
  open: { ton: "bla", badge: "blue" },
  won: { ton: "mossa", badge: "green" },
  lost: { ton: "mineral", badge: "neutral" }
};

/**
 * Affärens panel, i samma form som bolagets (DESIGN-CRM.md § Postens panel):
 * huvud med namn, steg och belopp, flikarna Översikt och Historik, fot med Ta bort.
 *
 * Steget byts här med en väljare: det är tangentbordets och telefonens väg till
 * samma flytt som dra och släpp gör på tavlan.
 */
export function AffarPanel({
  affar,
  laddar,
  steg,
  bolagsnamn,
  bolagVag,
  personVag,
  flyttar,
  stang,
  redigera,
  flytta,
  taBort
}: Readonly<{
  affar: Affar | null;
  /** Sant medan affären hämtas (öppnad från en adress). */
  laddar: boolean;
  steg: Affarssteg[];
  /** Bolagets namn på id, ur tavlans bolagslista. */
  bolagsnamn: (id: string) => string | null;
  /** Vägen till bolagslistan och personlistan: posterna öppnas där. */
  bolagVag: string;
  personVag: string;
  /** Sant medan en flytt sparas. */
  flyttar: boolean;
  stang: () => void;
  redigera: (falt?: Affarsfalt) => void;
  flytta: (a: Affar, stegId: string) => void;
  taBort: (a: Affar) => void;
}>) {
  const { text, locale } = useLocale();
  const smal = useSmal();
  const ETIKETT = smal ? ETIKETT_SMAL : ETIKETT_BRED;
  const [flik, setFlik] = useState<Flik>("oversikt");
  const [person, setPerson] = useState<string | null>(null);
  const id = affar?.id;
  const personId = affar?.person_id ?? null;
  const oppen = affar != null || laddar;

  useEffect(() => {
    setFlik("oversikt");
  }, [id]);

  // Kontaktpersonens namn: tavlan bär bara id:t.
  useEffect(() => {
    setPerson(null);
    if (!personId) return;
    let aktuell = true;
    crmAnrop<Person>(`/v1/people/${encodeURIComponent(personId)}`)
      .then((p) => aktuell && setPerson([p.first_name, p.last_name].filter(Boolean).join(" ") || p.email || null))
      .catch(() => undefined);
    return () => {
      aktuell = false;
    };
  }, [personId]);

  const namn = affar?.name ?? text({ sv: "Namnlös affär", en: "Unnamed deal" });
  const nuSteg = steg.find((s) => s.id === affar?.stage_id);
  const stil = STEGTON[nuSteg?.type ?? "open"];
  const summa = affar ? belopp(affar.amount, affar.currency, locale) : null;
  const chans = affar ? sannolikhet(affar, nuSteg) : null;
  const bolag = affar?.company_id ? bolagsnamn(affar.company_id) : null;
  const ikon = (i: LucideIcon) => <Icon icon={i} size="sm" color="inherit" />;
  const flikikon = (i: LucideIcon) => (smal ? undefined : <Icon icon={i} size="sm" />);

  const rad = (etikett: Localized, i: LucideIcon, innehall: React.ReactNode) => (
    <MetadataListItem label={text(etikett)} icon={ikon(i)}>
      {innehall}
    </MetadataListItem>
  );
  /** Ett tomt värde är en dämpad "Lägg till" som öppnar redigeringen på fältet. */
  const varde = (v: React.ReactNode, falt: Affarsfalt) =>
    v == null || v === "" || v === false ? (
      <button type="button" className="crm-lagg-till" onClick={() => redigera(falt)}>
        {text({ sv: "Lägg till", en: "Add" })}
      </button>
    ) : (
      <span className="crm-varde">{v}</span>
    );
  const datum = (v: string | null) => (v ? <Timestamp value={v} format="date" hasTooltip={false} color="primary" /> : null);

  return (
    <Drawer isOpen={oppen} onOpenChange={(o) => !o && stang()} label={affar ? namn : text({ sv: "Affärens uppgifter", en: "Deal details" })} width={520} hasScrim={false}>
      <Layout
        header={
          <DrawerHeader
            hasDivider={false}
            startContent={
              affar ? (
                <span aria-hidden className={`crm-platta inline-flex size-12 shrink-0 items-center justify-center rounded-[14px] ${tonklass("sigill")}`}>
                  <Icon icon={Handshake} size="md" color="inherit" />
                </span>
              ) : (
                <Skeleton width={48} height={48} radius={3} />
              )
            }
            title={affar ? <span className="crm-postnamn">{namn}</span> : <Skeleton width={200} height={22} radius="rounded" />}
            subtitle={
              affar ? (
                <span className="mt-1 inline-flex flex-wrap items-center gap-2">
                  {nuSteg ? <Badge variant={stil.badge} label={nuSteg.name} icon={<Prick ton={stil.ton} />} /> : null}
                  {summa ? <span className="text-[0.875rem] font-semibold tabular-nums text-ink">{summa}</span> : null}
                </span>
              ) : undefined
            }
            endContent={
              affar ? (
                <IconButton label={text({ sv: "Redigera affären", en: "Edit deal" })} icon={<Icon icon={Pencil} size="sm" />} variant="ghost" onClick={() => redigera()} />
              ) : undefined
            }
            onOpenChange={(o) => !o && stang()}
          />
        }
        content={
          <LayoutContent padding={0}>
            <div data-autofocus tabIndex={-1} className="crm-autofokus">
              {!affar ? (
                <div className="flex flex-col gap-4 px-5 py-4" role="status" aria-busy="true" aria-label={text({ sv: "Hämtar affären", en: "Loading the deal" })}>
                  {Array.from({ length: 6 }, (_, i) => (
                    <div key={i} className="flex items-center gap-4">
                      <Skeleton width={120} height={10} radius="rounded" index={i} />
                      <Skeleton width={`${30 + ((i * 13) % 40)}%`} height={10} radius="rounded" index={i} />
                    </div>
                  ))}
                </div>
              ) : (
                <>
                  <div className="px-5">
                    <TabList value={flik} onChange={(v) => setFlik(v as Flik)} hasDivider role="tablist">
                      <Tab value="oversikt" panelId="crm-affarsflik" label={text({ sv: "Översikt", en: "Overview" })} icon={flikikon(LayoutGrid)} />
                      <Tab value="historik" panelId="crm-affarsflik" label={text({ sv: "Historik", en: "History" })} icon={flikikon(History)} />
                    </TabList>
                  </div>

                  <div id="crm-affarsflik" role="tabpanel" className="crm-panelinnehall px-5 pb-6 pt-5">
                    {flik === "oversikt" ? (
                      <div className="flex flex-col gap-6">
                        <MetadataList title={text({ sv: "Affär", en: "Deal" })} label={ETIKETT}>
                          {rad(
                            { sv: "Steg", en: "Stage" },
                            Milestone,
                            <Selector
                              label={text({ sv: "Steg", en: "Stage" })}
                              isLabelHidden
                              size="sm"
                              variant="secondary"
                              value={affar.stage_id ?? undefined}
                              isDisabled={flyttar}
                              onChange={(v) => v && v !== affar.stage_id && flytta(affar, v)}
                              options={steg.map((s) => ({ value: s.id, label: s.name, icon: <Prick ton={STEGTON[s.type].ton} /> }))}
                            />
                          )}
                          {rad({ sv: "Belopp", en: "Amount" }, Wallet, varde(summa ? <span className="tabular-nums">{summa}</span> : null, "amount"))}
                          {/* Sannolikheten säger något bara medan affären är öppen: en vunnen eller förlorad är avgjord. */}
                          {nuSteg && nuSteg.type !== "open"
                            ? null
                            : rad(
                                { sv: "Sannolikhet", en: "Probability" },
                                Percent,
                                chans == null ? (
                                  varde(null, "probability")
                                ) : (
                                  <span className="crm-varde">
                                    <span className="tabular-nums">{chans} %</span>
                                    {affar.probability == null ? (
                                      <span className="ml-2 text-[0.8125rem] text-ink-muted">{text({ sv: "stegets", en: "the stage's" })}</span>
                                    ) : null}
                                  </span>
                                )
                              )}
                          {rad({ sv: "Väntat avslut", en: "Expected close" }, CalendarClock, varde(datum(affar.expected_close_date), "expected_close_date"))}
                          {affar.closed_at ? rad({ sv: "Avslutad", en: "Closed" }, CalendarCheck, <span className="crm-varde">{datum(affar.closed_at)}</span>) : null}
                          {nuSteg?.type === "lost" || affar.lost_reason
                            ? rad({ sv: "Förlustorsak", en: "Lost reason" }, CircleSlash, varde(affar.lost_reason, "lost_reason"))
                            : null}
                        </MetadataList>

                        <MetadataList title={text({ sv: "Kopplingar", en: "Links" })} label={ETIKETT}>
                          {rad(
                            { sv: "Bolag", en: "Company" },
                            Building2,
                            varde(
                              affar.company_id ? (
                                <Postchip
                                  namn={bolag ?? text({ sv: "Bolaget", en: "The company" })}
                                  href={`${bolagVag}?bolag=${encodeURIComponent(affar.company_id)}`}
                                  label={text({ sv: `Öppna ${bolag ?? "bolaget"}`, en: `Open ${bolag ?? "the company"}` })}
                                />
                              ) : null,
                              "company_id"
                            )
                          )}
                          {affar.person_id
                            ? rad(
                                { sv: "Kontaktperson", en: "Contact person" },
                                Users,
                                <span className="crm-varde">
                                <Personchip
                                  namn={person ?? text({ sv: "Personen", en: "The person" })}
                                  href={`${personVag}?person=${encodeURIComponent(affar.person_id)}`}
                                  label={text({ sv: `Öppna ${person ?? "personen"}`, en: `Open ${person ?? "the person"}` })}
                                />
                                </span>
                              )
                            : affar.company_id
                              ? rad({ sv: "Kontaktperson", en: "Contact person" }, Users, varde(null, "person_id"))
                              : null}
                          {rad({ sv: "Ansvarig", en: "Owner" }, UserRound, varde(affar.owner ? <Personchip namn={affar.owner} vikt="lugn" /> : null, "owner"))}
                        </MetadataList>

                        <MetadataList title={text({ sv: "System", en: "System" })} label={ETIKETT}>
                          {rad(
                            { sv: "Skapad", en: "Created" },
                            CalendarPlus,
                            affar.created_at ? <Timestamp value={affar.created_at} format="date_time" hasTooltip={false} color="primary" /> : <span className="crm-varde text-ink-muted">-</span>
                          )}
                          {rad(
                            { sv: "Ändrad", en: "Updated" },
                            Clock,
                            affar.updated_at ? <Timestamp value={affar.updated_at} format="relative" color="primary" /> : <span className="crm-varde text-ink-muted">-</span>
                          )}
                        </MetadataList>
                      </div>
                    ) : null}

                    {flik === "historik" ? <Tidslinje objekt="deals" id={affar.id} andrad={affar.updated_at} /> : null}
                  </div>
                </>
              )}
            </div>
          </LayoutContent>
        }
        footer={
          affar ? (
            <LayoutFooter hasDivider>
              <HStack gap={2} vAlign="center" justify="between">
                <Text type="supporting" color="secondary" maxLines={1}>
                  {affar.updated_at ? (
                    <>
                      {text({ sv: "Ändrad ", en: "Updated " })}
                      <Timestamp value={affar.updated_at} format="relative" />
                    </>
                  ) : null}
                </Text>
                <Button label={text({ sv: "Ta bort", en: "Delete" })} variant="ghost" icon={<Icon icon={Trash2} size="sm" />} className="crm-farlig" onClick={() => taBort(affar)} />
              </HStack>
            </LayoutFooter>
          ) : undefined
        }
      />
    </Drawer>
  );
}
