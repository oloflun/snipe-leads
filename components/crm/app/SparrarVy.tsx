"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Ban, CalendarPlus, Globe, Hash, Mail, Phone, Plug, Plus, Radio, SearchCheck, SearchX, ShieldQuestion, Upload, type LucideIcon } from "lucide-react";
import { Banner } from "@astryxdesign/core/Banner";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { List, ListItem } from "@astryxdesign/core/List";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { Selector } from "@astryxdesign/core/Selector";
import { HStack } from "@astryxdesign/core/Stack";
import { Table, pixel, proportional, type TableColumn } from "@astryxdesign/core/Table";
import { Text } from "@astryxdesign/core/Text";
import { TextArea } from "@astryxdesign/core/TextArea";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { useToast } from "@astryxdesign/core/Toast";
import { Kolumnrubrik, Tabellskelett, useBestallning, useSmal, Vyval } from "@/components/crm/app/kit";
import { Felruta, Sida } from "@/components/crm/app/Sida";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { CrmFel, crmAnrop, orgnrVisning, type Sida as Svarssida } from "@/lib/crm/api";
import { FALTKODER, kodtext, uppraknat } from "@/lib/crm/felkoder";
import {
  SLAG_I_KANAL,
  SPARRGRINDAR,
  SPARRKALLOR,
  SPARRKANALER,
  SPARRORSAKER,
  SPARRORSAK_VAD,
  SPARRSLAG,
  gissaSlag,
  type Importsvar,
  type Sparr,
  type Sparrkanal,
  type Sparrkontroll,
  type Sparrorsak,
  type Sparrslag
} from "@/lib/crm/sparr";
import { useLocale, type Localized } from "@/lib/i18n";

type Vy = "alla" | "email" | "phone" | "havda";

const SIDSTORLEK = 100;
/** API:ts tak per anrop i `POST /suppressions/import`. En längre lista skickas i flera omgångar. */
const IMPORTSATS = 10_000;

const SLAGIKON: Record<Sparrslag, LucideIcon> = { email: Mail, domain: Globe, phone: Phone, org_number: Hash };

const feltext = (e: unknown): Localized => (e instanceof CrmFel ? e.text : { sv: "Okänt fel.", en: "Unknown error." });

/** Värdet som det läses: organisationsnumret med sitt streck, resten som det är sparat. */
const visat = (s: Pick<Sparr, "kind" | "value">) => (s.kind === "org_number" ? orgnrVisning(s.value) : s.value);

/**
 * Spärrlistan: adresser, domäner, telefonnummer och organisationsnummer som
 * aldrig ska kontaktas, per kanal (Antons beslut 2026-11-27: en gemensam spärr
 * för alla kanaler). Här läggs en spärr till för hand, en lista laddas upp
 * (till exempel utfallet av den egna NIX-kontrollen) och en spärr hävs.
 *
 * Listan är inte hela sanningen: bolag och personer märkta Kontakta inte,
 * avregistrerade adresser och leads som bett att slippa kontakt spärrar också.
 * Därför finns Kontrollera, som frågar alla källor på en gång
 * (`POST /v1/suppressions/check`) och säger vilken som spärrar.
 */
