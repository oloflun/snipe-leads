"use client";

import "@/components/crm/app/crm-vyer.css";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  CalendarClock,
  Check,
  CircleDot,
  Clock,
  Layers,
  Pause,
  Play,
  Plug,
  Plus,
  RefreshCw,
  Scale,
  Tag,
  Trash2,
  Unplug,
  type LucideIcon
} from "lucide-react";
import { AlertDialog } from "@astryxdesign/core/AlertDialog";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Badge } from "@astryxdesign/core/Badge";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { Card } from "@astryxdesign/core/Card";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { Drawer, DrawerHeader } from "@astryxdesign/core/Drawer";
import { type DropdownMenuOption } from "@astryxdesign/core/DropdownMenu";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Grid } from "@astryxdesign/core/Grid";
import { Icon } from "@astryxdesign/core/Icon";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { List, ListItem } from "@astryxdesign/core/List";
import { MetadataList, MetadataListItem } from "@astryxdesign/core/MetadataList";
import { MoreMenu } from "@astryxdesign/core/MoreMenu";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { Selector } from "@astryxdesign/core/Selector";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { HStack } from "@astryxdesign/core/Stack";
import { Table, pixel, proportional, type TableColumn } from "@astryxdesign/core/Table";
import { Text } from "@astryxdesign/core/Text";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { useToast } from "@astryxdesign/core/Toast";
import { Kolumnrubrik, Kopierbar, Postchip, Prick, Relationsetikett, Tabellskelett, tonFor, tonklass, useBestallning, useSmal, Vyval, type Ton } from "@/components/crm/app/kit";
import { Felruta, Sida } from "@/components/crm/app/Sida";
import { CrmFel, RELATIONER, SYSTEMNAMN, crmAnrop, type Anslutning, type Korning, type Relation } from "@/lib/crm/api";
import { SYNKPULS, avslutar, klara, pagar, useAktuell, useSynklage } from "@/components/crm/app/synklage";
import { FALTKODER, KORNINGSFEL, ORSAKER, kodtext } from "@/lib/crm/felkoder";
import { useLocale, type Localized } from "@/lib/i18n";

// ---------------------------------------------------------------------------
// Ord och räkning
// ---------------------------------------------------------------------------

const KONFLIKT: Record<Anslutning["conflict_rule"], { namn: Localized; vad: Localized }> = {
  source_wins: { namn: { sv: "Källan vinner", en: "Source wins" }, vad: { sv: "Källans värde gäller.", en: "The source's value applies." } },
  snajp_wins: { namn: { sv: "Snajp vinner", en: "Snajp wins" }, vad: { sv: "Värdet i Snajp gäller.", en: "The value in Snajp applies." } },
  newest_wins: { namn: { sv: "Nyast vinner", en: "Newest wins" }, vad: { sv: "Det senast ändrade värdet gäller.", en: "The most recently changed value applies." } }
};
const SAKNADE: Record<Anslutning["missing_records"], { namn: Localized; vad: Localized }> = {
  keep: { namn: { sv: "Behålls", en: "Kept" }, vad: { sv: "Posterna ligger kvar som de är.", en: "The records stay as they are." } },
  mark_former_customer: { namn: { sv: "Blir tidigare kunder", en: "Become former customers" }, vad: { sv: "Bolagen får relationen tidigare kund.", en: "The companies get the relation former customer." } },
  delete: { namn: { sv: "Tas bort", en: "Deleted" }, vad: { sv: "Posterna tas bort ur Snajp.", en: "The records are deleted from Snajp." } }
};
const STATUS: Record<Korning["status"], { text: Localized; badge: "neutral" | "yellow" | "green" | "red"; prick: Ton | "fara" | null }> = {
  queued: { text: { sv: "Köad", en: "Queued" }, badge: "neutral", prick: null },
  processing: { text: { sv: "Pågår", en: "Running" }, badge: "yellow", prick: "ockra" },
  completed: { text: { sv: "Klar", en: "Completed" }, badge: "green", prick: "mossa" },
  failed: { text: { sv: "Misslyckades", en: "Failed" }, badge: "red", prick: "fara" }
};

type Filter = "alla" | "pagar" | "ratta" | "fel";

/** Samma räkning som översiktens kort Att rätta: felposterna, och hoppade poster utöver dem. */
const attRatta = (k: Korning) => k.errors.length + Math.max(0, k.counts.skipped - k.errors.length);
const systemnamn = (s: string) => SYSTEMNAMN[s] ?? s;

/** Körningens utfall i en mening, på läsarens språk. */
function utfall(k: Korning, text: (l: Localized) => string, tal: (n: number) => string): string {
  if (k.status === "failed") return text(k.error ? kodtext(KORNINGSFEL, k.error) : { sv: "Körningen misslyckades.", en: "The run failed." });
  if (k.status === "queued") return text({ sv: "Väntar på att starta", en: "Waiting to start" });
  if (avslutar(k)) return text({ sv: `Avslutar, ${tal(k.counts.total)} poster behandlade`, en: `Finishing, ${tal(k.counts.total)} records processed` });
  if (k.status === "processing") return text({ sv: `${tal(klara(k))} av ${tal(k.counts.total)} poster`, en: `${tal(klara(k))} of ${tal(k.counts.total)} records` });
  const ratta = attRatta(k);
  const delar = [
    text({ sv: `${tal(k.counts.created)} nya`, en: `${tal(k.counts.created)} new` }),
    text({ sv: `${tal(k.counts.updated)} ändrade`, en: `${tal(k.counts.updated)} changed` }),
    ...(k.counts.removed ? [text({ sv: `${tal(k.counts.removed)} borttagna`, en: `${tal(k.counts.removed)} removed` })] : []),
    ratta ? text({ sv: `${tal(ratta)} att rätta`, en: `${tal(ratta)} to fix` }) : text({ sv: "inget att rätta", en: "nothing to fix" })
  ];
  return delar.join(", ");
}

/** Statusen som helt rundad etikett med prick; den pågående pricken pulserar. */
function Statusetikett({ k }: Readonly<{ k: Korning }>) {
  const { text } = useLocale();
  const s = STATUS[k.status];
  return <Badge variant={s.badge} label={text(s.text)} icon={<Prick ton={s.prick} pulserar={k.status === "processing"} />} />;
}

