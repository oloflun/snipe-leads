"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertDialog } from "@astryxdesign/core/AlertDialog";
import { Badge } from "@astryxdesign/core/Badge";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { Link } from "@astryxdesign/core/Link";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { HStack, VStack } from "@astryxdesign/core/Stack";
import { Table, pixel, proportional, type TableColumn } from "@astryxdesign/core/Table";
import { Text } from "@astryxdesign/core/Text";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { Felruta, Sida, Uppgift } from "@/components/crm/app/Sida";
import { CrmFel, crmAnrop, type Nyckel } from "@/lib/crm/api";
import { useLocale, type Localized } from "@/lib/i18n";

const OMFANG: { id: string; namn: Localized; vad: Localized }[] = [
  { id: "crm:las", namn: { sv: "Läsa", en: "Read" }, vad: { sv: "Hämta bolag, personer och synkens utfall.", en: "Fetch companies, people and sync outcomes." } },
  { id: "crm:skriv", namn: { sv: "Skriva", en: "Write" }, vad: { sv: "Skapa, ändra och ta bort enskilda poster.", en: "Create, change and delete single records." } },
  { id: "crm:synk", namn: { sv: "Synka", en: "Sync" }, vad: { sv: "Skicka in hela register från ett källsystem.", en: "Send whole registers from a source system." } },
  { id: "crm:admin", namn: { sv: "Administrera", en: "Administer" }, vad: { sv: "Skapa och ändra anslutningar och fältmappning.", en: "Create and change connections and field mapping." } }
];
const OMFANGSNAMN = Object.fromEntries(OMFANG.map((o) => [o.id, o.namn]));

