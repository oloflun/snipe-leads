"use client";

/**
 * Snajp CRM:s verktygslåda: de små delarna varje vy bygger av
 * (docs/crm/DESIGN-CRM.md). Importera härifrån i stället för att rita egna
 * chips, piller eller kort, så att samma post ser likadan ut i tabell, panel,
 * översikt och kommandopalett.
 *
 * Färg kommer bara ur objektfärgerna (crm.css: .crm-ton-*), som i sin tur bara
 * läser Snajps tokens.
 */

import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import NextLink from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  ArrowRight,
  Ban,
  Building2,
  Check,
  Code2,
  Copy,
  Globe,
  Handshake,
  LayoutDashboard,
  Mail,
  Phone,
  Plug,
  RefreshCw,
  Users,
  type LucideIcon
} from "lucide-react";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Badge } from "@astryxdesign/core/Badge";
import { Card } from "@astryxdesign/core/Card";
import { ClickableCard } from "@astryxdesign/core/ClickableCard";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { HStack, StackItem, VStack } from "@astryxdesign/core/Stack";
import { useTableSortable, type TableSortState } from "@astryxdesign/core/Table";
import { Text } from "@astryxdesign/core/Text";
import { Token } from "@astryxdesign/core/Token";
import { RELATIONER, type Ordning, type Relation } from "@/lib/crm/api";
import { useLocale, type Localized } from "@/lib/i18n";

// ---------------------------------------------------------------------------
// Objekt och färger
// ---------------------------------------------------------------------------

/** Objektfärgerna, bara ur paletten (DESIGN-CRM.md § Tema). */
export type Ton = "ockra" | "bla" | "mossa" | "sigill" | "mineral";

/** CRM:ets vyer. Samma nycklar som adressen: `/crm/<vy>`. */
export type Objekt = "oversikt" | "bolag" | "personer" | "affarer" | "synk" | "sparrar" | "utvecklare";

export const OBJEKT: Record<Objekt, { ton: Ton; ikon: LucideIcon; namn: Localized }> = {
  oversikt: { ton: "ockra", ikon: LayoutDashboard, namn: { sv: "Översikt", en: "Overview" } },
  bolag: { ton: "bla", ikon: Building2, namn: { sv: "Bolag", en: "Companies" } },
  personer: { ton: "mossa", ikon: Users, namn: { sv: "Personer", en: "People" } },
  // Sigill, som Synk: de står i var sin sektion av navigeringen och möts aldrig.
  affarer: { ton: "sigill", ikon: Handshake, namn: { sv: "Affärer", en: "Deals" } },
  synk: { ton: "sigill", ikon: RefreshCw, namn: { sv: "Synk", en: "Sync" } },
  // Ockra, som Översikt: också de står i var sin sektion.
  sparrar: { ton: "ockra", ikon: Ban, namn: { sv: "Spärrar", en: "Blocks" } },
  utvecklare: { ton: "mineral", ikon: Code2, namn: { sv: "Utvecklare", en: "Developers" } }
};

/** Klassen som bär en tons tre värden (färg, platta, textsäker ton). */
export const tonklass = (ton: Ton) => `crm-ton-${ton}`;

const TONER: Ton[] = ["bla", "mossa", "ockra", "sigill", "mineral"];

/**
 * Samma namn får alltid samma färg, i tabell, panel, kort och palett (Twentys
 * detalj 14). En enkel, stabil hash; ingen slump.
 */
export function tonFor(namn: string): Ton {
  let h = 0;
  for (let i = 0; i < namn.length; i++) h = (h * 31 + namn.charCodeAt(i)) | 0;
  return TONER[Math.abs(h) % TONER.length];
}

/** "Byggbolaget Norr AB" blir "Byggbolaget Norr", så att initialerna blir BN. */
export function utanBolagsform(namn: string) {
  return namn.replace(/\s+(AB|HB|KB|Ek\.?\s*för\.?|Aktiebolag)$/i, "").trim() || namn;
}

/** Klasser utan tomma delar. */
const klasser = (...delar: (string | false | null | undefined)[]) => delar.filter(Boolean).join(" ");

