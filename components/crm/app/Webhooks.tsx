"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Bell, Check, CircleDot, Clock, Copy, History, Plus, Power, PowerOff, RefreshCw, Send, Trash2, Webhook as WebhookIkon, X } from "lucide-react";
import { AlertDialog } from "@astryxdesign/core/AlertDialog";
import { Badge } from "@astryxdesign/core/Badge";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { Card } from "@astryxdesign/core/Card";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { Drawer, DrawerHeader } from "@astryxdesign/core/Drawer";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { List, ListItem } from "@astryxdesign/core/List";
import { MoreMenu } from "@astryxdesign/core/MoreMenu";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { HStack } from "@astryxdesign/core/Stack";
import { Table, pixel, proportional, type TableColumn } from "@astryxdesign/core/Table";
import { Text } from "@astryxdesign/core/Text";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { useToast } from "@astryxdesign/core/Toast";
import { Kolumnrubrik, Objektikon, Prick, Tabellskelett, useSmal } from "@/components/crm/app/kit";
import { Felruta } from "@/components/crm/app/Sida";
import { CrmFel, crmAnrop, type Leverans, type Webhook } from "@/lib/crm/api";
import { useLocale, type Localized } from "@/lib/i18n";

/** Hur ofta leveransloggen hämtas om medan en leverans väntar (som synkens puls). */
const LEVERANSPULS = 3000;

// ---------------------------------------------------------------------------
// Ord
// ---------------------------------------------------------------------------

const OBJEKTORD: Record<string, Localized> = {
  company: { sv: "Bolag", en: "Company" },
  person: { sv: "Person", en: "Person" },
  deal: { sv: "Affär", en: "Deal" },
  task: { sv: "Uppgift", en: "Task" },
  note: { sv: "Anteckning", en: "Note" },
  sync: { sv: "Synk", en: "Sync" }
};
const TYPORD: Record<string, Localized> = {
  created: { sv: "skapas", en: "created" },
  updated: { sv: "ändras", en: "updated" },
  deleted: { sv: "raderas", en: "deleted" },
  restored: { sv: "återställs", en: "restored" },
  purged: { sv: "töms", en: "purged" },
  completed: { sv: "blir klar", en: "completed" }
};

/** "Bolag ändras" för `company.updated`; okänt visas som koden. */
function handelsenamn(kod: string, text: (l: Localized) => string): string {
  if (kod === "ping") return text({ sv: "Testanrop", en: "Test call" });
  const [objekt, typ] = kod.split(".");
  if (!OBJEKTORD[objekt] || !TYPORD[typ]) return kod;
  return `${text(OBJEKTORD[objekt])} ${text(TYPORD[typ])}`;
}

/** API:ts felkoder för webhooks, på läsarens språk. Okänt: API:ts egen text. */
const WEBHOOKFEL: Record<string, Localized> = {
  invalid_url: { sv: "Adressen går inte att använda. Den ska vara en publik https-adress.", en: "The address cannot be used. It must be a public https address." },
  invalid_events: { sv: "Välj minst en händelse som finns.", en: "Pick at least one event that exists." },
  too_many_webhooks: { sv: "Arbetsytan har redan tio webhooks, det högsta som går. Ta bort en innan du lägger till en ny.", en: "The workspace already has ten webhooks, the most allowed. Delete one before adding another." },
  webhooks_unavailable: { sv: "Webhooks går inte att skapa just nu. Kontakta Snajp.", en: "Webhooks cannot be created right now. Contact Snajp." },
  agreement_missing: { sv: "Personuppgiftsbiträdesavtalet är inte registrerat än. Kontakta Snajp.", en: "The data processing agreement is not registered yet. Contact Snajp." }
};

const LEVERANSLAGE: Record<Leverans["status"], { text: Localized; badge: "yellow" | "green" | "red"; prick: "ockra" | "mossa" | "fara" }> = {
  pending: { text: { sv: "Väntar", en: "Pending" }, badge: "yellow", prick: "ockra" },
  delivered: { text: { sv: "Levererad", en: "Delivered" }, badge: "green", prick: "mossa" },
  failed: { text: { sv: "Misslyckad", en: "Failed" }, badge: "red", prick: "fara" }
};