export function UtvecklareVy() {
  const { text } = useLocale();
  const [nycklar, setNycklar] = useState<Nyckel[] | null>(null);
  const [fel, setFel] = useState<unknown>(null);
  const [ny, setNy] = useState(false);
  const [skapad, setSkapad] = useState<Nyckel | null>(null);
  const [aterkalla, setAterkalla] = useState<Nyckel | null>(null);
  const [arbetar, setArbetar] = useState(false);

  const hamta = useCallback(async () => {
    try {
      setNycklar((await crmAnrop<{ nycklar: Nyckel[] }>("/nycklar")).nycklar);
      setFel(null);
    } catch (e) {
      setFel(e);
    }
  }, []);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  async function dra() {
    if (!aterkalla) return;
    setArbetar(true);
    try {
      await crmAnrop<null>(`/nycklar/${aterkalla.id}`, { method: "DELETE" });
      setAterkalla(null);
      await hamta();
    } catch (e) {
      setFel(e);
      setAterkalla(null);
    } finally {
      setArbetar(false);
    }
  }

  const kolumner = useMemo<TableColumn<Nyckel>[]>(
    () => [
      { key: "namn", header: text({ sv: "Namn", en: "Name" }), width: proportional(2, { minWidth: 150 }), renderCell: (n) => <Text weight="medium">{n.namn}</Text> },
      { key: "prefix", header: text({ sv: "Nyckel", en: "Key" }), width: pixel(190), renderCell: (n) => <Text type="code">{`${n.prefix}...`}</Text> },
      {
        key: "omfang",
        header: text({ sv: "Får", en: "May" }),
        width: proportional(2, { minWidth: 180 }),
        renderCell: (n) => (
          <HStack gap={1} wrap="wrap">
            {n.omfang.map((o) => (
              <Badge key={o} variant="gray" label={OMFANGSNAMN[o] ? text(OMFANGSNAMN[o]) : o} />
            ))}
          </HStack>
        )
      },
      { key: "created_at", header: text({ sv: "Skapad", en: "Created" }), width: pixel(130), renderCell: (n) => (n.created_at ? <Timestamp value={n.created_at} format="date" /> : null) },
      {
        key: "last_used_at",
        header: text({ sv: "Senast använd", en: "Last used" }),
        width: pixel(150),
        renderCell: (n) => (n.last_used_at ? <Timestamp value={n.last_used_at} format="auto" /> : <Text color="secondary">{text({ sv: "Aldrig", en: "Never" })}</Text>)
      },
      {
        key: "atgard",
        header: text({ sv: "Läge", en: "State" }),
        width: pixel(140),
        renderCell: (n) =>
          n.revoked_at ? (
            <Badge variant="red" label={text({ sv: "Återkallad", en: "Revoked" })} />
          ) : (
            <Button size="sm" variant="ghost" label={text({ sv: "Återkalla", en: "Revoke" })} onClick={() => setAterkalla(n)} />
          )
      }
    ],
    [text]
  );

  return (
    <Sida
      rubrik={text({ sv: "Utvecklare", en: "Developers" })}
      antal={nycklar ? text({ sv: `${nycklar.filter((n) => !n.revoked_at).length} aktiva nycklar`, en: `${nycklar.filter((n) => !n.revoked_at).length} active keys` }) : undefined}
      atgarder={<Button variant="primary" label={text({ sv: "Ny nyckel", en: "New key" })} onClick={() => setNy(true)} />}
    >
      {fel ? <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />} /> : null}
      {skapad?.api_key ? <NyckelnEnGang nyckel={skapad.api_key} namn={skapad.namn} stang={() => setSkapad(null)} /> : null}

      <VStack gap={0}>
        <HStack paddingInline={2} paddingBlockStart={4} paddingBlockEnd={2}>
          <Text weight="semibold" as="h2">
            {text({ sv: "API-nycklar", en: "API keys" })}
          </Text>
        </HStack>
        {nycklar == null && !fel ? (
          <ProgressBar label={text({ sv: "Hämtar nycklar", en: "Loading keys" })} isLabelHidden isIndeterminate />
        ) : (
          <Table
            data={nycklar ?? []}
            columns={kolumner}
            idKey="id"
            density="compact"
            textOverflow="truncate"
            emptyState={
              <EmptyState
                title={text({ sv: "Ingen nyckel än", en: "No key yet" })}
                description={text({
                  sv: "En nyckel låter ert CRM eller ett eget skript tala med Snajp CRM. Den når bara CRM-API:t, ingenting annat i Snajp.",
                  en: "A key lets your CRM or your own script talk to Snajp CRM. It reaches only the CRM API, nothing else in Snajp."
                })}
                actions={<Button variant="primary" label={text({ sv: "Ny nyckel", en: "New key" })} onClick={() => setNy(true)} />}
              />
            }
          />
        )}
      </VStack>

      <VStack gap={3} paddingInline={2} paddingBlock={5}>
        <Text weight="semibold" as="h2">
          {text({ sv: "API:t", en: "The API" })}
        </Text>
        <div className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
          <Uppgift etikett={text({ sv: "Adress", en: "Address" })}>
            <Text type="code">/api/crm/v1</Text>
          </Uppgift>
          <Uppgift etikett={text({ sv: "Nyckeln skickas i huvudet", en: "The key goes in the header" })}>
            <Text type="code">X-API-Key</Text>
          </Uppgift>
          <Uppgift etikett={text({ sv: "Specifikation", en: "Specification" })}>
            <Link href="/api/snajp-support/crm/v1/openapi.json" isExternalLink>
              {text({ sv: "OpenAPI som JSON", en: "OpenAPI as JSON" })}
            </Link>
          </Uppgift>
          <Uppgift etikett={text({ sv: "Tak", en: "Limit" })}>{text({ sv: "600 anrop per minut", en: "600 requests per minute" })}</Uppgift>
        </div>
      </VStack>

      <NyNyckel
        oppen={ny}
        stang={() => setNy(false)}
        klar={(n) => {
          setNy(false);
          setSkapad(n);
          void hamta();
        }}
      />
      <AlertDialog
        isOpen={aterkalla != null}
        onOpenChange={(o) => !o && setAterkalla(null)}
        title={text({ sv: "Återkalla nyckeln?", en: "Revoke the key?" })}
        description={text({
          sv: `Integrationen som använder ${aterkalla?.namn ?? ""} slutar fungera direkt. Det går inte att ångra.`,
          en: `The integration using ${aterkalla?.namn ?? ""} stops working at once. This cannot be undone.`
        })}
        actionLabel={text({ sv: "Återkalla", en: "Revoke" })}
        cancelLabel={text({ sv: "Avbryt", en: "Cancel" })}
        onAction={() => void dra()}
        isActionLoading={arbetar}
      />
    </Sida>
  );
}

