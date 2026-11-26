"use client";

import { useEffect, useState } from "react";
import NextLink from "next/link";
import { usePathname } from "next/navigation";
import {
  Ban,
  Building2,
  CalendarCheck,
  CalendarClock,
  CalendarPlus,
  Clock,
  Eye,
  Factory,
  Globe,
  Hash,
  History,
  LayoutGrid,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Plug,
  Receipt,
  Tag,
  Trash2,
  UserRound,
  Users,
  Wallet,
  type LucideIcon
} from "lucide-react";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { Drawer, DrawerHeader } from "@astryxdesign/core/Drawer";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { MetadataList, MetadataListItem } from "@astryxdesign/core/MetadataList";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { HStack } from "@astryxdesign/core/Stack";
import { Tab, TabList } from "@astryxdesign/core/TabList";
import { Text } from "@astryxdesign/core/Text";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import type { Bolagsfalt } from "@/components/crm/app/BolagFormular";
import { Historik } from "@/components/crm/app/Historik";
import { Kallpiller, Lankpiller, Personchip, Privatpersonetikett, Relationsetikett, tonFor, tonklass, useSmal, utanBolagsform } from "@/components/crm/app/kit";
import { SYSTEMNAMN, crmAnrop, orgnrVisning, type Bolag, type Person, type Sida as Svarssida } from "@/lib/crm/api";
import { useLocale, type Localized } from "@/lib/i18n";

type Flik = "oversikt" | "personer" | "kalla" | "historik";

/** Etikettkolumnen: en knapp tredjedel av panelen (Twentys rutnät), smalare på telefon. */
const ETIKETT_BRED = { position: "start" as const, width: 160 };
const ETIKETT_SMAL = { position: "start" as const, width: 136 };

/** Anslutningens namn som det står i systemlistan, annars som kunden döpt den. */
export const kallnamn = (namn: string) => SYSTEMNAMN[namn] ?? namn;

/** Varifrån ett bolag kom, på läsarens språk: första anslutningen, annars Snajp eller API:t. */
export function bolagetsKalla(b: Bolag): Localized {
  const forsta = b.external_ids[0]?.connection;
  if (forsta) return { sv: kallnamn(forsta), en: kallnamn(forsta) };
  return b.source === "api" ? { sv: "API", en: "API" } : { sv: "Snajp", en: "Snajp" };
}

/**
 * Postens panel (DESIGN-CRM.md § Postens panel): en Drawer från höger, 520 px,
 * med huvud (avatar, namnet i Fraunces, organisationsnummer, relation),
 * snabbval, flikarna Översikt, Personer och Källa, och en fot med Ta bort.
 * Listan ligger kvar bakom.
 */