const visadAdress = (url: string) => url.replace(/^https:\/\//, "");

/** Webhookens läge som etikett: aktiv, avstängd av Snajp (för många fel) eller avslagen. */
function Lage({ w }: Readonly<{ w: Webhook }>) {
  const { text } = useLocale();
  if (w.active) return <Badge variant="green" label={text({ sv: "Aktiv", en: "Active" })} icon={<Prick ton="mossa" />} />;
  if (w.disabled_reason) return <Badge variant="red" label={text({ sv: "Avstängd", en: "Disabled" })} icon={<Prick ton="fara" />} />;
  return <Badge variant="neutral" label={text({ sv: "Avslagen", en: "Turned off" })} icon={<Prick ton={null} />} />;
}

/** Senaste leveransen: det som hände senast av lyckat och misslyckat. */
function Senaste({ w }: Readonly<{ w: Webhook }>) {
  const { text } = useLocale();
  const ok = w.last_success_at;
  const fel = w.last_failure_at;
  if (!ok && !fel) return <span className="text-ink-muted">{text({ sv: "Ingen än", en: "None yet" })}</span>;
  const felSenast = fel && (!ok || fel > ok);
  return (
    <span className="inline-flex min-w-0 items-center gap-1.5">
      <Prick ton={felSenast ? "fara" : "mossa"} />
      <span className="sr-only">{felSenast ? text({ sv: "Misslyckades", en: "Failed" }) : text({ sv: "Levererad", en: "Delivered" })}</span>
      <Timestamp value={(felSenast ? fel : ok)!} format="relative" />
    </span>
  );
}

// ---------------------------------------------------------------------------
// Avsnittet
// ---------------------------------------------------------------------------

/**
 * Webhooks i Utvecklare-vyn, i samma form som nycklarna: tabell, ny webhook i en
 * dialog, hemligheten en gång efter skapandet, och en leveranslogg per webhook i
 * en panel som följer adressen (`?webhook=<id>`). Loggen hämtas om var tredje
 * sekund medan en leverans väntar, så att ett testanrop syns där det skickades;
 * utfallet ligger kvar i API:t efter en omladdning.
 */
export function Webhooks() {
  const { text, locale } = useLocale();
  const visa = useToast();
  const smal = useSmal();
  const params = useSearchParams();
  const adressens = params?.get("webhook") ?? null;
  const [oppenId, setOppenId] = useState<string | null>(adressens);
  useEffect(() => {
    setOppenId(adressens);
  }, [adressens]);
  const tal = (n: number) => n.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB");

  const [webhooks, setWebhooks] = useState<Webhook[] | null>(null);
  const [handelser, setHandelser] = useState<string[]>([]);
  const [fel, setFel] = useState<unknown>(null);
  const [ny, setNy] = useState(false);
  const [skapad, setSkapad] = useState<Webhook | null>(null);
  const [taBort, setTaBort] = useState<Webhook | null>(null);
  const [arbetar, setArbetar] = useState<string | null>(null);

  const hamta = useCallback(async () => {
    try {
      const [w, h] = await Promise.all([
        crmAnrop<{ data: Webhook[] }>("/v1/webhooks"),
        crmAnrop<{ events: string[] }>("/v1/webhooks/events").catch(() => ({ events: [] as string[] }))
      ]);
      setWebhooks(w.data);
      setHandelser(h.events);
      setFel(null);
    } catch (e) {
      setFel(e);
    }
  }, []);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  const sattOppen = useCallback((id: string | null) => {
    setOppenId(id);
    const q = new URLSearchParams(window.location.search);
    if (id) q.set("webhook", id);
    else q.delete("webhook");
    const s = q.toString();
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${s ? `?${s}` : ""}`);
  }, []);

  /** En webhook som hämtats på nytt (panelen läser den med loggen) ersätter raden i listan. */
  const ersatt = useCallback((w: Webhook) => setWebhooks((forr) => (forr ?? []).map((x) => (x.id === w.id ? w : x))), []);

  const feltext = (e: unknown, reserv: Localized): Localized => (e instanceof CrmFel ? (e.kod && WEBHOOKFEL[e.kod]) || e.text : reserv);

  async function slaPa(w: Webhook, pa: boolean) {
    setArbetar(w.id);
    try {
      const svar = await crmAnrop<Webhook>(`/v1/webhooks/${encodeURIComponent(w.id)}`, { method: "PATCH", body: JSON.stringify({ active: pa }) });
      setWebhooks((forr) => (forr ?? []).map((x) => (x.id === svar.id ? svar : x)));
      visa({
        body: pa
          ? text({ sv: `${visadAdress(w.url)} är påslagen igen.`, en: `${visadAdress(w.url)} is turned on again.` })
          : text({ sv: `${visadAdress(w.url)} är avslagen.`, en: `${visadAdress(w.url)} is turned off.` }),
        uniqueID: "crm-webhook-lage"
      });
    } catch (e) {
      visa({ type: "error", body: text(feltext(e, { sv: "Det gick inte att ändra webhooken.", en: "Could not change the webhook." })), uniqueID: "crm-webhook-lage" });
    } finally {
      setArbetar(null);
    }
  }

  async function radera(w: Webhook) {
    setTaBort(null);
    setArbetar(w.id);
    try {
      await crmAnrop<null>(`/v1/webhooks/${encodeURIComponent(w.id)}`, { method: "DELETE" });
      if (oppenId === w.id) sattOppen(null);
      if (skapad?.id === w.id) setSkapad(null);
      setWebhooks((forr) => (forr ?? []).filter((x) => x.id !== w.id));
      visa({ body: text({ sv: `${visadAdress(w.url)} är borttagen, med sin leveranslogg.`, en: `${visadAdress(w.url)} is deleted, with its delivery log.` }), uniqueID: "crm-webhook-bort" });
    } catch (e) {
      visa({ type: "error", body: text(feltext(e, { sv: "Det gick inte att ta bort webhooken.", en: "Could not delete the webhook." })), uniqueID: "crm-webhook-bort" });
    } finally {
      setArbetar(null);
    }
  }

  const meny = (w: Webhook) => [
    { label: text({ sv: "Leveranslogg", en: "Delivery log" }), icon: History, onClick: () => sattOppen(w.id) },
    w.active
      ? { label: text({ sv: "Slå av", en: "Turn off" }), icon: PowerOff, onClick: () => void slaPa(w, false) }
      : { label: text({ sv: "Slå på", en: "Turn on" }), icon: Power, onClick: () => void slaPa(w, true) },
    { type: "divider" as const },
    { label: text({ sv: "Ta bort", en: "Delete" }), icon: Trash2, variant: "destructive" as const, onClick: () => setTaBort(w) }
  ];

  const handelsetext = (w: Webhook) =>
    w.events.includes("*")
      ? text({ sv: "Alla händelser", en: "All events" })
      : w.events.length === 1
        ? handelsenamn(w.events[0], text)
        : text({ sv: `${tal(w.events.length)} händelser`, en: `${tal(w.events.length)} events` });

  const kolumner = useMemo<TableColumn<Webhook>[]>(
    () => [
      {
        key: "url",
        header: <Kolumnrubrik ikon={WebhookIkon}>{text({ sv: "Adress", en: "Address" })}</Kolumnrubrik>,
        width: proportional(1, { minWidth: 220 }),
        renderCell: (w) => (
          <button
            type="button"
            className="crm-chip inline-flex h-7 min-w-0 max-w-full items-center gap-2 rounded-[6px] pl-1 pr-2 text-left"
            onClick={() => sattOppen(w.id)}
            aria-label={text({ sv: `Öppna leveransloggen för ${visadAdress(w.url)}`, en: `Open the delivery log for ${visadAdress(w.url)}` })}
          >
            <Objektikon ikon={WebhookIkon} ton="mineral" storlek={20} />
            <span className="min-w-0 truncate text-[0.875rem] font-semibold text-ink">{visadAdress(w.url)}</span>
          </button>
        )
      },
      {
        key: "events",
        header: <Kolumnrubrik ikon={Bell}>{text({ sv: "Händelser", en: "Events" })}</Kolumnrubrik>,
        width: pixel(176),
        renderCell: (w) => <span className="text-ink2">{handelsetext(w)}</span>
      },
      {
        key: "active",
        header: <Kolumnrubrik ikon={CircleDot}>{text({ sv: "Läge", en: "State" })}</Kolumnrubrik>,
        width: pixel(132),
        renderCell: (w) => <Lage w={w} />
      },
      {
        key: "senaste",
        header: <Kolumnrubrik ikon={Clock}>{text({ sv: "Senaste leverans", en: "Last delivery" })}</Kolumnrubrik>,
        width: pixel(176),
        renderCell: (w) => <Senaste w={w} />
      },
      {
        key: "atgard",
        header: <span className="sr-only">{text({ sv: "Åtgärd", en: "Action" })}</span>,
        width: pixel(64),
        align: "end",
        renderCell: (w) => (
          <MoreMenu label={text({ sv: `Val för ${visadAdress(w.url)}`, en: `Options for ${visadAdress(w.url)}` })} alignment="end" size="sm" isDisabled={arbetar === w.id} items={meny(w)} />
        )
      }
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [text, arbetar, sattOppen]
  );

  const nyKnapp = <Button variant="secondary" label={text({ sv: "Ny webhook", en: "New webhook" })} icon={<Icon icon={Plus} size="sm" />} onClick={() => setNy(true)} />;
  const oppen = oppenId ? (webhooks?.find((w) => w.id === oppenId) ?? null) : null;

  return (
    <section aria-labelledby="crm-webhooks" className="flex flex-col gap-3 border-t border-ink/[0.08] px-4 pt-6 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div className="flex min-w-0 flex-col gap-0.5">
          <h2 id="crm-webhooks" className="crm-delrubrik">
            {text({ sv: "Webhooks", en: "Webhooks" })}
          </h2>
          <span className="text-[0.8125rem] text-ink-muted">
            {text({
              sv: "Snajp skickar en signerad händelse till er adress när en post skapas, ändras eller raderas, och när en synk blir klar.",
              en: "Snajp sends a signed event to your address when a record is created, changed or deleted, and when a sync completes."
            })}
          </span>
        </div>
        {webhooks && webhooks.length > 0 ? nyKnapp : null}
      </div>

      {skapad?.secret ? <HemlighetenEnGang webhook={skapad} stang={() => setSkapad(null)} /> : null}

      {fel && !webhooks ? (
        <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />} />
      ) : (
        <div className="crm-tabellram">
          {!webhooks ? (
            <Tabellskelett rader={2} kolumner={smal ? 2 : 5} markering={false} label={text({ sv: "Hämtar webhooks", en: "Loading webhooks" })} />
          ) : webhooks.length === 0 ? (
            <div className="py-8">
              <EmptyState
                icon={<Icon icon={WebhookIkon} size="lg" color="secondary" />}
                title={text({ sv: "Ingen webhook än", en: "No webhook yet" })}
                description={text({
                  sv: "En webhook låter ert system få veta direkt när något ändras i Snajp CRM, i stället för att fråga om och om igen.",
                  en: "A webhook lets your system know at once when something changes in Snajp CRM, instead of asking again and again."
                })}
                actions={nyKnapp}
              />
            </div>
          ) : smal ? (
            <div className="px-2">
              <List hasDividers density="balanced" edge="padded">
                {webhooks.map((w) => (
                  <ListItem
                    key={w.id}
                    label={<span className="block truncate font-semibold text-ink">{visadAdress(w.url)}</span>}
                    description={handelsetext(w)}
                    startContent={<Objektikon ikon={WebhookIkon} ton="mineral" storlek={32} />}
                    endContent={<Lage w={w} />}
                    onClick={() => sattOppen(w.id)}
                  />
                ))}
              </List>
            </div>
          ) : (
            <div className="crm-tabell crm-tabell-utan-val">
              <Table<Webhook> data={webhooks} columns={kolumner} idKey="id" density="balanced" dividers="rows" hasHover textOverflow="truncate" />
              <div className="crm-raknefot" role="status">
                <span>
                  <span className="crm-raknefot-etikett">{text({ sv: "Aktiva", en: "Active" })}</span>{" "}
                  <span className="crm-raknefot-tal">{tal(webhooks.filter((w) => w.active).length)}</span>
                </span>
                <span>
                  <span className="crm-raknefot-etikett">{text({ sv: "Högst", en: "At most" })}</span> <span className="crm-raknefot-tal">10</span>
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      <Leveranspanel
        webhook={oppen}
        laddar={oppenId != null && oppen == null && webhooks == null}
        stang={() => sattOppen(null)}
        slaPa={(w) => void slaPa(w, true)}
        arbetar={oppen ? arbetar === oppen.id : false}
        uppdaterad={ersatt}
      />

      <NyWebhook
        oppen={ny}
        handelser={handelser}
        stang={() => setNy(false)}
        skapad={(w) => {
          setNy(false);
          setSkapad(w);
          void hamta();
        }}
      />

      <AlertDialog
        isOpen={taBort != null}
        onOpenChange={(o) => !o && setTaBort(null)}
        title={text({ sv: `Ta bort ${taBort ? visadAdress(taBort.url) : "webhooken"}?`, en: `Delete ${taBort ? visadAdress(taBort.url) : "the webhook"}?` })}
        description={text({
          sv: "Snajp slutar skicka händelser till adressen, och leveransloggen tas bort. Det går inte att ångra.",
          en: "Snajp stops sending events to the address, and the delivery log is deleted. This cannot be undone."
        })}
        actionLabel={text({ sv: "Ta bort", en: "Delete" })}
        cancelLabel={text({ sv: "Avbryt", en: "Cancel" })}
        onAction={() => taBort && void radera(taBort)}
      />
    </section>
  );
}

// ---------------------------------------------------------------------------
// Hemligheten, en gång
// ---------------------------------------------------------------------------

/** Signeringshemligheten i klartext, en enda gång efter skapandet. Sidans enda framhävda ruta. */
function HemlighetenEnGang({ webhook, stang }: Readonly<{ webhook: Webhook; stang: () => void }>) {
  const { text } = useLocale();
  const [kopierad, setKopierad] = useState<boolean | null>(null);
  const [fragaStang, setFragaStang] = useState(false);
  const hemlighet = webhook.secret ?? "";
  async function kopiera() {
    try {
      await navigator.clipboard.writeText(hemlighet);
      setKopierad(true);
    } catch {
      setKopierad(false);
    }
  }
  return (
    <Card variant="yellow" padding={5} className="crm-kort-framhavd">
      <section aria-labelledby="crm-ny-hemlighet" className="flex flex-col gap-3">
        <div className="flex items-start gap-3">
          <Objektikon ikon={WebhookIkon} ton="ockra" storlek={32} />
          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
            <h3 id="crm-ny-hemlighet" className="font-sans text-[0.9375rem] font-semibold tracking-normal text-ink [overflow-wrap:anywhere] [word-break:normal]">
              {text({ sv: `Webhooken till ${visadAdress(webhook.url)} är skapad`, en: `The webhook to ${visadAdress(webhook.url)} is created` })}
            </h3>
            <p className="text-[0.875rem] text-ink2">
              {text({
                sv: "Varje leverans signeras med hemligheten nedan (huvudet X-Snajp-Signature). Kopiera den nu och lägg den hos mottagaren. Den går inte att se igen.",
                en: "Every delivery is signed with the secret below (the X-Snajp-Signature header). Copy it now and give it to the receiver. It cannot be seen again."
              })}
            </p>
          </div>
          <IconButton label={text({ sv: "Stäng", en: "Close" })} icon={<Icon icon={X} size="sm" />} variant="ghost" onClick={() => (kopierad ? stang() : setFragaStang(true))} />
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="crm-nyckelruta min-w-0 flex-1" aria-label={text({ sv: "Signeringshemligheten", en: "The signing secret" })}>
            {hemlighet}
          </div>
          <Button
            variant="primary"
            label={kopierad ? text({ sv: "Kopierad", en: "Copied" }) : text({ sv: "Kopiera hemligheten", en: "Copy the secret" })}
            icon={<Icon icon={kopierad ? Check : Copy} size="sm" />}
            onClick={() => void kopiera()}
          />
        </div>
        {kopierad === false ? (
          <span role="status" className="text-[0.8125rem] text-danger">
            {text({ sv: "Webbläsaren tillät inte kopiering. Markera hemligheten och kopiera den för hand.", en: "The browser did not allow copying. Select the secret and copy it by hand." })}
          </span>
        ) : null}
      </section>
      <AlertDialog
        isOpen={fragaStang}
        onOpenChange={(o) => !o && setFragaStang(false)}
        title={text({ sv: "Hemligheten visas inte igen. Stäng ändå?", en: "The secret will not be shown again. Close anyway?" })}
        description={text({
          sv: "Du har inte kopierat den. Utan den kan mottagaren inte kontrollera signaturen; då får du ta bort webhooken och skapa en ny.",
          en: "You have not copied it. Without it the receiver cannot check the signature; you would have to delete the webhook and create a new one."
        })}
        actionLabel={text({ sv: "Stäng ändå", en: "Close anyway" })}
        cancelLabel={text({ sv: "Tillbaka till hemligheten", en: "Back to the secret" })}
        onAction={() => {
          setFragaStang(false);
          stang();
        }}
      />
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Leveransloggen
// ---------------------------------------------------------------------------

function Leveranspanel({
  webhook,
  laddar,
  stang,
  slaPa,
  arbetar,
  uppdaterad
}: Readonly<{
  webhook: Webhook | null;
  laddar: boolean;
  stang: () => void;
  slaPa: (w: Webhook) => void;
  arbetar: boolean;
  uppdaterad: (w: Webhook) => void;
}>) {
  const { text } = useLocale();
  const visa = useToast();
  const [leveranser, setLeveranser] = useState<Leverans[] | null>(null);
  const [fel, setFel] = useState<unknown>(null);
  const [hamtar, setHamtar] = useState(false);
  const [skickar, setSkickar] = useState<string | null>(null);
  const id = webhook?.id ?? null;

  const hamta = useCallback(async () => {
    if (!id) return;
    setHamtar(true);
    try {
      const [l, w] = await Promise.all([
        crmAnrop<{ data: Leverans[] }>(`/v1/webhooks/${encodeURIComponent(id)}/deliveries?limit=50`),
        crmAnrop<Webhook>(`/v1/webhooks/${encodeURIComponent(id)}`)
      ]);
      setLeveranser(l.data);
      uppdaterad(w);
      setFel(null);
    } catch (e) {
      setFel(e);
    } finally {
      setHamtar(false);
    }
  }, [id, uppdaterad]);

  useEffect(() => {
    setLeveranser(null);
    setFel(null);
    if (id) void hamta();
    // Bara när en annan webhook öppnas; hamta byts när listan uppdateras.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Förloppet följs här, där testanropet skickades: medan en leverans väntar
  // hämtas loggen om var tredje sekund. Utfallet ligger kvar i API:t.
  const vantar = leveranser?.some((l) => l.status === "pending") ?? false;
  useEffect(() => {
    if (!vantar) return;
    const t = window.setInterval(() => void hamta(), LEVERANSPULS);
    return () => window.clearInterval(t);
  }, [vantar, hamta]);

  async function skicka(vag: string, nyckel: string, klart: Localized) {
    setSkickar(nyckel);
    try {
      const ny = await crmAnrop<Leverans>(vag, { method: "POST" });
      setLeveranser((forr) => [ny, ...(forr ?? []).filter((l) => l.id !== ny.id)]);
      visa({ body: text(klart), uniqueID: "crm-webhook-skickad" });
    } catch (e) {
      visa({ type: "error", body: text(e instanceof CrmFel ? e.text : { sv: "Det gick inte att skicka.", en: "Could not send." }), uniqueID: "crm-webhook-skickad" });
    } finally {
      setSkickar(null);
    }
  }

  const w = webhook;
  const avstangd = w && !w.active;

  return (
    <Drawer
      isOpen={w != null || laddar}
      onOpenChange={(o) => !o && stang()}
      label={w ? text({ sv: `Leveransloggen för ${visadAdress(w.url)}`, en: `Delivery log for ${visadAdress(w.url)}` }) : text({ sv: "Leveransloggen", en: "Delivery log" })}
      width={520}
      hasScrim={false}
    >
      <Layout
        header={
          <DrawerHeader
            hasDivider={false}
            startContent={<Objektikon ikon={WebhookIkon} ton="mineral" storlek={32} />}
            title={
              w ? (
                // En adress är inget namn: den kapas på en rad (hela står i tipset) i stället för att brytas mitt i ett ord.
                <span className="crm-postnamn block max-w-full truncate" style={{ fontSize: "1.125rem" }} title={w.url}>
                  {visadAdress(w.url)}
                </span>
              ) : (
                <Skeleton width={200} height={22} radius="rounded" />
              )
            }
            subtitle={
              w ? (
                <span className="mt-1 inline-flex flex-wrap items-center gap-2">
                  <Lage w={w} />
                  <span className="text-[0.8125rem] text-ink-muted">
                    {w.events.includes("*") ? text({ sv: "Alla händelser", en: "All events" }) : w.events.map((h) => handelsenamn(h, text)).join(", ")}
                  </span>
                </span>
              ) : undefined
            }
            onOpenChange={(o) => !o && stang()}
          />
        }
        content={
          <LayoutContent padding={0}>
            <div data-autofocus tabIndex={-1} className="crm-autofokus flex flex-col gap-5 border-t border-ink/[0.08] px-5 pb-6 pt-5">
              {avstangd && w.disabled_reason === "for_manga_fel" ? (
                <Banner
                  status="error"
                  container="card"
                  title={text({ sv: "Snajp har stängt av webhooken", en: "Snajp has disabled the webhook" })}
                  description={text({
                    sv: `Leveranserna misslyckades ${w.consecutive_failures} gånger i rad${w.last_error ? ` (senast: ${w.last_error})` : ""}. Se till att adressen svarar med 2xx och slå sedan på webhooken igen; räknaren börjar då om.`,
                    en: `Deliveries failed ${w.consecutive_failures} times in a row${w.last_error ? ` (last: ${w.last_error})` : ""}. Make sure the address answers with 2xx, then turn the webhook on again; the count then starts over.`
                  })}
                  endContent={<Button size="sm" label={text({ sv: "Slå på igen", en: "Turn on again" })} isLoading={arbetar} onClick={() => slaPa(w)} />}
                />
              ) : avstangd ? (
                <Banner
                  status="info"
                  container="card"
                  title={text({ sv: "Webhooken är avslagen", en: "The webhook is turned off" })}
                  description={text({ sv: "Inga händelser skickas förrän den slås på igen.", en: "No events are sent until it is turned on again." })}
                  endContent={<Button size="sm" label={text({ sv: "Slå på", en: "Turn on" })} isLoading={arbetar} onClick={() => slaPa(w)} />}
                />
              ) : null}

              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-sans text-[0.8125rem] font-semibold tracking-normal text-ink-muted">{text({ sv: "Leveranser, nyast först", en: "Deliveries, newest first" })}</h3>
                <span className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    label={text({ sv: "Uppdatera", en: "Refresh" })}
                    icon={<Icon icon={RefreshCw} size="sm" />}
                    isLoading={hamtar && !vantar}
                    onClick={() => void hamta()}
                  />
                  <Button
                    size="sm"
                    variant="secondary"
                    label={text({ sv: "Skicka testanrop", en: "Send test call" })}
                    icon={<Icon icon={Send} size="sm" />}
                    isLoading={skickar === "test"}
                    isDisabled={!w || !w.active}
                    onClick={() =>
                      w &&
                      void skicka(`/v1/webhooks/${encodeURIComponent(w.id)}/test`, "test", {
                        sv: "Testanropet är köat. Utfallet syns i loggen.",
                        en: "The test call is queued. The outcome shows in the log."
                      })
                    }
                  />
                </span>
              </div>

              {vantar ? (
                <div className="flex items-center gap-2 text-[0.8125rem] text-ink-muted" role="status" aria-live="polite">
                  <Prick ton="ockra" pulserar />
                  <span>{text({ sv: "En leverans väntar. Loggen uppdateras var tredje sekund.", en: "A delivery is pending. The log is updated every three seconds." })}</span>
                </div>
              ) : null}

              {fel && !leveranser ? (
                <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />} />
              ) : !leveranser ? (
                <div className="flex flex-col gap-4" role="status" aria-busy="true" aria-label={text({ sv: "Hämtar leveranserna", en: "Loading the deliveries" })}>
                  {Array.from({ length: 4 }, (_, i) => (
                    <Skeleton key={i} width={`${45 + ((i * 17) % 40)}%`} height={10} radius="rounded" index={i} />
                  ))}
                </div>
              ) : leveranser.length === 0 ? (
                <EmptyState
                  isCompact
                  icon={<Icon icon={Send} size="lg" color="secondary" />}
                  title={text({ sv: "Inga leveranser än", en: "No deliveries yet" })}
                  description={text({
                    sv: "Varje händelse som skickas till adressen står här i 30 dagar. Skicka ett testanrop för att prova mottagaren.",
                    en: "Every event sent to the address shows here for 30 days. Send a test call to try the receiver."
                  })}
                />
              ) : (
                <ul className="flex flex-col">
                  {leveranser.map((l) => {
                    const lage = LEVERANSLAGE[l.status];
                    return (
                      <li key={l.id} className="crm-rattarad flex items-start gap-3 py-3">
                        <span className="flex min-w-0 flex-1 flex-col gap-1">
                          <span className="flex min-w-0 flex-wrap items-center gap-2">
                            <span className="text-[0.875rem] font-semibold text-ink">{handelsenamn(l.event, text)}</span>
                            <Badge variant={lage.badge} label={text(lage.text)} icon={<Prick ton={lage.prick} pulserar={l.status === "pending"} />} />
                          </span>
                          <span className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-[0.8125rem] text-ink-muted">
                            <code className="crm-kod">{l.event}</code>
                            {/* Varje uppgift håller ihop med sin punkt, så att raden bryter mellan uppgifterna. */}
                            <span className="whitespace-nowrap">
                              {l.attempts === 1 ? text({ sv: "1 försök", en: "1 attempt" }) : text({ sv: `${l.attempts} försök`, en: `${l.attempts} attempts` })}
                            </span>
                            {l.status_code != null ? (
                              <span className="whitespace-nowrap tabular-nums">
                                <span aria-hidden>· </span>
                                {text({ sv: `Svar ${l.status_code}`, en: `Response ${l.status_code}` })}
                              </span>
                            ) : null}
                            {l.created_at ? (
                              <span className="whitespace-nowrap">
                                <span aria-hidden>· </span>
                                <Timestamp value={l.delivered_at ?? l.created_at} format="relative" />
                              </span>
                            ) : null}
                          </span>
                          {l.error ? <span className="text-[0.8125rem] text-danger">{l.error}</span> : null}
                          {l.status === "pending" && l.next_attempt_at ? (
                            <span className="text-[0.8125rem] text-ink-muted">
                              {text({ sv: "Nästa försök ", en: "Next attempt " })}
                              <Timestamp value={l.next_attempt_at} format="relative" />
                            </span>
                          ) : null}
                        </span>
                        {l.status === "failed" && w ? (
                          <Button
                            size="sm"
                            variant="secondary"
                            label={text({ sv: "Skicka om", en: "Send again" })}
                            isLoading={skickar === l.id}
                            onClick={() =>
                              void skicka(`/v1/webhooks/${encodeURIComponent(w.id)}/deliveries/${encodeURIComponent(l.id)}/retry`, l.id, {
                                sv: "Leveransen skickas om. Utfallet syns i loggen.",
                                en: "The delivery is being sent again. The outcome shows in the log."
                              })
                            }
                          />
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </LayoutContent>
        }
        footer={
          w ? (
            <LayoutFooter hasDivider>
              <HStack gap={2} vAlign="center" justify="between">
                <Text type="supporting" color="secondary" maxLines={2}>
                  {text({ sv: "Ett misslyckat försök görs om sju gånger under ett dygn. Loggen sparas i 30 dagar.", en: "A failed attempt is retried seven times over a day. The log is kept for 30 days." })}
                </Text>
              </HStack>
            </LayoutFooter>
          ) : undefined
        }
      />
    </Drawer>
  );
}

// ---------------------------------------------------------------------------
// Dialogen Ny webhook
// ---------------------------------------------------------------------------

function NyWebhook({ oppen, handelser, stang, skapad }: Readonly<{ oppen: boolean; handelser: string[]; stang: () => void; skapad: (w: Webhook) => void }>) {
  const { text } = useLocale();
  const [url, setUrl] = useState("");
  const [beskrivning, setBeskrivning] = useState("");
  const [alla, setAlla] = useState(true);
  const [valda, setValda] = useState<string[]>([]);
  const [sparar, setSparar] = useState(false);
  const [urlfel, setUrlfel] = useState<Localized | null>(null);
  const [handelsefel, setHandelsefel] = useState<Localized | null>(null);
  const [allmant, setAllmant] = useState<Localized | null>(null);

  useEffect(() => {
    if (!oppen) return;
    setUrl("");
    setBeskrivning("");
    setAlla(true);
    setValda([]);
    setUrlfel(null);
    setHandelsefel(null);
    setAllmant(null);
  }, [oppen]);

  // Händelserna i grupper efter objekt, i API:ts ordning.
  const grupper = useMemo(() => {
    const ut: { objekt: string; koder: string[] }[] = [];
    for (const kod of handelser) {
      const objekt = kod.split(".")[0];
      const grupp = ut.find((g) => g.objekt === objekt);
      if (grupp) grupp.koder.push(kod);
      else ut.push({ objekt, koder: [kod] });
    }
    return ut;
  }, [handelser]);

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    if (sparar) return;
    if (!/^https:\/\//i.test(url.trim())) {
      setUrlfel({ sv: "Adressen ska börja med https://.", en: "The address must start with https://." });
      return;
    }
    if (!alla && valda.length === 0) {
      setHandelsefel(WEBHOOKFEL.invalid_events);
      return;
    }
    setSparar(true);
    setUrlfel(null);
    setHandelsefel(null);
    setAllmant(null);
    try {
      const w = await crmAnrop<Webhook>("/v1/webhooks", {
        method: "POST",
        body: JSON.stringify({ url: url.trim(), events: alla ? ["*"] : valda, ...(beskrivning.trim() ? { description: beskrivning.trim() } : {}) })
      });
      skapad(w);
    } catch (orsak) {
      const kod = orsak instanceof CrmFel ? orsak.kod : null;
      // invalid_url gäller adressen och invalid_events valet; resten säger något om arbetsytan.
      if (kod === "invalid_url") setUrlfel(WEBHOOKFEL.invalid_url);
      else if (kod === "invalid_events") setHandelsefel(WEBHOOKFEL.invalid_events);
      else setAllmant(kod && WEBHOOKFEL[kod] ? WEBHOOKFEL[kod] : orsak instanceof CrmFel ? orsak.text : { sv: "Det gick inte att skapa webhooken.", en: "Could not create the webhook." });
    } finally {
      setSparar(false);
    }
  }

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && stang()} purpose="form" width={600}>
      <Layout
        header={<DialogHeader title={text({ sv: "Ny webhook", en: "New webhook" })} onOpenChange={(o) => !o && stang()} />}
        content={
          <LayoutContent>
            <form id="crm-ny-webhook" onSubmit={spara} noValidate className="flex flex-col gap-6">
              {allmant ? <Banner status="error" container="card" title={text({ sv: "Det gick inte att skapa webhooken", en: "Could not create the webhook" })} description={text(allmant)} /> : null}
              <TextInput
                label={text({ sv: "Adress", en: "Address" })}
                description={text({ sv: "En publik https-adress hos er som tar emot POST-anrop.", en: "A public https address of yours that accepts POST requests." })}
                placeholder="https://"
                type="url"
                value={url}
                onChange={(v) => {
                  setUrl(v);
                  setUrlfel(null);
                }}
                isRequired
                hasAutoFocus
                autoCapitalize="none"
                width="100%"
                status={urlfel ? { type: "error", message: text(urlfel) } : undefined}
              />
              <TextInput
                label={text({ sv: "Beskrivning", en: "Description" })}
                description={text({ sv: "Vad webhooken används till, så att ni känner igen den.", en: "What the webhook is for, so that you recognise it." })}
                value={beskrivning}
                onChange={setBeskrivning}
                isOptional
                width="100%"
              />
              <fieldset className="crm-formgrupp">
                <legend className="mb-3 text-[0.8125rem] font-semibold text-ink-muted">{text({ sv: "Händelser", en: "Events" })}</legend>
                <div className="flex flex-col gap-4">
                  <CheckboxInput
                    label={text({ sv: "Alla händelser", en: "All events" })}
                    description={text({ sv: "Också händelser som läggs till senare.", en: "Including events added later." })}
                    value={alla}
                    onChange={(v) => {
                      setAlla(v);
                      setHandelsefel(null);
                    }}
                  />
                  {!alla ? (
                    <div className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
                      {grupper.map((g) => (
                        <div key={g.objekt} className="flex flex-col gap-2">
                          <span className="text-[0.8125rem] font-semibold text-ink-muted">{OBJEKTORD[g.objekt] ? text(OBJEKTORD[g.objekt]) : g.objekt}</span>
                          {g.koder.map((kod) => (
                            <CheckboxInput
                              key={kod}
                              label={handelsenamn(kod, text)}
                              value={valda.includes(kod)}
                              onChange={(pa) => {
                                setValda((v) => (pa ? [...v, kod] : v.filter((x) => x !== kod)));
                                setHandelsefel(null);
                              }}
                            />
                          ))}
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {handelsefel ? (
                    <p role="status" className="text-[0.8125rem] text-danger">
                      {text(handelsefel)}
                    </p>
                  ) : null}
                </div>
              </fieldset>
            </form>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Avbryt", en: "Cancel" })} variant="ghost" onClick={stang} />
              <Button type="submit" form="crm-ny-webhook" variant="primary" label={text({ sv: "Skapa webhooken", en: "Create webhook" })} isLoading={sparar} />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
