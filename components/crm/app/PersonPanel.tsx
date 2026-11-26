"use client";

import {
  Ban,
  Briefcase,
  Building2,
  CalendarPlus,
  Clock,
  Eye,
  Hash,
  Mail,
  Pencil,
  Phone,
  Plug,
  Scale,
  Smartphone,
  Trash2,
  type LucideIcon
} from "lucide-react";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { Drawer, DrawerHeader } from "@astryxdesign/core/Drawer";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { MetadataList, MetadataListItem } from "@astryxdesign/core/MetadataList";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { HStack } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { kallnamn } from "@/components/crm/app/BolagPanel";
import { Bilagor } from "@/components/crm/app/Bilagor";
import { Tidslinje } from "@/components/crm/app/Tidslinje";
import type { Personfalt } from "@/components/crm/app/PersonFormular";
import { Kallpiller, Lankpiller, Postchip, tonFor, tonklass, useSmal } from "@/components/crm/app/kit";
import { GRUNDER, personnamn, type Personpost } from "@/lib/crm/person";
import { useLocale, type Localized } from "@/lib/i18n";

const ETIKETT_BRED = { position: "start" as const, width: 160 };
const ETIKETT_SMAL = { position: "start" as const, width: 136 };

/** Varifrån en person kom: första anslutningen, annars Snajp eller API:t. */
export function personensKalla(p: Personpost): Localized {
  const forsta = p.external_ids?.[0]?.connection;
  if (forsta) return { sv: kallnamn(forsta), en: kallnamn(forsta) };
  if (p.source === "api") return { sv: "API", en: "API" };
  if (p.source === "synk") return { sv: "Synk", en: "Sync" };
  return { sv: "Snajp", en: "Snajp" };
}

/**
 * Personens panel, i samma form som bolagets (DESIGN-CRM.md § Postens panel):
 * en Drawer från höger, 520 px, med huvud (rund avatar, namnet i Fraunces,
 * titeln och bolaget som chip), snabbval, fält i grupper och en fot med Ta bort.
 * Listan ligger kvar bakom.
 */
