"use client";

import "@/components/crm/app/crm-vyer.css";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Ban, CalendarPlus, Check, CircleDot, Clock, Copy, FileJson, Gauge, Hash, KeyRound, Link2, Plus, ShieldCheck, X } from "lucide-react";
import { AlertDialog } from "@astryxdesign/core/AlertDialog";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { Card } from "@astryxdesign/core/Card";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Grid } from "@astryxdesign/core/Grid";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { Link } from "@astryxdesign/core/Link";
import { List, ListItem } from "@astryxdesign/core/List";
import { MetadataList, MetadataListItem } from "@astryxdesign/core/MetadataList";
import { MoreMenu } from "@astryxdesign/core/MoreMenu";
import { Selector } from "@astryxdesign/core/Selector";
import { HStack } from "@astryxdesign/core/Stack";
import { Table, pixel, proportional, type TableColumn } from "@astryxdesign/core/Table";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { useToast } from "@astryxdesign/core/Toast";
import { Kolumnrubrik, Kopierbar, Objektikon, Panelkort, Prick, Tabellskelett, useBestallning, useSmal, Vyval } from "@/components/crm/app/kit";
import { Felruta, Sida } from "@/components/crm/app/Sida";
import { Webhooks } from "@/components/crm/app/Webhooks";
import { CrmFel, crmAnrop, type Nyckel } from "@/lib/crm/api";
import { useLocale, type Localized } from "@/lib/i18n";

const OMFANG: { id: string; namn: Localized; vad: Localized }[] = [
  { id: "crm:las", namn: { sv: "Läsa", en: "Read" }, vad: { sv: "Hämta bolag, personer och synkens utfall.", en: "Fetch companies, people and sync outcomes." } },
  { id: "crm:skriv", namn: { sv: "Skriva", en: "Write" }, vad: { sv: "Skapa, ändra och ta bort enskilda poster.", en: "Create, change and delete single records." } },
  { id: "crm:synk", namn: { sv: "Synka", en: "Sync" }, vad: { sv: "Skicka in hela register från ett källsystem.", en: "Send whole registers from a source system." } },
  { id: "crm:admin", namn: { sv: "Administrera", en: "Administer" }, vad: { sv: "Skapa och ändra anslutningar och fältmappning.", en: "Create and change connections and field mapping." } }
];
const OMFANGSNAMN: Record<string, Localized> = Object.fromEntries(OMFANG.map((o) => [o.id, o.namn]));

type Filter = "aktiva" | "aterkallade" | "alla";

/**
 * Utvecklare: API-nycklarna i tabellens anatomi (som Bolag), den nya nyckeln som
 * visas en gång med kopieringsknapp, och API:ts uppgifter som kort. Nycklarna
 * kommer ur `/nycklar`; Återkalla frågar först och går inte att ångra.
 * `?ny=1` öppnar dialogen Ny nyckel.
 */
