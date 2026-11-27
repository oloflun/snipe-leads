"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Archive,
  ArchiveRestore,
  ArrowRightLeft,
  Ban,
  Building2,
  CalendarPlus,
  Clock,
  Factory,
  FlaskConical,
  Gauge,
  Globe,
  Hash,
  History,
  LayoutGrid,
  Link2,
  Mail,
  MapPin,
  MoreHorizontal,
  Phone,
  PhoneCall,
  Plug,
  Scale,
  Tag,
  Target,
  Trash2,
  UserRound,
  Users,
  ThumbsDown,
  ThumbsUp,
  FilePen,
  Wrench,
  type LucideIcon
} from "lucide-react";
import { AlertDialog } from "@astryxdesign/core/AlertDialog";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { Drawer, DrawerHeader } from "@astryxdesign/core/Drawer";
import { DropdownMenu, type DropdownMenuOption } from "@astryxdesign/core/DropdownMenu";
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
import { useToast } from "@astryxdesign/core/Toast";
import { pafyllnadSkal } from "@/components/leads/pafyllnad";
import { LeadHistorik } from "@/components/crm/app/iris/LeadHistorik";
import { LeadUtkast } from "@/components/crm/app/iris/LeadUtkast";
import { Kallpiller, Lankpiller, Personchip, Prick, tonFor, tonklass, useSkrivratt, useSmal, utanBolagsform } from "@/components/crm/app/kit";
import { Felruta } from "@/components/crm/app/Sida";
import { CrmFel, orgnrVisning } from "@/lib/crm/api";
import { irisAnrop } from "@/lib/crm/iris/anrop";
import {
  KONTAKTVAG,
  LEAD_TYP_ETIKETT,
  STATUSTON,
  STATUS_ETIKETT,
  SYSTEMSTATUS,
  VALBARA,
  domanAv,
  kontaktvag,
  kriterier,
  leadTyp,
  nivaEtikett,
  obedomd,
  poang,
  utfallEtikett,
  type Lead,
  type LeadPost,
  type LeadSvar,
  type Webbrevision
} from "@/lib/crm/iris/lead";
import { barWebb } from "@/lib/crm/iris/webb";
import { useLocale, type Localized } from "@/lib/i18n";

type Flik = "oversikt" | "bedomning" | "utkast" | "historik" | "kalla";

const ETIKETT_BRED = { position: "start" as const, width: 160 };
const ETIKETT_SMAL = { position: "start" as const, width: 132 };

/** Webbnivån som backenden satte (webbrevision.webbniva). Bara när svaret bär den. */
const WEBBNIVA: Record<string, Localized> = {
  akut: { sv: "Akut", en: "Urgent" },
  dalig: { sv: "Dålig", en: "Poor" },
  bra: { sv: "Bra", en: "Good" },
  mycket_bra: { sv: "Mycket bra", en: "Very good" },
  okand: { sv: "Okänd", en: "Unknown" }
};

/** Kriteriets utfall som etikettens färg: ett hårt krav som missar i rött. Nycklarna är backendens (lib/prospekt.ts). */
function utfallston(utfall: string, hart?: boolean): "error" | "yellow" | "green" | "neutral" {
  if (utfall === "miss") return hart ? "error" : "neutral";
  if (utfall === "delvis") return "yellow";
  if (utfall === "träff") return "green"; // inte-copy: backendens utfallsnyckel
  return "neutral";
}

const feltext = (e: unknown): Localized => (e instanceof CrmFel ? e.text : { sv: "Okänt fel.", en: "Unknown error." });

/**
 * Leadets panel (LR-008, LR-060 till LR-075, LR-110 till LR-113), byggd som
 * BolagPanel: en Drawer från höger med huvud, snabbval, flikar och en fot.
 * Öppnas med `?lead=<id>` i adressen.
 *
 * Flikarna: Översikt (bolaget, kontakten och läget hos Iris, och webbplatsen när
 * svaret bär bedömningen), Bedömning (motivering, kriterier med belägg, Jev),
 * Utkast (som mottagaren ser det), Historik (leadets tidslinje) och Källa.
 */
