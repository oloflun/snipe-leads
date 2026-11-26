"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import NextLink from "next/link";
import { avslutar, klara, pagar, useAktuell, useSynklage } from "@/components/crm/app/synklage";
import { ArrowRight, Building2, Plus, RefreshCw } from "lucide-react";
import { Cell, Pie, PieChart, Tooltip as DiagramTips } from "recharts";
import { Button } from "@astryxdesign/core/Button";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Grid } from "@astryxdesign/core/Grid";
import { Icon } from "@astryxdesign/core/Icon";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { Text } from "@astryxdesign/core/Text";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { Tooltip } from "@astryxdesign/core/Tooltip";
import { Nyckeltalskort, Panelkort, Postchip, Prick, Relationsetikett, type Ton } from "@/components/crm/app/kit";
import { Felruta, Sida } from "@/components/crm/app/Sida";
import { SYSTEMNAMN, crmAnrop, type Anslutning, type Bolag, type Korning, type Oversikt, type Sida as Svarssida } from "@/lib/crm/api";
import { KORNINGSFEL, kodtext } from "@/lib/crm/felkoder";
import { useLocale, type Localized } from "@/lib/i18n";

/** Så många bolag räknas orterna ur. Är registret större står det i kortets fot. */
const ORTSURVAL = 500;

/**
 * Ringens sektorer: översiktens svenska nycklar, i kontraktets relationsfärger.
 * Partner och leverantör är båda blå i tabellen; i ringen ligger de bredvid
 * varandra och skiljs därför med två steg av samma blå.
 */
const RING: { nyckel: string; namn: Localized; farg: string; ton: Ton | null }[] = [
  { nyckel: "kund", namn: { sv: "Kund", en: "Customer" }, farg: "oklch(var(--moss))", ton: "mossa" },
  { nyckel: "prospekt", namn: { sv: "Prospekt", en: "Prospect" }, farg: "oklch(var(--ochre))", ton: "ockra" },
  { nyckel: "tidigare_kund", namn: { sv: "Tidigare kund", en: "Former customer" }, farg: "oklch(var(--mineral))", ton: "mineral" },
  { nyckel: "partner", namn: { sv: "Partner", en: "Partner" }, farg: "oklch(var(--chart-blue))", ton: "bla" },
  { nyckel: "leverantor", namn: { sv: "Leverantör", en: "Supplier" }, farg: "oklch(var(--chart-ramp-3))", ton: "bla" },
  { nyckel: "ovrigt", namn: { sv: "Övrigt", en: "Other" }, farg: "oklch(var(--ink) / 0.3)", ton: null }
];

/** Samma räkning som Synk-vyns kolumn Att rätta: felposterna, och hoppade poster utöver dem. */
const attRatta = (k: Korning) => k.errors.length + Math.max(0, k.counts.skipped - k.errors.length);

type Data = {
  oversikt: Oversikt;
  anslutningar: Record<string, Anslutning>;
  urval: Bolag[];
  urvalHelt: boolean;
  senast: Bolag[];
};

/**
 * Senast ändrade bolag. API:t listar ändringsordning äldst först, så de nyaste
 * ligger sist. Ryms hela registret i urvalet räcker det; annars hämtas bara det
 * som ändrats den senaste veckan (sedan månaden, sedan allt), sida för sida.
 */
async function senastAndrade(urval: Bolag[], helt: boolean): Promise<Bolag[]> {
  const nyast = (lista: Bolag[]) =>
    [...lista].sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? "")).slice(0, 5);
  if (helt) return nyast(urval);
  for (const dagar of [7, 31, null]) {
    const funna: Bolag[] = [];
    let markor: string | null = null;
    for (let sida = 0; sida < 6; sida++) {
      const q = new URLSearchParams({ limit: "500", sort: "updated" });
      if (dagar) q.set("updated_since", new Date(Date.now() - dagar * 864e5).toISOString());
      if (markor) q.set("cursor", markor);
      const svar: Svarssida<Bolag> = await crmAnrop<Svarssida<Bolag>>(`/v1/companies?${q}`);
      funna.push(...svar.data);
      markor = svar.next_cursor;
      if (!markor) break;
    }
    if (funna.length >= 5 || dagar == null) return nyast(funna);
  }
  return [];
}

