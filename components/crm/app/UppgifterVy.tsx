"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CalendarClock, CalendarX2, CheckCheck, Handshake, Link2, ListTodo, MoreHorizontal, Pencil, Plus, SearchX, Trash2, UserRound } from "lucide-react";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import type { ISODateString } from "@astryxdesign/core/Calendar";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { DateInput } from "@astryxdesign/core/DateInput";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { DropdownMenu } from "@astryxdesign/core/DropdownMenu";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { Selector } from "@astryxdesign/core/Selector";
import { HStack } from "@astryxdesign/core/Stack";
import { Table, pixel, proportional, type TableColumn } from "@astryxdesign/core/Table";
import { TextArea } from "@astryxdesign/core/TextArea";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { useToast } from "@astryxdesign/core/Toast";
import { Kolumnrubrik, Objektikon, Personchip, Postchip, Tabellskelett, useBestallning, useSmal, Vyval } from "@/components/crm/app/kit";
import { Felruta, Sida } from "@/components/crm/app/Sida";
import { CrmFel, crmAnrop, dagtext, idagLokalt, type Bolag, type Person, type Sida as Svarssida } from "@/lib/crm/api";
import type { Affar } from "@/lib/crm/affar";
import { FALT, FALTKODER, kodtext } from "@/lib/crm/felkoder";
import { dagSomTid, lokalDag, type Uppgift } from "@/lib/crm/uppgift";
import { useLocale, type Localized } from "@/lib/i18n";

type Vy = "oppna" | "forsenade" | "klara";

const SIDSTORLEK = 100;
/** Selectorns värde för "inget valt"; skickas som `null`. */
const INGET = "inget";

const feltext = (e: unknown): Localized => (e instanceof CrmFel ? e.text : { sv: "Okänt fel.", en: "Unknown error." });
const isodag = (v: string): ISODateString | undefined => (/^\d{4}-\d{2}-\d{2}$/.test(v) ? (v as ISODateString) : undefined);

/** Förfallodagen först, uppgifter utan dag sist. Samma ordning som API:ts `sort=due`. */
const efterDag = (a: Uppgift, b: Uppgift) => (a.due_at ?? "9999").localeCompare(b.due_at ?? "9999");

/**
 * Namnen på bolagen, personerna och affärerna som uppgifterna hör till.
 * Uppgiften bär bara id:n: varje post hämtas en gång och blir kvar medan vyn lever.
 */
function useNamn(rader: Uppgift[]) {
  const [namn, setNamn] = useState<Record<string, string>>({});
  const fragade = useRef(new Set<string>());
  useEffect(() => {
    const behov: [string, string, (svar: unknown) => string | null][] = [];
    for (const u of rader) {
      if (u.company_id) behov.push([`b:${u.company_id}`, `/v1/companies/${encodeURIComponent(u.company_id)}`, (s) => (s as Bolag).name ?? null]);
      if (u.person_id)
        behov.push([`p:${u.person_id}`, `/v1/people/${encodeURIComponent(u.person_id)}`, (s) => [(s as Person).first_name, (s as Person).last_name].filter(Boolean).join(" ") || null]);
      if (u.deal_id) behov.push([`a:${u.deal_id}`, `/v1/deals/${encodeURIComponent(u.deal_id)}`, (s) => (s as Affar).name ?? null]);
    }
    for (const [nyckel, vag, las] of behov) {
      if (fragade.current.has(nyckel) || fragade.current.size > 600) continue;
      fragade.current.add(nyckel);
      crmAnrop<unknown>(vag)
        .then((svar) => {
          const n = las(svar);
          if (n) setNamn((forr) => ({ ...forr, [nyckel]: n }));
        })
        .catch(() => undefined);
    }
  }, [rader]);
  return namn;
}