export function LeadPanel({
  id,
  listrad,
  stang,
  andrat
}: Readonly<{
  id: string | null;
  /** Listans rad, så att huvudet syns direkt medan hela leadet hämtas. */
  listrad: Lead | null;
  bas?: string;
  stang: () => void;
  /** Något ändrades i panelen: listan bakom hämtar om. */
  andrat: () => void;
}>) {
  const { text, locale } = useLocale();
  const visa = useToast();
  const smal = useSmal();
  const skriv = useSkrivratt("test");
  const ETIKETT = smal ? ETIKETT_SMAL : ETIKETT_BRED;
  const sprak = locale === "sv" ? "sv-SE" : "en-GB";
  const [flik, setFlik] = useState<Flik>("oversikt");
  const [svar, setSvar] = useState<LeadSvar | null>(null);
  const [fel, setFel] = useState<unknown>(null);
  const [omgang, setOmgang] = useState(0);
  const [fraga, setFraga] = useState<"kontakta-inte" | "ta-bort" | null>(null);
  const [upptagen, setUpptagen] = useState(false);

  const hamta = useCallback(async () => {
    if (!id) return;
    try {
      setSvar(await irisAnrop<LeadSvar>(`/leads/prospects/${encodeURIComponent(id)}`));
      setFel(null);
    } catch (e) {
      setFel(e);
    }
  }, [id]);

  useEffect(() => {
    setSvar(null);
    setFel(null);
    setFlik("oversikt");
    void hamta();
  }, [hamta]);

  const ny = () => {
    setOmgang((n) => n + 1);
    void hamta();
    andrat();
  };

  const post: LeadPost | null = svar?.prospect ?? null;
  const visad: Lead | null = post ?? listrad;
  const oppen = id != null;
  const namn = visad?.company_name || text({ sv: "Namnlöst bolag", en: "Unnamed company" });
  const kontaktasInte = visad?.status === "suppressed";
  const arkiverad = Boolean(visad?.arkiverad_at);
  const test = visad?.origin === "test";
  const exempel = visad?.origin === "example";
  const ikon = (i: LucideIcon) => <Icon icon={i} size="sm" color="inherit" />;
  const rad = (etikett: Localized, i: LucideIcon, innehall: React.ReactNode) => (
    <MetadataListItem label={text(etikett)} icon={ikon(i)}>
      {innehall}
    </MetadataListItem>
  );
  const varde = (v: React.ReactNode) => (v == null || v === "" ? <span className="crm-varde text-ink-muted">-</span> : <span className="crm-varde">{v}</span>);

  // ---- Handlingarna ----------------------------------------------------------
  async function gor(fn: () => Promise<{ text: string; angra?: () => Promise<unknown> } | null>) {
    if (upptagen) return;
    setUpptagen(true);
    try {
      const ut = await fn();
      if (ut) {
        visa({
          body: ut.text,
          endContent: ut.angra
            ? <Button size="sm" variant="secondary" label={text({ sv: "Ångra", en: "Undo" })} onClick={() => void ut.angra?.().then(ny, (e) => visa({ type: "error", body: text(feltext(e)), uniqueID: "iris-lead" }))} />
            : undefined,
          autoHideDuration: ut.angra ? 10000 : undefined,
          uniqueID: "iris-lead"
        });
      }
      ny();
    } catch (e) {
      const saknas = (e as { saknas?: string[] }).saknas;
      visa({ type: "error", body: text(feltext(e)) + (saknas?.length ? ` (${saknas.join(", ")})` : ""), uniqueID: "iris-lead" });
    } finally {
      setUpptagen(false);
      setFraga(null);
    }
  }

  const patcha = (kropp: Record<string, unknown>) => irisAnrop(`/leads/prospects/${encodeURIComponent(id ?? "")}`, { method: "PATCH", body: JSON.stringify(kropp) });

  const bytStatus = (status: string) => {
    if (!visad || visad.status === status) return;
    const forra = visad.status;
    const nyEtikett = text(STATUS_ETIKETT[status] ?? { sv: status, en: status }).toLocaleLowerCase(sprak);
    void gor(async () => {
      await patcha({ status });
      return { text: text({ sv: `${namn} står nu som ${nyEtikett}.`, en: `${namn} is now ${nyEtikett}.` }), angra: () => patcha({ status: forra }) };
    });
  };

  const arkivera = (pa: boolean) =>
    void gor(async () => {
      const ids = [id];
      const s = await irisAnrop<{ installda_utskick?: number }>("/leads/prospects/arkivera", { method: "POST", body: JSON.stringify({ ids, arkivera: pa }) });
      const stoppade = s.installda_utskick ?? 0;
      return {
        text: pa
          ? text({ sv: `${namn} är arkiverat och får inga mejl.`, en: `${namn} is archived and gets no emails.` }) + (stoppade ? ` ${text({ sv: "Det väntande utkastet ställdes in.", en: "The pending draft was cancelled." })}` : "")
          : text({ sv: `${namn} är tillbaka i listan.`, en: `${namn} is back in the list.` }),
        angra: () => irisAnrop("/leads/prospects/arkivera", { method: "POST", body: JSON.stringify({ ids, arkivera: !pa }) })
      };
    });

  const valjBort = (bort: boolean) =>
    void gor(async () => {
      await patcha({ qualified: !bort });
      return {
        text: bort ? text({ sv: `${namn} är bortvalt och står under Bortvalda.`, en: `${namn} is ruled out and listed under Ruled out.` }) : text({ sv: `${namn} är tillbaka bland leadsen.`, en: `${namn} is back among the leads.` }),
        angra: () => patcha({ qualified: bort })
      };
    });

  const flytta = (till: "test" | "skarp") =>
    void gor(async () => {
      const s = await irisAnrop<{ andrad?: boolean }>(`/leads/prospects/${encodeURIComponent(id ?? "")}/${till === "test" ? "degradera" : "befordra"}`, { method: "POST" });
      if (!s.andrad) return null;
      return {
        text: till === "test" ? text({ sv: `${namn} står nu på testytan och kan inte skickas.`, en: `${namn} is now in the test area and cannot be sent.` }) : text({ sv: `${namn} står nu i skarpa listan.`, en: `${namn} is now in the live list.` })
      };
    });

  const kontaktaInte = () =>
    void gor(async () => {
      await irisAnrop(`/leads/prospects/${encodeURIComponent(id ?? "")}/samtal`, { method: "POST", body: JSON.stringify({ utfall: "kontakta_inte" }) });
      return { text: text({ sv: `${namn} kontaktas inte. Alla utskick är stoppade.`, en: `${namn} will not be contacted. All sends are stopped.` }) };
    });

  const taBort = () =>
    void gor(async () => {
      const s = await irisAnrop<{ raderade?: string[]; vagrade?: { skal: string }[] }>("/leads/prospects/radera", { method: "POST", body: JSON.stringify({ ids: [id] }) });
      if (s.raderade?.length) {
        stang();
        return { text: text({ sv: `${namn} är borttaget.`, en: `${namn} is deleted.` }) };
      }
      throw new CrmFel(
        s.vagrade?.[0]?.skal === "kontaktad"
          ? { sv: "Leadet har fått mejl och kan bara arkiveras.", en: "The lead has been emailed and can only be archived." }
          : { sv: "Leadet finns inte längre.", en: "The lead no longer exists." },
        409,
        null
      );
    });

  const fler: DropdownMenuOption[] = [
    ...(post?.qualified === false && post.niva !== "C"
      ? [{ label: text({ sv: "Välj in igen", en: "Rule back in" }), icon: <Icon icon={ThumbsUp} size="sm" />, onClick: () => valjBort(false) }]
      : post?.niva !== "C"
        ? [{ label: text({ sv: "Välj bort", en: "Rule out" }), icon: <Icon icon={ThumbsDown} size="sm" />, description: text({ sv: "Flyttas till Bortvalda", en: "Moves to Ruled out" }), onClick: () => valjBort(true) }]
        : []),
    ...(!kontaktasInte ? [{ label: text({ sv: "Kontakta inte", en: "Do not contact" }), icon: <Icon icon={Ban} size="sm" />, onClick: () => setFraga("kontakta-inte") }] : []),
    test
      ? { label: text({ sv: "Flytta till skarpa listan", en: "Move to the live list" }), icon: <Icon icon={ArrowRightLeft} size="sm" />, onClick: () => flytta("skarp") }
      : { label: text({ sv: "Flytta till testytan", en: "Move to the test area" }), icon: <Icon icon={FlaskConical} size="sm" />, description: text({ sv: "Kan då inte skickas", en: "Can then not be sent" }), onClick: () => flytta("test") },
    { type: "divider" },
    { label: text({ sv: "Ta bort för gott", en: "Delete for good" }), icon: <Icon icon={Trash2} size="sm" />, variant: "destructive" as const, onClick: () => setFraga("ta-bort") }
  ];

  const flikikon = (i: LucideIcon) => (smal ? undefined : <Icon icon={i} size="sm" />);
  const webb = post && barWebb(post) ? (post.webbrevision as Webbrevision | null) : null;
  const n = visad ? poang(visad) : null;
  const pafyllt = post?.pafylld ? pafyllnadSkal(post.pafylld_skal) : null;
  const krit = kriterier(post?.score_breakdown);
  const statusval = VALBARA.map((s) => ({ value: s, label: text(STATUS_ETIKETT[s]) }));

  return (
    <>
      <Drawer isOpen={oppen} onOpenChange={(o) => !o && stang()} label={visad ? namn : text({ sv: "Leadets uppgifter", en: "Lead details" })} width={560} hasScrim={false}>
        <Layout
          header={
            <DrawerHeader
              hasDivider={false}
              startContent={
                visad ? (
                  <Avatar name={utanBolagsform(namn)} size={48} shape="rounded" tooltip={false} className={`crm-avatar crm-avatar-stor ${tonklass(tonFor(utanBolagsform(namn)))}`} />
                ) : (
                  <Skeleton width={48} height={48} radius={3} />
                )
              }
              title={visad ? <span className="crm-postnamn">{namn}</span> : <Skeleton width={200} height={22} radius="rounded" />}
              subtitle={
                visad ? (
                  <span className="mt-1 inline-flex flex-wrap items-center gap-2">
                    {post?.orgnr ? <span className="text-[0.8125rem] tabular-nums text-ink-muted">{orgnrVisning(post.orgnr)}</span> : null}
                    <Badge variant="neutral" label={text(STATUS_ETIKETT[visad.status] ?? { sv: visad.status, en: visad.status })} icon={<Prick ton={STATUSTON[visad.status] ?? null} />} />
                    {kontaktasInte ? <Badge variant="error" label={text({ sv: "Kontakta inte", en: "Do not contact" })} /> : null}
                    {arkiverad ? <Badge variant="neutral" label={text({ sv: "Arkiverad", en: "Archived" })} /> : null}
                    {test ? <Badge variant="yellow" label={text({ sv: "Provkörning", en: "Test run" })} /> : null}
                    {exempel ? <Badge variant="neutral" label={text({ sv: "Exempel", en: "Example" })} /> : null}
                  </span>
                ) : undefined
              }
              onOpenChange={(o) => !o && stang()}
            />
          }
          content={
            <LayoutContent padding={0}>
              <div data-autofocus tabIndex={-1} className="crm-autofokus">
                {fel && !visad ? (
                  <div className="px-5 py-4">
                    <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />} />
                  </div>
                ) : !visad ? (
                  <div className="flex flex-col gap-4 px-5 py-4" role="status" aria-busy="true" aria-label={text({ sv: "Hämtar leadet", en: "Loading the lead" })}>
                    {Array.from({ length: 7 }, (_, i) => (
                      <div key={i} className="flex items-center gap-4">
                        <Skeleton width={120} height={10} radius="rounded" index={i} />
                        <Skeleton width={`${30 + ((i * 13) % 40)}%`} height={10} radius="rounded" index={i} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <>
                    {/* Snabbval: avstängda med förklaring när uppgiften saknas eller leadet inte får kontaktas. */}
                    <div className="flex items-center gap-2 px-5 pb-4">
                      <IconButton
                        label={visad.contact_email ? text({ sv: `Mejla ${visad.contact_email}`, en: `Email ${visad.contact_email}` }) : text({ sv: "Mejla", en: "Email" })}
                        icon={<Icon icon={Mail} size="sm" />}
                        className="crm-snabbval"
                        href={visad.contact_email && !kontaktasInte ? `mailto:${visad.contact_email}` : undefined}
                        isDisabled={!visad.contact_email || kontaktasInte}
                        tooltip={kontaktasInte ? text({ sv: "Leadet ska inte kontaktas.", en: "The lead is not to be contacted." }) : visad.contact_email ? undefined : text({ sv: "Ingen mejladress hittad.", en: "No email address found." })}
                      />
                      <IconButton
                        label={visad.contact_phone ? text({ sv: `Ring ${visad.contact_phone}`, en: `Call ${visad.contact_phone}` }) : text({ sv: "Ring", en: "Call" })}
                        icon={<Icon icon={Phone} size="sm" />}
                        className="crm-snabbval"
                        href={visad.contact_phone && !kontaktasInte ? `tel:${visad.contact_phone}` : undefined}
                        isDisabled={!visad.contact_phone || kontaktasInte}
                        tooltip={kontaktasInte ? text({ sv: "Leadet ska inte kontaktas.", en: "The lead is not to be contacted." }) : visad.contact_phone ? undefined : text({ sv: "Inget telefonnummer hittat.", en: "No phone number found." })}
                      />
                      <IconButton
                        label={text({ sv: "Öppna webbplatsen", en: "Open the website" })}
                        icon={<Icon icon={Globe} size="sm" />}
                        className="crm-snabbval"
                        href={visad.website ?? undefined}
                        target="_blank"
                        rel="noopener noreferrer"
                        isDisabled={!visad.website}
                        tooltip={visad.website ? undefined : text({ sv: "Bolaget har ingen känd webbplats.", en: "The company has no known website." })}
                      />
                    </div>

                    <div className="crm-panelflikar px-5">
                      <TabList value={flik} onChange={(v) => setFlik(v as Flik)} hasDivider role="tablist">
                        <Tab value="oversikt" panelId="iris-panelflik" label={text({ sv: "Översikt", en: "Overview" })} icon={flikikon(LayoutGrid)} />
                        <Tab value="bedomning" panelId="iris-panelflik" label={text({ sv: "Bedömning", en: "Assessment" })} icon={flikikon(Scale)} />
                        <Tab value="utkast" panelId="iris-panelflik" label={text({ sv: "Utkast", en: "Draft" })} icon={flikikon(FilePen)} />
                        <Tab value="historik" panelId="iris-panelflik" label={text({ sv: "Historik", en: "History" })} icon={flikikon(History)} />
                        <Tab value="kalla" panelId="iris-panelflik" label={text({ sv: "Källa", en: "Source" })} icon={flikikon(Plug)} endContent={svar ? <span className="crm-flikantal tabular-nums">{svar.sources.length}</span> : undefined} />
                      </TabList>
                    </div>

                    <div id="iris-panelflik" role="tabpanel" className="crm-panelinnehall px-5 pb-6 pt-5">
                      {flik === "oversikt" ? (
                        <div className="flex flex-col gap-6">
                          <MetadataList title={text({ sv: "Hos Iris", en: "With Iris" })} label={ETIKETT}>
                            {rad(
                              { sv: "Status", en: "Status" },
                              Tag,
                              SYSTEMSTATUS.has(visad.status) || exempel || arkiverad ? (
                                <span className="crm-varde inline-flex items-center gap-1.5">
                                  <Prick ton={STATUSTON[visad.status] ?? null} />
                                  {text(STATUS_ETIKETT[visad.status] ?? { sv: visad.status, en: visad.status })}
                                </span>
                              ) : (
                                <div className="w-full max-w-[220px]">
                                  <Selector
                                    label={text({ sv: "Status", en: "Status" })}
                                    isLabelHidden
                                    size="sm"
                                    value={visad.status}
                                    onChange={(v) => v && bytStatus(v)}
                                    options={statusval}
                                    isDisabled={!skriv.far || upptagen}
                                    width="100%"
                                  />
                                  {!skriv.far ? <span className="mt-1 block text-[0.8125rem] text-ink-muted">{skriv.skal}</span> : null}
                                </div>
                              )
                            )}
                            {rad(
                              { sv: "Bedömning", en: "Assessment" },
                              Target,
                              obedomd(visad) ? (
                                varde(text({ sv: "Researchar", en: "Researching" }))
                              ) : (
                                <span className="crm-varde inline-flex flex-wrap items-baseline gap-2">
                                  {n != null ? <span className="font-semibold tabular-nums">{text({ sv: `${n} poäng`, en: `${n} points` })}</span> : null}
                                  {visad.pafylld ? (
                                    <Badge variant="yellow" label={text({ sv: "Påfyllt", en: "Filled in" })} />
                                  ) : visad.niva ? (
                                    <span className={visad.niva === "C" ? "text-danger" : "text-ink-muted"}>{nivaEtikett(visad.niva, locale)}</span>
                                  ) : null}
                                </span>
                              )
                            )}
                            {rad({ sv: "Typ", en: "Type" }, Plug, <Kallpiller kalla={text(LEAD_TYP_ETIKETT[leadTyp(visad.origin)])} />)}
                            {rad({ sv: "Hittad", en: "Found" }, CalendarPlus, visad.created_at ? <Timestamp value={visad.created_at} format="date_time" hasTooltip={false} color="primary" /> : varde(null))}
                            {rad({ sv: "Senast hänt", en: "Last event" }, Clock, visad.senaste_handelse_at ? <Timestamp value={visad.senaste_handelse_at} format="relative" color="primary" /> : varde(null))}
                          </MetadataList>

                          <MetadataList title={text({ sv: "Kontakt", en: "Contact" })} label={ETIKETT}>
                            {rad(
                              { sv: "Kontaktperson", en: "Contact person" },
                              UserRound,
                              visad.contact_name ? (
                                <span className="crm-varde inline-flex flex-wrap items-center gap-2">
                                  <Personchip namn={visad.contact_name} vikt="lugn" />
                                  {post?.contact_role ? <span className="text-[0.8125rem] text-ink-muted">{post.contact_role}</span> : null}
                                </span>
                              ) : (
                                varde(text({ sv: "Ingen namngiven person", en: "No named person" }))
                              )
                            )}
                            {rad({ sv: "E-post", en: "Email" }, Mail, visad.contact_email ? <Lankpiller slag="epost" varde={visad.contact_email} passiv={kontaktasInte} /> : varde(null))}
                            {rad({ sv: "Telefon", en: "Phone" }, Phone, visad.contact_phone ? <Lankpiller slag="telefon" varde={visad.contact_phone} passiv={kontaktasInte} /> : varde(null))}
                            {rad({ sv: "Kontaktväg", en: "Contact route" }, PhoneCall, varde(text(KONTAKTVAG[kontaktvag(visad)])))}
                          </MetadataList>

                          <MetadataList title={text({ sv: "Bolaget", en: "The company" })} label={ETIKETT}>
                            {rad({ sv: "Org.nr", en: "Org. no." }, Hash, varde(post?.orgnr ? <span className="tabular-nums">{orgnrVisning(post.orgnr)}</span> : null))}
                            {rad({ sv: "Ort", en: "City" }, MapPin, varde(visad.ort))}
                            {rad({ sv: "Webbplats", en: "Website" }, Globe, visad.website ? <Lankpiller slag="webb" varde={domanAv(visad.website) ?? visad.website} /> : varde(null))}
                            {rad({ sv: "SNI-kod", en: "SNI code" }, Factory, varde(post?.sni))}
                            {rad({ sv: "Anställda", en: "Employees" }, Users, varde(post?.anstallda == null ? null : <span className="tabular-nums">{post.anstallda.toLocaleString(sprak)}</span>))}
                          </MetadataList>

                          {/* Webbplatsen: bara när svaret bär bedömningen (lib/crm/iris/webb.ts, LR-090 till LR-092). */}
                          {webb ? (
                            <MetadataList title={text({ sv: "Webbplatsen", en: "The website" })} label={ETIKETT}>
                              {typeof webb.modernitet === "number" ? rad({ sv: "Betyg", en: "Score" }, Gauge, varde(<span className="tabular-nums">{`${webb.modernitet}/10`}</span>)) : null}
                              {post?.webbniva ? rad({ sv: "Nivå", en: "Level" }, Tag, varde(text(WEBBNIVA[post.webbniva] ?? { sv: post.webbniva, en: post.webbniva }))) : null}
                              {webb.platshallare ? rad({ sv: "Platshållare", en: "Placeholder" }, Link2, varde(webb.platshallare)) : null}
                              {webb.brister?.length
                                ? rad(
                                    { sv: "Brister", en: "Flaws" },
                                    Wrench,
                                    <ul className="crm-varde flex flex-col gap-1">
                                      {webb.brister.map((b) => (
                                        <li key={b}>{b}</li>
                                      ))}
                                    </ul>
                                  )
                                : null}
                              {webb.layout_era || webb.uppskattat_byggar ? rad({ sv: "Byggd", en: "Built" }, Building2, varde([webb.layout_era, webb.uppskattat_byggar].filter(Boolean).join(", "))) : null}
                              {typeof webb.pagespeed?.mobil?.prestanda === "number"
                                ? rad({ sv: "Prestanda, mobil", en: "Performance, mobile" }, Gauge, varde(<span className="tabular-nums">{`${webb.pagespeed.mobil.prestanda}/100`}</span>))
                                : null}
                            </MetadataList>
                          ) : null}
                        </div>
                      ) : null}

                      {flik === "bedomning" ? (
                        !post ? (
                          <Skeleton width="80%" height={10} radius="rounded" />
                        ) : (
                          <div className="flex flex-col gap-6">
                            {pafyllt ? (
                              <div className="crm-kallkort rounded-[16px] p-4">
                                <p className="text-[0.875rem] font-semibold text-ink">{text({ sv: "Påfyllt för att nå beställt antal", en: "Filled in to reach the ordered number" })}</p>
                                <p className="mt-1 text-[0.875rem] text-ink2">{text(pafyllt)}</p>
                              </div>
                            ) : null}
                            {post.motivering ? (
                              <section className="flex flex-col gap-1.5">
                                <Text type="label" color="secondary" weight="medium">
                                  {text({ sv: "Motivering", en: "Reasoning" })}
                                </Text>
                                <p className="max-w-[65ch] text-[0.9375rem] leading-7 text-ink">{post.motivering}</p>
                              </section>
                            ) : null}
                            <section className="flex flex-col gap-1.5">
                              <Text type="label" color="secondary" weight="medium">
                                {text({ sv: "Kriterier", en: "Criteria" })}
                              </Text>
                              {krit.length ? (
                                <ul className="flex flex-col">
                                  {krit.map((k, i) => (
                                    <li key={`${k.nyckel ?? k.etikett}-${i}`} className="border-b border-ink/[0.07] py-3 last:border-b-0">
                                      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                                        <span className="text-[0.875rem] font-semibold text-ink">{k.etikett}</span>
                                        <Badge variant={utfallston(k.utfall, k.hart)} label={utfallEtikett(k.utfall, locale) ?? k.utfall} />
                                      </div>
                                      {k.motivering ? <p className="mt-1 max-w-[65ch] text-[0.875rem] leading-6 text-ink2">{k.motivering}</p> : null}
                                      {k.belagg?.length ? (
                                        <ul className="mt-2 flex flex-col gap-1">
                                          {k.belagg.map((b) => (
                                            <li key={b.citat} className="border-l-2 border-ink/15 pl-3 text-[0.8125rem] leading-5 text-ink-muted">
                                              <span>{`”${b.citat}”`}</span>{" "}
                                              {b.url.startsWith("http") ? (
                                                <a href={b.url} target="_blank" rel="noopener noreferrer" className="crm-tidslinje-lank text-ink2">
                                                  {text({ sv: "källa", en: "source" })}
                                                </a>
                                              ) : null}
                                            </li>
                                          ))}
                                        </ul>
                                      ) : null}
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <Text color="secondary">
                                  {obedomd(post)
                                    ? text({ sv: "Iris researchar bolaget. Poäng och motivering visas när researchen är klar.", en: "Iris is researching the company. Score and reasoning appear when the research is done." })
                                    : text({ sv: "Bedömdes innan Iris-profilen fanns. Kör researchen igen för poäng och motivering.", en: "Assessed before the Iris profile existed. Run the research again to get a score and reasoning." })}
                                </Text>
                              )}
                            </section>
                            {post.niva === "C" && post.disqualifiers?.length ? (
                              <section className="flex flex-col gap-1.5">
                                <Text type="label" color="secondary" weight="medium">
                                  {text({ sv: "Varför bortvald", en: "Why ruled out" })}
                                </Text>
                                <ul className="flex flex-col gap-1.5">
                                  {post.disqualifiers.map((s) => (
                                    <li key={s} className="border-l-2 border-danger pl-3 text-[0.875rem] text-ink2">
                                      {s}
                                    </li>
                                  ))}
                                </ul>
                              </section>
                            ) : null}
                            {post.jev?.triage || post.jev?.klassning ? (
                              <section className="flex flex-col gap-1.5">
                                <Text type="label" color="secondary" weight="medium">
                                  {text({ sv: "Jevs förbedömning", en: "Jev's pre-assessment" })}
                                </Text>
                                <p className="max-w-[65ch] text-[0.875rem] leading-6 text-ink2">
                                  {[
                                    typeof post.jev.triage?.fit === "number" ? text({ sv: `förbedömning ${post.jev.triage.fit.toFixed(1)} av 3`, en: `pre-assessment ${post.jev.triage.fit.toFixed(1)} of 3` }) : null,
                                    post.jev.triage?.skulle_falla ? text({ sv: `hade valt bort (${(post.jev.triage.fall_skal ?? []).join("; ")})`, en: `would have ruled out (${(post.jev.triage.fall_skal ?? []).join("; ")})` }) : null,
                                    typeof post.jev.klassning?.sannolikhet === "number" ? text({ sv: `bra lead ${Math.round(post.jev.klassning.sannolikhet * 100)} %`, en: `good lead ${Math.round(post.jev.klassning.sannolikhet * 100)} %` }) : null,
                                    post.jev.klassning?.trafikniva ? text({ sv: `prioritet ${post.jev.klassning.trafikniva}`, en: `priority ${post.jev.klassning.trafikniva}` }) : null
                                  ]
                                    .filter(Boolean)
                                    .join(" · ")}
                                </p>
                                {post.jev.triage?.stodrad ? <p className="text-[0.8125rem] text-ink-muted">{text({ sv: `Stödrad: ”${post.jev.triage.stodrad}”`, en: `Supporting line: ”${post.jev.triage.stodrad}”` })}</p> : null}
                              </section>
                            ) : null}
                          </div>
                        )
                      ) : null}

                      {flik === "utkast" && id ? <LeadUtkast id={id} lead={post ?? visad} andrat={ny} /> : null}

                      {flik === "historik" && id ? <LeadHistorik id={id} omgang={omgang} /> : null}

                      {flik === "kalla" ? (
                        <div className="flex flex-col gap-4">
                          <MetadataList label={ETIKETT}>
                            {rad({ sv: "Typ", en: "Type" }, Plug, <Kallpiller kalla={text(LEAD_TYP_ETIKETT[leadTyp(visad.origin)])} />)}
                            {rad({ sv: "Hittad", en: "Found" }, CalendarPlus, visad.created_at ? <Timestamp value={visad.created_at} format="date_time" hasTooltip={false} color="primary" /> : varde(null))}
                          </MetadataList>
                          {svar && svar.sources.length ? (
                            <ul className="crm-kallkort flex flex-col gap-1.5 rounded-[16px] p-4" aria-label={text({ sv: "Källor", en: "Sources" })}>
                              {svar.sources.map((u) => (
                                <li key={u} className="min-w-0">
                                  <a href={u} target="_blank" rel="noopener noreferrer" className="crm-tidslinje-lank break-all text-[0.875rem] text-ink2">
                                    {u}
                                  </a>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <Text color="secondary">{svar ? text({ sv: "Inga källor sparade.", en: "No sources saved." }) : text({ sv: "Hämtar källorna.", en: "Loading the sources." })}</Text>
                          )}
                          <Text type="supporting" color="secondary">
                            {text({ sv: "Källorna är sidorna Iris läste. Bolagets kontaktuppgifter kommer därifrån.", en: "The sources are the pages Iris read. The company's contact details come from there." })}
                          </Text>
                        </div>
                      ) : null}
                    </div>
                  </>
                )}
              </div>
            </LayoutContent>
          }
          footer={
            visad && !exempel ? (
              <LayoutFooter hasDivider>
                <HStack gap={2} vAlign="center" justify="between">
                  <Text type="supporting" color="secondary" maxLines={1}>
                    {visad.senaste_handelse_at ? (
                      <>
                        {text({ sv: "Senast hänt ", en: "Last event " })}
                        <Timestamp value={visad.senaste_handelse_at} format="relative" />
                      </>
                    ) : null}
                  </Text>
                  <HStack gap={1} vAlign="center">
                    <Button
                      label={arkiverad ? text({ sv: "Återställ", en: "Restore" }) : text({ sv: "Arkivera", en: "Archive" })}
                      variant="ghost"
                      icon={<Icon icon={arkiverad ? ArchiveRestore : Archive} size="sm" />}
                      isDisabled={!skriv.far || upptagen}
                      tooltip={skriv.skal ?? undefined}
                      onClick={() => arkivera(!arkiverad)}
                    />
                    <DropdownMenu
                      button={{ label: text({ sv: "Fler", en: "More" }), variant: "ghost", icon: <Icon icon={MoreHorizontal} size="sm" />, isDisabled: !skriv.far || upptagen, tooltip: skriv.skal ?? undefined }}
                      items={fler}
                      placement="above"
                    />
                  </HStack>
                </HStack>
              </LayoutFooter>
            ) : undefined
          }
        />
      </Drawer>

      <AlertDialog
        isOpen={fraga === "kontakta-inte"}
        onOpenChange={(o) => !o && !upptagen && setFraga(null)}
        title={text({ sv: `Kontakta inte ${namn}?`, en: `Do not contact ${namn}?` })}
        description={text({
          sv: "Alla utskick till leadet stoppas och adressen spärras, som när någon i samtal ber att slippa kontakt. Det står i historiken.",
          en: "All sends to the lead are stopped and the address is blocked, as when someone asks in a call not to be contacted. It shows in the history."
        })}
        actionLabel={text({ sv: "Kontakta inte", en: "Do not contact" })}
        cancelLabel={text({ sv: "Avbryt", en: "Cancel" })}
        isActionLoading={upptagen}
        onAction={kontaktaInte}
      />
      <AlertDialog
        isOpen={fraga === "ta-bort"}
        onOpenChange={(o) => !o && !upptagen && setFraga(null)}
        title={text({ sv: `Ta bort ${namn} för gott?`, en: `Delete ${namn} for good?` })}
        description={text({ sv: "Det går inte att ångra. Ett lead som fått mejl tas inte bort; arkivera det i stället.", en: "This cannot be undone. A lead that has been emailed is not deleted; archive it instead." })}
        actionLabel={text({ sv: "Ta bort", en: "Delete" })}
        cancelLabel={text({ sv: "Avbryt", en: "Cancel" })}
        isActionLoading={upptagen}
        onAction={taBort}
      />
    </>
  );
}