// ---------------------------------------------------------------------------
// Objektikon
// ---------------------------------------------------------------------------

const IKONPLATTA = {
  20: { ruta: "size-5 rounded-[6px]", ikon: "xsm" },
  24: { ruta: "size-6 rounded-[6px]", ikon: "sm" },
  28: { ruta: "size-7 rounded-[8px]", ikon: "sm" },
  32: { ruta: "size-8 rounded-[10px]", ikon: "sm" }
} as const;

/**
 * Ikonplattan: objektets färg med 14 procents alfa, ikonen i färgens textsäkra
 * ton. Ange `objekt` för en av CRM:ets vyer, eller `ikon` och `ton` för något annat.
 */
export function Objektikon({
  objekt,
  ikon,
  ton,
  storlek = 32
}: Readonly<{ objekt?: Objekt; ikon?: LucideIcon; ton?: Ton; storlek?: 20 | 24 | 28 | 32 }>) {
  const o = objekt ? OBJEKT[objekt] : null;
  const glyf = ikon ?? o?.ikon ?? Building2;
  const farg = ton ?? o?.ton ?? "mineral";
  const matt = IKONPLATTA[storlek];
  return (
    <span aria-hidden className={klasser("crm-platta inline-flex shrink-0 items-center justify-center", tonklass(farg), matt.ruta)}>
      <Icon icon={glyf} size={matt.ikon} color="inherit" />
    </span>
  );
}

// ---------------------------------------------------------------------------
// Postchip och personchip
// ---------------------------------------------------------------------------

type ChipProps = Readonly<{
  /** Postens namn som det ska stå. */
  namn: string;
  /** Färg på avatarens platta. Utelämnad: ur namnets hash. */
  ton?: Ton;
  /** Öppnar posten. Utan `onClick` och `href` är chipet passivt. */
  onClick?: () => void;
  href?: string;
  /** Tillgängligt namn när chipet gör något annat än att öppna posten. */
  label?: string;
  /** `md` i tabeller och listor, `sm` i täta rader. */
  storlek?: "sm" | "md";
  /**
   * `stark` (standard) för posten raden handlar om, `lugn` för en post som bara
   * nämns i en annan rad (ansvarig i bolagstabellen): normal vikt och utan platta.
   */
  vikt?: "stark" | "lugn";
}>;

function Chip({ namn, ton, onClick, href, label, storlek = "md", vikt = "stark", form }: ChipProps & { form: "fyrkant" | "rund" }) {
  const initialnamn = form === "fyrkant" ? utanBolagsform(namn) : namn;
  const farg = ton ?? tonFor(initialnamn);
  // Namnet står bredvid: avataren är dold för skärmläsare, annars läses namnet två gånger.
  const avatar = (
    <span aria-hidden className="inline-flex shrink-0">
      <Avatar
        name={initialnamn}
        size={storlek === "md" ? 20 : 16}
        shape={form === "fyrkant" ? "rounded" : "circle"}
        tooltip={false}
        className={klasser("crm-avatar", tonklass(farg))}
      />
    </span>
  );
  const innehall = (
    <>
      {avatar}
      <span className={klasser("min-w-0 truncate text-[0.875rem] leading-5", vikt === "stark" ? "font-semibold text-ink" : "text-ink2")}>{namn}</span>
    </>
  );
  const form_ = klasser(
    "inline-flex max-w-full items-center gap-2 rounded-[6px] text-left align-middle",
    vikt === "stark" || onClick || href ? "crm-chip" : "!pl-0",
    storlek === "md" ? "h-7 pl-1 pr-2" : "h-6 pl-1 pr-1.5"
  );
  if (href) {
    return (
      <NextLink href={href} className={form_} aria-label={label} onClick={onClick}>
        {innehall}
      </NextLink>
    );
  }
  if (onClick) {
    return (
      <button type="button" className={form_} onClick={onClick} aria-label={label}>
        {innehall}
      </button>
    );
  }
  return <span className={form_}>{innehall}</span>;
}

/** Ett bolag: fyrkantig avatar med initialer på objektfärgad platta, plus namnet. */
export function Postchip(props: ChipProps) {
  return <Chip {...props} form="fyrkant" />;
}