/**
 * Alla uppgifter på ett ställe, oavsett vilken post de hör till. Samma
 * uppgifter som står under Att göra i bolagets, personens och affärens panel
 * (`/v1/tasks`): här bockas de av, flyttas i tid och läggs till utan att
 * posten först öppnas.
 *
 * Vyerna: Att göra (förfallodag först), Försenade (förfallodagen har passerat)
 * och Klara (senast avbockad först). `?ny=1` öppnar dialogen.
 */
export function UppgifterVy({ bas = "/crm" }: Readonly<{ bas?: string }>) {
  const { text, locale } = useLocale();
  const visa = useToast();
  const smal = useSmal();
  const sprak = locale === "sv" ? "sv-SE" : "en-GB";
  const tal = useCallback((n: number) => n.toLocaleString(sprak), [sprak]);

  const [vy, setVy] = useState<Vy>("oppna");
  const [sok, setSok] = useState("");
  const [fraga, setFraga] = useState("");
  const [rader, setRader] = useState<Uppgift[]>([]);
  const [nasta, setNasta] = useState<string | null>(null);
  const [laddar, setLaddar] = useState(true);
  const [laddarFler, setLaddarFler] = useState(false);
  const [fel, setFel] = useState<unknown>(null);
  const [formular, setFormular] = useState<{ uppgift: Uppgift | null } | null>(null);
  const omgang = useRef(0);
  const namn = useNamn(rader);
  const idag = idagLokalt();

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
      const q = new URLSearchParams({ limit: String(SIDSTORLEK), status: vy === "klara" ? "done" : "todo", sort: vy === "klara" ? "-updated" : "due" });
      // Försenad är en uppgift vars dag har passerat: en uppgift som förfaller i dag är inte sen förrän i morgon.
      if (vy === "forsenade") q.set("due_before", new Date(`${idagLokalt()}T00:00:00`).toISOString());
      if (fraga) q.set("q", fraga);
      if (markor) q.set("cursor", markor);
      try {
        const [sida, pagaende] = await Promise.all([
          crmAnrop<Svarssida<Uppgift>>(`/v1/tasks?${q}`),
          // Påbörjade uppgifter (sätts över API:t, inte i appen) hör också till det som ska göras. De är få: en sida räcker.
          vy !== "klara" && !markor
            ? crmAnrop<Svarssida<Uppgift>>(`/v1/tasks?${new URLSearchParams({ ...Object.fromEntries(q), status: "in_progress" })}`).catch(() => null)
            : Promise.resolve(null)
        ]);
        if (denna !== omgang.current) return;
        const nya = pagaende?.data.length ? [...sida.data, ...pagaende.data].sort(efterDag) : sida.data;
        setRader((forr) => (markor ? [...forr, ...nya] : nya));
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

  useBestallning("ny", () => setFormular({ uppgift: null }));

  /** Bockar av eller öppnar igen. Raden lämnar vyn direkt, och kommer tillbaka om API:t säger nej. */
  async function bocka(u: Uppgift, klar: boolean, tyst = false) {
    setRader((forr) => forr.filter((r) => r.id !== u.id));
    try {
      await crmAnrop<Uppgift>(`/v1/tasks/${encodeURIComponent(u.id)}`, { method: "PATCH", body: JSON.stringify({ status: klar ? "done" : "todo" }) });
    } catch (e) {
      visa({ type: "error", body: text(feltext(e)), uniqueID: "crm-uppgift" });
      void hamta(null);
      return;
    }
    if (tyst) return void hamta(null);
    visa({
      body: klar ? text({ sv: `Klar: ${u.title ?? "uppgiften"}`, en: `Done: ${u.title ?? "the task"}` }) : text({ sv: `Öppnad igen: ${u.title ?? "uppgiften"}`, en: `Reopened: ${u.title ?? "the task"}` }),
      endContent: <Button size="sm" variant="secondary" label={text({ sv: "Ångra", en: "Undo" })} onClick={() => void bocka(u, !klar, true)} />,
      autoHideDuration: 8000,
      uniqueID: "crm-uppgift"
    });
  }

  async function taBort(u: Uppgift) {
    try {
      await crmAnrop<null>(`/v1/tasks/${encodeURIComponent(u.id)}`, { method: "DELETE" });
    } catch (e) {
      visa({ type: "error", body: text(feltext(e)), uniqueID: "crm-uppgift" });
      return;
    }
    setRader((forr) => forr.filter((r) => r.id !== u.id));
    const angra = async () => {
      try {
        await crmAnrop<Uppgift>(`/v1/tasks/${encodeURIComponent(u.id)}/restore`, { method: "POST" });
      } catch (e) {
        visa({ type: "error", body: text(feltext(e)), uniqueID: "crm-uppgift" });
      }
      void hamta(null);
    };
    visa({
      body: text({ sv: `Borttagen: ${u.title ?? "uppgiften"}`, en: `Deleted: ${u.title ?? "the task"}` }),
      endContent: <Button size="sm" variant="secondary" label={text({ sv: "Ångra", en: "Undo" })} onClick={() => void angra()} />,
      autoHideDuration: 10000,
      uniqueID: "crm-uppgift"
    });
  }

  const klara = vy === "klara";

  const bock = (u: Uppgift) => (
    <CheckboxInput
      label={klara ? text({ sv: `Öppna igen: ${u.title ?? "uppgiften"}`, en: `Reopen: ${u.title ?? "the task"}` }) : text({ sv: `Klar: ${u.title ?? "uppgiften"}`, en: `Done: ${u.title ?? "the task"}` })}
      isLabelHidden
      value={klara}
      onChange={(v) => void bocka(u, v)}
    />
  );

  const titel = (u: Uppgift) => (
    <span className="flex min-w-0 flex-col items-start">
      <button
        type="button"
        className={`max-w-full truncate text-left text-[0.875rem] font-semibold underline-offset-2 hover:underline ${klara ? "text-ink-muted line-through" : "text-ink"}`}
        onClick={() => setFormular({ uppgift: u })}
      >
        {u.title ?? text({ sv: "Utan titel", en: "Untitled" })}
      </button>
      {u.description ? <span className="max-w-full truncate text-[0.8125rem] text-ink-muted">{u.description}</span> : null}
    </span>
  );

  /** Posterna uppgiften hör till: bolaget eller personen, och affären. Namnet hämtas för sig, så länge står en neutral text. */
  const hor = (u: Uppgift, bryt = false) => {
    const affar = u.deal_id ? (
      <a href={`${bas}/affarer?affar=${encodeURIComponent(u.deal_id)}`} className="crm-chip inline-flex h-7 min-w-0 max-w-full items-center gap-2 rounded-[6px] pl-1 pr-2">
        <Objektikon ikon={Handshake} ton="sigill" storlek={20} />
        <span className="min-w-0 truncate text-[0.875rem] text-ink2">{namn[`a:${u.deal_id}`] ?? text({ sv: "Affär", en: "Deal" })}</span>
      </a>
    ) : null;
    const post = u.company_id ? (
      <Postchip namn={namn[`b:${u.company_id}`] ?? text({ sv: "Bolag", en: "Company" })} href={`${bas}/bolag?bolag=${encodeURIComponent(u.company_id)}`} vikt="lugn" />
    ) : u.person_id ? (
      <Personchip namn={namn[`p:${u.person_id}`] ?? text({ sv: "Person", en: "Person" })} href={`${bas}/personer?person=${encodeURIComponent(u.person_id)}`} vikt="lugn" />
    ) : null;
    if (!post && !affar) return <span className="text-ink-muted">{text({ sv: "Fristående", en: "Standalone" })}</span>;
    return (
      <span className={bryt ? "flex min-w-0 max-w-full flex-wrap items-center gap-1" : "flex w-full min-w-0 items-center gap-1"}>
        {post}
        {affar}
      </span>
    );
  };

  const forfaller = (u: Uppgift) => {
    if (!u.due_at) return <span className="text-ink-muted">{text({ sv: "Ingen dag", en: "No date" })}</span>;
    const dag = lokalDag(u.due_at);
    const sen = dag < idag;
    return (
      <span className={`inline-flex items-center gap-1.5 tabular-nums ${sen ? "text-danger" : dag === idag ? "font-semibold text-ink" : "text-ink2"}`}>
        {/* Ett passerat datum har en egen ikon: färgen ensam bär inte betydelsen. */}
        <Icon icon={sen ? CalendarX2 : CalendarClock} size="xsm" color="inherit" />
        <span>{dag === idag ? text({ sv: "I dag", en: "Today" }) : dagtext(dag, locale, true)}</span>
        {sen ? <span className="sr-only">{text({ sv: ", har passerat", en: ", has passed" })}</span> : null}
      </span>
    );
  };

  const meny = (u: Uppgift) => (
    <DropdownMenu
      renderTrigger={(props) => (
        <IconButton
          {...props}
          size="sm"
          variant="ghost"
          icon={<Icon icon={MoreHorizontal} size="sm" />}
          label={text({ sv: `Åtgärder för ${u.title ?? "uppgiften"}`, en: `Actions for ${u.title ?? "the task"}` })}
        />
      )}
      items={[
        { label: text({ sv: "Ändra", en: "Edit" }), icon: <Icon icon={Pencil} size="sm" />, onClick: () => setFormular({ uppgift: u }) },
        { label: text({ sv: "Ta bort", en: "Delete" }), icon: <Icon icon={Trash2} size="sm" />, onClick: () => void taBort(u) }
      ]}
    />
  );

  const kolumner = useMemo<TableColumn<Uppgift>[]>(
    () => [
      { key: "bock", header: <span className="sr-only">{text({ sv: "Klar", en: "Done" })}</span>, width: pixel(48), renderCell: bock },
      { key: "title", header: <Kolumnrubrik ikon={ListTodo}>{text({ sv: "Uppgift", en: "Task" })}</Kolumnrubrik>, width: proportional(1.3, { minWidth: 260 }), renderCell: titel },
      { key: "hor", header: <Kolumnrubrik ikon={Link2}>{text({ sv: "Hör till", en: "Belongs to" })}</Kolumnrubrik>, width: proportional(1, { minWidth: 220 }), renderCell: (u) => hor(u) },
      klara
        ? {
            key: "completed_at",
            header: <Kolumnrubrik ikon={CheckCheck}>{text({ sv: "Klar", en: "Done" })}</Kolumnrubrik>,
            width: pixel(160),
            renderCell: (u) => (u.completed_at ? <Timestamp value={u.completed_at} format="relative" /> : null)
          }
        : { key: "due_at", header: <Kolumnrubrik ikon={CalendarClock}>{text({ sv: "Förfaller", en: "Due" })}</Kolumnrubrik>, width: pixel(150), renderCell: forfaller },
      {
        key: "owner",
        header: <Kolumnrubrik ikon={UserRound}>{text({ sv: "Ansvarig", en: "Owner" })}</Kolumnrubrik>,
        width: pixel(170),
        renderCell: (u) => (u.owner ? <Personchip namn={u.owner} vikt="lugn" /> : null)
      },
      { key: "meny", header: <span className="sr-only">{text({ sv: "Åtgärder", en: "Actions" })}</span>, width: pixel(72), align: "end" as const, renderCell: meny }
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [text, locale, klara, namn, idag, bas]
  );

  const tomt = fraga ? (
    <EmptyState icon={<Icon icon={SearchX} size="lg" color="secondary" />} title={text({ sv: `Ingen uppgift matchar ”${fraga}”`, en: `No task matches “${fraga}”` })} />
  ) : vy === "forsenade" ? (
    <EmptyState
      icon={<Icon icon={CheckCheck} size="lg" color="secondary" />}
      title={text({ sv: "Inget är försenat", en: "Nothing is overdue" })}
      description={text({ sv: "Här hamnar uppgifter vars dag har passerat.", en: "Tasks whose date has passed end up here." })}
    />
  ) : klara ? (
    <EmptyState icon={<Icon icon={CheckCheck} size="lg" color="secondary" />} title={text({ sv: "Inga klara uppgifter än", en: "No finished tasks yet" })} />
  ) : (
    <EmptyState
      icon={<Icon icon={ListTodo} size="lg" color="secondary" />}
      title={text({ sv: "Inget att göra just nu", en: "Nothing to do right now" })}
      description={text({
        sv: "En uppgift läggs till här, eller på ett bolag, en person eller en affär under Historik.",
        en: "A task is added here, or on a company, a person or a deal under History."
      })}
      actions={<Button label={text({ sv: "Ny uppgift", en: "New task" })} variant="primary" icon={<Icon icon={Plus} size="sm" />} onClick={() => setFormular({ uppgift: null })} />}
    />
  );

  const fot = (
    <div className="crm-raknefot" role="status">
      <span>
        <span className="crm-raknefot-etikett">{text({ sv: "Visar", en: "Showing" })}</span> <span className="crm-raknefot-tal">{tal(rader.length)}</span>
        {nasta ? <span className="crm-raknefot-etikett">{text({ sv: " och fler", en: " and more" })}</span> : null}
      </span>
      {nasta ? (
        <span className="ml-auto">
          <Button size="sm" variant="secondary" label={text({ sv: "Visa fler", en: "Show more" })} isLoading={laddarFler} onClick={() => void hamta(nasta)} />
        </span>
      ) : null}
    </div>
  );

  const vyer: { v: Vy; namn: string }[] = [
    { v: "oppna", namn: text({ sv: "Att göra", en: "To do" }) },
    { v: "forsenade", namn: text({ sv: "Försenade", en: "Overdue" }) },
    { v: "klara", namn: text({ sv: "Klara", en: "Done" }) }
  ];

  return (
    <Sida
      objekt="uppgifter"
      rubrik={text({ sv: "Uppgifter", en: "Tasks" })}
      antal={laddar && rader.length === 0 ? undefined : `${tal(rader.length)}${nasta ? "+" : ""}`}
      atgarder={<Button variant="primary" label={text({ sv: "Ny uppgift", en: "New task" })} icon={<Icon icon={Plus} size="sm" />} onClick={() => setFormular({ uppgift: null })} />}
      vyrad={
        smal ? (
          <Selector label={text({ sv: "Vy", en: "View" })} isLabelHidden variant="secondary" size="md" value={vy} onChange={(v) => v && setVy(v as Vy)} options={vyer.map((f) => ({ value: f.v, label: f.namn }))} />
        ) : (
          <Vyval value={vy} onChange={setVy} label={text({ sv: "Vy", en: "View" })} val={vyer} />
        )
      }
      vyradHoger={
        <div className="min-w-0 flex-1 sm:w-[260px] sm:flex-none">
          <TextInput
            type="search"
            label={text({ sv: "Sök uppgifter", en: "Search tasks" })}
            isLabelHidden
            placeholder={text({ sv: "Sök", en: "Search" })}
            startIcon="search"
            hasClear
            value={sok}
            onChange={(v) => setSok(v)}
            width="100%"
            controlClassName="crm-sokfalt"
          />
        </div>
      }
    >
      {fel ? (
        <div className="p-4 sm:p-6">
          <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta(null)} />} />
        </div>
      ) : laddar && rader.length === 0 ? (
        <Tabellskelett rader={8} kolumner={smal ? 2 : 5} markering={false} label={text({ sv: "Hämtar uppgifterna", en: "Loading the tasks" })} />
      ) : rader.length === 0 ? (
        <div className="py-12">{tomt}</div>
      ) : smal ? (
        <>
          <ul className="flex flex-col px-4">
            {rader.map((u) => (
              <li key={u.id} className="crm-filrad flex items-start gap-3 py-3">
                <span className="pt-0.5">{bock(u)}</span>
                <span className="flex min-w-0 flex-1 flex-col gap-1">
                  {titel(u)}
                  <span className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 text-[0.8125rem]">
                    {klara ? u.completed_at ? <Timestamp value={u.completed_at} format="relative" /> : null : forfaller(u)}
                    {u.company_id || u.person_id || u.deal_id ? hor(u, true) : null}
                  </span>
                </span>
                {meny(u)}
              </li>
            ))}
          </ul>
          {fot}
        </>
      ) : (
        <div className={laddar ? "crm-tabell crm-tabell-utan-val crm-tabell-laddar" : "crm-tabell crm-tabell-utan-val"}>
          <Table<Uppgift> data={rader} columns={kolumner} idKey="id" density="balanced" dividers="rows" hasHover textOverflow="truncate" />
          {fot}
        </div>
      )}

      <Uppgiftsformular
        lage={formular}
        bolagsnamn={formular?.uppgift?.company_id ? (namn[`b:${formular.uppgift.company_id}`] ?? null) : null}
        stang={() => setFormular(null)}
        sparad={(u, ny) => {
          setFormular(null);
          visa({ body: ny ? text({ sv: `Tillagd: ${u.title ?? "uppgiften"}`, en: `Added: ${u.title ?? "the task"}` }) : text({ sv: "Uppgiften är sparad.", en: "The task is saved." }), uniqueID: "crm-uppgift" });
          void hamta(null);
        }}
      />
    </Sida>
  );
}