export function PersonPanel({
  person,
  laddar,
  bolagsnamn,
  bolagHref,
  stang,
  redigera,
  taBort
}: Readonly<{
  person: Personpost | null;
  laddar: boolean;
  /** Bolagets namn, när det är känt. */
  bolagsnamn: string | null;
  /** Adressen som öppnar bolagets panel. */
  bolagHref: (id: string) => string;
  stang: () => void;
  redigera: (falt?: Personfalt) => void;
  taBort: (p: Personpost) => void;
}>) {
  const { text } = useLocale();
  const smal = useSmal();
  const ETIKETT = smal ? ETIKETT_SMAL : ETIKETT_BRED;
  const oppen = person != null || laddar;
  const namn = person ? (personnamn(person) ?? text({ sv: "Namnlös person", en: "Unnamed person" })) : "";
  const ikon = (i: LucideIcon) => <Icon icon={i} size="sm" color="inherit" />;
  const rad = (etikett: Localized, i: LucideIcon, innehall: React.ReactNode) => (
    <MetadataListItem label={text(etikett)} icon={ikon(i)}>
      {innehall}
    </MetadataListItem>
  );
  const varde = (v: React.ReactNode, falt: Personfalt) =>
    v == null || v === "" || v === false ? (
      <button type="button" className="crm-lagg-till" onClick={() => redigera(falt)}>
        {text({ sv: "Lägg till", en: "Add" })}
      </button>
    ) : (
      <span className="crm-varde">{v}</span>
    );
  const tel = person?.mobile ?? person?.phone ?? null;

  return (
    <Drawer isOpen={oppen} onOpenChange={(o) => !o && stang()} label={person ? namn : text({ sv: "Personens uppgifter", en: "Person details" })} width={520} hasScrim={false}>
      <Layout
        header={
          <DrawerHeader
            hasDivider={false}
            startContent={
              person ? (
                <Avatar name={namn} size={48} tooltip={false} className={`crm-avatar crm-avatar-rund ${tonklass(tonFor(namn))}`} />
              ) : (
                <Skeleton width={48} height={48} radius="rounded" />
              )
            }
            title={person ? <span className="crm-postnamn">{namn}</span> : <Skeleton width={200} height={22} radius="rounded" />}
            subtitle={
              person ? (
                <span className="mt-1 inline-flex flex-wrap items-center gap-2">
                  {person.title ? <span className="text-[0.8125rem] text-ink-muted">{person.title}</span> : null}
                  {person.company_id ? (
                    <Postchip
                      namn={bolagsnamn ?? text({ sv: "Bolaget", en: "The company" })}
                      href={bolagHref(person.company_id)}
                      storlek="sm"
                      label={text({ sv: `Öppna ${bolagsnamn ?? "bolaget"}`, en: `Open ${bolagsnamn ?? "the company"}` })}
                    />
                  ) : null}
                  {person.do_not_contact ? <Badge variant="error" label={text({ sv: "Kontakta inte", en: "Do not contact" })} /> : null}
                </span>
              ) : undefined
            }
            endContent={
              person ? <IconButton label={text({ sv: "Redigera personen", en: "Edit person" })} icon={<Icon icon={Pencil} size="sm" />} variant="ghost" onClick={() => redigera()} /> : undefined
            }
            onOpenChange={(o) => !o && stang()}
          />
        }
        content={
          <LayoutContent padding={0}>
            <div data-autofocus tabIndex={-1} className="crm-autofokus">
              {!person ? (
                <div className="flex flex-col gap-4 px-5 py-4" role="status" aria-busy="true" aria-label={text({ sv: "Hämtar personen", en: "Loading the person" })}>
                  {Array.from({ length: 6 }, (_, i) => (
                    <div key={i} className="flex items-center gap-4">
                      <Skeleton width={120} height={10} radius="rounded" index={i} />
                      <Skeleton width={`${30 + ((i * 13) % 40)}%`} height={10} radius="rounded" index={i} />
                    </div>
                  ))}
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-2 px-5 pb-4">
                    <IconButton
                      label={person.email ? text({ sv: `Mejla ${person.email}`, en: `Email ${person.email}` }) : text({ sv: "Mejla", en: "Email" })}
                      icon={<Icon icon={Mail} size="sm" />}
                      className="crm-snabbval"
                      href={person.email && !person.do_not_contact ? `mailto:${person.email}` : undefined}
                      isDisabled={!person.email || !!person.do_not_contact}
                      tooltip={
                        person.do_not_contact
                          ? text({ sv: "Personen ska inte kontaktas.", en: "The person is not to be contacted." })
                          : person.email
                            ? undefined
                            : text({ sv: "E-post saknas. Lägg till den under Redigera.", en: "No email. Add it under Edit." })
                      }
                    />
                    <IconButton
                      label={tel ? text({ sv: `Ring ${tel}`, en: `Call ${tel}` }) : text({ sv: "Ring", en: "Call" })}
                      icon={<Icon icon={Phone} size="sm" />}
                      className="crm-snabbval"
                      href={tel && !person.do_not_contact ? `tel:${tel}` : undefined}
                      isDisabled={!tel || !!person.do_not_contact}
                      tooltip={
                        person.do_not_contact
                          ? text({ sv: "Personen ska inte kontaktas.", en: "The person is not to be contacted." })
                          : tel
                            ? undefined
                            : text({ sv: "Telefon saknas. Lägg till den under Redigera.", en: "No phone. Add it under Edit." })
                      }
                    />
                  </div>

                  <div className="crm-panelinnehall border-t border-ink/[0.08] px-5 pb-6 pt-5">
                    <div className="flex flex-col gap-6">
                      <MetadataList title={text({ sv: "Arbete", en: "Work" })} label={ETIKETT}>
                        {rad(
                          { sv: "Bolag", en: "Company" },
                          Building2,
                          person.company_id ? (
                            <Postchip
                              namn={bolagsnamn ?? text({ sv: "Bolaget", en: "The company" })}
                              href={bolagHref(person.company_id)}
                              label={text({ sv: `Öppna ${bolagsnamn ?? "bolaget"}`, en: `Open ${bolagsnamn ?? "the company"}` })}
                            />
                          ) : (
                            varde(null, "company_id")
                          )
                        )}
                        {rad({ sv: "Titel", en: "Title" }, Briefcase, varde(person.title, "title"))}
                      </MetadataList>

                      <MetadataList title={text({ sv: "Kontakt", en: "Contact" })} label={ETIKETT}>
                        {rad({ sv: "E-post", en: "Email" }, Mail, varde(person.email ? <Lankpiller slag="epost" varde={person.email} /> : null, "email"))}
                        {rad({ sv: "Mobil", en: "Mobile" }, Smartphone, varde(person.mobile ? <Lankpiller slag="telefon" varde={person.mobile} /> : null, "mobile"))}
                        {rad({ sv: "Telefon", en: "Phone" }, Phone, varde(person.phone ? <Lankpiller slag="telefon" varde={person.phone} /> : null, "phone"))}
                      </MetadataList>

                      <MetadataList title={text({ sv: "Behandling", en: "Processing" })} label={ETIKETT}>
                        {rad({ sv: "Rättslig grund", en: "Legal basis" }, Scale, varde(person.legal_basis ? text(GRUNDER[person.legal_basis]) : null, "legal_basis"))}
                        {rad(
                          { sv: "Kontakta inte", en: "Do not contact" },
                          Ban,
                          person.do_not_contact ? (
                            <Badge variant="error" label={text({ sv: "Kontakta inte", en: "Do not contact" })} />
                          ) : (
                            <span className="crm-varde text-ink-muted">{text({ sv: "Får kontaktas", en: "May be contacted" })}</span>
                          )
                        )}
                      </MetadataList>

                      <MetadataList title={text({ sv: "System", en: "System" })} label={ETIKETT}>
                        {rad({ sv: "Källa", en: "Source" }, Plug, <Kallpiller kalla={text(personensKalla(person))} />)}
                        {(person.external_ids ?? []).map((x) => (
                          <MetadataListItem key={`${x.connection}:${x.id}`} label={text({ sv: `Id i ${kallnamn(x.connection)}`, en: `Id in ${kallnamn(x.connection)}` })} icon={ikon(Hash)}>
                            <code className="crm-kod">{x.id}</code>
                          </MetadataListItem>
                        ))}
                        {person.external_ids?.[0]?.last_seen_at
                          ? rad({ sv: "Senast sedd", en: "Last seen" }, Eye, <Timestamp value={person.external_ids[0].last_seen_at} format="relative" color="primary" />)
                          : null}
                        {rad(
                          { sv: "Skapad", en: "Created" },
                          CalendarPlus,
                          person.created_at ? <Timestamp value={person.created_at} format="date_time" hasTooltip={false} color="primary" /> : <span className="crm-varde text-ink-muted">-</span>
                        )}
                        {rad(
                          { sv: "Ändrad", en: "Updated" },
                          Clock,
                          person.updated_at ? <Timestamp value={person.updated_at} format="relative" color="primary" /> : <span className="crm-varde text-ink-muted">-</span>
                        )}
                      </MetadataList>

                      {/* Personens panel har inga flikar: filerna och historiken står sist, under samma slags rubrik som grupperna. */}
                      <section aria-labelledby="crm-personfiler" className="flex flex-col gap-3">
                        <h3 id="crm-personfiler" className="crm-gruppnamn">
                          {text({ sv: "Filer", en: "Files" })}
                        </h3>
                        <Bilagor objekt="people" id={person.id} />
                      </section>

                      <section aria-labelledby="crm-personhistorik" className="flex flex-col gap-3">
                        <h3 id="crm-personhistorik" className="crm-gruppnamn">
                          {text({ sv: "Historik", en: "History" })}
                        </h3>
                        <Tidslinje objekt="people" id={person.id} andrad={person.updated_at} />
                      </section>
                    </div>
                  </div>
                </>
              )}
            </div>
          </LayoutContent>
        }
        footer={
          person ? (
            <LayoutFooter hasDivider>
              <HStack gap={2} vAlign="center" justify="between">
                <Text type="supporting" color="secondary" maxLines={1}>
                  {person.updated_at ? (
                    <>
                      {text({ sv: "Ändrad ", en: "Updated " })}
                      <Timestamp value={person.updated_at} format="relative" />
                    </>
                  ) : null}
                </Text>
                <Button label={text({ sv: "Ta bort", en: "Delete" })} variant="ghost" icon={<Icon icon={Trash2} size="sm" />} className="crm-farlig" onClick={() => taBort(person)} />
              </HStack>
            </LayoutFooter>
          ) : undefined
        }
      />
    </Drawer>
  );
}
