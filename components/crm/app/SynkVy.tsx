"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { Drawer, DrawerHeader } from "@astryxdesign/core/Drawer";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { FormLayout } from "@astryxdesign/core/FormLayout";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { Link } from "@astryxdesign/core/Link";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { Selector } from "@astryxdesign/core/Selector";
import { HStack, VStack } from "@astryxdesign/core/Stack";
import { Table, pixel, proportional, type TableColumn } from "@astryxdesign/core/Table";
import { Text } from "@astryxdesign/core/Text";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { Felruta, Sida, Uppgift } from "@/components/crm/app/Sida";
import { CrmFel, SYSTEMNAMN, crmAnrop, type Anslutning, type Korning } from "@/lib/crm/api";
import { FALTKODER, KORNINGSFEL, ORSAKER, kodtext } from "@/lib/crm/felkoder";
import { useLocale, type Localized } from "@/lib/i18n";

const KONFLIKT: Record<Anslutning["conflict_rule"], Localized> = {
  source_wins: { sv: "Källan vinner", en: "Source wins" },
  snajp_wins: { sv: "Snajp vinner", en: "Snajp wins" },
  newest_wins: { sv: "Nyast vinner", en: "Newest wins" }
};
const SAKNADE: Record<Anslutning["missing_records"], Localized> = {
  keep: { sv: "Behålls", en: "Kept" },
  mark_former_customer: { sv: "Blir tidigare kund", en: "Become former customer" },
  delete: { sv: "Tas bort", en: "Deleted" }
};
const STATUS: Record<Korning["status"], { text: Localized; farg: "gray" | "yellow" | "green" | "red" }> = {
  queued: { text: { sv: "Köad", en: "Queued" }, farg: "gray" },
  processing: { text: { sv: "Pågår", en: "Running" }, farg: "yellow" },
  completed: { text: { sv: "Klar", en: "Completed" }, farg: "green" },
  failed: { text: { sv: "Misslyckades", en: "Failed" }, farg: "red" }
};
const klara = (k: Korning) => k.counts.created + k.counts.updated + k.counts.unchanged + k.counts.skipped + k.counts.conflicts;