export function UtvecklareVy() {
  const { text, locale } = useLocale();
  const visa = useToast();
  const smal = useSmal();
  const tal = useCallback((n: number) => n.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB"), [locale]);
  const [nycklar, setNycklar] = useState<Nyckel[] | null>(null);
  const [fel, setFel] = useState<unknown>(null);
  const [ny, setNy] = useState(false);
  const [skapad, setSkapad] = useState<Nyckel | null>(null);
  const [aterkalla, setAterkalla] = useState<Nyckel | null>(null);
  const [arbetar, setArbetar] = useState(false);
  const [filter, setFilter] = useState<Filter>("aktiva");

  useBestallning("ny", () => setNy(true));

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
    const n = aterkalla;
    setArbetar(true);
    try {
      await crmAnrop<null>(`/nycklar/${encodeURIComponent(n.id)}`, { method: "DELETE" });
      visa({ body: text({ sv: `Nyckeln ${n.namn} är återkallad.`, en: `The key ${n.namn} is revoked.` }), uniqueID: "crm-nyckel-aterkallad" });
      if (skapad?.id === n.id) setSkapad(null);
      await hamta();
    } catch (e) {
      visa({ type: "error", body: text(e instanceof CrmFel ? e.text : { sv: "Det gick inte att återkalla nyckeln.", en: "Could not revoke the key." }), uniqueID: "crm-nyckel-aterkallad" });
    } finally {
      setArbetar(false);
      setAterkalla(null);
    }
  }

  const aktiva = (nycklar ?? []).filter((n) => !n.revoked_at);
  const raknat: Record<Filter, number> = { aktiva: aktiva.length, aterkallade: (nycklar ?? []).length - aktiva.length, alla: (nycklar ?? []).length };
  const visade = filter === "aktiva" ? aktiva : filter === "aterkallade" ? (nycklar ?? []).filter((n) => n.revoked_at) : (nycklar ?? []);
  const vyer: { v: Filter; namn: Localized }[] = [
    { v: "aktiva", namn: { sv: "Aktiva", en: "Active" } },
    { v: "aterkallade", namn: { sv: "Återkallade", en: "Revoked" } },
    { v: "alla", namn: { sv: "Alla", en: "All" } }
  ];

  const omfangsetiketter = (n: Nyckel) => (
    <span className="flex flex-wrap gap-1">
      {n.omfang.map((o) => (
        <Badge key={o} variant="neutral" label={OMFANGSNAMN[o] ? text(OMFANGSNAMN[o]) : o} />
      ))}
    </span>
  );
  const lage = (n: Nyckel) =>
    n.revoked_at ? (
      <Badge variant="error" label={text({ sv: "Återkallad", en: "Revoked" })} icon={<Prick ton="fara" />} />
    ) : (
      <Badge variant="green" label={text({ sv: "Aktiv", en: "Active" })} icon={<Prick ton="mossa" />} />
    );

  const kolumner = useMemo<TableColumn<Nyckel>[]>(
    () => [
      {
        key: "namn",
        header: <Kolumnrubrik ikon={KeyRound}>{text({ sv: "Nyckel", en: "Key" })}</Kolumnrubrik>,
        width: proportional(1, { minWidth: 190 }),
        renderCell: (n) => (
          <span className="inline-flex min-w-0 items-center gap-2">
            <Objektikon ikon={KeyRound} ton={n.revoked_at ? "mineral" : "sigill"} storlek={24} />
            <span className={n.revoked_at ? "truncate text-[0.875rem] text-ink-muted line-through decoration-ink/30" : "truncate text-[0.875rem] font-semibold text-ink"}>{n.namn}</span>
          </span>
        )
      },
      {
        key: "prefix",
        header: <Kolumnrubrik ikon={Hash}>{text({ sv: "Början", en: "Prefix" })}</Kolumnrubrik>,
        width: pixel(176),
        renderCell: (n) => <code className="crm-kod">{`${n.prefix}…`}</code>
      },
      {
        key: "omfang",
        header: <Kolumnrubrik ikon={ShieldCheck}>{text({ sv: "Får", en: "May" })}</Kolumnrubrik>,
        width: pixel(220),
        renderCell: omfangsetiketter
      },
      {
        key: "lage",
        header: <Kolumnrubrik ikon={CircleDot}>{text({ sv: "Läge", en: "State" })}</Kolumnrubrik>,
        width: pixel(132),
        renderCell: lage
      },
      {
        key: "created_at",
        header: <Kolumnrubrik ikon={CalendarPlus}>{text({ sv: "Skapad", en: "Created" })}</Kolumnrubrik>,
        width: pixel(124),
        renderCell: (n) => (n.created_at ? <Timestamp value={n.created_at} format="date" /> : null)
      },
      {
        key: "last_used_at",
        header: <Kolumnrubrik ikon={Clock}>{text({ sv: "Senast använd", en: "Last used" })}</Kolumnrubrik>,
        width: pixel(156),
        renderCell: (n) =>
          n.revoked_at ? (
            <span className="text-ink-muted">{text({ sv: "Återkallad ", en: "Revoked " })}<Timestamp value={n.revoked_at} format="date" /></span>
          ) : n.last_used_at ? (
            <Timestamp value={n.last_used_at} format="relative" />
          ) : (
            <span className="text-ink-muted">{text({ sv: "Aldrig", en: "Never" })}</span>
          )
      },
      {
        key: "atgard",
        header: <span className="sr-only">{text({ sv: "Åtgärd", en: "Action" })}</span>,
        width: pixel(64),
        align: "end",
        // Radens handlingar ligger i en meny (Twentys mönster): den farliga
        // handlingen blir röd först i menyn och i bekräftelsen, inte på varje rad.
        renderCell: (n) =>
          n.revoked_at ? null : (
            <MoreMenu
              label={text({ sv: `Val för ${n.namn}`, en: `Options for ${n.namn}` })}
              alignment="end"
              size="sm"
              items={[{ label: text({ sv: "Återkalla", en: "Revoke" }), icon: Ban, variant: "destructive", onClick: () => setAterkalla(n) }]}
            />
          )
      }
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [text]
  );

  const nyNyckel = <Button variant="primary" label={text({ sv: "Ny nyckel", en: "New key" })} icon={<Icon icon={Plus} size="sm" />} onClick={() => setNy(true)} />;
  const laddar = nycklar == null && !fel;

  return (
    <Sida
      objekt="utvecklare"
      rubrik={text({ sv: "Utvecklare", en: "Developers" })}
      antal={nycklar ? tal(aktiva.length) : undefined}
      atgarder={nyNyckel}
      vyrad={
        smal ? (
          <Selector
            label={text({ sv: "Vy", en: "View" })}
            isLabelHidden
            variant="secondary"
            size="md"
            value={filter}
            onChange={(v) => v && setFilter(v as Filter)}
            options={vyer.map((f) => ({ value: f.v, label: nycklar ? `${text(f.namn)}  ${tal(raknat[f.v])}` : text(f.namn) }))}
          />
        ) : (
          <Vyval
            value={filter}
            onChange={setFilter}
            label={text({ sv: "Vy", en: "View" })}
            val={vyer.map((f) => ({ v: f.v, namn: text(f.namn), antal: nycklar ? tal(raknat[f.v]) : undefined }))}
          />
        )
      }
    >
      {skapad?.api_key ? (
        <div className="px-4 pt-4 sm:px-6">
          <NyckelnEnGang nyckel={skapad.api_key} namn={skapad.namn} omfang={skapad.omfang} stang={() => setSkapad(null)} />
        </div>
      ) : null}

      {fel ? (
        <div className="p-4 sm:p-6">
          <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />} />
        </div>
      ) : laddar ? (
        <Tabellskelett rader={3} kolumner={smal ? 2 : 6} markering={false} label={text({ sv: "Hämtar nycklar", en: "Loading keys" })} />
      ) : visade.length === 0 ? (
        <div className="py-10">
          {raknat.alla === 0 ? (
            <EmptyState
              icon={<Icon icon={KeyRound} size="lg" color="secondary" />}
              title={text({ sv: "Ingen nyckel än", en: "No key yet" })}
              description={text({
                sv: "En nyckel låter ert CRM eller ett eget skript tala med Snajp CRM. Den når bara CRM-API:t, ingenting annat i Snajp.",
                en: "A key lets your CRM or your own script talk to Snajp CRM. It reaches only the CRM API, nothing else in Snajp."
              })}
              actions={nyNyckel}
            />
          ) : (
            <EmptyState
              icon={<Icon icon={KeyRound} size="lg" color="secondary" />}
              title={filter === "aktiva" ? text({ sv: "Ingen aktiv nyckel", en: "No active key" }) : text({ sv: "Ingen återkallad nyckel", en: "No revoked key" })}
              description={text({ sv: "Byt vy för att se de andra.", en: "Switch view to see the others." })}
              actions={<Button variant="secondary" label={text({ sv: "Visa alla", en: "Show all" })} onClick={() => setFilter("alla")} />}
            />
          )}
        </div>
      ) : smal ? (
        <div className="px-2">
          <List hasDividers density="balanced" edge="padded">
            {visade.map((n) => (
              <ListItem
                key={n.id}
                label={<span className={n.revoked_at ? "text-ink-muted line-through" : "font-semibold text-ink"}>{n.namn}</span>}
                description={`${n.prefix}…  ${n.omfang.map((o) => (OMFANGSNAMN[o] ? text(OMFANGSNAMN[o]) : o)).join(", ")}`}
                startContent={<Objektikon ikon={KeyRound} ton={n.revoked_at ? "mineral" : "sigill"} storlek={32} />}
                endContent={
                  n.revoked_at ? (
                    lage(n)
                  ) : (
                    <MoreMenu
                      label={text({ sv: `Val för ${n.namn}`, en: `Options for ${n.namn}` })}
                      alignment="end"
                      items={[{ label: text({ sv: "Återkalla", en: "Revoke" }), icon: Ban, variant: "destructive", onClick: () => setAterkalla(n) }]}
                    />
                  )
                }
              />
            ))}
          </List>
        </div>
      ) : (
        <div className="crm-tabell crm-tabell-utan-val">
          <Table<Nyckel> data={visade} columns={kolumner} idKey="id" density="balanced" dividers="rows" hasHover textOverflow="truncate" />
          <div className="crm-raknefot" role="status">
            <span>
              <span className="crm-raknefot-etikett">{text({ sv: "Aktiva", en: "Active" })}</span> <span className="crm-raknefot-tal">{tal(raknat.aktiva)}</span>
            </span>
            <span>
              <span className="crm-raknefot-etikett">{text({ sv: "Aldrig använda", en: "Never used" })}</span>{" "}
              <span className="crm-raknefot-tal">{tal(aktiva.filter((n) => !n.last_used_at).length)}</span>
            </span>
          </div>
        </div>
      )}

      {/* Webhooks: samma form som nycklarna ovan, i en egen del av sidan. */}
      <div className="pb-6">
        <Webhooks />
      </div>

      {/* API:ts uppgifter */}
      <div className="border-t border-ink/[0.08] px-4 pb-8 pt-6 sm:px-6">
        <Grid columns={{ minWidth: 320, max: 2 }} gap={4}>
          <Panelkort titel={text({ sv: "API:t", en: "The API" })} id="crm-api-uppgifter">
            <div className="crm-panelinnehall">
              <MetadataList label={{ position: "start", width: smal ? 128 : 168 }}>
                <MetadataListItem label={text({ sv: "Adress", en: "Address" })} icon={<Icon icon={Link2} size="sm" color="inherit" />}>
                  <Kopierbar varde="/api/crm/v1" />
                </MetadataListItem>
                <MetadataListItem label={text({ sv: "Nyckeln i huvudet", en: "Key in the header" })} icon={<Icon icon={KeyRound} size="sm" color="inherit" />}>
                  <Kopierbar varde="X-API-Key" />
                </MetadataListItem>
                <MetadataListItem label={text({ sv: "Specifikation", en: "Specification" })} icon={<Icon icon={FileJson} size="sm" color="inherit" />}>
                  <Link href="/api/snajp-support/crm/v1/openapi.json" isExternalLink>
                    {text({ sv: "OpenAPI som JSON", en: "OpenAPI as JSON" })}
                  </Link>
                </MetadataListItem>
                <MetadataListItem label={text({ sv: "Tak", en: "Rate limit" })} icon={<Icon icon={Gauge} size="sm" color="inherit" />}>
                  <span className="crm-varde">{text({ sv: "600 anrop per minut och nyckel", en: "600 requests per minute per key" })}</span>
                </MetadataListItem>
              </MetadataList>
            </div>
          </Panelkort>
          <Panelkort titel={text({ sv: "Vad en nyckel kan få göra", en: "What a key may do" })} id="crm-api-omfang">
            <ul className="flex flex-col">
              {OMFANG.map((o) => (
                <li key={o.id} className="crm-rattarad flex items-start gap-3 py-2.5">
                  <span className="w-[112px] shrink-0">
                    <Badge variant="neutral" label={text(o.namn)} />
                  </span>
                  <span className="text-[0.875rem] text-ink2">{text(o.vad)}</span>
                </li>
              ))}
            </ul>
          </Panelkort>
        </Grid>
      </div>

      <NyNyckel
        oppen={ny}
        stang={() => setNy(false)}
        klar={(n) => {
          setNy(false);
          setSkapad(n);
          setFilter("aktiva");
          void hamta();
        }}
      />
      <AlertDialog
        isOpen={aterkalla != null}
        onOpenChange={(o) => !o && setAterkalla(null)}
        title={text({ sv: `Återkalla ${aterkalla?.namn ?? "nyckeln"}?`, en: `Revoke ${aterkalla?.namn ?? "the key"}?` })}
        description={text({
          sv: "Integrationen som använder nyckeln slutar fungera direkt. Det går inte att ångra; skapa en ny nyckel om den behövs igen.",
          en: "The integration using the key stops working at once. This cannot be undone; create a new key if it is needed again."
        })}
        actionLabel={text({ sv: "Återkalla", en: "Revoke" })}
        cancelLabel={text({ sv: "Avbryt", en: "Cancel" })}
        onAction={() => void dra()}
        isActionLoading={arbetar}
      />
    </Sida>
  );
}