/** Systemets platta: initialerna på objektfärg ur systemets namn. */
function Systemplatta({ system, storlek = 40 }: Readonly<{ system: string; storlek?: 32 | 40 | 48 }>) {
  const namn = systemnamn(system);
  return <Avatar name={namn} size={storlek} shape="rounded" tooltip={false} className={`crm-avatar crm-avatar-system ${tonklass(tonFor(system))}`} />;
}

// ---------------------------------------------------------------------------
// Vyn
// ---------------------------------------------------------------------------

/**
 * Synken (DESIGN-CRM.md § Tabellen; CLAUDE.md: varje funktion visar sitt
 * förlopp). Anslutningarna står som kort med sina regler och en meny med det
 * API:t kan ändra. Körningarna står i tabellens anatomi med status, förlopp och
 * utfall i klartext; medan något pågår hämtas listan var tredje sekund. Allt
 * kommer ur liggaren i API:t och står kvar efter en omladdning. Körningens panel
 * följer adressen (`?korning=<id>`); `?ny=1` öppnar dialogen Ny anslutning.
 */
export function SynkVy({ utvecklarvag = "/crm/utvecklare" }: Readonly<{ utvecklarvag?: string }>) {
  const { text, locale } = useLocale();
  const visa = useToast();
  const smal = useSmal();
  const params = useSearchParams();
  const adressensKorning = params?.get("korning") ?? null;
  // Panelen följer adressen men hålls också i eget läge: replaceState når inte
  // alltid useSearchParams, och ett klick ska öppna panelen direkt.
  const [korningId, setKorningId] = useState<string | null>(adressensKorning);
  useEffect(() => {
    setKorningId(adressensKorning);
  }, [adressensKorning]);
  const sprak = locale === "sv" ? "sv-SE" : "en-GB";
  const tal = useCallback((n: number) => n.toLocaleString(sprak), [sprak]);

  const [anslutningar, setAnslutningar] = useState<Anslutning[] | null>(null);
  const [hamtade, setKorningar] = useState<Korning[] | null>(null);
  // Det som hämtas här lämnas in i det delade läget, och det som visas är alltid
  // det senast hämtade, så att navigeringens kort och tabellen säger samma tal.
  const { publicera } = useSynklage();
  const korningar = useAktuell(hamtade);
  const [fel, setFel] = useState<unknown>(null);
  const [ny, setNy] = useState(false);
  const [filter, setFilter] = useState<Filter>("alla");
  const [ensam, setEnsam] = useState<Korning | null>(null);
  const [taBort, setTaBort] = useState<Anslutning | null>(null);
  const [andrar, setAndrar] = useState<string | null>(null);

  useBestallning("ny", () => setNy(true));

  const hamta = useCallback(async () => {
    try {
      const [a, k] = await Promise.all([crmAnrop<{ data: Anslutning[] }>("/v1/connections"), crmAnrop<{ data: Korning[] }>("/v1/sync/runs?limit=50")]);
      setAnslutningar(a.data);
      setKorningar(k.data);
      publicera(k.data);
      setFel(null);
    } catch (e) {
      setFel(e);
    }
  }, [publicera]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  // Förloppet följs här, där synken syns: så länge en körning pågår hämtas
  // listan om var tredje sekund. Utfallet ligger kvar i liggaren efter omladdning.
  const nagotPagar = korningar?.some(pagar) ?? false;
  useEffect(() => {
    if (!nagotPagar) return;
    const t = window.setInterval(() => void hamta(), SYNKPULS);
    return () => window.clearInterval(t);
  }, [nagotPagar, hamta]);

  const perId = useMemo(() => Object.fromEntries((anslutningar ?? []).map((a) => [a.id, a])), [anslutningar]);
  const anslutningsnamn = useCallback((id: string | null) => (id && perId[id] ? systemnamnFor(perId[id]) : text({ sv: "Okänd källa", en: "Unknown source" })), [perId, text]);

  // ---- Körningens panel följer adressen -------------------------------------

  const sattKorning = useCallback((id: string | null) => {
    setKorningId(id);
    const q = new URLSearchParams(window.location.search);
    if (id) q.set("korning", id);
    else q.delete("korning");
    const s = q.toString();
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${s ? `?${s}` : ""}`);
  }, []);

  const iListan = korningId ? (korningar?.find((k) => k.id === korningId) ?? null) : null;
  useEffect(() => {
    setEnsam(null);
    if (!korningId || !korningar || iListan) return;
    // Äldre än de 50 senaste: hämtas för sig.
    let aktuell = true;
    crmAnrop<Korning>(`/v1/sync/runs/${encodeURIComponent(korningId)}`)
      .then((k) => aktuell && setEnsam(k))
      .catch((e) => {
        if (!aktuell) return;
        sattKorning(null);
        visa({ type: "error", body: text(e instanceof CrmFel ? e.text : { sv: "Körningen finns inte.", en: "The run does not exist." }), uniqueID: "crm-korning-saknas" });
      });
    return () => {
      aktuell = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [korningId, korningar == null]);
  const oppen = iListan ?? ensam;

  // ---- Ändra en anslutning --------------------------------------------------

  async function andra(a: Anslutning, falt: Partial<Pick<Anslutning, "active" | "conflict_rule" | "missing_records">>, klart: Localized) {
    setAndrar(a.id);
    try {
      const ny = await crmAnrop<Anslutning>(`/v1/connections/${encodeURIComponent(a.id)}`, { method: "PATCH", body: JSON.stringify(falt) });
      setAnslutningar((forr) => (forr ?? []).map((x) => (x.id === ny.id ? ny : x)));
      visa({ body: text(klart), uniqueID: "crm-anslutning-andrad" });
    } catch (e) {
      visa({ type: "error", body: text(e instanceof CrmFel ? e.text : { sv: "Det gick inte att ändra anslutningen.", en: "Could not change the connection." }), uniqueID: "crm-anslutning-andrad" });
    } finally {
      setAndrar(null);
    }
  }

  async function radera(a: Anslutning) {
    setTaBort(null);
    try {
      await crmAnrop<null>(`/v1/connections/${encodeURIComponent(a.id)}`, { method: "DELETE" });
      visa({ body: text({ sv: `Anslutningen ${systemnamnFor(a)} är borttagen.`, en: `The connection ${systemnamnFor(a)} is deleted.` }), uniqueID: "crm-anslutning-borttagen" });
      void hamta();
    } catch (e) {
      visa({ type: "error", body: text(e instanceof CrmFel ? e.text : { sv: "Det gick inte att ta bort anslutningen.", en: "Could not delete the connection." }), uniqueID: "crm-anslutning-borttagen" });
    }
  }

  // ---- Körningarnas tabell --------------------------------------------------

  const raknat = useMemo(() => {
    const k = korningar ?? [];
    return { alla: k.length, pagar: k.filter(pagar).length, ratta: k.filter((x) => x.status === "completed" && attRatta(x) > 0).length, fel: k.filter((x) => x.status === "failed").length };
  }, [korningar]);
  const visade = useMemo(() => {
    const k = korningar ?? [];
    if (filter === "pagar") return k.filter(pagar);
    if (filter === "ratta") return k.filter((x) => x.status === "completed" && attRatta(x) > 0);
    if (filter === "fel") return k.filter((x) => x.status === "failed");
    return k;
  }, [korningar, filter]);

  const kolumner = useMemo<TableColumn<Korning>[]>(
    () => [
      {
        key: "connection",
        header: <Kolumnrubrik ikon={Plug}>{text({ sv: "Anslutning", en: "Connection" })}</Kolumnrubrik>,
        width: pixel(176),
        renderCell: (k) => {
          const a = k.connection_id ? perId[k.connection_id] : null;
          const namn = anslutningsnamn(k.connection_id);
          return (
            <Postchip
              namn={namn}
              ton={tonFor(a?.system ?? namn)}
              onClick={() => sattKorning(k.id)}
              label={text({ sv: `Öppna körningen från ${namn}`, en: `Open the run from ${namn}` })}
            />
          );
        }
      },
      {
        key: "status",
        header: <Kolumnrubrik ikon={CircleDot}>{text({ sv: "Status", en: "Status" })}</Kolumnrubrik>,
        width: pixel(148),
        renderCell: (k) => <Statusetikett k={k} />
      },
      {
        key: "mode",
        header: <Kolumnrubrik ikon={Layers}>{text({ sv: "Omfång", en: "Scope" })}</Kolumnrubrik>,
        width: pixel(124),
        renderCell: (k) => <span className="text-ink2">{k.mode === "full" ? text({ sv: "Full synk", en: "Full sync" }) : text({ sv: "Ändringar", en: "Changes" })}</span>
      },
      {
        key: "counts",
        header: <Kolumnrubrik ikon={RefreshCw}>{text({ sv: "Utfall", en: "Outcome" })}</Kolumnrubrik>,
        width: proportional(1, { minWidth: 260 }),
        renderCell: (k) =>
          k.status === "processing" ? (
            <div className="flex items-center gap-3 pr-2">
              <div className="min-w-0 flex-1">
                <ProgressBar
                  label={text({ sv: `Förloppet för ${anslutningsnamn(k.connection_id)}`, en: `Progress for ${anslutningsnamn(k.connection_id)}` })}
                  isLabelHidden
                  value={klara(k)}
                  max={Math.max(k.counts.total, 1)}
                  isIndeterminate={k.counts.total === 0 || avslutar(k)}
                />
              </div>
              <span className="whitespace-nowrap text-[0.8125rem] tabular-nums text-ink-muted">{utfall(k, text, tal)}</span>
            </div>
          ) : (
            <span className={k.status === "failed" ? "text-ink" : "text-ink2"}>{utfall(k, text, tal)}</span>
          )
      },
      {
        key: "errors",
        header: <Kolumnrubrik ikon={AlertTriangle}>{text({ sv: "Att rätta", en: "To fix" })}</Kolumnrubrik>,
        width: pixel(128),
        renderCell: (k) => {
          const n = attRatta(k);
          return n > 0 ? (
            <button type="button" className="crm-chip inline-flex h-7 items-center gap-1.5 rounded-[6px] px-2 text-[0.8125rem] font-semibold text-warning" onClick={() => sattKorning(k.id)}>
              <Icon icon={AlertTriangle} size="xsm" color="inherit" />
              <span className="tabular-nums">{text({ sv: `${tal(n)} poster`, en: `${tal(n)} records` })}</span>
            </button>
          ) : (
            <span className="text-ink-muted">{k.status === "completed" ? text({ sv: "Inget", en: "Nothing" }) : ""}</span>
          );
        }
      },
      {
        key: "created_at",
        header: <Kolumnrubrik ikon={Clock}>{text({ sv: "Startad", en: "Started" })}</Kolumnrubrik>,
        width: pixel(156),
        renderCell: (k) => (k.created_at ? <Timestamp value={k.created_at} format="relative" isLive={pagar(k)} /> : null)
      }
    ],
    [text, tal, perId, anslutningsnamn, sattKorning]
  );

  // ---- Delarna --------------------------------------------------------------

  const laddar = anslutningar == null || korningar == null;
  const filtervyer: { v: Filter; namn: Localized }[] = [
    { v: "alla", namn: { sv: "Alla", en: "All" } },
    { v: "pagar", namn: { sv: "Pågår", en: "Running" } },
    { v: "ratta", namn: { sv: "Att rätta", en: "To fix" } },
    { v: "fel", namn: { sv: "Misslyckade", en: "Failed" } }
  ];

  const nyAnslutning = <Button variant="primary" label={text({ sv: "Ny anslutning", en: "New connection" })} icon={<Icon icon={Plus} size="sm" />} onClick={() => setNy(true)} />;

  return (
    <Sida
      objekt="synk"
      rubrik={text({ sv: "Synk", en: "Sync" })}
      antal={anslutningar ? tal(anslutningar.length) : undefined}
      atgarder={nyAnslutning}
      utfyllnad="sida"
    >
      {fel && laddar ? (
        <div className="pt-4">
          <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />} />
        </div>
      ) : (
        <div className="flex flex-col gap-8 pt-4">
          {/* Anslutningarna */}
          <section aria-labelledby="crm-anslutningar" className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <h2 id="crm-anslutningar" className="crm-delrubrik">
                {text({ sv: "Anslutningar", en: "Connections" })}
              </h2>
            </div>
            {laddar ? (
              <Grid columns={{ minWidth: 300, max: 3 }} gap={4}>
                {[0, 1].map((i) => (
                  <Card key={i} padding={5} className="crm-anslutning">
                    <div className="flex flex-col gap-4" role="status" aria-busy="true" aria-label={text({ sv: "Hämtar anslutningar", en: "Loading connections" })}>
                      <div className="flex items-center gap-3">
                        <Skeleton width={40} height={40} radius={3} index={i} />
                        <Skeleton width="40%" height={12} radius="rounded" index={i} />
                      </div>
                      {[0, 1, 2].map((r) => (
                        <Skeleton key={r} width={`${50 + r * 12}%`} height={10} radius="rounded" index={i + r} />
                      ))}
                    </div>
                  </Card>
                ))}
              </Grid>
            ) : anslutningar.length === 0 ? (
              <Card padding={6} className="crm-anslutning">
                <EmptyState
                  icon={<Icon icon={Unplug} size="lg" color="secondary" />}
                  title={text({ sv: "Ingen anslutning än", en: "No connection yet" })}
                  description={text({
                    sv: "En anslutning är en källa, till exempel ert CRM. Skapa den här, hämta en nyckel under Utvecklare och låt källan skicka sina bolag.",
                    en: "A connection is a source, for example your CRM. Create it here, get a key under Developers and let the source send its companies."
                  })}
                  actions={
                    <>
                      {nyAnslutning}
                      <Button variant="secondary" label={text({ sv: "Till Utvecklare", en: "Go to Developers" })} href={utvecklarvag} />
                    </>
                  }
                />
              </Card>
            ) : (
              <Grid columns={{ minWidth: 300, max: 3 }} gap={4}>
                {anslutningar.map((a) => (
                  <Anslutningskort
                    key={a.id}
                    a={a}
                    senaste={(korningar ?? []).find((k) => k.connection_id === a.id) ?? null}
                    arbetar={andrar === a.id}
                    andra={(falt, klart) => void andra(a, falt, klart)}
                    taBort={() => setTaBort(a)}
                    oppnaKorning={(id) => sattKorning(id)}
                  />
                ))}
                <button type="button" className="crm-nytt-kort" onClick={() => setNy(true)}>
                  <span aria-hidden className="inline-flex size-9 items-center justify-center rounded-full bg-ink/[0.05]">
                    <Icon icon={Plus} size="sm" color="inherit" />
                  </span>
                  {text({ sv: "Lägg till en anslutning", en: "Add a connection" })}
                </button>
              </Grid>
            )}
          </section>

          {/* Körningarna */}
          <section aria-labelledby="crm-korningar" className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
              <h2 id="crm-korningar" className="crm-delrubrik">
                {text({ sv: "Körningar", en: "Runs" })}
              </h2>
              {!laddar && korningar.length > 0 ? (
                smal ? (
                  <Selector
                    label={text({ sv: "Visa körningar", en: "Show runs" })}
                    isLabelHidden
                    variant="secondary"
                    size="md"
                    value={filter}
                    onChange={(v) => v && setFilter(v as Filter)}
                    options={filtervyer.map((f) => ({ value: f.v, label: `${text(f.namn)}  ${tal(raknat[f.v])}` }))}
                  />
                ) : (
                  <Vyval
                    value={filter}
                    onChange={setFilter}
                    label={text({ sv: "Visa körningar", en: "Show runs" })}
                    val={filtervyer.map((f) => ({ v: f.v, namn: text(f.namn), antal: tal(raknat[f.v]) }))}
                  />
                )
              ) : null}
            </div>
            <div className="crm-tabellram">
              {laddar ? (
                <Tabellskelett rader={5} kolumner={smal ? 2 : 6} markering={false} label={text({ sv: "Hämtar körningar", en: "Loading runs" })} />
              ) : visade.length === 0 ? (
                <div className="py-10">
                  <EmptyState
                    icon={<Icon icon={RefreshCw} size="lg" color="secondary" />}
                    title={
                      korningar.length === 0
                        ? text({ sv: "Ingen synk har körts", en: "No sync has run" })
                        : text({ sv: "Inga körningar i den här vyn", en: "No runs in this view" })
                    }
                    description={
                      korningar.length === 0
                        ? text({
                            sv: "Varje synk från en källa syns här, med förlopp medan den pågår och utfall efteråt.",
                            en: "Every sync from a source shows here, with progress while it runs and the outcome afterwards."
                          })
                        : text({ sv: "Listan gäller de 50 senaste körningarna.", en: "The list covers the 50 latest runs." })
                    }
                    actions={korningar.length > 0 ? <Button variant="secondary" label={text({ sv: "Visa alla", en: "Show all" })} onClick={() => setFilter("alla")} /> : undefined}
                  />
                </div>
              ) : smal ? (
                <div className="px-2">
                  <List hasDividers density="balanced" edge="padded">
                    {visade.map((k) => (
                      <ListItem
                        key={k.id}
                        label={<span className="font-semibold text-ink">{anslutningsnamn(k.connection_id)}</span>}
                        description={utfall(k, text, tal)}
                        // Statusen står i ord, inte bara som prickens färg.
                        endContent={<Statusetikett k={k} />}
                        onClick={() => sattKorning(k.id)}
                        isSelected={oppen?.id === k.id}
                      />
                    ))}
                  </List>
                </div>
              ) : (
                <div className="crm-tabell crm-tabell-utan-val">
                  <Table<Korning> data={visade} columns={kolumner} idKey="id" density="balanced" dividers="rows" hasHover textOverflow="truncate" />
                  <div className="crm-raknefot" role="status">
                    <span>
                      <span className="crm-raknefot-etikett">{text({ sv: "Visar", en: "Showing" })}</span> <span className="crm-raknefot-tal">{tal(visade.length)}</span>{" "}
                      <span className="crm-raknefot-etikett">{text({ sv: "av de senaste", en: "of the latest" })}</span> <span className="crm-raknefot-tal">{tal(korningar.length)}</span>
                    </span>
                    {nagotPagar ? (
                      <span className="inline-flex items-center gap-2">
                        <Prick ton="ockra" pulserar />
                        <span className="crm-raknefot-etikett">{text({ sv: "Följer förloppet, uppdateras var tredje sekund", en: "Following the progress, updated every three seconds" })}</span>
                      </span>
                    ) : null}
                  </div>
                </div>
              )}
            </div>
          </section>
        </div>
      )}

      <Korningspanel korning={oppen} laddar={korningId != null && oppen == null} anslutning={oppen ? (perId[oppen.connection_id ?? ""] ?? null) : null} stang={() => sattKorning(null)} />

      <NyAnslutning
        oppen={ny}
        stang={() => setNy(false)}
        skapad={(a) => {
          setNy(false);
          visa({ body: text({ sv: `Anslutningen ${systemnamnFor(a)} är skapad.`, en: `The connection ${systemnamnFor(a)} is created.` }), uniqueID: "crm-anslutning-skapad" });
          void hamta();
        }}
      />

      <AlertDialog
        isOpen={taBort != null}
        onOpenChange={(o) => !o && setTaBort(null)}
        title={text({ sv: `Ta bort anslutningen ${taBort ? systemnamnFor(taBort) : ""}?`, en: `Delete the connection ${taBort ? systemnamnFor(taBort) : ""}?` })}
        description={text({
          sv: "Bolagen och personerna ligger kvar. Källans id för dem glöms, så nästa synk från källan börjar om och matchar på organisationsnummer och e-post.",
          en: "The companies and people stay. The source's ids for them are forgotten, so the next sync from the source starts over and matches on organisation number and email."
        })}
        actionLabel={text({ sv: "Ta bort", en: "Delete" })}
        cancelLabel={text({ sv: "Avbryt", en: "Cancel" })}
        onAction={() => taBort && void radera(taBort)}
      />
    </Sida>
  );
}

/** Anslutningens namn som det står i systemlistan när namnet är systemets, annars kundens eget. */
function systemnamnFor(a: Anslutning) {
  return SYSTEMNAMN[a.name] ?? a.name;
}

// ---------------------------------------------------------------------------
// Anslutningskortet
// ---------------------------------------------------------------------------

function Anslutningskort({
  a,
  senaste,
  arbetar,
  andra,
  taBort,
  oppnaKorning
}: Readonly<{
  a: Anslutning;
  senaste: Korning | null;
  arbetar: boolean;
  andra: (falt: Partial<Pick<Anslutning, "active" | "conflict_rule" | "missing_records">>, klart: Localized) => void;
  taBort: () => void;
  oppnaKorning: (id: string) => void;
}>) {
  const { text, locale } = useLocale();
  const tal = (n: number) => n.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB");
  const namn = systemnamnFor(a);
  const bock = (pa: boolean) => (pa ? <Icon icon={Check} size="sm" color="secondary" /> : undefined);
  const ikon = (i: LucideIcon) => <Icon icon={i} size="sm" color="inherit" />;

  const meny: DropdownMenuOption[] = [
    a.active
      ? { label: text({ sv: "Pausa", en: "Pause" }), icon: Pause, description: text({ sv: "Källan kan inte synka förrän ni återupptar.", en: "The source cannot sync until you resume." }), onClick: () => andra({ active: false }, { sv: `${namn} är pausad.`, en: `${namn} is paused.` }) }
      : { label: text({ sv: "Återuppta", en: "Resume" }), icon: Play, onClick: () => andra({ active: true }, { sv: `${namn} är aktiv igen.`, en: `${namn} is active again.` }) },
    {
      label: text({ sv: "Vid konflikt", en: "On conflict" }),
      icon: Scale,
      items: (Object.keys(KONFLIKT) as Anslutning["conflict_rule"][]).map((r) => ({
        label: text(KONFLIKT[r].namn),
        description: text(KONFLIKT[r].vad),
        endContent: bock(a.conflict_rule === r),
        onClick: () => andra({ conflict_rule: r }, { sv: `${namn}: ${KONFLIKT[r].namn.sv.toLowerCase()}.`, en: `${namn}: ${KONFLIKT[r].namn.en.toLowerCase()}.` })
      }))
    },
    {
      label: text({ sv: "Poster som försvunnit", en: "Missing records" }),
      icon: Unplug,
      items: (Object.keys(SAKNADE) as Anslutning["missing_records"][]).map((r) => ({
        label: text(SAKNADE[r].namn),
        description: text(SAKNADE[r].vad),
        endContent: bock(a.missing_records === r),
        onClick: () => andra({ missing_records: r }, { sv: `${namn}: försvunna poster ${SAKNADE[r].namn.sv.toLowerCase()}.`, en: `${namn}: missing records ${SAKNADE[r].namn.en.toLowerCase()}.` })
      }))
    },
    { type: "divider" },
    { label: text({ sv: "Ta bort anslutningen", en: "Delete the connection" }), icon: Trash2, variant: "destructive", onClick: taBort }
  ];

  return (
    <Card padding={5} className={a.active ? "crm-anslutning" : "crm-anslutning crm-anslutning-pausad"} height="100%">
      <article aria-label={namn} className="flex h-full flex-col gap-4">
        <div className="flex items-start gap-3">
          <Systemplatta system={a.system} />
          <div className="flex min-w-0 flex-1 flex-col">
            <span className="truncate text-[0.9375rem] font-semibold text-ink">{namn}</span>
            <span className="truncate text-[0.8125rem] text-ink-muted">
              {a.name !== a.system && SYSTEMNAMN[a.system] ? systemnamn(a.system) : text({ sv: "Källsystem", en: "Source system" })}
            </span>
          </div>
          {a.active ? (
            <Badge variant="green" label={text({ sv: "Aktiv", en: "Active" })} icon={<Prick ton="mossa" />} />
          ) : (
            <Badge variant="neutral" label={text({ sv: "Pausad", en: "Paused" })} icon={<Prick ton={null} />} />
          )}
          <MoreMenu items={meny} label={text({ sv: `Ändra ${namn}`, en: `Change ${namn}` })} alignment="end" size="sm" isDisabled={arbetar} />
        </div>

        <div className="crm-panelinnehall">
          <MetadataList label={{ position: "start", width: 148 }}>
            <MetadataListItem label={text({ sv: "Vid konflikt", en: "On conflict" })} icon={ikon(Scale)}>
              <span className="crm-varde">{text(KONFLIKT[a.conflict_rule].namn)}</span>
            </MetadataListItem>
            <MetadataListItem label={text({ sv: "Försvunna poster", en: "Missing records" })} icon={ikon(Unplug)}>
              <span className="crm-varde">{text(SAKNADE[a.missing_records].namn)}</span>
            </MetadataListItem>
            <MetadataListItem label={text({ sv: "Nya bolag blir", en: "New companies are" })} icon={ikon(Tag)}>
              <Relationsetikett relation={a.default_relation as Relation} />
            </MetadataListItem>
            <MetadataListItem label={text({ sv: "Senaste synk", en: "Last sync" })} icon={ikon(CalendarClock)}>
              {a.last_sync_at ? <Timestamp value={a.last_sync_at} format="relative" color="primary" /> : <span className="crm-varde text-ink-muted">{text({ sv: "Aldrig", en: "Never" })}</span>}
            </MetadataListItem>
          </MetadataList>
        </div>

        {senaste ? (
          <button
            type="button"
            onClick={() => oppnaKorning(senaste.id)}
            className="crm-chip crm-chip-platta mt-auto flex w-full flex-col gap-2 rounded-[10px] px-3 py-2.5 text-left"
          >
            {/* Det synliga bär knappens namn; handlingen står efter, dold för ögat. */}
            <span className="flex w-full items-center gap-2">
              <Prick ton={STATUS[senaste.status].prick} pulserar={senaste.status === "processing"} />
              <span className="min-w-0 flex-1 truncate text-[0.8125rem] text-ink2">
                {utfall(senaste, text, tal)}
                <span className="sr-only">{text({ sv: `. ${text(STATUS[senaste.status].text)}. Öppna körningen.`, en: `. ${text(STATUS[senaste.status].text)}. Open the run.` })}</span>
              </span>
              {senaste.created_at ? <Timestamp value={senaste.completed_at ?? senaste.created_at} format="relative" hasTooltip={false} /> : null}
            </span>
            {senaste.status === "processing" ? (
              <ProgressBar
                label={text({ sv: `Förloppet för ${namn}`, en: `Progress for ${namn}` })}
                isLabelHidden
                value={klara(senaste)}
                max={Math.max(senaste.counts.total, 1)}
                isIndeterminate={senaste.counts.total === 0 || avslutar(senaste)}
              />
            ) : null}
          </button>
        ) : (
          <p className="mt-auto rounded-[10px] bg-ink/[0.04] px-3 py-2.5 text-[0.8125rem] text-ink-muted">
            {text({ sv: "Ingen körning än. Källan startar den över API:t.", en: "No run yet. The source starts it over the API." })}
          </p>
        )}
      </article>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Körningens panel
// ---------------------------------------------------------------------------

/** Körningens utfall och de poster som inte kom in, med skälet per post. */
function Korningspanel({ korning, laddar, anslutning, stang }: Readonly<{ korning: Korning | null; laddar: boolean; anslutning: Anslutning | null; stang: () => void }>) {
  const { text, locale } = useLocale();
  const tal = (n: number) => n.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB");
  const k = korning;
  const namn = anslutning ? systemnamnFor(anslutning) : text({ sv: "Körning", en: "Run" });
  const ratta = k ? attRatta(k) : 0;
  const utanSkal = k ? Math.max(0, k.counts.skipped - k.errors.length) : 0;

  const talruta = (etikett: Localized, varde: number, framhavd = false) => (
    <div className="crm-talruta" style={framhavd ? { backgroundColor: "oklch(var(--ochre) / 0.16)" } : undefined}>
      <div className="text-[0.8125rem] text-ink-muted">{text(etikett)}</div>
      <div className="crm-tal text-[1.5rem] leading-tight text-ink">{tal(varde)}</div>
    </div>
  );

  return (
    <Drawer isOpen={k != null || laddar} onOpenChange={(o) => !o && stang()} label={text({ sv: `Körningen från ${namn}`, en: `The run from ${namn}` })} width={520} hasScrim={false}>
      <Layout
        header={
          <DrawerHeader
            hasDivider={false}
            startContent={anslutning ? <Systemplatta system={anslutning.system} storlek={48} /> : <Skeleton width={48} height={48} radius={3} />}
            title={k ? <span className="crm-postnamn">{namn}</span> : <Skeleton width={180} height={22} radius="rounded" />}
            subtitle={
              k ? (
                <span className="mt-1 inline-flex flex-wrap items-center gap-2">
                  <Statusetikett k={k} />
                  <span className="text-[0.8125rem] text-ink-muted">{k.mode === "full" ? text({ sv: "Full synk", en: "Full sync" }) : text({ sv: "Ändringar", en: "Changes" })}</span>
                  {k.created_at ? <Timestamp value={k.created_at} format="date_time" hasTooltip={false} size="sm" /> : null}
                </span>
              ) : undefined
            }
            onOpenChange={(o) => !o && stang()}
          />
        }
        content={
          <LayoutContent padding={0}>
            <div data-autofocus tabIndex={-1} className="crm-autofokus">
              {!k ? (
                <div className="flex flex-col gap-4 px-5 py-4" role="status" aria-busy="true" aria-label={text({ sv: "Hämtar körningen", en: "Loading the run" })}>
                  {Array.from({ length: 5 }, (_, i) => (
                    <Skeleton key={i} width={`${40 + ((i * 17) % 50)}%`} height={10} radius="rounded" index={i} />
                  ))}
                </div>
              ) : (
                <div className="flex flex-col gap-6 border-t border-ink/[0.08] px-5 pb-6 pt-5">
                  {k.status === "processing" || k.status === "queued" ? (
                    <div className="flex flex-col gap-2" role="status" aria-live="polite">
                      <div className="flex items-baseline justify-between gap-3">
                        <span className="text-[0.875rem] font-semibold text-ink">{text({ sv: "Förlopp", en: "Progress" })}</span>
                        <span className="text-[0.8125rem] tabular-nums text-ink-muted">{utfall(k, text, tal)}</span>
                      </div>
                      <ProgressBar
                        label={text({ sv: "Synkens förlopp", en: "Sync progress" })}
                        isLabelHidden
                        value={klara(k)}
                        max={Math.max(k.counts.total, 1)}
                        isIndeterminate={k.status === "queued" || k.counts.total === 0 || avslutar(k)}
                      />
                      <span className="text-[0.8125rem] text-ink-muted">{text({ sv: "Uppdateras var tredje sekund medan körningen pågår.", en: "Updated every three seconds while the run is in progress." })}</span>
                    </div>
                  ) : null}

                  {k.status === "failed" ? (
                    <Banner
                      status="error"
                      container="card"
                      title={text({ sv: "Körningen misslyckades", en: "The run failed" })}
                      description={text(k.error ? kodtext(KORNINGSFEL, k.error) : { sv: "Synken angav inget skäl.", en: "The sync gave no reason." })}
                    />
                  ) : null}

                  <section aria-label={text({ sv: "Utfallet i tal", en: "The outcome in numbers" })} className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {talruta({ sv: "Poster", en: "Records" }, k.counts.total)}
                    {talruta({ sv: "Nya", en: "New" }, k.counts.created)}
                    {talruta({ sv: "Ändrade", en: "Changed" }, k.counts.updated)}
                    {talruta({ sv: "Oförändrade", en: "Unchanged" }, k.counts.unchanged)}
                    {/* Hoppade poster räknas i Att rätta; två rutor med samma tal sade samma sak. */}
                    {talruta({ sv: "Konflikter", en: "Conflicts" }, k.counts.conflicts)}
                    {talruta({ sv: "Borttagna", en: "Removed" }, k.counts.removed)}
                    {talruta({ sv: "Att rätta", en: "To fix" }, ratta, ratta > 0)}
                  </section>

                  <section aria-labelledby="crm-att-ratta" className="flex flex-col gap-1">
                    <h3 id="crm-att-ratta" className="font-sans text-[0.8125rem] font-semibold tracking-normal text-ink-muted">
                      {text({ sv: "Poster att rätta i källan", en: "Records to fix in the source" })}
                    </h3>
                    {k.errors.length === 0 && utanSkal === 0 ? (
                      <p className="py-2 text-[0.875rem] text-ink2">
                        {pagar(k)
                          ? text({ sv: "Inget än. Poster som inte kommer in syns här medan körningen pågår.", en: "Nothing yet. Records that do not come in show here while the run is in progress." })
                          : text({ sv: "Alla poster kom in.", en: "Every record came in." })}
                      </p>
                    ) : (
                      <ul className="flex flex-col">
                        {k.errors.map((f, i) => {
                          const skal = [...(f.orsak ? [text(kodtext(ORSAKER, f.orsak))] : []), ...(f.faltfel ?? []).map((x) => text(kodtext(FALTKODER, x.kod)))];
                          const falt = (f.faltfel ?? []).map((x) => (x.varde ? `${x.falt} ${x.varde}` : x.falt)).join(", ");
                          // Synken sparar inte postens namn, och aldrig ett felaktigt
                          // organisationsnummer (det kan vara ett personnummer). Det som
                          // hittar posten i källan är dess id; därför står det först och går att kopiera.
                          const slag = f.objekt === "person" ? text({ sv: "Person", en: "Person" }) : text({ sv: "Bolag", en: "Company" });
                          const plats = text({ sv: `post ${f.index + 1} i satsen`, en: `record ${f.index + 1} in the batch` });
                          return (
                            <li key={`${f.objekt}:${f.index}:${i}`} className="crm-rattarad flex items-start gap-3 py-3">
                              <span aria-hidden className="crm-platta crm-ton-ockra mt-0.5 inline-flex size-7 shrink-0 items-center justify-center rounded-[8px]">
                                <Icon icon={AlertTriangle} size="sm" color="inherit" />
                              </span>
                              <span className="flex min-w-0 flex-1 flex-col gap-1">
                                <span className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-[0.875rem] text-ink">
                                  <span className="font-semibold">
                                    {f.externt_id ? text({ sv: `${slag} med id`, en: `${slag} with id` }) : text({ sv: `${slag} utan id i källan`, en: `${slag} without an id in the source` })}
                                  </span>
                                  {f.externt_id ? (
                                    <Kopierbar varde={f.externt_id} label={text({ sv: `Kopiera id ${f.externt_id}`, en: `Copy id ${f.externt_id}` })} />
                                  ) : null}
                                </span>
                                <span className="text-[0.875rem] text-ink2">{skal.join(" ") || text({ sv: "Posten kom inte in.", en: "The record did not come in." })}</span>
                                <span className="text-[0.8125rem] text-ink-muted">{(() => {
                                  const rad = [falt ? text({ sv: `Fält ${falt}`, en: `Field ${falt}` }) : null, plats].filter(Boolean).join(", ");
                                  return rad.charAt(0).toLocaleUpperCase() + rad.slice(1);
                                })()}</span>
                              </span>
                            </li>
                          );
                        })}
                        {utanSkal > 0 ? (
                          <li className="crm-rattarad py-3 text-[0.8125rem] text-ink-muted">
                            {text({
                              sv: `Ytterligare ${tal(utanSkal)} poster hoppades över utan att synken sparade ett skäl.`,
                              en: `Another ${tal(utanSkal)} records were skipped without the sync storing a reason.`
                            })}
                          </li>
                        ) : null}
                      </ul>
                    )}
                  </section>
                </div>
              )}
            </div>
          </LayoutContent>
        }
        footer={
          k ? (
            <LayoutFooter hasDivider>
              <HStack gap={2} vAlign="center" justify="between">
                <Text type="supporting" color="secondary" maxLines={1}>
                  {k.completed_at ? (
                    <>
                      {text({ sv: "Klar ", en: "Finished " })}
                      <Timestamp value={k.completed_at} format="relative" />
                    </>
                  ) : (
                    text({ sv: "Inte klar än", en: "Not finished yet" })
                  )}
                </Text>
                {k.started_by ? (
                  <Text type="supporting" color="secondary" maxLines={1}>
                    {text({ sv: `Startad av ${k.started_by === "api" ? "API:t" : k.started_by}`, en: `Started by ${k.started_by === "api" ? "the API" : k.started_by}` })}
                  </Text>
                ) : null}
              </HStack>
            </LayoutFooter>
          ) : undefined
        }
      />
    </Drawer>
  );
}

// ---------------------------------------------------------------------------
// Dialogen Ny anslutning
// ---------------------------------------------------------------------------

function NyAnslutning({ oppen, stang, skapad }: Readonly<{ oppen: boolean; stang: () => void; skapad: (a: Anslutning) => void }>) {
  const { text } = useLocale();
  const [namn, setNamn] = useState("");
  const [system, setSystem] = useState("generisk");
  const [konflikt, setKonflikt] = useState<Anslutning["conflict_rule"]>("source_wins");
  const [saknade, setSaknade] = useState<Anslutning["missing_records"]>("keep");
  const [relation, setRelation] = useState<Relation>("customer");
  const [sparar, setSparar] = useState(false);
  const [namnfel, setNamnfel] = useState<Localized | null>(null);
  const [allmant, setAllmant] = useState<Localized | null>(null);

  useEffect(() => {
    if (oppen) {
      setNamn("");
      setSystem("generisk");
      setKonflikt("source_wins");
      setSaknade("keep");
      setRelation("customer");
      setNamnfel(null);
      setAllmant(null);
    }
  }, [oppen]);

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    if (sparar) return;
    if (!namn.trim()) {
      setNamnfel({ sv: "Anslutningen behöver ett namn.", en: "The connection needs a name." });
      return;
    }
    setSparar(true);
    setNamnfel(null);
    setAllmant(null);
    try {
      const a = await crmAnrop<Anslutning>("/v1/connections", {
        method: "POST",
        body: JSON.stringify({ name: namn.trim(), system, conflict_rule: konflikt, missing_records: saknade, default_relation: relation })
      });
      skapad(a);
    } catch (orsak) {
      // Krocken och namnets längd gäller namnet; annat visas överst.
      if (orsak instanceof CrmFel && (orsak.status === 409 || orsak.kod === "invalid_fields")) setNamnfel(orsak.text);
      else setAllmant(orsak instanceof CrmFel ? orsak.text : { sv: "Det gick inte att spara. Försök igen.", en: "Could not save. Try again." });
    } finally {
      setSparar(false);
    }
  }

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && stang()} purpose="form" width={560}>
      <Layout
        header={<DialogHeader title={text({ sv: "Ny anslutning", en: "New connection" })} onOpenChange={(o) => !o && stang()} />}
        content={
          <LayoutContent>
            <form id="crm-ny-anslutning" onSubmit={spara} noValidate className="flex flex-col gap-6">
              {allmant ? <Banner status="error" container="card" title={text({ sv: "Det gick inte att spara", en: "Could not save" })} description={text(allmant)} /> : null}
              <fieldset className="crm-formgrupp">
                <legend className="mb-3 text-[0.8125rem] font-semibold text-ink-muted">{text({ sv: "Källan", en: "The source" })}</legend>
                {/* En kolumn: Namn har en tvåradig hjälptext, och två fält bredvid
                    varandra hamnade då på olika höjd. */}
                <div className="grid grid-cols-1 gap-4">
                  <TextInput
                    label={text({ sv: "Namn", en: "Name" })}
                    description={text({ sv: "Det namn källan anger när den synkar, till exempel hubspot.", en: "The name the source gives when it syncs, for example hubspot." })}
                    value={namn}
                    onChange={(v) => {
                      setNamn(v);
                      setNamnfel(null);
                    }}
                    isRequired
                    hasAutoFocus
                    autoCapitalize="none"
                    width="100%"
                    status={namnfel ? { type: "error", message: text(namnfel) } : undefined}
                  />
                  <Selector
                    label={text({ sv: "Källsystem", en: "Source system" })}
                    description={text({ sv: "Väljer fältmappningen ni utgår från.", en: "Selects the field mapping you start from." })}
                    value={system}
                    onChange={(v) => v && setSystem(v)}
                    options={Object.entries(SYSTEMNAMN).map(([value, label]) => ({ value, label }))}
                    hasSearch
                    searchPlaceholder={text({ sv: "Sök system", en: "Search systems" })}
                    width="100%"
                  />
                </div>
              </fieldset>
              <fieldset className="crm-formgrupp">
                <legend className="mb-3 text-[0.8125rem] font-semibold text-ink-muted">{text({ sv: "Regler", en: "Rules" })}</legend>
                <div className="grid grid-cols-1 gap-4">
                  <Selector
                    label={text({ sv: "När källan och Snajp säger olika", en: "When the source and Snajp disagree" })}
                    value={konflikt}
                    onChange={(v) => v && setKonflikt(v as Anslutning["conflict_rule"])}
                    options={(Object.keys(KONFLIKT) as Anslutning["conflict_rule"][]).map((r) => ({ value: r, label: text(KONFLIKT[r].namn), description: text(KONFLIKT[r].vad) }))}
                    width="100%"
                  />
                  <Selector
                    label={text({ sv: "Poster som försvunnit ur källan", en: "Records gone from the source" })}
                    description={text({ sv: "Gäller efter en full synk, när källan skickat allt den har.", en: "Applies after a full sync, when the source has sent everything it has." })}
                    value={saknade}
                    onChange={(v) => v && setSaknade(v as Anslutning["missing_records"])}
                    options={(Object.keys(SAKNADE) as Anslutning["missing_records"][]).map((r) => ({ value: r, label: text(SAKNADE[r].namn), description: text(SAKNADE[r].vad) }))}
                    width="100%"
                  />
                  <Selector
                    label={text({ sv: "Nya bolag från källan blir", en: "New companies from the source become" })}
                    value={relation}
                    onChange={(v) => v && setRelation(v as Relation)}
                    options={(Object.keys(RELATIONER) as Relation[]).map((r) => ({ value: r, label: text(RELATIONER[r]) }))}
                    width="100%"
                  />
                </div>
              </fieldset>
            </form>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Avbryt", en: "Cancel" })} variant="ghost" onClick={stang} />
              <Button type="submit" form="crm-ny-anslutning" variant="primary" label={text({ sv: "Skapa anslutningen", en: "Create connection" })} isLoading={sparar} />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