export function SynkVy({ utvecklarvag = "/crm/utvecklare" }: Readonly<{ utvecklarvag?: string }>) {
  const { text } = useLocale();
  const [anslutningar, setAnslutningar] = useState<Anslutning[] | null>(null);
  const [korningar, setKorningar] = useState<Korning[] | null>(null);
  const [fel, setFel] = useState<unknown>(null);
  const [ny, setNy] = useState(false);
  const [oppen, setOppen] = useState<Korning | null>(null);

  const hamta = useCallback(async () => {
    try {
      const [a, k] = await Promise.all([
        crmAnrop<{ data: Anslutning[] }>("/v1/connections"),
        crmAnrop<{ data: Korning[] }>("/v1/sync/runs?limit=50")
      ]);
      setAnslutningar(a.data);
      setKorningar(k.data);
      setFel(null);
    } catch (e) {
      setFel(e);
    }
  }, []);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  // Förloppet följs här, där synken syns: så länge en körning pågår hämtas
  // listan om var tredje sekund. Utfallet ligger kvar i liggaren efter omladdning.
  const pagar = korningar?.some((k) => k.status === "processing" || k.status === "queued") ?? false;
  useEffect(() => {
    if (!pagar) return;
    const t = window.setInterval(() => void hamta(), 3000);
    return () => window.clearInterval(t);
  }, [pagar, hamta]);

  const namn = useMemo(() => Object.fromEntries((anslutningar ?? []).map((a) => [a.id, a.name])), [anslutningar]);

  const anslutningskolumner = useMemo<TableColumn<Anslutning>[]>(
    () => [
      { key: "name", header: text({ sv: "Anslutning", en: "Connection" }), width: proportional(2, { minWidth: 150 }), renderCell: (a) => <Text weight="medium">{a.name}</Text> },
      { key: "system", header: text({ sv: "System", en: "System" }), width: proportional(1.5, { minWidth: 120 }), renderCell: (a) => SYSTEMNAMN[a.system] ?? a.system },
      { key: "conflict_rule", header: text({ sv: "Vid konflikt", en: "On conflict" }), width: proportional(1.5, { minWidth: 130 }), renderCell: (a) => text(KONFLIKT[a.conflict_rule]) },
      { key: "missing_records", header: text({ sv: "Poster som försvunnit", en: "Missing records" }), width: proportional(1.5, { minWidth: 150 }), renderCell: (a) => text(SAKNADE[a.missing_records]) },
      {
        key: "last_sync_at",
        header: text({ sv: "Senaste synk", en: "Last sync" }),
        width: pixel(150),
        renderCell: (a) => (a.last_sync_at ? <Timestamp value={a.last_sync_at} format="auto" /> : <Text color="secondary">{text({ sv: "Aldrig", en: "Never" })}</Text>)
      },
      {
        key: "active",
        header: text({ sv: "Läge", en: "State" }),
        width: pixel(110),
        renderCell: (a) => <Badge variant={a.active ? "green" : "gray"} label={a.active ? text({ sv: "Aktiv", en: "Active" }) : text({ sv: "Pausad", en: "Paused" })} />
      }
    ],
    [text]
  );

  const korningskolumner = useMemo<TableColumn<Korning>[]>(
    () => [
      { key: "created_at", header: text({ sv: "Startad", en: "Started" }), width: pixel(150), renderCell: (k) => (k.created_at ? <Timestamp value={k.created_at} format="auto" isLive /> : null) },
      { key: "connection", header: text({ sv: "Anslutning", en: "Connection" }), width: proportional(1.2, { minWidth: 120 }), renderCell: (k) => (k.connection_id ? (namn[k.connection_id] ?? "") : "") },
      { key: "mode", header: text({ sv: "Omfång", en: "Scope" }), width: pixel(110), renderCell: (k) => (k.mode === "full" ? text({ sv: "Full", en: "Full" }) : text({ sv: "Ändringar", en: "Changes" })) },
      { key: "status", header: text({ sv: "Status", en: "Status" }), width: pixel(130), renderCell: (k) => <Badge variant={STATUS[k.status].farg} label={text(STATUS[k.status].text)} /> },
      {
        key: "counts",
        header: text({ sv: "Utfall", en: "Outcome" }),
        width: proportional(3, { minWidth: 260 }),
        renderCell: (k) =>
          k.status === "processing" || k.status === "queued" ? (
            <ProgressBar
              label={text({ sv: "Synkens förlopp", en: "Sync progress" })}
              isLabelHidden
              hasValueLabel
              value={klara(k)}
              max={Math.max(k.counts.total, 1)}
              isIndeterminate={k.counts.total === 0}
              formatValueLabel={(v, max) => text({ sv: `${v} av ${max} poster`, en: `${v} of ${max} records` })}
            />
          ) : k.status === "failed" ? (
            <Text color="secondary" maxLines={1}>
              {k.error ? text(kodtext(KORNINGSFEL, k.error)) : ""}
            </Text>
          ) : (
            <Text hasTabularNumbers maxLines={1}>
              {text({
                sv: `${k.counts.total} poster: ${k.counts.created} nya, ${k.counts.updated} ändrade, ${k.counts.unchanged} oförändrade`,
                en: `${k.counts.total} records: ${k.counts.created} new, ${k.counts.updated} changed, ${k.counts.unchanged} unchanged`
              })}
            </Text>
          )
      },
      {
        key: "errors",
        header: text({ sv: "Att rätta", en: "To fix" }),
        width: pixel(130),
        renderCell: (k) => {
          const antal = k.errors.length + (k.counts.skipped > k.errors.length ? k.counts.skipped - k.errors.length : 0);
          return antal > 0 || k.status === "failed" ? (
            <Link href="#" onClick={(e) => { e.preventDefault(); setOppen(k); }}>
              {antal > 0 ? text({ sv: `${antal} poster`, en: `${antal} records` }) : text({ sv: "Visa", en: "View" })}
            </Link>
          ) : (
            <Text color="secondary">{text({ sv: "Inget", en: "Nothing" })}</Text>
          );
        }
      }
    ],
    [text, namn]
  );

  if (fel && !anslutningar) {
    return (
      <Sida rubrik={text({ sv: "Synk", en: "Sync" })}>
        <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />} />
      </Sida>
    );
  }

  return (
    <Sida
      rubrik={text({ sv: "Synk", en: "Sync" })}
      antal={anslutningar ? text({ sv: `${anslutningar.length} anslutningar`, en: `${anslutningar.length} connections` }) : undefined}
      atgarder={<Button variant="primary" label={text({ sv: "Ny anslutning", en: "New connection" })} onClick={() => setNy(true)} />}
    >
      {anslutningar == null || korningar == null ? (
        <ProgressBar label={text({ sv: "Hämtar synken", en: "Loading sync" })} isLabelHidden isIndeterminate />
      ) : (
        <VStack gap={0}>
          <VStack gap={0}>
            <HStack paddingInline={2} paddingBlockStart={4} paddingBlockEnd={2}>
              <Text weight="semibold" as="h2">
                {text({ sv: "Anslutningar", en: "Connections" })}
              </Text>
            </HStack>
            <Table
              data={anslutningar}
              columns={anslutningskolumner}
              idKey="id"
              density="compact"
              textOverflow="truncate"
              emptyState={
                <EmptyState
                  title={text({ sv: "Ingen anslutning än", en: "No connection yet" })}
                  description={text({
                    sv: "En anslutning är en källa, till exempel ert CRM. Skapa den här, hämta en nyckel under Utvecklare och låt källan skicka sina bolag.",
                    en: "A connection is a source, for example your CRM. Create it here, get a key under Developers and let the source send its companies."
                  })}
                  actions={
                    <>
                      <Button variant="primary" label={text({ sv: "Ny anslutning", en: "New connection" })} onClick={() => setNy(true)} />
                      <Button label={text({ sv: "Till Utvecklare", en: "Go to Developers" })} href={utvecklarvag} />
                    </>
                  }
                />
              }
            />
          </VStack>
          <VStack gap={0}>
            <HStack paddingInline={2} paddingBlockStart={4} paddingBlockEnd={2}>
              <Text weight="semibold" as="h2">
                {text({ sv: "Körningar", en: "Runs" })}
              </Text>
            </HStack>
            <Table
              data={korningar}
              columns={korningskolumner}
              idKey="id"
              density="compact"
              textOverflow="truncate"
              emptyState={
                <EmptyState
                  isCompact
                  title={text({ sv: "Ingen synk har körts", en: "No sync has run" })}
                  description={text({ sv: "Varje synk från en källa syns här, med förlopp medan den pågår och utfall efteråt.", en: "Every sync from a source shows here, with progress while it runs and the outcome afterwards." })}
                />
              }
            />
          </VStack>
        </VStack>
      )}

      <Korningspanel korning={oppen} anslutning={oppen?.connection_id ? namn[oppen.connection_id] : undefined} stang={() => setOppen(null)} />
      <NyAnslutning
        oppen={ny}
        stang={() => setNy(false)}
        skapad={() => {
          setNy(false);
          void hamta();
        }}
      />
    </Sida>
  );
}