/** Nyckeln i klartext, en enda gång. Servern sparar bara dess hash. Sidans enda framhävda ruta. */
function NyckelnEnGang({ nyckel, namn, omfang, stang }: Readonly<{ nyckel: string; namn: string; omfang: string[]; stang: () => void }>) {
  const { text } = useLocale();
  const [kopierad, setKopierad] = useState<boolean | null>(null);
  const [fragaStang, setFragaStang] = useState(false);
  // Nyckeln går inte att få fram igen: den som stänger utan att ha kopierat får en fråga först.
  const forsokStang = () => (kopierad === true ? stang() : setFragaStang(true));
  async function kopiera() {
    try {
      await navigator.clipboard.writeText(nyckel);
      setKopierad(true);
    } catch {
      setKopierad(false);
    }
  }
  return (
    <Card variant="yellow" padding={5} className="crm-kort-framhavd">
      <section aria-labelledby="crm-ny-nyckel-rubrik" className="flex flex-col gap-3">
        <div className="flex items-start gap-3">
          <Objektikon ikon={KeyRound} ton="ockra" storlek={32} />
          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
            <h2 id="crm-ny-nyckel-rubrik" className="font-sans text-[0.9375rem] font-semibold tracking-normal text-ink">
              {text({ sv: `Nyckeln ${namn} är skapad`, en: `The key ${namn} is created` })}
            </h2>
            <p className="text-[0.875rem] text-ink2">
              {text({ sv: "Kopiera den nu och lägg den i integrationen. Den visas inte igen; Snajp sparar bara ett avtryck av den.", en: "Copy it now and put it in the integration. It will not be shown again; Snajp stores only a fingerprint of it." })}
            </p>
          </div>
          <IconButton label={text({ sv: "Stäng", en: "Close" })} icon={<Icon icon={X} size="sm" />} variant="ghost" onClick={forsokStang} />
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="crm-nyckelruta min-w-0 flex-1" aria-label={text({ sv: "Den nya nyckeln", en: "The new key" })}>
            {nyckel}
          </div>
          <Button
            variant="primary"
            label={kopierad ? text({ sv: "Kopierad", en: "Copied" }) : text({ sv: "Kopiera nyckeln", en: "Copy the key" })}
            icon={<Icon icon={kopierad ? Check : Copy} size="sm" />}
            onClick={() => void kopiera()}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[0.8125rem] text-ink-muted">
          <span>{text({ sv: "Får", en: "May" })}</span>
          {omfang.map((o) => (
            <Badge key={o} variant="neutral" label={OMFANGSNAMN[o] ? text(OMFANGSNAMN[o]) : o} />
          ))}
          {kopierad === false ? (
            <span role="status" className="text-danger">
              {text({ sv: "Webbläsaren tillät inte kopiering. Markera nyckeln och kopiera den för hand.", en: "The browser did not allow copying. Select the key and copy it by hand." })}
            </span>
          ) : null}
        </div>
      </section>
      <AlertDialog
        isOpen={fragaStang}
        onOpenChange={(o) => !o && setFragaStang(false)}
        title={text({ sv: "Nyckeln visas inte igen. Stäng ändå?", en: "The key will not be shown again. Close anyway?" })}
        description={text({
          sv: "Du har inte kopierat den. Stänger du nu måste du skapa en ny nyckel.",
          en: "You have not copied it. If you close now you will need to create a new key."
        })}
        actionLabel={text({ sv: "Stäng ändå", en: "Close anyway" })}
        cancelLabel={text({ sv: "Tillbaka till nyckeln", en: "Back to the key" })}
        onAction={() => {
          setFragaStang(false);
          stang();
        }}
      />
    </Card>
  );
}