// ---------------------------------------------------------------------------
// Ny uppgift och Ändra
// ---------------------------------------------------------------------------

function Uppgiftsformular({
  lage,
  bolagsnamn,
  stang,
  sparad
}: Readonly<{ lage: { uppgift: Uppgift | null } | null; bolagsnamn: string | null; stang: () => void; sparad: (u: Uppgift, ny: boolean) => void }>) {
  const { text } = useLocale();
  const uppgift = lage?.uppgift ?? null;
  const [titel, setTitel] = useState("");
  const [beskrivning, setBeskrivning] = useState("");
  const [dag, setDag] = useState("");
  const [ansvarig, setAnsvarig] = useState("");
  const [bolagId, setBolagId] = useState(INGET);
  const [bolag, setBolag] = useState<{ id: string; namn: string }[]>([]);
  const [falt, setFalt] = useState<Record<string, Localized>>({});
  const [allmant, setAllmant] = useState<Localized | null>(null);
  const [sparar, setSparar] = useState(false);
  const oppen = lage != null;

  useEffect(() => {
    if (!oppen) return;
    setTitel(uppgift?.title ?? "");
    setBeskrivning(uppgift?.description ?? "");
    setDag(uppgift?.due_at ? lokalDag(uppgift.due_at) : "");
    setAnsvarig(uppgift?.owner ?? "");
    setBolagId(uppgift?.company_id ?? INGET);
    setFalt({});
    setAllmant(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [oppen, uppgift?.id]);

  // Bolagen att välja bland: de 500 första i namnordning, hämtade första gången dialogen öppnas.
  const hamtat = useRef(false);
  useEffect(() => {
    if (!oppen || hamtat.current) return;
    hamtat.current = true;
    crmAnrop<Svarssida<Bolag>>("/v1/companies?limit=500&sort=name")
      .then((svar) => setBolag(svar.data.map((b) => ({ id: b.id, namn: b.name ?? "" })).filter((b) => b.namn)))
      .catch(() => (hamtat.current = false));
  }, [oppen]);

  const status = (k: string) => (falt[k] ? { type: "error" as const, message: text(falt[k]) } : undefined);

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    if (sparar) return;
    if (!titel.trim()) {
      setFalt({ title: { sv: "Skriv vad som ska göras.", en: "Write what is to be done." } });
      return;
    }
    setSparar(true);
    setFalt({});
    setAllmant(null);
    const kropp = {
      title: titel.trim(),
      description: beskrivning.trim() || null,
      due_at: dag ? dagSomTid(dag) : null,
      owner: ansvarig.trim() || null,
      company_id: bolagId === INGET ? null : bolagId
    };
    try {
      const svar = uppgift
        ? await crmAnrop<Uppgift>(`/v1/tasks/${encodeURIComponent(uppgift.id)}`, { method: "PATCH", body: JSON.stringify(kropp) })
        : await crmAnrop<Uppgift>("/v1/tasks", { method: "POST", body: JSON.stringify(kropp) });
      sparad({ ...svar, title: svar.title ?? kropp.title }, !uppgift);
    } catch (orsak) {
      if (orsak instanceof CrmFel && orsak.falt.length) setFalt(Object.fromEntries(orsak.falt.map((f) => [f.field, kodtext(FALTKODER, f.code)])));
      else setAllmant(feltext(orsak));
    } finally {
      setSparar(false);
    }
  }

  // Fel på ett fält som formuläret inte visar (personen, affären) står i den allmänna rutan, med fältets namn.
  const dolda = Object.entries(falt).filter(([k]) => !["title", "description", "due_at", "owner", "company_id"].includes(k));

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && stang()} purpose="form" width={560}>
      <Layout
        header={<DialogHeader title={uppgift ? text({ sv: "Ändra uppgiften", en: "Edit the task" }) : text({ sv: "Ny uppgift", en: "New task" })} onOpenChange={(o) => !o && stang()} />}
        content={
          <LayoutContent>
            <form id="crm-uppgiftsformular" onSubmit={spara} noValidate className="flex flex-col gap-4">
              <div role="alert">
                {allmant || dolda.length ? (
                  <Banner
                    status="error"
                    container="card"
                    title={text({ sv: "Det gick inte att spara", en: "Could not save" })}
                    description={allmant ? text(allmant) : dolda.map(([k, v]) => `${FALT[k] ? text(FALT[k].etikett) : k}: ${text(v)}`).join(" ")}
                  />
                ) : null}
              </div>
              <TextInput
                label={text({ sv: "Vad ska göras", en: "What is to be done" })}
                value={titel}
                onChange={(v) => {
                  setTitel(v);
                  setFalt((f) => Object.fromEntries(Object.entries(f).filter(([k]) => k !== "title")));
                }}
                width="100%"
                status={status("title")}
                hasAutoFocus
              />
              <TextArea label={text({ sv: "Beskrivning", en: "Description" })} rows={3} value={beskrivning} onChange={setBeskrivning} width="100%" status={status("description")} isOptional />
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <DateInput
                  label={text({ sv: "Förfaller", en: "Due" })}
                  value={isodag(dag)}
                  onChange={(v) => setDag(v ?? "")}
                  weekStartsOn="mon"
                  format="date"
                  hasClear
                  isOptional
                  width="100%"
                  status={status("due_at")}
                />
                <TextInput label={text({ sv: "Ansvarig", en: "Owner" })} value={ansvarig} onChange={setAnsvarig} width="100%" status={status("owner")} isOptional />
              </div>
              <Selector
                label={text({ sv: "Bolag", en: "Company" })}
                value={bolagId}
                onChange={(x) => x && setBolagId(x)}
                options={[
                  { value: INGET, label: text({ sv: "Inget bolag", en: "No company" }) },
                  { type: "divider" as const },
                  ...bolag.map((b) => ({ value: b.id, label: b.namn })),
                  // Det sparade bolaget står kvar också när det inte ryms bland de 500 första.
                  ...(bolagId !== INGET && !bolag.some((b) => b.id === bolagId) ? [{ value: bolagId, label: bolagsnamn ?? text({ sv: "Valt bolag", en: "Selected company" }) }] : [])
                ]}
                hasSearch
                searchPlaceholder={text({ sv: "Sök bolag", en: "Search companies" })}
                width="100%"
                status={status("company_id")}
              />
            </form>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Avbryt", en: "Cancel" })} variant="ghost" onClick={stang} />
              <Button type="submit" form="crm-uppgiftsformular" variant="primary" label={uppgift ? text({ sv: "Spara", en: "Save" }) : text({ sv: "Lägg till", en: "Add" })} isLoading={sparar} />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