export function SparrarVy() {
  const { text, locale } = useLocale();
  const visa = useToast();
  const smal = useSmal();
  const sprak = locale === "sv" ? "sv-SE" : "en-GB";
  const tal = useCallback((n: number) => n.toLocaleString(sprak), [sprak]);

  const [vy, setVy] = useState<Vy>("alla");
  const [sok, setSok] = useState("");
  const [fraga, setFraga] = useState("");
  const [rader, setRader] = useState<Sparr[]>([]);
  const [nasta, setNasta] = useState<string | null>(null);
  const [laddar, setLaddar] = useState(true);
  const [laddarFler, setLaddarFler] = useState(false);
  const [fel, setFel] = useState<unknown>(null);
  const [haver, setHaver] = useState<string | null>(null);
  const [dialog, setDialog] = useState<"ny" | "lista" | "senaste" | "kontroll" | null>(null);
  // Senaste uppladdningens utfall står kvar efter en omladdning: det sparas i webbläsaren, per arbetsyta, utan värdena.
  const lage = useDashboard();
  const nyckel = `${SENASTE_NYCKEL}:${lage.impersonation?.slug ?? lage.workspaceName ?? ""}`;
  const [senaste, setSenaste] = useState<Importutfall | null>(null);
  useEffect(() => setSenaste(lasSenaste(nyckel)), [nyckel]);
  const omgang = useRef(0);

  useEffect(() => {
    const t = window.setTimeout(() => setFraga(sok.trim()), 250);
    return () => window.clearTimeout(t);
  }, [sok]);

  const hamta = useCallback(
    async (markor: string | null) => {
      const denna = ++omgang.current;
      if (markor) setLaddarFler(true);
      else setLaddar(true);
      setFel(null);
      const q = new URLSearchParams({ limit: String(SIDSTORLEK) });
      if (vy === "email" || vy === "phone") q.set("channel", vy);
      if (vy === "havda") q.set("include_lifted", "true");
      if (fraga) q.set("q", fraga);
      if (markor) q.set("cursor", markor);
      try {
        const sida = await crmAnrop<Svarssida<Sparr>>(`/v1/suppressions?${q}`);
        if (denna !== omgang.current) return;
        // Vyn Hävda visar bara de hävda: API:t lämnar dem tillsammans med de som gäller.
        const data = vy === "havda" ? sida.data.filter((s) => s.lifted_at) : sida.data.filter((s) => !s.lifted_at);
        setRader((forr) => (markor ? [...forr, ...data] : data));
        setNasta(sida.next_cursor);
      } catch (e) {
        if (denna === omgang.current) setFel(e);
      } finally {
        if (denna === omgang.current) {
          setLaddar(false);
          setLaddarFler(false);
        }
      }
    },
    [vy, fraga]
  );

  useEffect(() => {
    void hamta(null);
  }, [hamta]);

  useBestallning("ny", () => setDialog("ny"));

  async function hav(s: Sparr) {
    if (haver) return;
    setHaver(s.id);
    try {
      await crmAnrop<null>(`/v1/suppressions/${encodeURIComponent(s.id)}`, { method: "DELETE" });
    } catch (e) {
      visa({ type: "error", body: text(feltext(e)), uniqueID: "crm-sparr" });
      setHaver(null);
      return;
    }
    setHaver(null);
    setRader((forr) => forr.filter((r) => r.id !== s.id));
    // Ångra lägger tillbaka samma spärr. Den hävda står kvar under Hävda, som bevis.
    const angra = async () => {
      try {
        await crmAnrop<Sparr>("/v1/suppressions", { method: "POST", body: JSON.stringify({ channel: s.channel, kind: s.kind, value: s.value, reason: s.reason, ...(s.note ? { note: s.note } : {}) }) });
        visa({ body: text({ sv: `${s.value} är spärrad igen.`, en: `${s.value} is blocked again.` }), uniqueID: "crm-sparr" });
      } catch (e) {
        visa({ type: "error", body: text(feltext(e)), uniqueID: "crm-sparr" });
      }
      void hamta(null);
    };
    visa({
      body: text({ sv: `Spärren för ${s.value} är hävd. Den står kvar under Hävda.`, en: `The block for ${s.value} is lifted. It stays under Lifted.` }),
      endContent: <Button size="sm" variant="secondary" label={text({ sv: "Ångra", en: "Undo" })} onClick={() => void angra()} />,
      autoHideDuration: 10000,
      uniqueID: "crm-sparr"
    });
  }

  const havda = vy === "havda";
  const vardecell = useCallback(
    (s: Sparr) => (
      <span className="inline-flex min-w-0 max-w-full items-center gap-2">
        <span className="inline-flex shrink-0 text-ink-muted" title={text(SPARRSLAG[s.kind])}>
          <Icon icon={SLAGIKON[s.kind]} size="sm" color="inherit" />
          <span className="sr-only">{text(SPARRSLAG[s.kind])}</span>
        </span>
        <span className={`min-w-0 truncate text-[0.875rem] font-semibold tabular-nums ${havda ? "text-ink-muted line-through" : "text-ink"}`}>{visat(s)}</span>
      </span>
    ),
    [text, havda]
  );
  const kanalmarke = useCallback((s: Sparr) => <Badge variant={s.channel === "all" ? "error" : "neutral"} label={text(SPARRKANALER[s.channel])} />, [text]);
  const havknapp = (s: Sparr) => (
    <Button size="sm" variant="secondary" label={text({ sv: "Häv", en: "Lift" })} isLoading={haver === s.id} onClick={() => void hav(s)} aria-label={text({ sv: `Häv spärren för ${s.value}`, en: `Lift the block for ${s.value}` })} />
  );

  const kolumner = useMemo<TableColumn<Sparr>[]>(
    () => [
      { key: "value", header: <Kolumnrubrik ikon={Ban}>{text({ sv: "Spärrat", en: "Blocked" })}</Kolumnrubrik>, width: proportional(1, { minWidth: 240 }), renderCell: vardecell },
      { key: "channel", header: <Kolumnrubrik ikon={Radio}>{text({ sv: "Kanal", en: "Channel" })}</Kolumnrubrik>, width: pixel(140), renderCell: kanalmarke },
      {
        key: "reason",
        header: <Kolumnrubrik ikon={ShieldQuestion}>{text({ sv: "Orsak", en: "Reason" })}</Kolumnrubrik>,
        width: pixel(220),
        renderCell: (s) => (
          <span className="flex min-w-0 flex-col">
            <span className="text-ink2">{text(SPARRORSAKER[s.reason])}</span>
            {s.note ? <span className="truncate text-[0.8125rem] text-ink-muted" title={s.note}>{s.note}</span> : null}
          </span>
        )
      },
      {
        key: "source",
        header: <Kolumnrubrik ikon={Plug}>{text({ sv: "Källa", en: "Source" })}</Kolumnrubrik>,
        width: pixel(160),
        renderCell: (s) => <span className="text-ink2">{text(SPARRKALLOR[s.source] ?? { sv: s.source, en: s.source })}</span>
      },
      havda
        ? {
            key: "lifted_at",
            header: <Kolumnrubrik ikon={CalendarPlus}>{text({ sv: "Hävd", en: "Lifted" })}</Kolumnrubrik>,
            width: pixel(160),
            renderCell: (s) => (s.lifted_at ? <Timestamp value={s.lifted_at} format="relative" /> : null)
          }
        : {
            key: "created_at",
            header: <Kolumnrubrik ikon={CalendarPlus}>{text({ sv: "Tillagd", en: "Added" })}</Kolumnrubrik>,
            width: pixel(160),
            renderCell: (s) => (s.created_at ? <Timestamp value={s.created_at} format="relative" /> : null)
          },
      ...(havda
        ? []
        : [
            {
              key: "atgard",
              header: <span className="sr-only">{text({ sv: "Åtgärd", en: "Action" })}</span>,
              width: pixel(96),
              align: "end" as const,
              renderCell: havknapp
            }
          ])
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [text, vardecell, kanalmarke, havda, haver]
  );

  const tomt = fraga ? (
    <EmptyState
      icon={<Icon icon={SearchX} size="lg" color="secondary" />}
      title={text({ sv: `Ingen spärr matchar ”${fraga}”`, en: `No block matches “${fraga}”` })}
      description={text({
        sv: "Sökningen gäller spärrlistan. Kontrollera frågar också bolag, personer, avregistreringar och leads.",
        en: "The search covers the block list. Check also asks companies, people, unsubscribes and leads."
      })}
      actions={<Button label={text({ sv: "Kontrollera en adress", en: "Check an address" })} variant="secondary" onClick={() => setDialog("kontroll")} />}
    />
  ) : havda ? (
    <EmptyState
      icon={<Icon icon={Ban} size="lg" color="secondary" />}
      title={text({ sv: "Ingen hävd spärr", en: "No lifted block" })}
      description={text({ sv: "En spärr som hävs står kvar här, så att det går att visa när den gällde.", en: "A block that is lifted stays here, so it can be shown when it applied." })}
    />
  ) : (
    <EmptyState
      icon={<Icon icon={Ban} size="lg" color="secondary" />}
      title={text({ sv: "Inga spärrar än", en: "No blocks yet" })}
      description={text({
        sv: "Lägg till den som bett att slippa kontakt, eller ladda upp utfallet av er egen NIX-kontroll. En spärr stoppar utskick och ringlistor i den kanal den gäller.",
        en: "Add anyone who has asked not to be contacted, or upload the result of your own NIX check. A block stops mailings and call lists in the channel it covers."
      })}
      actions={
        <HStack gap={2}>
          <Button label={text({ sv: "Ladda upp lista", en: "Upload list" })} variant="secondary" icon={<Icon icon={Upload} size="sm" />} onClick={() => setDialog("lista")} />
          <Button label={text({ sv: "Ny spärr", en: "New block" })} variant="primary" icon={<Icon icon={Plus} size="sm" />} onClick={() => setDialog("ny")} />
        </HStack>
      }
    />
  );

  const fot = (
    <div className="crm-raknefot" role="status">
      <span>
        <span className="crm-raknefot-etikett">{text({ sv: "Visar", en: "Showing" })}</span> <span className="crm-raknefot-tal">{tal(rader.length)}</span>
        {nasta ? <span className="crm-raknefot-etikett">{text({ sv: " och fler", en: " and more" })}</span> : null}
      </span>
      <span className="crm-raknefot-etikett">
        {havda
          ? text({ sv: "En hävd spärr gäller inte längre. Den står kvar som bevis på när den gällde.", en: "A lifted block no longer applies. It stays as proof of when it applied." })
          : text({
              sv: "Kontakta inte på ett bolag eller en person, avregistreringar och leads som bett att slippa kontakt spärrar också. De står på sina poster.",
              en: "Do not contact on a company or person, unsubscribes and leads that asked not to be contacted also block. They are on their records."
            })}
      </span>
      {senaste?.nar && !havda ? (
        <button type="button" className="crm-raknefot-etikett underline decoration-dotted underline-offset-4 hover:decoration-solid" onClick={() => setDialog("senaste")}>
          {text({ sv: "Senaste uppladdningen: ", en: "Latest upload: " })}
          <span className="crm-raknefot-tal">{tal(senaste.tillagda)}</span>
          {text({ sv: " nya", en: " new" })}
          {senaste.ogiltiga.length ? (
            <>
              {", "}
              <span className="crm-raknefot-tal">{tal(senaste.ogiltiga.length)}</span>
              {senaste.ogiltiga.length === 1 ? text({ sv: " oläst rad", en: " unread row" }) : text({ sv: " olästa rader", en: " unread rows" })}
            </>
          ) : null}
        </button>
      ) : null}
      {nasta ? (
        <span className="ml-auto">
          <Button size="sm" variant="secondary" label={text({ sv: "Visa fler", en: "Show more" })} isLoading={laddarFler} onClick={() => void hamta(nasta)} />
        </span>
      ) : null}
    </div>
  );

  const vyer: { v: Vy; namn: string }[] = [
    { v: "alla", namn: text({ sv: "Alla", en: "All" }) },
    { v: "email", namn: text({ sv: "Mejl", en: "Email" }) },
    { v: "phone", namn: text({ sv: "Telefon", en: "Phone" }) },
    { v: "havda", namn: text({ sv: "Hävda", en: "Lifted" }) }
  ];

  return (
    <Sida
      objekt="sparrar"
      rubrik={text({ sv: "Spärrar", en: "Blocks" })}
      antal={laddar && rader.length === 0 ? undefined : `${tal(rader.length)}${nasta ? "+" : ""}`}
      atgarder={
        <>
          {smal ? null : <Button variant="ghost" label={text({ sv: "Kontrollera", en: "Check" })} icon={<Icon icon={SearchCheck} size="sm" />} onClick={() => setDialog("kontroll")} />}
          {smal ? null : <Button variant="secondary" label={text({ sv: "Ladda upp lista", en: "Upload list" })} icon={<Icon icon={Upload} size="sm" />} onClick={() => setDialog("lista")} />}
          <Button variant="primary" label={text({ sv: "Ny spärr", en: "New block" })} icon={<Icon icon={Plus} size="sm" />} onClick={() => setDialog("ny")} />
        </>
      }
      vyrad={
        smal ? (
          <Selector label={text({ sv: "Vy", en: "View" })} isLabelHidden variant="secondary" size="md" value={vy} onChange={(v) => v && setVy(v as Vy)} options={vyer.map((f) => ({ value: f.v, label: f.namn }))} />
        ) : (
          <Vyval value={vy} onChange={setVy} label={text({ sv: "Vy", en: "View" })} val={vyer} />
        )
      }
      vyradHoger={
        <>
          <div className="min-w-0 flex-1 sm:w-[260px] sm:flex-none">
            <TextInput
              type="search"
              label={text({ sv: "Sök spärrar", en: "Search blocks" })}
              isLabelHidden
              placeholder={smal ? text({ sv: "Sök", en: "Search" }) : text({ sv: "Sök adress, nummer eller domän", en: "Search address, number or domain" })}
              startIcon="search"
              hasClear
              value={sok}
              onChange={(v) => setSok(v)}
              width="100%"
              controlClassName="crm-sokfalt"
            />
          </div>
          {smal ? (
            <>
              <Button variant="ghost" size="md" label={text({ sv: "Kontrollera", en: "Check" })} onClick={() => setDialog("kontroll")} />
              <Button variant="ghost" size="md" label={text({ sv: "Lista", en: "List" })} icon={<Icon icon={Upload} size="sm" />} onClick={() => setDialog("lista")} />
            </>
          ) : null}
        </>
      }
    >
      {fel ? (
        <div className="p-4 sm:p-6">
          <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta(null)} />} />
        </div>
      ) : laddar && rader.length === 0 ? (
        <Tabellskelett rader={8} kolumner={smal ? 2 : 5} markering={false} label={text({ sv: "Hämtar spärrarna", en: "Loading the blocks" })} />
      ) : rader.length === 0 ? (
        <div className="py-12">{tomt}</div>
      ) : smal ? (
        <>
          <div className="px-2">
            <List hasDividers density="balanced" edge="padded">
              {rader.map((s) => (
                <ListItem
                  key={s.id}
                  label={<span className={`font-semibold tabular-nums ${havda ? "text-ink-muted line-through" : "text-ink"}`}>{visat(s)}</span>}
                  description={[text(SPARRKANALER[s.channel]), text(SPARRORSAKER[s.reason])].join(" · ")}
                  endContent={havda ? undefined : havknapp(s)}
                />
              ))}
            </List>
          </div>
          {fot}
        </>
      ) : (
        <div className={laddar ? "crm-tabell crm-tabell-utan-val crm-tabell-laddar" : "crm-tabell crm-tabell-utan-val"}>
          <Table<Sparr> data={rader} columns={kolumner} idKey="id" density="balanced" dividers="rows" hasHover textOverflow="truncate" />
          {fot}
        </div>
      )}

      <NySparr oppen={dialog === "ny"} stang={() => setDialog(null)} sparad={() => void hamta(null)} />
      <Listuppladdning
        oppen={dialog === "lista" || dialog === "senaste"}
        visa={dialog === "senaste" ? senaste : null}
        stang={() => setDialog(null)}
        klar={(ut) => {
          setSenaste(sparaSenaste(nyckel, ut));
          if (ut.tillagda > 0) void hamta(null);
        }}
      />
      <Kontroll oppen={dialog === "kontroll"} stang={() => setDialog(null)} />

    </Sida>
  );
}