function NyNyckel({ oppen, stang, klar }: Readonly<{ oppen: boolean; stang: () => void; klar: (n: Nyckel) => void }>) {
  const { text } = useLocale();
  const [namn, setNamn] = useState("");
  const [valda, setValda] = useState<string[]>(["crm:las", "crm:synk"]);
  const [sparar, setSparar] = useState(false);
  const [fel, setFel] = useState<Localized | null>(null);

  useEffect(() => {
    if (oppen) {
      setNamn("");
      setValda(["crm:las", "crm:synk"]);
      setFel(null);
    }
  }, [oppen]);

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    if (sparar) return;
    if (!namn.trim()) {
      setFel({ sv: "Nyckeln behöver ett namn.", en: "The key needs a name." });
      return;
    }
    if (valda.length === 0) return;
    setSparar(true);
    setFel(null);
    try {
      klar(await crmAnrop<Nyckel>("/nycklar", { method: "POST", body: JSON.stringify({ namn: namn.trim(), omfang: valda }) }));
    } catch (orsak) {
      setFel(orsak instanceof CrmFel ? orsak.text : { sv: "Det gick inte att skapa nyckeln.", en: "Could not create the key." });
    } finally {
      setSparar(false);
    }
  }

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && stang()} purpose="form" width={520}>
      <Layout
        header={<DialogHeader title={text({ sv: "Ny nyckel", en: "New key" })} onOpenChange={(o) => !o && stang()} />}
        content={
          <LayoutContent>
            <form id="crm-ny-nyckel" onSubmit={spara} noValidate className="flex flex-col gap-6">
              <TextInput
                label={text({ sv: "Namn", en: "Name" })}
                description={text({ sv: "Vad nyckeln används till, så att ni känner igen den i listan.", en: "What the key is for, so that you recognise it in the list." })}
                placeholder={text({ sv: "HubSpot-synken", en: "HubSpot sync" })}
                value={namn}
                onChange={(v) => {
                  setNamn(v);
                  setFel(null);
                }}
                isRequired
                hasAutoFocus
                width="100%"
                status={fel ? { type: "error", message: text(fel) } : undefined}
              />
              <fieldset className="crm-formgrupp">
                <legend className="mb-3 text-[0.8125rem] font-semibold text-ink-muted">{text({ sv: "Vad nyckeln får göra", en: "What the key may do" })}</legend>
                <div className="flex flex-col gap-3">
                  {OMFANG.map((o) => (
                    <CheckboxInput
                      key={o.id}
                      label={text(o.namn)}
                      description={text(o.vad)}
                      value={valda.includes(o.id)}
                      onChange={(pa) => setValda((v) => (pa ? [...v, o.id] : v.filter((x) => x !== o.id)))}
                    />
                  ))}
                </div>
                {valda.length === 0 ? (
                  <p role="status" className="mt-3 text-[0.8125rem] text-ink-muted">
                    {text({ sv: "Välj minst en sak nyckeln får göra.", en: "Pick at least one thing the key may do." })}
                  </p>
                ) : null}
              </fieldset>
            </form>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Avbryt", en: "Cancel" })} variant="ghost" onClick={stang} />
              <Button type="submit" form="crm-ny-nyckel" variant="primary" label={text({ sv: "Skapa nyckeln", en: "Create key" })} isLoading={sparar} isDisabled={valda.length === 0} />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