/** Körningens utfall och de poster som inte kom in, med skälet per post. */
function Korningspanel({ korning, anslutning, stang }: Readonly<{ korning: Korning | null; anslutning?: string; stang: () => void }>) {
  const { text } = useLocale();
  const k = korning;
  return (
    <Drawer isOpen={k != null} onOpenChange={(o) => !o && stang()} label={text({ sv: "Körningens utfall", en: "Run outcome" })} width={460}>
      {k ? (
        <Layout
          header={
            <DrawerHeader
              title={anslutning ?? text({ sv: "Körning", en: "Run" })}
              subtitle={k.created_at ? <Timestamp value={k.created_at} format="date_time" hasTooltip={false} /> : undefined}
              onOpenChange={(o) => !o && stang()}
              endContent={<Badge variant={STATUS[k.status].farg} label={text(STATUS[k.status].text)} />}
            />
          }
          content={
            <LayoutContent>
              <VStack gap={5}>
                {k.error ? <Text>{text(kodtext(KORNINGSFEL, k.error))}</Text> : null}
                <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
                  <Uppgift etikett={text({ sv: "Poster", en: "Records" })}>{String(k.counts.total)}</Uppgift>
                  <Uppgift etikett={text({ sv: "Nya", en: "New" })}>{String(k.counts.created)}</Uppgift>
                  <Uppgift etikett={text({ sv: "Ändrade", en: "Changed" })}>{String(k.counts.updated)}</Uppgift>
                  <Uppgift etikett={text({ sv: "Oförändrade", en: "Unchanged" })}>{String(k.counts.unchanged)}</Uppgift>
                  <Uppgift etikett={text({ sv: "Hoppade", en: "Skipped" })}>{String(k.counts.skipped)}</Uppgift>
                  <Uppgift etikett={text({ sv: "Borttagna", en: "Removed" })}>{String(k.counts.removed)}</Uppgift>
                </div>
                <VStack gap={3}>
                  <Text weight="semibold">{text({ sv: "Poster att rätta i källan", en: "Records to fix in the source" })}</Text>
                  {k.errors.length === 0 ? (
                    <Text color="secondary">{text({ sv: "Alla poster kom in.", en: "Every record came in." })}</Text>
                  ) : (
                    k.errors.map((f, i) => {
                      const skal = [
                        ...(f.orsak ? [text(kodtext(ORSAKER, f.orsak))] : []),
                        ...(f.faltfel ?? []).map((x) => text(kodtext(FALTKODER, x.kod)))
                      ];
                      const falt = (f.faltfel ?? []).map((x) => x.falt).join(", ");
                      return (
                        <VStack key={`${f.objekt}:${f.index}:${i}`} gap={0.5}>
                          <HStack justify="between" gap={3}>
                            <Text weight="medium">{skal.join(" ") || text({ sv: "Posten kom inte in.", en: "The record did not come in." })}</Text>
                            {f.externt_id ? (
                              <Text type="code" color="secondary">
                                {f.externt_id}
                              </Text>
                            ) : null}
                          </HStack>
                          <Text type="supporting" color="secondary">
                            {[
                              f.objekt === "person" ? text({ sv: `Person ${f.index + 1} i satsen`, en: `Person ${f.index + 1} in the batch` }) : text({ sv: `Bolag ${f.index + 1} i satsen`, en: `Company ${f.index + 1} in the batch` }),
                              falt ? text({ sv: `fält: ${falt}`, en: `field: ${falt}` }) : null
                            ]
                              .filter(Boolean)
                              .join(", ")}
                          </Text>
                        </VStack>
                      );
                    })
                  )}
                </VStack>
              </VStack>
            </LayoutContent>
          }
        />
      ) : null}
    </Drawer>
  );
}