/** En person: rund avatar, plus namnet. */
export function Personchip(props: ChipProps) {
  return <Chip {...props} form="rund" />;
}

// ---------------------------------------------------------------------------
// Länkpiller
// ---------------------------------------------------------------------------

/** Länkar som lämnar appen: webbplats, e-post och telefon, som rundade piller. */
export function Lankpiller({
  slag,
  varde,
  passiv = false
}: Readonly<{
  slag: "webb" | "epost" | "telefon";
  varde: string;
  /** Uppgiften visas men går inte att klicka: personen ska inte kontaktas. */
  passiv?: boolean | null;
}>) {
  const { text } = useLocale();
  const ikon = slag === "webb" ? Globe : slag === "epost" ? Mail : Phone;
  const visning = slag === "webb" ? varde.replace(/^https?:\/\//, "").replace(/\/$/, "") : varde;
  const ikonElement = <Icon icon={ikon} size="xsm" color="secondary" />;
  if (passiv) {
    return <Token label={visning} size="sm" icon={ikonElement} className="crm-lankpiller crm-lankpiller-passiv" />;
  }
  if (slag === "webb") {
    // Token har ingen target-prop; webbplatsen öppnas i en ny flik.
    const adress = /^https?:\/\//.test(varde) ? varde : `https://${varde}`;
    return (
      <Token
        label={visning}
        size="sm"
        icon={ikonElement}
        className="crm-lankpiller"
        description={text({ sv: "Öppnar webbplatsen i en ny flik", en: "Opens the website in a new tab" })}
        onClick={(e) => {
          e.stopPropagation();
          window.open(adress, "_blank", "noopener,noreferrer");
        }}
      />
    );
  }
  const href = slag === "epost" ? `mailto:${varde}` : `tel:${varde.replace(/[^\d+]/g, "")}`;
  return <Token label={visning} size="sm" icon={ikonElement} href={href} className="crm-lankpiller" />;
}

/**
 * Varifrån en post kom: anslutningens namn (eller Snajp och API:t) som dämpad
 * text med kontaktikon. Ingen platta: raden bär redan postchip, länkpiller och
 * relation, och källan är en uppgift, inte något att klicka på.
 */
export function Kallpiller({ kalla }: Readonly<{ kalla: string }>) {
  return (
    <span className="inline-flex min-w-0 max-w-full items-center gap-1.5 text-[0.8125rem] text-ink-muted">
      <Icon icon={Plug} size="xsm" color="inherit" />
      <span className="truncate">{kalla}</span>
    </span>
  );
}

/** Ett värde i kodstil med en kopieringsknapp bredvid (id, adresser, rubriknamn). */
export function Kopierbar({ varde, label }: Readonly<{ varde: string; label?: string }>) {
  const { text } = useLocale();
  const [kopierad, setKopierad] = useState(false);
  return (
    <span className="inline-flex min-w-0 items-center gap-1">
      <code className="crm-kod min-w-0 truncate">{varde}</code>
      <IconButton
        label={kopierad ? text({ sv: "Kopierad", en: "Copied" }) : (label ?? text({ sv: `Kopiera ${varde}`, en: `Copy ${varde}` }))}
        icon={<Icon icon={kopierad ? Check : Copy} size="sm" />}
        variant="ghost"
        size="md"
        onClick={() => {
          void navigator.clipboard.writeText(varde).then(
            () => {
              setKopierad(true);
              window.setTimeout(() => setKopierad(false), 1800);
            },
            () => setKopierad(false)
          );
        }}
      />
    </span>
  );
}

/**
 * Vägen till posten som redan har numret eller adressen, under ett fält eller
 * en rad som krockade (409 `conflict` med `conflicting_id`). En textlänk med
 * pil, inte en knapp: den leder bort, den ändrar ingenting.
 */
export function Krocklank({ etikett, onClick, href }: Readonly<{ etikett: string; onClick?: () => void; href?: string }>) {
  const innehall = (
    <>
      <span>{etikett}</span>
      <Icon icon={ArrowRight} size="xsm" color="inherit" />
    </>
  );
  return href ? (
    <NextLink href={href} onClick={onClick} className="crm-krocklank">
      {innehall}
    </NextLink>
  ) : (
    <button type="button" onClick={onClick} className="crm-krocklank">
      {innehall}
    </button>
  );
}

/**
 * Vyvalet ovanför en lista: namnet, och antalet i dämpad ton bredvid
 * (DESIGN-CRM.md § Sidhuvud och vyrad). SegmentedControlItem tar bara en
 * sträng som etikett, så antalet ritas av crm.css ur `data-antal`.
 */
export function Vyval<V extends string>({
  value,
  onChange,
  label,
  val
}: Readonly<{ value: V; onChange: (v: V) => void; label: string; val: { v: V; namn: string; antal?: string }[] }>) {
  return (
    <div className="crm-vyval min-w-0">
      <SegmentedControl value={value} onChange={(v) => onChange(v as V)} label={label} size="md">
        {val.map((f) => (
          <SegmentedControlItem key={f.v} value={f.v} label={f.namn} data-antal={f.antal} />
        ))}
      </SegmentedControl>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Smal skärm
// ---------------------------------------------------------------------------

const SMAL = "(max-width: 639.98px)";

function prenumereraSmal(anmal: () => void) {
  const m = window.matchMedia(SMAL);
  m.addEventListener("change", anmal);
  return () => m.removeEventListener("change", anmal);
}

/**
 * Sant under 640 px, där tabeller blir listor (DESIGN-CRM.md § Tabellen, Mobil).
 * Servern antar bred skärm; klienten rättar vid första målningen.
 */
export function useSmal(): boolean {
  return useSyncExternalStore(
    prenumereraSmal,
    () => window.matchMedia(SMAL).matches,
    () => false
  );
}

// ---------------------------------------------------------------------------
// Relationsetikett och statusprick
// ---------------------------------------------------------------------------

/** Kontraktets relationsfärger: kund mossa, prospekt ockra, tidigare kund mineral, partner och leverantör blå. */
export const RELATIONSTON: Record<Relation, { badge: "green" | "yellow" | "neutral" | "blue"; prick: Ton | null }> = {
  customer: { badge: "green", prick: "mossa" },
  prospect: { badge: "yellow", prick: "ockra" },
  former_customer: { badge: "neutral", prick: "mineral" },
  partner: { badge: "blue", prick: "bla" },
  supplier: { badge: "blue", prick: "bla" },
  not_relevant: { badge: "neutral", prick: null },
  other: { badge: "neutral", prick: null }
};

/**
 * En liten fylld prick i en objektfärg (StatusDot har bara fem varianter).
 * Bär ingen egen betydelse: texten bredvid säger alltid vad den betyder.
 */
export function Prick({ ton, pulserar = false }: Readonly<{ ton: Ton | "fara" | null; pulserar?: boolean }>) {
  const farg = ton === "fara" ? "oklch(var(--danger))" : ton ? "var(--crm-ton)" : "oklch(var(--ink) / 0.35)";
  return (
    <span aria-hidden className={klasser("relative inline-flex size-2 shrink-0", ton && ton !== "fara" && tonklass(ton))}>
      {pulserar ? <span className="absolute inset-0 animate-ping rounded-full opacity-60 motion-reduce:hidden" style={{ backgroundColor: farg }} /> : null}
      <span className="relative size-2 rounded-full" style={{ backgroundColor: farg }} />
    </span>
  );
}

/** Relationen som helt rundad etikett med statusprick. */
export function Relationsetikett({ relation }: Readonly<{ relation: Relation }>) {
  const { text } = useLocale();
  const stil = RELATIONSTON[relation];
  return <Badge variant={stil.badge} label={text(RELATIONER[relation])} icon={<Prick ton={stil.prick} />} />;
}

/**
 * En privatperson, i relationsetikettens form. Privatpersoner kontaktas
 * aldrig: etiketten säger det också, i en dold rad för skärmläsare och i
 * tipset, så att märkningen aldrig står utan sin följd.
 */
export function Privatpersonetikett() {
  const { text } = useLocale();
  return (
    <span title={text({ sv: "Privatperson. Kontaktas aldrig.", en: "Private person. Never contacted." })} className="inline-flex">
      <Badge variant="neutral" label={text({ sv: "Privatperson", en: "Private person" })} icon={<Prick ton="mineral" />} />
      <span className="sr-only">{text({ sv: ", kontaktas aldrig", en: ", never contacted" })}</span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Tabellens delar
// ---------------------------------------------------------------------------

/** Sorteringens val i vyraden (Bolag, Personer). Samma ordning som kolumnrubrikerna ger. */
export const ORDNINGAR: { v: Ordning; namn: Localized; vad: Localized }[] = [
  { v: "-updated", namn: { sv: "Senast ändrad", en: "Last changed" }, vad: { sv: "Det som ändrades senast står först", en: "What changed last comes first" } },
  { v: "updated", namn: { sv: "Ändringsordning", en: "Change order" }, vad: { sv: "Det som ändrades för längst sedan står först", en: "What changed longest ago comes first" } },
  { v: "name", namn: { sv: "Namn", en: "Name" }, vad: { sv: "A till Ö", en: "A to Z" } }
];

/**
 * Sorterbara kolumnrubriker för en lista som API:t sorterar (Bolag, Personer).
 * Rubriken med `sortable: true` och nyckeln `name` ger `name`; nyckeln
 * `updated_at` vänds mellan senast ändrad först (`-updated`) och äldst först
 * (`updated`). API:t har ingen omvänd namnordning, så namnet står kvar A till Ö.
 * Pluginet sorterar inga rader: vyn hämtar om när ordningen byts.
 */
export function useKolumnsortering<T extends Record<string, unknown>>(ordning: Ordning, satt: (o: Ordning) => void) {
  const sort = useMemo<TableSortState>(
    () =>
      ordning === "name"
        ? [{ sortKey: "name", direction: "ascending" }]
        : [{ sortKey: "updated_at", direction: ordning === "-updated" ? "descending" : "ascending" }],
    [ordning]
  );
  return useTableSortable<T>({
    sort,
    allowUnsortedState: false,
    onSortChange: (ny) => {
      const forsta = ny[0];
      if (!forsta) satt("-updated");
      else if (forsta.sortKey === "name") satt("name");
      // Från namnordningen börjar Ändrad med det senast ändrade, som listan öppnar med.
      else if (ordning === "name") satt("-updated");
      else satt(forsta.direction === "descending" ? "-updated" : "updated");
    }
  });
}

/** Kolumnrubrik: liten dämpad ikon per fälttyp plus rubriken. Svagare än datan under. */
export function Kolumnrubrik({ ikon, children }: Readonly<{ ikon: LucideIcon; children: string }>) {
  return (
    <span className="inline-flex min-w-0 items-center gap-1.5 text-[0.8125rem] font-semibold text-ink-muted">
      <Icon icon={ikon} size="xsm" color="inherit" />
      <span className="truncate">{children}</span>
    </span>
  );
}

/**
 * Laddning i tabellens form: rader på tabellens höjd med kryssruta, avatar och
 * celler, inte en naken förloppsstapel.
 */
export function Tabellskelett({
  rader = 8,
  kolumner = 5,
  markering = true,
  label
}: Readonly<{ rader?: number; kolumner?: number; markering?: boolean; label?: string }>) {
  const { text } = useLocale();
  const bredder = ["30%", "18%", "14%", "12%", "10%", "8%"];
  return (
    <div role="status" aria-busy="true" aria-label={label ?? text({ sv: "Hämtar", en: "Loading" })} className="divide-y divide-ink/[0.07]">
      {Array.from({ length: rader }, (_, i) => (
        <div key={i} className="flex h-11 items-center gap-4 px-3">
          {markering ? <Skeleton width={16} height={16} radius={1} index={i} /> : null}
          <span className="flex w-[30%] items-center gap-2">
            <Skeleton width={20} height={20} radius={1} index={i} />
            <Skeleton width={`${55 + ((i * 17) % 35)}%`} height={10} radius="rounded" index={i} />
          </span>
          {Array.from({ length: Math.max(0, kolumner - 1) }, (_, k) => (
            <Skeleton key={k} width={bredder[(k + 1) % bredder.length]} height={10} radius="rounded" index={i + k} />
          ))}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Kort
// ---------------------------------------------------------------------------

/**
 * Ett nyckeltal: etikett överst, talet i Fraunces 2,5 rem, en dämpad rad under.
 * `framhavd` är sidans enda framhävda ruta (ockratonad). Med `href` är hela kortet
 * en länk dit talet kommer ifrån.
 */
export function Nyckeltalskort({
  etikett,
  varde,
  rad,
  href,
  label,
  framhavd = false,
  laddar = false
}: Readonly<{
  etikett: string;
  varde: number | null;
  rad?: string;
  href?: string;
  label?: string;
  framhavd?: boolean;
  laddar?: boolean;
}>) {
  const { locale } = useLocale();
  const innehall = (
    <VStack gap={2}>
      <Text type="label" color="secondary" weight="medium">
        {etikett}
      </Text>
      {laddar || varde == null ? (
        <Skeleton width={72} height={40} radius={2} />
      ) : (
        <span className="crm-tal block text-[2.5rem] leading-[1.05] text-ink">{varde.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB")}</span>
      )}
      {rad ? (
        <Text type="supporting" color="secondary" maxLines={2}>
          {rad}
        </Text>
      ) : null}
    </VStack>
  );
  const klass = framhavd ? "crm-kort-framhavd" : "crm-kort";
  if (href) {
    return (
      <ClickableCard label={label ?? etikett} href={href} variant={framhavd ? "yellow" : "default"} padding={5} className={klass} height="100%">
        {innehall}
      </ClickableCard>
    );
  }
  return (
    <Card variant={framhavd ? "yellow" : "default"} padding={5} className={klass} height="100%">
      {innehall}
    </Card>
  );
}

/**
 * Ett kort i översiktens rutnät: titel uppe till vänster (Geist halvfet), valfritt
 * innehåll till höger om titeln, och en dämpad fot.
 */
export function Panelkort({
  titel,
  hoger,
  fot,
  children,
  id
}: Readonly<{ titel: string; hoger?: React.ReactNode; fot?: React.ReactNode; children: React.ReactNode; id?: string }>) {
  return (
    <Card padding={5} className="crm-kort" height="100%">
      <section aria-labelledby={id} className="flex h-full flex-col gap-4">
        <HStack gap={3} vAlign="center">
          <StackItem size="fill">
            <Text as="h2" id={id} weight="semibold" maxLines={1}>
              {titel}
            </Text>
          </StackItem>
          {hoger}
        </HStack>
        <div className="flex-1">{children}</div>
        {fot ? (
          <Text type="supporting" color="secondary">
            {fot}
          </Text>
        ) : null}
      </section>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Beställningar via adressen
// ---------------------------------------------------------------------------

/**
 * Kommandopaletten beställer saker av vyerna genom adressen: `?ny=1` öppnar
 * vyns skapa-dialog, `?bolag=<id>` öppnar ett bolags panel. Adressen överlever
 * både klientnavigering och omladdning, och vyn behöver ingen delad kontext.
 *
 * Hooken anropar `gor(varde)` en gång per nytt värde och tar sedan bort
 * parametern ur adressen, så att en omladdning inte öppnar dialogen igen.
 */
export function useBestallning(nyckel: string, gor: (varde: string) => void) {
  const params = useSearchParams();
  const router = useRouter();
  const vag = usePathname();
  const varde = params?.get(nyckel) ?? null;
  const senast = useRef<string | null>(null);
  const gorRef = useRef(gor);
  gorRef.current = gor;

  useEffect(() => {
    if (!varde || senast.current === varde) return;
    senast.current = varde;
    gorRef.current(varde);
    const kvar = new URLSearchParams(params?.toString() ?? "");
    kvar.delete(nyckel);
    const fraga = kvar.toString();
    router.replace(fraga ? `${vag}?${fraga}` : (vag ?? ""), { scroll: false });
  }, [varde, nyckel, params, router, vag]);

  useEffect(() => {
    if (!varde) senast.current = null;
  }, [varde]);
}