// ---------------------------------------------------------------------------
// Ny spärr
// ---------------------------------------------------------------------------

function NySparr({ oppen, stang, sparad }: Readonly<{ oppen: boolean; stang: () => void; sparad: () => void }>) {
  const { text } = useLocale();
  const visa = useToast();
  const [kanal, setKanal] = useState<Sparrkanal>("all");
  const [slag, setSlag] = useState<Sparrslag>("email");
  const [varde, setVarde] = useState("");
  const [orsak, setOrsak] = useState<Sparrorsak>("customer_request");
  const [anteckning, setAnteckning] = useState("");
  const [falt, setFalt] = useState<Record<string, Localized>>({});
  const [allmant, setAllmant] = useState<Localized | null>(null);
  const [sparar, setSparar] = useState(false);
  // Slaget följer det som skrivs tills användaren själv valt ett.
  const [slagValt, setSlagValt] = useState(false);

  useEffect(() => {
    if (!oppen) return;
    setKanal("all");
    setSlag("email");
    setVarde("");
    setOrsak("customer_request");
    setAnteckning("");
    setFalt({});
    setAllmant(null);
    setSlagValt(false);
  }, [oppen]);

  const tillatna = SLAG_I_KANAL[kanal];
  const valtSlag = tillatna.includes(slag) ? slag : tillatna[0];
  const status = (k: string) => (falt[k] ? { type: "error" as const, message: text(falt[k]) } : undefined);

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    if (sparar) return;
    if (!varde.trim()) {
      setFalt({ value: { sv: "Skriv det som ska spärras.", en: "Enter what to block." } });
      return;
    }
    setSparar(true);
    setFalt({});
    setAllmant(null);
    try {
      const s = await crmAnrop<Sparr>("/v1/suppressions", {
        method: "POST",
        body: JSON.stringify({ channel: kanal, kind: valtSlag, value: varde.trim(), reason: orsak, ...(anteckning.trim() ? { note: anteckning.trim() } : {}) })
      });
      visa({ body: text({ sv: `${s.value} är spärrad.`, en: `${s.value} is blocked.` }), uniqueID: "crm-sparr" });
      sparad();
      stang();
    } catch (orsakFel) {
      if (orsakFel instanceof CrmFel && orsakFel.falt.length) setFalt(Object.fromEntries(orsakFel.falt.map((f) => [f.field, kodtext(FALTKODER, f.code)])));
      else setAllmant(feltext(orsakFel));
    } finally {
      setSparar(false);
    }
  }

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && stang()} purpose="form" width={560}>
      <Layout
        header={<DialogHeader title={text({ sv: "Ny spärr", en: "New block" })} onOpenChange={(o) => !o && stang()} />}
        content={
          <LayoutContent>
            <form id="crm-sparrformular" onSubmit={spara} noValidate className="flex flex-col gap-4">
              <div role="alert">{allmant ? <Banner status="error" container="card" title={text({ sv: "Det gick inte att spara", en: "Could not save" })} description={text(allmant)} /> : null}</div>
              <TextInput
                label={text({ sv: "Det som ska spärras", en: "What to block" })}
                description={text({ sv: "En e-postadress, en domän, ett telefonnummer eller ett organisationsnummer.", en: "An email address, a domain, a phone number or an organisation number." })}
                value={varde}
                onChange={(v) => {
                  setVarde(v);
                  setFalt((f) => Object.fromEntries(Object.entries(f).filter(([k]) => k !== "value")));
                  if (!slagValt && v.trim()) setSlag(gissaSlag(v));
                }}
                width="100%"
                status={status("value")}
                hasAutoFocus
              />
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Selector
                  label={text({ sv: "Kanal", en: "Channel" })}
                  value={kanal}
                  onChange={(v) => v && setKanal(v as Sparrkanal)}
                  options={(Object.keys(SPARRKANALER) as Sparrkanal[]).map((k) => ({ value: k, label: text(SPARRKANALER[k]) }))}
                  width="100%"
                  status={status("channel")}
                />
                <Selector
                  label={text({ sv: "Slag", en: "Kind" })}
                  value={valtSlag}
                  onChange={(v) => {
                    if (!v) return;
                    setSlag(v as Sparrslag);
                    setSlagValt(true);
                  }}
                  options={tillatna.map((s) => ({ value: s, label: text(SPARRSLAG[s]) }))}
                  width="100%"
                  status={status("kind")}
                />
              </div>
              <Selector
                label={text({ sv: "Orsak", en: "Reason" })}
                description={text(SPARRORSAK_VAD[orsak])}
                value={orsak}
                onChange={(v) => v && setOrsak(v as Sparrorsak)}
                options={(Object.keys(SPARRORSAKER) as Sparrorsak[]).map((o) => ({ value: o, label: text(SPARRORSAKER[o]) }))}
                width="100%"
                status={status("reason")}
              />
              <TextInput
                label={text({ sv: "Anteckning", en: "Note" })}
                description={text({ sv: "Syns bara här. Den skickas aldrig vidare.", en: "Only shown here. It is never passed on." })}
                value={anteckning}
                onChange={setAnteckning}
                width="100%"
                status={status("note")}
                isOptional
              />
            </form>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Avbryt", en: "Cancel" })} variant="ghost" onClick={stang} />
              <Button type="submit" form="crm-sparrformular" variant="primary" label={text({ sv: "Spärra", en: "Block" })} isLoading={sparar} />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Ladda upp en lista (till exempel NIX-utfallet)
// ---------------------------------------------------------------------------

type Importutfall = { tillagda: number; redan: number; ogiltiga: { rad: number; varde: string; kod: string }[]; fel: Localized | null; nar?: string };

const SENASTE_NYCKEL = "snajp.crm.sparrimport";
/** Så många olästa rader sparas med radnummer och skäl. Resten räknas bara. */
const MAX_SPARADE_RADER = 200;

function lasSenaste(nyckel: string): Importutfall | null {
  try {
    const ra = window.localStorage.getItem(nyckel);
    const ut = ra ? (JSON.parse(ra) as Importutfall) : null;
    return ut && typeof ut.tillagda === "number" && Array.isArray(ut.ogiltiga) ? ut : null;
  } catch {
    return null;
  }
}

/** Sparar utfallet utan värdena: radnummer och skäl räcker för att hitta raden i den egna filen. */
function sparaSenaste(nyckel: string, ut: Importutfall): Importutfall {
  const sparat: Importutfall = { ...ut, nar: new Date().toISOString(), ogiltiga: ut.ogiltiga.slice(0, MAX_SPARADE_RADER).map((o) => ({ rad: o.rad, varde: "", kod: o.kod })) };
  try {
    window.localStorage.setItem(nyckel, JSON.stringify(sparat));
  } catch {
    // Utan lagring står utfallet kvar tills sidan laddas om.
  }
  return { ...sparat, ogiltiga: ut.ogiltiga };
}

function Listuppladdning({
  oppen,
  visa,
  stang,
  klar
}: Readonly<{ oppen: boolean; visa: Importutfall | null; stang: () => void; klar: (ut: Importutfall) => void }>) {
  const { text, locale } = useLocale();
  const sprak = locale === "sv" ? "sv-SE" : "en-GB";
  const [kanal, setKanal] = useState<Sparrkanal>("phone");
  const [orsak, setOrsak] = useState<Sparrorsak>("nix");
  const [lista, setLista] = useState("");
  const [forlopp, setForlopp] = useState<{ klara: number; totalt: number } | null>(null);
  const [utfall, setUtfall] = useState<Importutfall | null>(null);
  const valjare = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!oppen) return;
    setKanal("phone");
    setOrsak("nix");
    setLista("");
    setForlopp(null);
    // Öppnad från räknefoten: senaste uppladdningens utfall, inte en ny uppladdning.
    setUtfall(visa);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [oppen]);

  // Ett värde per rad. I en CSV-fil räknas första kolumnen, och en rubrikrad utan siffror och utan @ hoppas över av API:t som ogiltig.
  const varden = useMemo(
    () =>
      lista
        .split(/\r?\n/)
        .map((r) => r.split(/[;,\t]/)[0].trim().replace(/^"|"$/g, ""))
        .filter(Boolean),
    [lista]
  );

  async function lasFil(fil: File) {
    setLista(await fil.text());
    setUtfall(null);
  }

  async function laddaUpp(e: React.FormEvent) {
    e.preventDefault();
    if (forlopp || varden.length === 0) return;
    const ut: Importutfall = { tillagda: 0, redan: 0, ogiltiga: [], fel: null };
    setUtfall(null);
    setForlopp({ klara: 0, totalt: varden.length });
    for (let start = 0; start < varden.length; start += IMPORTSATS) {
      const sats = varden.slice(start, start + IMPORTSATS);
      try {
        const svar = await crmAnrop<Importsvar>("/v1/suppressions/import", { method: "POST", body: JSON.stringify({ channel: kanal, reason: orsak, values: sats }) });
        ut.tillagda += svar.added;
        ut.redan += svar.already_blocked;
        ut.ogiltiga.push(...svar.invalid.map((o) => ({ rad: start + o.index + 1, varde: sats[o.index] ?? "", kod: o.code })));
      } catch (orsakFel) {
        // Det som redan lagts till står kvar: utfallet säger hur långt det kom.
        ut.fel = feltext(orsakFel);
        break;
      }
      setForlopp({ klara: Math.min(start + sats.length, varden.length), totalt: varden.length });
    }
    setForlopp(null);
    setUtfall(ut);
    klar(ut);
  }

  const pagar = forlopp != null;
  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && !pagar && stang()} purpose="form" width={600}>
      <Layout
        header={
          <DialogHeader
            title={visa ? text({ sv: "Senaste uppladdningen", en: "Latest upload" }) : text({ sv: "Ladda upp en lista", en: "Upload a list" })}
            subtitle={
              visa?.nar
                ? new Date(visa.nar).toLocaleString(sprak, { dateStyle: "medium", timeStyle: "short" })
                : text({ sv: "Till exempel utfallet av er egen kontroll mot NIX-registret.", en: "For example the result of your own check against the NIX registry." })
            }
            onOpenChange={(o) => !o && !pagar && stang()}
          />
        }
        content={
          <LayoutContent>
            <form id="crm-sparrlista" onSubmit={laddaUpp} noValidate className="flex flex-col gap-4">
              {utfall ? (
                <div role="status" className="flex flex-col gap-3">
                  <Banner
                    status={utfall.fel ? "error" : utfall.ogiltiga.length ? "warning" : "success"}
                    container="card"
                    title={
                      utfall.fel
                        ? text({ sv: "Uppladdningen avbröts", en: "The upload stopped" })
                        : utfall.ogiltiga.length
                          ? text({ sv: "Listan är inlagd, utom det som inte gick att läsa", en: "The list is in, except what could not be read" })
                          : text({ sv: "Listan är inlagd", en: "The list is in" })
                    }
                    description={
                      [
                        utfall.tillagda === 1 ? text({ sv: "1 ny spärr.", en: "1 new block." }) : text({ sv: `${utfall.tillagda.toLocaleString(sprak)} nya spärrar.`, en: `${utfall.tillagda.toLocaleString(sprak)} new blocks.` }),
                        utfall.redan === 1 ? text({ sv: "1 var redan spärrad.", en: "1 was already blocked." }) : utfall.redan ? text({ sv: `${utfall.redan.toLocaleString(sprak)} var redan spärrade.`, en: `${utfall.redan.toLocaleString(sprak)} were already blocked.` }) : "",
                        utfall.ogiltiga.length === 1
                          ? text({ sv: "1 rad gick inte att läsa.", en: "1 row could not be read." })
                          : utfall.ogiltiga.length
                            ? text({ sv: `${utfall.ogiltiga.length.toLocaleString(sprak)} rader gick inte att läsa.`, en: `${utfall.ogiltiga.length.toLocaleString(sprak)} rows could not be read.` })
                            : "",
                        utfall.fel ? text(utfall.fel) : ""
                      ]
                        .filter(Boolean)
                        .join(" ")
                    }
                  />
                  {utfall.ogiltiga.length ? (
                    <div className="flex flex-col gap-1">
                      <Text type="label" color="secondary" weight="medium">
                        {text({ sv: "Rader som inte gick att läsa", en: "Rows that could not be read" })}
                      </Text>
                      <ul className="flex flex-col">
                        {utfall.ogiltiga.slice(0, 20).map((o) => (
                          <li key={o.rad} className="crm-filrad flex items-baseline gap-3 py-2 text-[0.875rem]">
                            <span className="w-16 shrink-0 tabular-nums text-ink-muted">{text({ sv: `Rad ${o.rad}`, en: `Row ${o.rad}` })}</span>
                            {o.varde ? <code className="crm-kod min-w-0 truncate">{o.varde}</code> : null}
                            <span className="ml-auto shrink-0 text-ink-muted">{text(kodtext(FALTKODER, o.kod))}</span>
                          </li>
                        ))}
                      </ul>
                      {utfall.ogiltiga.length > 20 ? (
                        <Text type="supporting" color="secondary">
                          {text({ sv: `Och ${(utfall.ogiltiga.length - 20).toLocaleString(sprak)} till.`, en: `And ${(utfall.ogiltiga.length - 20).toLocaleString(sprak)} more.` })}
                        </Text>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <Selector
                      label={text({ sv: "Kanal", en: "Channel" })}
                      value={kanal}
                      onChange={(v) => v && setKanal(v as Sparrkanal)}
                      options={(Object.keys(SPARRKANALER) as Sparrkanal[]).map((k) => ({ value: k, label: text(SPARRKANALER[k]) }))}
                      width="100%"
                      isDisabled={pagar}
                    />
                    <Selector
                      label={text({ sv: "Orsak", en: "Reason" })}
                      value={orsak}
                      onChange={(v) => v && setOrsak(v as Sparrorsak)}
                      options={(Object.keys(SPARRORSAKER) as Sparrorsak[]).map((o) => ({ value: o, label: text(SPARRORSAKER[o]) }))}
                      width="100%"
                      isDisabled={pagar}
                    />
                  </div>
                  <TextArea
                    label={text({ sv: "Värden, ett per rad", en: "Values, one per row" })}
                    description={text({
                      sv: "Klistra in, eller välj en textfil eller CSV-fil. Ur en CSV-fil läses första kolumnen.",
                      en: "Paste, or choose a text or CSV file. From a CSV file the first column is read."
                    })}
                    rows={8}
                    value={lista}
                    onChange={setLista}
                    width="100%"
                    isDisabled={pagar}
                  />
                  <input
                    ref={valjare}
                    type="file"
                    accept=".txt,.csv,text/plain,text/csv"
                    className="sr-only"
                    tabIndex={-1}
                    aria-hidden
                    onChange={(e) => {
                      const fil = e.target.files?.[0];
                      e.target.value = "";
                      if (fil) void lasFil(fil);
                    }}
                  />
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <Button size="sm" variant="secondary" label={text({ sv: "Välj fil", en: "Choose file" })} icon={<Icon icon={Upload} size="sm" />} isDisabled={pagar} onClick={() => valjare.current?.click()} />
                    <Text type="supporting" color="secondary">
                      <span className="tabular-nums">{text({ sv: `${varden.length.toLocaleString(sprak)} värden`, en: `${varden.length.toLocaleString(sprak)} values` })}</span>
                    </Text>
                  </div>
                  {forlopp ? (
                    <div className="flex flex-col gap-2" role="status" aria-live="polite">
                      <Text type="supporting" color="secondary">
                        <span className="tabular-nums">
                          {text({ sv: `Lägger in ${forlopp.klara.toLocaleString(sprak)} av ${forlopp.totalt.toLocaleString(sprak)}`, en: `Adding ${forlopp.klara.toLocaleString(sprak)} of ${forlopp.totalt.toLocaleString(sprak)}` })}
                        </span>
                      </Text>
                      <ProgressBar label={text({ sv: "Förlopp", en: "Progress" })} isLabelHidden value={forlopp.klara} max={forlopp.totalt} />
                    </div>
                  ) : null}
                </>
              )}
            </form>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              {utfall ? (
                <Button variant="primary" label={text({ sv: "Klar", en: "Done" })} onClick={stang} />
              ) : (
                <>
                  <Button label={text({ sv: "Avbryt", en: "Cancel" })} variant="ghost" isDisabled={pagar} onClick={stang} />
                  <Button
                    type="submit"
                    form="crm-sparrlista"
                    variant="primary"
                    isDisabled={varden.length === 0}
                    isLoading={pagar}
                    label={
                      varden.length === 1
                        ? text({ sv: "Lägg in 1 spärr", en: "Add 1 block" })
                        : text({ sv: `Lägg in ${varden.length.toLocaleString(sprak)} spärrar`, en: `Add ${varden.length.toLocaleString(sprak)} blocks` })
                    }
                  />
                </>
              )}
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Kontrollera: frågar alla källor på en gång
// ---------------------------------------------------------------------------

function Kontroll({ oppen, stang }: Readonly<{ oppen: boolean; stang: () => void }>) {
  const { text, locale } = useLocale();
  const [varde, setVarde] = useState("");
  const [kanal, setKanal] = useState<Sparrkanal>("all");
  const [svar, setSvar] = useState<{ fraga: string; kontroll: Sparrkontroll; traffar: Sparr[] } | null>(null);
  const [fel, setFel] = useState<Localized | null>(null);
  const [fragar, setFragar] = useState(false);

  useEffect(() => {
    if (!oppen) return;
    setVarde("");
    setKanal("all");
    setSvar(null);
    setFel(null);
  }, [oppen]);

  async function kontrollera(e: React.FormEvent) {
    e.preventDefault();
    const v = varde.trim();
    if (!v || fragar) return;
    const slag = gissaSlag(v);
    if (slag === "domain") {
      setFel({ sv: "Skriv en e-postadress, ett telefonnummer eller ett organisationsnummer.", en: "Enter an email address, a phone number or an organisation number." });
      return;
    }
    setFragar(true);
    setFel(null);
    try {
      const kontroll = await crmAnrop<Sparrkontroll>("/v1/suppressions/check", {
        method: "POST",
        body: JSON.stringify({ channel: kanal, ...(slag === "email" ? { email: v } : slag === "phone" ? { phone: v } : { org_number: v }) })
      });
      // Spärrlistans träffar hämtas, så att svaret kan säga vilken spärr det är (till exempel en hel domän).
      // Listan söks på domänen eller på numrets siffror utan inledande nolla och landskod, och träffarna väljs på id.
      const id = new Set(kontroll.suppression_ids ?? []);
      let traffar: Sparr[] = [];
      if (id.size) {
        const siffror = v.replace(/\D/g, "");
        const sokord = slag === "email" ? (v.split("@")[1] ?? v).toLowerCase() : slag === "phone" ? siffror.replace(/^(0046|46|0)/, "") : siffror;
        const sida = await crmAnrop<Svarssida<Sparr>>(`/v1/suppressions?limit=100&q=${encodeURIComponent(sokord)}`).catch(() => null);
        traffar = (sida?.data ?? []).filter((s) => id.has(s.id));
      }
      setSvar({ fraga: v, kontroll, traffar });
    } catch (orsak) {
      setSvar(null);
      setFel(orsak instanceof CrmFel && orsak.falt.length ? kodtext(FALTKODER, orsak.falt[0].code) : feltext(orsak));
    } finally {
      setFragar(false);
    }
  }

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && stang()} purpose="form" width={520}>
      <Layout
        header={
          <DialogHeader
            title={text({ sv: "Får den kontaktas?", en: "May it be contacted?" })}
            subtitle={text({ sv: "Frågar spärrlistan, bolag och personer, avregistreringar och leads på en gång.", en: "Asks the block list, companies and people, unsubscribes and leads at once." })}
            onOpenChange={(o) => !o && stang()}
          />
        }
        content={
          <LayoutContent>
            <form id="crm-sparrkontroll" onSubmit={kontrollera} noValidate className="flex flex-col gap-4">
              <TextInput
                label={text({ sv: "Adress, nummer eller organisationsnummer", en: "Address, number or organisation number" })}
                value={varde}
                onChange={(v) => {
                  setVarde(v);
                  setFel(null);
                }}
                width="100%"
                status={fel ? { type: "error", message: text(fel) } : undefined}
                hasAutoFocus
              />
              <Selector
                label={text({ sv: "Kanal", en: "Channel" })}
                value={kanal}
                onChange={(v) => v && setKanal(v as Sparrkanal)}
                options={(Object.keys(SPARRKANALER) as Sparrkanal[]).map((k) => ({ value: k, label: text(SPARRKANALER[k]) }))}
                width="100%"
              />
              <div role="status">
                {svar ? (
                  svar.kontroll.blocked ? (
                    <Banner
                      status="error"
                      container="card"
                      title={text({ sv: `${svar.fraga} är spärrad`, en: `${svar.fraga} is blocked` })}
                      description={[
                        text({
                          sv: `Det som spärrar: ${uppraknat(svar.kontroll.sources.map((k) => text(SPARRGRINDAR[k] ?? { sv: k, en: k })), "och")}.`,
                          en: `What blocks: ${uppraknat(svar.kontroll.sources.map((k) => text(SPARRGRINDAR[k] ?? { sv: k, en: k })), "and")}.`
                        }),
                        ...svar.traffar.map((s) => `${text(SPARRSLAG[s.kind])} ${visat(s)}, ${text(SPARRKANALER[s.channel]).toLocaleLowerCase(locale)}, ${text(SPARRORSAKER[s.reason]).toLocaleLowerCase(locale)}.`)
                      ].join(" ")}
                    />
                  ) : (
                    <Banner
                      status="success"
                      container="card"
                      title={text({ sv: `${svar.fraga} är inte spärrad`, en: `${svar.fraga} is not blocked` })}
                      description={text({ sv: "Ingen källa i Snajp spärrar den i den kanalen.", en: "No source in Snajp blocks it in that channel." })}
                    />
                  )
                ) : null}
              </div>
            </form>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Stäng", en: "Close" })} variant="ghost" onClick={stang} />
              <Button type="submit" form="crm-sparrkontroll" variant="primary" label={text({ sv: "Kontrollera", en: "Check" })} isLoading={fragar} />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