/** Nyckeln i klartext, en enda gång. Servern sparar bara dess hash. */
function NyckelnEnGang({ nyckel, namn, stang }: Readonly<{ nyckel: string; namn: string; stang: () => void }>) {
  const { text } = useLocale();
  const [kopierad, setKopierad] = useState(false);
  async function kopiera() {
    try {
      await navigator.clipboard.writeText(nyckel);
      setKopierad(true);
    } catch {
      setKopierad(false);
    }
  }
  return (
    <Banner
      status="success"
      container="section"
      collapsible={false}
      title={text({ sv: `Nyckeln ${namn} är skapad`, en: `The key ${namn} is created` })}
      description={text({ sv: "Kopiera den nu. Den visas inte igen.", en: "Copy it now. It will not be shown again." })}
      isDismissable
      onDismiss={stang}
      dismissLabel={text({ sv: "Stäng", en: "Close" })}
    >
      <HStack gap={3} align="center" wrap="wrap">
        <Text type="code" wordBreak="break-all">
          {nyckel}
        </Text>
        <Button size="sm" label={kopierad ? text({ sv: "Kopierad", en: "Copied" }) : text({ sv: "Kopiera", en: "Copy" })} onClick={() => void kopiera()} />
      </HStack>
    </Banner>
  );
}

function NyNyckel({ oppen, stang, klar }: Readonly<{ oppen: boolean; stang: () => void; klar: (n: Nyckel) => void }>) {
  const { text } = useLocale();
  const [namn, setNamn] = useState("");
  const [valda, setValda] = useState<string[]>(["crm:las", "crm:synk"]);
  const [sparar, setSparar] = useState(false);
  const [fel, setFel] = useState<CrmFel | null>(null);

  useEffect(() => {
    if (oppen) {
      setNamn("");
      setValda(["crm:las", "crm:synk"]);
      setFel(null);
    }
  }, [oppen]);

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    if (!namn.trim() || valda.length === 0 || sparar) return;
    setSparar(true);
    setFel(null);
    try {
      klar(await crmAnrop<Nyckel>("/nycklar", { method: "POST", body: JSON.stringify({ namn: namn.trim(), omfang: valda }) }));
    } catch (orsak) {
      setFel(orsak instanceof CrmFel ? orsak : new CrmFel({ sv: "Det gick inte att skapa nyckeln.", en: "Could not create the key." }, 0, null));
    } finally {
      setSparar(false);
    }
  }

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && stang()} purpose="form" width={460}>
      <Layout
        header={<DialogHeader title={text({ sv: "Ny nyckel", en: "New key" })} onOpenChange={(o) => !o && stang()} />}
        content={
          <LayoutContent>
            <form id="crm-ny-nyckel" onSubmit={spara}>
              <VStack gap={4}>
          <TextInput
            label={text({ sv: "Namn", en: "Name" })}
            description={text({ sv: "Vad nyckeln används till, så att ni känner igen den i listan.", en: "What the key is for, so that you recognise it in the list." })}
            value={namn}
            onChange={setNamn}
            isRequired
            hasAutoFocus
            width="100%"
            status={fel ? { type: "error", message: text(fel.text) } : undefined}
          />
          <VStack gap={2}>
            <Text type="label">{text({ sv: "Vad nyckeln får göra", en: "What the key may do" })}</Text>
            {OMFANG.map((o) => (
              <CheckboxInput
                key={o.id}
                label={text(o.namn)}
                description={text(o.vad)}
                value={valda.includes(o.id)}
                onChange={(pa) => setValda((v) => (pa ? [...v, o.id] : v.filter((x) => x !== o.id)))}
              />
            ))}
          </VStack>
              </VStack>
            </form>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Avbryt", en: "Cancel" })} onClick={stang} />
              <Button type="submit" form="crm-ny-nyckel" variant="primary" label={text({ sv: "Skapa nyckeln", en: "Create key" })} isLoading={sparar} isDisabled={!namn.trim() || valda.length === 0} />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