export function BolagPanel({
  bolag,
  laddar,
  stang,
  redigera,
  taBort
}: Readonly<{
  bolag: Bolag | null;
  /** Sant medan bolaget hämtas (öppnat från en adress). */
  laddar: boolean;
  stang: () => void;
  redigera: (falt?: Bolagsfalt) => void;
  taBort: (b: Bolag) => void;
}>) {
  const { text, locale } = useLocale();
  const smal = useSmal();
  // Panelen ligger under <bas>/bolag; personerna öppnas i <bas>/personer.
  const personerVag = (usePathname() ?? "/crm/bolag").replace(/\/bolag\/?$/, "/personer");
  const ETIKETT = smal ? ETIKETT_SMAL : ETIKETT_BRED;
  const flikikon = (i: LucideIcon) => (smal ? undefined : <Icon icon={i} size="sm" />);
  const [flik, setFlik] = useState<Flik>("oversikt");
  const [personer, setPersoner] = useState<Person[] | null>(null);
  const id = bolag?.id;
  const oppen = bolag != null || laddar;

  // Personerna hämtas när panelen öppnas, så att fliken kan visa antalet direkt.
  useEffect(() => {
    setPersoner(null);
    if (!id) return;
    let aktuell = true;
    crmAnrop<Svarssida<Person>>(`/v1/people?${new URLSearchParams({ company_id: id, limit: "100", sort: "name" })}`)
      .then((s) => aktuell && setPersoner(s.data))
      .catch(() => aktuell && setPersoner([]));
    return () => {
      aktuell = false;
    };
  }, [id]);

  // Ett nytt bolag börjar alltid på Översikt.
  useEffect(() => {
    setFlik("oversikt");
  }, [id]);

  const sprak = locale === "sv" ? "sv-SE" : "en-GB";
  const namn = bolag?.name ?? text({ sv: "Namnlöst bolag", en: "Unnamed company" });
  // En privatperson kontaktas aldrig, oavsett vad do_not_contact säger.
  const kontaktaInte = bolag?.private_person === true || bolag?.do_not_contact === true;
  const sparrskal = !kontaktaInte
    ? undefined
    : bolag?.private_person
      ? text({ sv: "Privatpersoner kontaktas aldrig.", en: "Private persons are never contacted." })
      : text({ sv: "Bolaget ska inte kontaktas.", en: "The company is not to be contacted." });
  const ikon = (i: LucideIcon) => <Icon icon={i} size="sm" color="inherit" />;

  /** Ett tomt värde är en dämpad "Lägg till" som öppnar redigeringen på fältet. */
  const varde = (v: React.ReactNode, falt: Bolagsfalt) =>
    v == null || v === "" || v === false ? (
      <button type="button" className="crm-lagg-till" onClick={() => redigera(falt)}>
        {text({ sv: "Lägg till", en: "Add" })}
      </button>
    ) : (
      <span className="crm-varde">{v}</span>
    );

  const datum = (v: string | null) => (v ? <Timestamp value={v} format="date" hasTooltip={false} color="primary" /> : null);
  const kronor = (v: number | null) =>
    v == null ? null : new Intl.NumberFormat(sprak, { style: "currency", currency: "SEK", maximumFractionDigits: 0 }).format(v);

  const a = bolag?.address;
  const adress = a ? [a.co ? `c/o ${a.co}` : null, a.street, [a.postal_code, a.city].filter(Boolean).join(" ")].filter(Boolean).join(", ") : "";

  const rad = (etikett: Localized, i: LucideIcon, innehall: React.ReactNode) => (
    <MetadataListItem label={text(etikett)} icon={ikon(i)}>
      {innehall}
    </MetadataListItem>
  );

  return (
    <Drawer isOpen={oppen} onOpenChange={(o) => !o && stang()} label={bolag ? namn : text({ sv: "Bolagets uppgifter", en: "Company details" })} width={520} hasScrim={false}>
      <Layout
        header={
          <DrawerHeader
            hasDivider={false}
            startContent={
              bolag ? (
                <Avatar
                  name={utanBolagsform(namn)}
                  size={48}
                  shape="rounded"
                  tooltip={false}
                  className={`crm-avatar crm-avatar-stor ${tonklass(tonFor(utanBolagsform(namn)))}`}
                />
              ) : (
                <Skeleton width={48} height={48} radius={3} />
              )
            }
            title={bolag ? <span className="crm-postnamn">{namn}</span> : <Skeleton width={200} height={22} radius="rounded" />}
            subtitle={
              bolag ? (
                <span className="mt-1 inline-flex flex-wrap items-center gap-2">
                  {bolag.org_number ? <span className="text-[0.8125rem] tabular-nums text-ink-muted">{orgnrVisning(bolag.org_number)}</span> : null}
                  <Relationsetikett relation={bolag.relation} />
                  {bolag.private_person ? <Privatpersonetikett /> : null}
                  {kontaktaInte ? <Badge variant="error" label={text({ sv: "Kontakta inte", en: "Do not contact" })} /> : null}
                </span>
              ) : undefined
            }
            endContent={
              bolag ? (
                <IconButton label={text({ sv: "Redigera bolaget", en: "Edit company" })} icon={<Icon icon={Pencil} size="sm" />} variant="ghost" onClick={() => redigera()} />
              ) : undefined
            }
            onOpenChange={(o) => !o && stang()}
          />
        }
        content={
          <LayoutContent padding={0}>
            {/* Fokus vid öppning landar i innehållet, inte på stängknappen (som annars visar sitt tips). */}
            <div data-autofocus tabIndex={-1} className="crm-autofokus">
            {!bolag ? (
              <div className="flex flex-col gap-4 px-5 py-4" role="status" aria-busy="true" aria-label={text({ sv: "Hämtar bolaget", en: "Loading the company" })}>
                {Array.from({ length: 7 }, (_, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <Skeleton width={120} height={10} radius="rounded" index={i} />
                    <Skeleton width={`${30 + ((i * 13) % 40)}%`} height={10} radius="rounded" index={i} />
                  </div>
                ))}
              </div>
            ) : (
              <>
                {/* Snabbval: avstängda med förklaring när uppgiften saknas eller posten inte får kontaktas. */}
                <div className="flex items-center gap-2 px-5 pb-4">
                  <IconButton
                    label={bolag.email ? text({ sv: `Mejla ${bolag.email}`, en: `Email ${bolag.email}` }) : text({ sv: "Mejla", en: "Email" })}
                    icon={<Icon icon={Mail} size="sm" />}
                    className="crm-snabbval"
                    href={bolag.email && !kontaktaInte ? `mailto:${bolag.email}` : undefined}
                    isDisabled={!bolag.email || kontaktaInte}
                    tooltip={
                      sparrskal ?? (bolag.email ? undefined : text({ sv: "E-post saknas. Lägg till den under Redigera.", en: "No email. Add it under Edit." }))
                    }
                  />
                  <IconButton
                    label={bolag.phone ? text({ sv: `Ring ${bolag.phone}`, en: `Call ${bolag.phone}` }) : text({ sv: "Ring", en: "Call" })}
                    icon={<Icon icon={Phone} size="sm" />}
                    className="crm-snabbval"
                    href={bolag.phone && !kontaktaInte ? `tel:${bolag.phone}` : undefined}
                    isDisabled={!bolag.phone || kontaktaInte}
                    tooltip={
                      sparrskal ?? (bolag.phone ? undefined : text({ sv: "Telefon saknas. Lägg till den under Redigera.", en: "No phone. Add it under Edit." }))
                    }
                  />
                  <IconButton
                    label={text({ sv: "Öppna webbplatsen", en: "Open the website" })}
                    icon={<Icon icon={Globe} size="sm" />}
                    className="crm-snabbval"
                    href={bolag.website ?? undefined}
                    target="_blank"
                    rel="noopener noreferrer"
                    isDisabled={!bolag.website}
                    tooltip={bolag.website ? undefined : text({ sv: "Webbplats saknas. Lägg till den under Redigera.", en: "No website. Add it under Edit." })}
                  />
                </div>

                <div className="px-5">
                  <TabList value={flik} onChange={(v) => setFlik(v as Flik)} hasDivider role="tablist">
                    <Tab value="oversikt" panelId="crm-panelflik" label={text({ sv: "Översikt", en: "Overview" })} icon={flikikon(LayoutGrid)} />
                    <Tab
                      value="personer"
                      panelId="crm-panelflik"
                      label={text({ sv: "Personer", en: "People" })}
                      icon={flikikon(Users)}
                      endContent={personer ? <span className="crm-flikantal tabular-nums">{personer.length}</span> : undefined}
                    />
                    <Tab value="kalla" panelId="crm-panelflik" label={text({ sv: "Källa", en: "Source" })} icon={flikikon(Plug)} />
                    <Tab value="historik" panelId="crm-panelflik" label={text({ sv: "Historik", en: "History" })} icon={flikikon(History)} />
                  </TabList>
                </div>

                <div id="crm-panelflik" role="tabpanel" className="crm-panelinnehall px-5 pb-6 pt-5">
                  {flik === "oversikt" ? (
                    <div className="flex flex-col gap-6">
                      <MetadataList title={text({ sv: "Allmänt", en: "General" })} label={ETIKETT}>
                        {rad({ sv: "Org.nr", en: "Org. no." }, Hash, varde(bolag.org_number ? <span className="tabular-nums">{orgnrVisning(bolag.org_number)}</span> : null, "org_number"))}
                        {rad(
                          { sv: "Bolagsform", en: "Legal form" },
                          Building2,
                          varde(bolag.sole_proprietor ? text({ sv: "Enskild firma", en: "Sole proprietorship" }) : bolag.legal_form, "legal_form")
                        )}
                        {rad({ sv: "Momsnummer", en: "VAT number" }, Receipt, varde(bolag.vat_number, "vat_number"))}
                        {rad({ sv: "SNI-kod", en: "SNI code" }, Factory, varde(bolag.sni_code, "sni_code"))}
                        {rad(
                          { sv: "Anställda", en: "Employees" },
                          Users,
                          varde(bolag.employees == null ? null : <span className="tabular-nums">{bolag.employees.toLocaleString(sprak)}</span>, "employees")
                        )}
                        {rad({ sv: "Omsättning", en: "Revenue" }, Wallet, varde(kronor(bolag.revenue_sek) ? <span className="tabular-nums">{kronor(bolag.revenue_sek)}</span> : null, "revenue_sek"))}
                      </MetadataList>

                      <MetadataList title={text({ sv: "Affär", en: "Business" })} label={ETIKETT}>
                        {rad({ sv: "Relation", en: "Relation" }, Tag, <Relationsetikett relation={bolag.relation} />)}
                        {rad({ sv: "Ansvarig", en: "Owner" }, UserRound, varde(bolag.owner ? <Personchip namn={bolag.owner} vikt="lugn" /> : null, "owner"))}
                        {rad({ sv: "Kund sedan", en: "Customer since" }, CalendarCheck, varde(datum(bolag.customer_since), "customer_since"))}
                        {rad({ sv: "Avtalsslut", en: "Contract end" }, CalendarClock, varde(datum(bolag.contract_end), "contract_end"))}
                        {rad(
                          { sv: "Kontakta inte", en: "Do not contact" },
                          Ban,
                          kontaktaInte ? (
                            <span className="inline-flex flex-wrap items-center gap-2">
                              <Badge variant="error" label={text({ sv: "Kontakta inte", en: "Do not contact" })} />
                              {bolag.private_person ? (
                                <span className="text-[0.8125rem] text-ink-muted">{text({ sv: "Privatperson", en: "Private person" })}</span>
                              ) : null}
                            </span>
                          ) : (
                            <span className="crm-varde text-ink-muted">{text({ sv: "Får kontaktas", en: "May be contacted" })}</span>
                          )
                        )}
                      </MetadataList>

                      <MetadataList title={text({ sv: "Kontakt", en: "Contact" })} label={ETIKETT}>
                        {rad({ sv: "Webbplats", en: "Website" }, Globe, varde(bolag.website ? <Lankpiller slag="webb" varde={bolag.domain ?? bolag.website} /> : null, "website"))}
                        {rad({ sv: "E-post", en: "Email" }, Mail, varde(bolag.email ? <Lankpiller slag="epost" varde={bolag.email} /> : null, "email"))}
                        {rad({ sv: "Telefon", en: "Phone" }, Phone, varde(bolag.phone ? <Lankpiller slag="telefon" varde={bolag.phone} /> : null, "phone"))}
                        {rad({ sv: "Adress", en: "Address" }, MapPin, varde(adress || null, "street"))}
                      </MetadataList>

                      <MetadataList title={text({ sv: "System", en: "System" })} label={ETIKETT}>
                        {rad({ sv: "Källa", en: "Source" }, Plug, <Kallpiller kalla={text(bolagetsKalla(bolag))} />)}
                        {rad(
                          { sv: "Skapad", en: "Created" },
                          CalendarPlus,
                          bolag.created_at ? <Timestamp value={bolag.created_at} format="date_time" hasTooltip={false} color="primary" /> : <span className="crm-varde text-ink-muted">-</span>
                        )}
                        {rad(
                          { sv: "Ändrad", en: "Updated" },
                          Clock,
                          bolag.updated_at ? <Timestamp value={bolag.updated_at} format="relative" color="primary" /> : <span className="crm-varde text-ink-muted">-</span>
                        )}
                      </MetadataList>
                    </div>
                  ) : null}

                  {flik === "personer" ? (
                    personer == null ? (
                      <div className="flex flex-col gap-4" role="status" aria-busy="true" aria-label={text({ sv: "Hämtar personer", en: "Loading people" })}>
                        {Array.from({ length: 3 }, (_, i) => (
                          <div key={i} className="flex items-center gap-3">
                            <Skeleton width={32} height={32} radius="rounded" index={i} />
                            <Skeleton width="40%" height={10} radius="rounded" index={i} />
                          </div>
                        ))}
                      </div>
                    ) : personer.length === 0 ? (
                      <EmptyState
                        isCompact
                        icon={<Icon icon={Users} size="lg" color="secondary" />}
                        title={text({ sv: "Inga personer här än", en: "No people here yet" })}
                        description={text({
                          sv: "Personer knyts till bolaget när synken tar in dem, eller över API:t med company_id.",
                          en: "People are linked to the company when the sync brings them in, or over the API with company_id."
                        })}
                      />
                    ) : (
                      <ul className="flex flex-col">
                        {personer.map((p) => {
                          const pn = [p.first_name, p.last_name].filter(Boolean).join(" ") || p.email || text({ sv: "Namnlös person", en: "Unnamed person" });
                          const tel = p.mobile ?? p.phone;
                          return (
                            <li key={p.id} className="crm-personrad flex items-start gap-3 py-3">
                              <span aria-hidden className="inline-flex shrink-0">
                                <Avatar name={pn} size={32} tooltip={false} className={`crm-avatar ${tonklass(tonFor(pn))}`} />
                              </span>
                              <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                                <div className="flex min-w-0 items-center gap-2">
                                  {/* Relationen går att följa åt båda hållen: personen öppnas i Personer. */}
                                  <NextLink
                                    href={`${personerVag}?person=${encodeURIComponent(p.id)}`}
                                    className="crm-chip -ml-1.5 inline-flex h-7 min-w-0 items-center rounded-[6px] px-1.5 text-[0.875rem] font-semibold text-ink no-underline"
                                  >
                                    <span className="truncate">{pn}</span>
                                  </NextLink>
                                  {p.title ? <span className="truncate text-[0.8125rem] text-ink-muted">{p.title}</span> : null}
                                  {p.do_not_contact ? <Badge variant="error" label={text({ sv: "Kontakta inte", en: "Do not contact" })} /> : null}
                                </div>
                                {p.email || tel ? (
                                  <div className="flex flex-wrap gap-1.5">
                                    {p.email ? <Lankpiller slag="epost" varde={p.email} passiv={p.do_not_contact} /> : null}
                                    {tel ? <Lankpiller slag="telefon" varde={tel} passiv={p.do_not_contact} /> : null}
                                  </div>
                                ) : null}
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    )
                  ) : null}

                  {flik === "kalla" ? (
                    bolag.external_ids.length === 0 ? (
                      <MetadataList label={ETIKETT}>
                        {rad({ sv: "Källa", en: "Source" }, Plug, <Kallpiller kalla={text(bolagetsKalla(bolag))} />)}
                        {rad(
                          { sv: "Skapad", en: "Created" },
                          CalendarPlus,
                          <span className="crm-varde">
                            {bolag.source === "api"
                              ? text({ sv: "Över API:t, utan koppling till en anslutning.", en: "Over the API, with no connection." })
                              : text({ sv: "För hand i Snajp, utan koppling till en anslutning.", en: "By hand in Snajp, with no connection." })}
                          </span>
                        )}
                      </MetadataList>
                    ) : (
                      <div className="flex flex-col gap-3">
                        {bolag.external_ids.map((x) => (
                          <div key={`${x.connection}:${x.id}`} className="crm-kallkort rounded-[16px] p-4">
                            <MetadataList label={{ position: "start", width: 144 }}>
                              {rad({ sv: "Anslutning", en: "Connection" }, Plug, <Kallpiller kalla={kallnamn(x.connection)} />)}
                              {rad({ sv: "Externt id", en: "External id" }, Hash, <code className="crm-kod">{x.id}</code>)}
                              {rad(
                                { sv: "Senast sedd", en: "Last seen" },
                                Eye,
                                x.last_seen_at ? <Timestamp value={x.last_seen_at} format="relative" color="primary" /> : <span className="crm-varde text-ink-muted">-</span>
                              )}
                            </MetadataList>
                          </div>
                        ))}
                        <Text type="supporting" color="secondary">
                          {text({
                            sv: "Ändrar du ett fält här räknas det som ändrat för hand när anslutningens konfliktregel tillämpas.",
                            en: "A field you change here counts as edited by hand when the connection's conflict rule is applied."
                          })}
                        </Text>
                      </div>
                    )
                  ) : null}

                  {flik === "historik" ? <Historik objekt="companies" id={bolag.id} andrad={bolag.updated_at} /> : null}
                </div>
              </>
            )}
            </div>
          </LayoutContent>
        }
        footer={
          bolag ? (
            <LayoutFooter hasDivider>
              <HStack gap={2} vAlign="center" justify="between">
                <Text type="supporting" color="secondary" maxLines={1}>
                  {bolag.updated_at ? (
                    <>
                      {text({ sv: "Ändrad ", en: "Updated " })}
                      <Timestamp value={bolag.updated_at} format="relative" />
                    </>
                  ) : null}
                </Text>
                <Button
                  label={text({ sv: "Ta bort", en: "Delete" })}
                  variant="ghost"
                  icon={<Icon icon={Trash2} size="sm" />}
                  className="crm-farlig"
                  onClick={() => taBort(bolag)}
                />
              </HStack>
            </LayoutFooter>
          ) : undefined
        }
      />
    </Drawer>
  );
}