export function OversiktVy({ bas = "/crm" }: Readonly<{ bas?: string }>) {
  const { text, locale } = useLocale();
  const [data, setData] = useState<Data | null>(null);
  const [fel, setFel] = useState<unknown>(null);
  const tal = useCallback((n: number) => n.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB"), [locale]);

  const hamta = useCallback(async () => {
    try {
      const [oversikt, anslutningar, urval] = await Promise.all([
        crmAnrop<Oversikt>("/oversikt"),
        crmAnrop<{ data: Anslutning[] }>("/v1/connections"),
        crmAnrop<Svarssida<Bolag>>(`/v1/companies?limit=${ORTSURVAL}&sort=name`)
      ]);
      const senast = await senastAndrade(urval.data, urval.next_cursor == null);
      setData({
        oversikt,
        anslutningar: Object.fromEntries(anslutningar.data.map((a) => [a.id, a])),
        urval: urval.data,
        urvalHelt: urval.next_cursor == null,
        senast
      });
      setFel(null);
    } catch (e) {
      setFel(e);
    }
  }, []);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  // Körningarna kommer ur det delade synkläget (synklage.tsx): ramen följer en
  // pågående synk var tredje sekund, och samma tal står i navigeringens kort.
  const { publicera } = useSynklage();
  useEffect(() => {
    if (data) publicera(data.oversikt.korningar);
  }, [data, publicera]);
  const korningar = useAktuell(data?.oversikt.korningar ?? null);

  const o = data?.oversikt;
  const alla = o?.bolag.alla ?? 0;
  const kunder = o?.bolag.kund ?? 0;

  // Att rätta: poster som inte kom in i den senaste avslutade körningen per anslutning.
  // Kortet länkar till den senaste av dem som har något att rätta, så att panelen öppnas direkt.
  const { rattas, rattaKorning } = useMemo(() => {
    if (!korningar) return { rattas: null, rattaKorning: null };
    const sedda = new Set<string>();
    let summa = 0;
    let forsta: Korning | null = null;
    for (const k of korningar) {
      if (k.status !== "completed") continue;
      const nyckel = k.connection_id ?? "";
      if (sedda.has(nyckel)) continue;
      sedda.add(nyckel);
      summa += attRatta(k);
      if (!forsta && attRatta(k) > 0) forsta = k;
    }
    return { rattas: summa, rattaKorning: forsta };
  }, [korningar]);

  const anslutningsnamn = useCallback(
    (k: Korning) => {
      const a = k.connection_id ? data?.anslutningar[k.connection_id] : undefined;
      return a ? (SYSTEMNAMN[a.system] ?? a.name) : text({ sv: "Okänd anslutning", en: "Unknown connection" });
    },
    [data, text]
  );

  if (fel && !data) {
    return (
      <Sida objekt="oversikt" rubrik={text({ sv: "Översikt", en: "Overview" })} utfyllnad="sida">
        <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />} />
      </Sida>
    );
  }

  return (
    <Sida
      objekt="oversikt"
      rubrik={text({ sv: "Översikt", en: "Overview" })}
      atgarder={
        <Button
          variant="primary"
          label={text({ sv: "Nytt bolag", en: "New company" })}
          icon={<Icon icon={Plus} size="sm" />}
          href={`${bas}/bolag?ny=1`}
        />
      }
      utfyllnad="sida"
    >
      <div className="flex flex-col gap-4 pt-2">
        {/* Fyra nyckeltal: 4 i bredd, 2 + 2 på mellanbredd, 1 på mobil, aldrig 3 + 1. */}
        <Grid columns={{ minWidth: 420, max: 2, repeat: "fit" }} gap={4}>
          <Grid columns={{ minWidth: 150, max: 2, repeat: "fit" }} gap={4}>
            <Nyckeltalskort
              etikett={text({ sv: "Bolag", en: "Companies" })}
              varde={o ? alla : null}
              rad={text({ sv: "i registret", en: "in the register" })}
              href={`${bas}/bolag`}
              label={text({ sv: `Bolag: ${alla}. Öppna Bolag.`, en: `Companies: ${alla}. Open Companies.` })}
            />
            <Nyckeltalskort
              etikett={text({ sv: "Kunder", en: "Customers" })}
              varde={o ? kunder : null}
              rad={
                alla > 0
                  ? text({ sv: `${Math.round((kunder / alla) * 100)} % av bolagen`, en: `${Math.round((kunder / alla) * 100)}% of the companies` })
                  : text({ sv: "inga bolag än", en: "no companies yet" })
              }
              href={`${bas}/bolag`}
              label={text({ sv: `Kunder: ${kunder}. Öppna Bolag.`, en: `Customers: ${kunder}. Open Companies.` })}
            />
          </Grid>
          <Grid columns={{ minWidth: 150, max: 2, repeat: "fit" }} gap={4}>
            <Nyckeltalskort
              etikett={text({ sv: "Personer", en: "People" })}
              varde={o ? o.personer : null}
              rad={text({ sv: "kontaktpersoner hos bolagen", en: "contacts at the companies" })}
              href={`${bas}/personer`}
              label={text({ sv: `Personer: ${o?.personer ?? 0}. Öppna Personer.`, en: `People: ${o?.personer ?? 0}. Open People.` })}
            />
            {/* Sidans enda framhävda ruta: ockratonad och länk till Synk. */}
            <Nyckeltalskort
              framhavd
              etikett={text({ sv: "Att rätta", en: "To fix" })}
              varde={rattas}
              rad={
                rattas === 0
                  ? text({ sv: "allt kom in i senaste synken", en: "everything came in on the last sync" })
                  : text({ sv: "poster som inte kom in i synken", en: "records the sync could not import" })
              }
              href={rattaKorning ? `${bas}/synk?korning=${encodeURIComponent(rattaKorning.id)}` : `${bas}/synk`}
              label={
                rattaKorning
                  ? text({ sv: `Att rätta: ${rattas ?? 0}. Öppna körningen.`, en: `To fix: ${rattas ?? 0}. Open the run.` })
                  : text({ sv: `Att rätta: ${rattas ?? 0}. Öppna Synk.`, en: `To fix: ${rattas ?? 0}. Open Sync.` })
              }
            />
          </Grid>
        </Grid>

        <Grid columns={{ minWidth: 360, max: 2, repeat: "fit" }} gap={4}>
          <Panelkort id="crm-ring" titel={text({ sv: "Bolag per relation", en: "Companies by relation" })}>
            {o ? <Ring antal={o.bolag} totalt={alla} /> : <Skeleton width="100%" height={260} radius={3} />}
          </Panelkort>

          <Panelkort
            id="crm-synkar"
            titel={text({ sv: "Senaste synkarna", en: "Latest syncs" })}
            hoger={
              <Button
                variant="ghost"
                size="sm"
                label={text({ sv: "Öppna Synk", en: "Open Sync" })}
                endContent={<Icon icon={ArrowRight} size="sm" />}
                href={`${bas}/synk`}
              />
            }
          >
            {!o || !korningar ? (
              <Radskelett />
            ) : korningar.length === 0 ? (
              <EmptyState
                isCompact
                icon={<Icon icon={RefreshCw} size="lg" color="secondary" />}
                title={text({ sv: "Ingen synk har körts än", en: "No sync has run yet" })}
                description={text({ sv: "Koppla ert CRM eller ekonomisystem så kommer kundstocken in här.", en: "Connect your CRM or accounting system and the customer base comes in here." })}
                actions={<Button label={text({ sv: "Ny anslutning", en: "New connection" })} href={`${bas}/synk?ny=1`} />}
              />
            ) : (
              <ul className="-mx-2 flex flex-col">
                {korningar.slice(0, 5).map((k) => (
                  <Synkrad key={k.id} k={k} namn={anslutningsnamn(k)} href={`${bas}/synk?korning=${encodeURIComponent(k.id)}`} />
                ))}
              </ul>
            )}
          </Panelkort>
        </Grid>

        <Grid columns={{ minWidth: 360, max: 2, repeat: "fit" }} gap={4}>
          <Panelkort
            id="crm-orter"
            titel={text({ sv: "Största orterna", en: "Largest cities" })}
            fot={
              data && !data.urvalHelt
                ? text({
                    sv: `Räknat på de första ${tal(data.urval.length)} bolagen i bokstavsordning av ${tal(alla)}.`,
                    en: `Counted from the first ${tal(data.urval.length)} companies alphabetically, of ${tal(alla)}.`
                  })
                : undefined
            }
          >
            {data ? <Orter bolag={data.urval} /> : <Radskelett />}
          </Panelkort>

          <Panelkort
            id="crm-senast"
            titel={text({ sv: "Senast ändrade", en: "Recently changed" })}
            hoger={
              <Button
                variant="ghost"
                size="sm"
                label={text({ sv: "Alla bolag", en: "All companies" })}
                endContent={<Icon icon={ArrowRight} size="sm" />}
                href={`${bas}/bolag`}
              />
            }
          >
            {!data ? (
              <Radskelett />
            ) : data.senast.length === 0 ? (
              <EmptyState
                isCompact
                icon={<Icon icon={Building2} size="lg" color="secondary" />}
                title={text({ sv: "Inga bolag än", en: "No companies yet" })}
                description={text({ sv: "Lägg till ett bolag eller koppla en synk.", en: "Add a company or connect a sync." })}
              />
            ) : (
              <ul className="-mx-2 flex flex-col">
                {data.senast.map((b) => (
                  <li key={b.id} className="flex h-11 items-center gap-3 rounded-[10px] px-2">
                    <span className="min-w-0 flex-1">
                      <Postchip
                        namn={b.name ?? text({ sv: "Namnlöst bolag", en: "Unnamed company" })}
                        href={`${bas}/bolag?bolag=${encodeURIComponent(b.id)}`}
                      />
                    </span>
                    <span className="hidden sm:inline-flex">
                      <Relationsetikett relation={b.relation} />
                    </span>
                    {b.updated_at ? (
                      <span className="shrink-0 whitespace-nowrap text-right sm:w-[9.5rem]">
                        <Timestamp value={b.updated_at} format="relative" />
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </Panelkort>
        </Grid>
      </div>
    </Sida>
  );
}

/** Rader i listans form medan korten hämtar. */
function Radskelett() {
  return (
    <div className="flex flex-col gap-4 py-1" aria-hidden>
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton width={20} height={20} radius={1} index={i} />
          <Skeleton width={`${40 + ((i * 13) % 30)}%`} height={10} radius="rounded" index={i} />
          <span className="ml-auto">
            <Skeleton width={56} height={10} radius="rounded" index={i} />
          </span>
        </div>
      ))}
    </div>
  );
}

/** En körning: statusprick, anslutning, utfall i klartext, relativ tid. Pågående har förloppsstapel. */
function Synkrad({ k, namn, href }: Readonly<{ k: Korning; namn: string; href: string }>) {
  const { text } = useLocale();
  const tal = (n: number) => n.toLocaleString("sv-SE");
  const ratta = attRatta(k);
  const utfall =
    k.status === "failed"
      ? text(k.error ? kodtext(KORNINGSFEL, k.error) : { sv: "Körningen misslyckades.", en: "The run failed." })
      : k.status === "queued"
        ? text({ sv: "Väntar på att starta", en: "Waiting to start" })
        : avslutar(k)
          ? text({ sv: `Avslutar, ${tal(k.counts.total)} poster behandlade`, en: `Finishing, ${tal(k.counts.total)} records processed` })
          : k.status === "processing"
          ? text({ sv: `${tal(klara(k))} av ${tal(k.counts.total)} poster`, en: `${tal(klara(k))} of ${tal(k.counts.total)} records` })
          : ratta > 0
            ? text({
                sv: `${k.counts.created} nya, ${k.counts.updated} ändrade, ${ratta} att rätta`,
                en: `${k.counts.created} new, ${k.counts.updated} changed, ${ratta} to fix`
              })
            : text({
                sv: `${k.counts.created} nya, ${k.counts.updated} ändrade, inget att rätta`,
                en: `${k.counts.created} new, ${k.counts.updated} changed, nothing to fix`
              });
  const ton = k.status === "failed" ? ("fara" as const) : pagar(k) || ratta > 0 ? ("ockra" as const) : ("mossa" as const);
  const status =
    k.status === "failed"
      ? text({ sv: "Misslyckades", en: "Failed" })
      : pagar(k)
        ? text({ sv: "Pågår", en: "Running" })
        : text({ sv: "Klar", en: "Completed" });
  const tid = k.completed_at ?? k.created_at;
  return (
    <li>
      <NextLink href={href} className="crm-synkrad flex min-h-11 flex-col justify-center gap-1.5 rounded-[10px] px-2 py-2 no-underline">
      {/* På mobil står utfallet på en egen rad under namnet och tiden. Utfallet
          bryter i stället för att kapas: ett felmeddelande ska gå att läsa färdigt. */}
      <span className="grid grid-cols-[0.5rem_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-0.5 sm:grid-cols-[0.5rem_6rem_minmax(0,1fr)_auto]">
        <Prick ton={ton} pulserar={pagar(k)} />
        <span className="truncate text-[0.875rem] font-semibold text-ink">{namn}</span>
        <span
          className="col-span-2 col-start-2 row-start-2 line-clamp-2 text-[0.875rem] text-ink-muted sm:col-span-1 sm:col-start-auto sm:row-start-auto"
          title={utfall}
        >
          <span className="sr-only">{`${status}. `}</span>
          {utfall}
        </span>
        {tid ? (
          <span className="col-start-3 row-start-1 whitespace-nowrap text-right sm:col-start-auto sm:row-start-auto">
            <Timestamp value={tid} format="relative" isLive={pagar(k)} />
          </span>
        ) : null}
      </span>
      {k.status === "processing" ? (
        <span className="pl-5">
          <ProgressBar
            label={text({ sv: `Förloppet för ${namn}`, en: `Progress for ${namn}` })}
            isLabelHidden
            value={klara(k)}
            max={Math.max(k.counts.total, 1)}
            isIndeterminate={k.counts.total === 0 || avslutar(k)}
          />
        </span>
      ) : null}
      </NextLink>
    </li>
  );
}

/**
 * Ringen: bolag per relation, totalen i mitten, förklaringen under. Färgen
 * följer relationen, aldrig storleksordningen, och varje post står också i
 * förklaringen med sitt tal, så att färgen aldrig bär betydelsen ensam.
 */
function Ring({ antal, totalt }: Readonly<{ antal: Oversikt["bolag"]; totalt: number }>) {
  const { text, locale } = useLocale();
  const tal = (n: number) => n.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB");
  const delar = RING.map((r) => ({ ...r, antal: antal[r.nyckel] ?? 0 })).filter((r) => r.antal > 0);

  if (totalt === 0 || delar.length === 0) {
    return (
      <EmptyState
        isCompact
        icon={<Icon icon={Building2} size="lg" color="secondary" />}
        title={text({ sv: "Inga bolag än", en: "No companies yet" })}
        description={text({ sv: "Ringen fylls när det första bolaget finns.", en: "The ring fills in once the first company exists." })}
      />
    );
  }

  const beskrivning = delar.map((d) => `${text(d.namn)} ${d.antal}`).join(", ");
  return (
    <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-center sm:gap-8">
      <figure
        className="relative size-[200px] shrink-0"
        role="img"
        aria-label={text({ sv: `${totalt} bolag: ${beskrivning}`, en: `${totalt} companies: ${beskrivning}` })}
      >
        <PieChart width={200} height={200}>
          <Pie
            data={delar}
            dataKey="antal"
            nameKey="nyckel"
            cx="50%"
            cy="50%"
            innerRadius={68}
            outerRadius={100}
            paddingAngle={2}
            cornerRadius={6}
            startAngle={90}
            endAngle={-270}
            stroke="none"
            isAnimationActive={false}
          >
            {delar.map((d) => (
              <Cell key={d.nyckel} style={{ fill: d.farg, outline: "none" }} />
            ))}
          </Pie>
          <DiagramTips
            cursor={false}
            content={({ active, payload }) => {
              const rad = active ? (payload?.[0]?.payload as (typeof delar)[number] | undefined) : undefined;
              if (!rad) return null;
              return (
                <div className="rounded-[10px] bg-paper px-3 py-2 text-[0.8125rem] text-ink shadow-[0_0_0_1px_oklch(var(--ink)/0.1),0_8px_24px_oklch(var(--seal)/0.1)]">
                  <span className="flex items-center gap-2">
                    <Prick ton={rad.ton} />
                    <span className="font-semibold">{text(rad.namn)}</span>
                  </span>
                  <span className="mt-0.5 block tabular-nums text-ink-muted">
                    {text({
                      sv: `${tal(rad.antal)} bolag, ${Math.round((rad.antal / totalt) * 100)} %`,
                      en: `${tal(rad.antal)} companies, ${Math.round((rad.antal / totalt) * 100)}%`
                    })}
                  </span>
                </div>
              );
            }}
          />
        </PieChart>
        <figcaption className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center" aria-hidden>
          <span className="crm-tal text-[2rem] leading-none text-ink">{tal(totalt)}</span>
          <span className="mt-1 text-[0.8125rem] text-ink-muted">{text({ sv: "bolag", en: "companies" })}</span>
        </figcaption>
      </figure>
      <ul className="grid w-full grid-cols-[auto_1fr_auto_auto] items-center gap-x-3 gap-y-2.5 text-[0.875rem] sm:w-auto sm:min-w-[14rem]">
        {delar.map((d) => (
          <li key={d.nyckel} className="contents">
            <span aria-hidden className="size-2.5 rounded-full" style={{ backgroundColor: d.farg }} />
            <span className="text-ink2">{text(d.namn)}</span>
            <span className="text-right font-semibold tabular-nums text-ink">{tal(d.antal)}</span>
            <span className="w-10 text-right tabular-nums text-ink-muted">{text({ sv: `${Math.round((d.antal / totalt) * 100)} %`, en: `${Math.round((d.antal / totalt) * 100)}%` })}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** De sex vanligaste orterna som liggande, helt rundade staplar i Bolags blå. */
function Orter({ bolag }: Readonly<{ bolag: Bolag[] }>) {
  const { text, locale } = useLocale();
  const tal = (n: number) => n.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB");
  const orter = useMemo(() => {
    const rakning = new Map<string, number>();
    for (const b of bolag) {
      const ort = b.address.city?.trim();
      if (ort) rakning.set(ort, (rakning.get(ort) ?? 0) + 1);
    }
    return [...rakning.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "sv")).slice(0, 6);
  }, [bolag]);

  if (orter.length === 0) {
    return (
      <Text color="secondary">
        {text({ sv: "Inget bolag har en ort ifylld än.", en: "No company has a city filled in yet." })}
      </Text>
    );
  }
  const storst = orter[0][1];
  const medOrt = bolag.filter((b) => b.address.city?.trim()).length;
  return (
    <ul className="flex flex-col gap-3.5">
      {orter.map(([ort, antal]) => (
        <li key={ort}>
          <Tooltip
            content={text({
              sv: `${ort}: ${tal(antal)} bolag, ${Math.round((antal / medOrt) * 100)} % av dem med ort`,
              en: `${ort}: ${tal(antal)} companies, ${Math.round((antal / medOrt) * 100)}% of those with a city`
            })}
            hasHoverIndication={false}
          >
            <span
              className="grid grid-cols-[6.5rem_1fr_2.5rem] items-center gap-3 rounded-[6px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--focus-outline-color)]"
              tabIndex={0}
            >
              <span className="truncate text-[0.875rem] text-ink2">{ort}</span>
              <span className="h-3 overflow-hidden rounded-full bg-ink/[0.06]">
                <span
                  className="block h-full rounded-full"
                  style={{ width: `${Math.max(4, (antal / storst) * 100)}%`, backgroundColor: "oklch(var(--chart-blue))" }}
                />
              </span>
              <span className="text-right text-[0.875rem] font-semibold tabular-nums text-ink">{tal(antal)}</span>
            </span>
          </Tooltip>
        </li>
      ))}
    </ul>
  );
}