function NyAnslutning({ oppen, stang, skapad }: Readonly<{ oppen: boolean; stang: () => void; skapad: () => void }>) {
  const { text } = useLocale();
  const [namn, setNamn] = useState("");
  const [system, setSystem] = useState("generisk");
  const [konflikt, setKonflikt] = useState<Anslutning["conflict_rule"]>("source_wins");
  const [sparar, setSparar] = useState(false);
  const [fel, setFel] = useState<CrmFel | null>(null);

  useEffect(() => {
    if (oppen) {
      setNamn("");
      setSystem("generisk");
      setKonflikt("source_wins");
      setFel(null);
    }
  }, [oppen]);

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    if (!namn.trim() || sparar) return;
    setSparar(true);
    setFel(null);
    try {
      await crmAnrop<Anslutning>("/v1/connections", { method: "POST", body: JSON.stringify({ name: namn.trim(), system, conflict_rule: konflikt }) });
      skapad();
    } catch (orsak) {
      setFel(orsak instanceof CrmFel ? orsak : new CrmFel({ sv: "Det gick inte att spara.", en: "Could not save." }, 0, null));
    } finally {
      setSparar(false);
    }
  }

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && stang()} purpose="form" width={460}>
      <Layout
        header={<DialogHeader title={text({ sv: "Ny anslutning", en: "New connection" })} onOpenChange={(o) => !o && stang()} />}
        content={
          <LayoutContent>
            <form id="crm-ny-anslutning" onSubmit={spara}>
              <FormLayout>
            <TextInput
              label={text({ sv: "Namn", en: "Name" })}
              description={text({ sv: "Det namn källan anger när den synkar, till exempel hubspot.", en: "The name the source gives when it syncs, for example hubspot." })}
              value={namn}
              onChange={setNamn}
              isRequired
              hasAutoFocus
              autoCapitalize="none"
              width="100%"
              status={fel ? { type: "error", message: text(fel.text) } : undefined}
            />
            <Selector
              label={text({ sv: "Källsystem", en: "Source system" })}
              description={text({ sv: "Väljer fältmappningen ni utgår från. Den går att ändra per fält över API:t.", en: "Selects the field mapping you start from. It can be changed per field over the API." })}
              value={system}
              onChange={(v) => v && setSystem(v)}
              options={Object.entries(SYSTEMNAMN).map(([value, label]) => ({ value, label }))}
              hasSearch
              searchPlaceholder={text({ sv: "Sök system", en: "Search systems" })}
              width="100%"
            />
            <Selector
              label={text({ sv: "När källan och Snajp säger olika", en: "When the source and Snajp disagree" })}
              value={konflikt}
              onChange={(v) => v && setKonflikt(v as Anslutning["conflict_rule"])}
              options={(Object.keys(KONFLIKT) as Anslutning["conflict_rule"][]).map((r) => ({ value: r, label: text(KONFLIKT[r]) }))}
              width="100%"
            />
              </FormLayout>
            </form>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Avbryt", en: "Cancel" })} onClick={stang} />
              <Button type="submit" form="crm-ny-anslutning" variant="primary" label={text({ sv: "Skapa anslutningen", en: "Create connection" })} isLoading={sparar} isDisabled={!namn.trim()} />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
