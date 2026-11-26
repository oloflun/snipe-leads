"use client";

import "@/components/crm/app/crm-vyer.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowDownAZ, Ban, Briefcase, Building2, Clock, Mail, Phone, Plug, Plus, SearchX, Trash2, UserRound, Users } from "lucide-react";
import { AlertDialog } from "@astryxdesign/core/AlertDialog";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { List, ListItem } from "@astryxdesign/core/List";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { Selector } from "@astryxdesign/core/Selector";
import { Table, TableSelectionToolbar, pixel, proportional, useTableSelection, useTableSelectionState, type TableColumn } from "@astryxdesign/core/Table";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { useToast } from "@astryxdesign/core/Toast";
import { PersonFormular, type Personfalt } from "@/components/crm/app/PersonFormular";
import { PersonPanel, personensKalla } from "@/components/crm/app/PersonPanel";
import { Kallpiller, Kolumnrubrik, Lankpiller, Personchip, Postchip, Tabellskelett, tonFor, tonklass, useBestallning, useSmal } from "@/components/crm/app/kit";
import { Felruta, Sida } from "@/components/crm/app/Sida";
import { CrmFel, crmAnrop, type Bolag, type Oversikt, type Sida as Svarssida } from "@/lib/crm/api";
import { iMangd } from "@/lib/crm/mangd";
import { personnamn, type Personpost } from "@/lib/crm/person";
import { useLocale, type Localized } from "@/lib/i18n";

type Sortering = "name" | "updated";
type Massjobb = { slag: "radera" | "kontakta_inte"; klara: number; totalt: number };

const SIDSTORLEK = 50;
/** Bolagsväljaren i vyraden: alla bolag, eller ett bolags personer (`company_id`). */
const ALLA = "alla";

const feltext = (e: unknown): Localized => (e instanceof CrmFel ? e.text : { sv: "Okänt fel.", en: "Unknown error." });

/**
 * Personlistan, i samma form som Bolag (DESIGN-CRM.md § Sidhuvud och vyrad,
 * § Tabellen). Personens panel följer adressen (`?person=<id>`), och bolagets
 * chip öppnar bolagets panel där (`<bas>/bolag?bolag=<id>`). `?ny=1` öppnar
 * dialogen Ny person.
 */
export function PersonerVy({ bas = "/crm" }: Readonly<{ bas?: string }>) {
  const { text, locale } = useLocale();
  const visa = useToast();
  const smal = useSmal();
  const params = useSearchParams();
  const adressensPerson = params?.get("person") ?? null;
  // Panelen följer adressen men hålls också i eget läge: replaceState når inte
  // alltid useSearchParams, och Stäng ska stänga direkt.
  const [postId, setPostId] = useState<string | null>(adressensPerson);
  useEffect(() => {
    setPostId(adressensPerson);
  }, [adressensPerson]);
  const sprak = locale === "sv" ? "sv-SE" : "en-GB";
  const tal = useCallback((n: number) => n.toLocaleString(sprak), [sprak]);

  const [sok, setSok] = useState("");
  const [fraga, setFraga] = useState("");
  const [sortering, setSortering] = useState<Sortering>("name");
  const [bolagsval, setBolagsval] = useState<string>(ALLA);
  const [rader, setRader] = useState<Personpost[]>([]);
  const [nasta, setNasta] = useState<string | null>(null);
  const [totalt, setTotalt] = useState<number | null>(null);
  const [bolagen, setBolagen] = useState<{ id: string; namn: string }[]>([]);
  const [laddar, setLaddar] = useState(true);
  const [laddarFler, setLaddarFler] = useState(false);
  const [fel, setFel] = useState<unknown>(null);
  const [post, setPost] = useState<Personpost | null>(null);
  const [formular, setFormular] = useState<{ person: Personpost | null; fokus: Personfalt | null } | null>(null);
  const [valda, setValda] = useState<Set<string>>(new Set());
  const [jobb, setJobb] = useState<Massjobb | null>(null);
  const [radera, setRadera] = useState<Personpost[] | null>(null);
  const omgang = useRef(0);

  const bolagsnamn = useMemo(() => Object.fromEntries(bolagen.map((b) => [b.id, b.namn])), [bolagen]);
  const bolagHref = useCallback((id: string) => `${bas}/bolag?bolag=${encodeURIComponent(id)}`, [bas]);
  const namnPa = useCallback(
    (p: Personpost | undefined | null) => (p ? personnamn(p) : null) ?? text({ sv: "Namnlös person", en: "Unnamed person" }),
    [text]
  );

  // ---- Adressen styr panelen ------------------------------------------------

  const sattPost = useCallback((id: string | null) => {
    setPostId(id);
    const q = new URLSearchParams(window.location.search);
    if (id) q.set("person", id);
    else q.delete("person");
    const s = q.toString();
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${s ? `?${s}` : ""}`);
  }, []);

  const oppna = useCallback(
    (p: Personpost) => {
      setPost(p);
      sattPost(p.id);
    },
    [sattPost]
  );

  useEffect(() => {
    if (!postId) {
      setPost(null);
      return;
    }
    let aktuell = true;
    setPost((nu) => (nu?.id === postId ? nu : (rader.find((r) => r.id === postId) ?? null)));
    crmAnrop<Personpost>(`/v1/people/${encodeURIComponent(postId)}`)
      .then((p) => aktuell && setPost(p))
      .catch((e) => {
        if (!aktuell) return;
        sattPost(null);
        visa({ type: "error", body: text(feltext(e)), uniqueID: "crm-person-saknas" });
      });
    return () => {
      aktuell = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postId]);

  useBestallning("ny", () => setFormular({ person: null, fokus: null }));

  // ---- Hämtning -------------------------------------------------------------

  useEffect(() => {
    const t = window.setTimeout(() => setFraga(sok.trim()), 250);
    return () => window.clearTimeout(t);
  }, [sok]);

  // Personens rad bär bara bolagets id. Namnen slås upp ur bolagslistan, högst
  // 500 åt gången, som också fyller bolagsväljaren och dialogen.
  const hamtaBolag = useCallback(async () => {
    try {
      const s = await crmAnrop<Svarssida<Bolag>>("/v1/companies?limit=500&sort=name");
      setBolagen(s.data.map((b) => ({ id: b.id, namn: b.name ?? text({ sv: "Namnlöst bolag", en: "Unnamed company" }) })));
    } catch {
      setBolagen([]);
    }
  }, [text]);

  useEffect(() => {
    void hamtaBolag();
  }, [hamtaBolag]);

  const hamta = useCallback(
    async (markor: string | null) => {
      const denna = ++omgang.current;
      if (markor) setLaddarFler(true);
      else setLaddar(true);
      setFel(null);
      const q = new URLSearchParams({ limit: String(SIDSTORLEK), sort: sortering });
      if (fraga) q.set("q", fraga);
      if (bolagsval !== ALLA) q.set("company_id", bolagsval);
      if (markor) q.set("cursor", markor);
      try {
        const [sida, oversikt] = await Promise.all([
          crmAnrop<Svarssida<Personpost>>(`/v1/people?${q}`),
          markor ? Promise.resolve(null) : crmAnrop<Oversikt>("/oversikt")
        ]);
        if (denna !== omgang.current) return;
        setRader((forr) => (markor ? [...forr, ...sida.data] : sida.data));
        setNasta(sida.next_cursor);
        if (oversikt) setTotalt(oversikt.personer);
      } catch (e) {
        if (denna === omgang.current) setFel(e);
      } finally {
        if (denna === omgang.current) {
          setLaddar(false);
          setLaddarFler(false);
        }
      }
    },
    [fraga, sortering, bolagsval]
  );

  useEffect(() => {
    void hamta(null);
  }, [hamta]);

  useEffect(() => {
    setValda(new Set());
  }, [fraga, sortering, bolagsval]);

  // ---- Markering och åtgärder -----------------------------------------------

  const { selectionConfig, selectionState } = useTableSelectionState<Personpost>({ data: rader, idKey: "id", selectedKeys: valda, setSelectedKeys: setValda });
  const markering = useTableSelection<Personpost>({ ...selectionConfig, getRowLabel: (p) => namnPa(p) });

  const fallna = useCallback(
    (fall: { id: string; fel: unknown }[]) => {
      const visade = fall.slice(0, 3).map((f) => `${namnPa(rader.find((r) => r.id === f.id))} (${text(feltext(f.fel)).replace(/\.$/, "")})`);
      const rest = fall.length - visade.length;
      return visade.join(", ") + (rest > 0 ? text({ sv: ` och ${rest} till`, en: ` and ${rest} more` }) : "");
    },
    [namnPa, rader, text]
  );

  async function kontaktaInte(ids: string[]) {
    if (!ids.length || jobb) return;
    setJobb({ slag: "kontakta_inte", klara: 0, totalt: ids.length });
    const { klara, fall } = await iMangd(
      ids,
      (id) => crmAnrop<Personpost>(`/v1/people/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ do_not_contact: true }) }),
      (n) => setJobb((j) => (j ? { ...j, klara: n } : j))
    );
    setJobb(null);
    visa({
      type: fall.length ? "error" : "info",
      body: fall.length
        ? text({ sv: `${klara.length} av ${ids.length} ändrades. Föll: ${fallna(fall)}.`, en: `${klara.length} of ${ids.length} changed. Failed: ${fallna(fall)}.` })
        : text({
            sv: klara.length === 1 ? `${namnPa(rader.find((r) => r.id === klara[0]))} ska inte kontaktas.` : `${klara.length} personer ska inte kontaktas.`,
            en: klara.length === 1 ? `${namnPa(rader.find((r) => r.id === klara[0]))} is not to be contacted.` : `${klara.length} people are not to be contacted.`
          }),
      uniqueID: "crm-person-kontakta"
    });
    setValda(new Set(fall.map((f) => f.id)));
    if (post && klara.includes(post.id)) setPost({ ...post, do_not_contact: true });
    void hamta(null);
  }

  async function taBort(lista: Personpost[]) {
    const ids = lista.map((p) => p.id);
    const namn = lista.length === 1 ? namnPa(lista[0]) : null;
    setRadera(null);
    if (!ids.length || jobb) return;
    setJobb({ slag: "radera", klara: 0, totalt: ids.length });
    const { klara, fall } = await iMangd(
      ids,
      (id) => crmAnrop<null>(`/v1/people/${encodeURIComponent(id)}`, { method: "DELETE" }),
      (n) => setJobb((j) => (j ? { ...j, klara: n } : j))
    );
    setJobb(null);
    if (post && klara.includes(post.id)) sattPost(null);
    setValda(new Set(fall.map((f) => f.id)));

    const aterstall = async () => {
      const ut = await iMangd(klara, (id) => crmAnrop<Personpost>(`/v1/people/${encodeURIComponent(id)}/restore`, { method: "POST" }), () => undefined);
      visa({
        type: ut.fall.length ? "error" : "info",
        body: ut.fall.length
          ? text({ sv: `${ut.klara.length} av ${klara.length} återställdes.`, en: `${ut.klara.length} of ${klara.length} restored.` })
          : klara.length === 1
            ? text({ sv: "Personen är återställd.", en: "The person is restored." })
            : text({ sv: `${klara.length} personer är återställda.`, en: `${klara.length} people are restored.` }),
        uniqueID: "crm-person-radera"
      });
      void hamta(null);
    };

    visa({
      type: fall.length ? "error" : "info",
      body: fall.length
        ? text({ sv: `${klara.length} av ${ids.length} flyttades till papperskorgen. Föll: ${fallna(fall)}.`, en: `${klara.length} of ${ids.length} moved to the trash. Failed: ${fallna(fall)}.` })
        : text({
            sv: namn ? `${namn} ligger i papperskorgen i 30 dagar.` : `${klara.length} personer ligger i papperskorgen i 30 dagar.`,
            en: namn ? `${namn} is in the trash for 30 days.` : `${klara.length} people are in the trash for 30 days.`
          }),
      endContent: klara.length ? <Button size="sm" variant="secondary" label={text({ sv: "Ångra", en: "Undo" })} onClick={() => void aterstall()} /> : undefined,
      autoHideDuration: 10000,
      uniqueID: "crm-person-radera"
    });
    void hamta(null);
  }

  // ---- Kolumnerna -----------------------------------------------------------

  const kolumner = useMemo<TableColumn<Personpost>[]>(
    () => [
      {
        key: "name",
        header: <Kolumnrubrik ikon={UserRound}>{text({ sv: "Namn", en: "Name" })}</Kolumnrubrik>,
        width: proportional(1, { minWidth: 200 }),
        // Kontakta inte står i namnkolumnen, som i mobillistan, och gör personens
        // e-post och telefon passiva: uppgiften får inte försvinna vid en viss bredd.
        renderCell: (p) => (
          <span className="inline-flex min-w-0 max-w-full items-center gap-1.5">
            <span className="min-w-0 shrink">
              <Personchip namn={namnPa(p)} onClick={() => oppna(p)} label={text({ sv: `Öppna ${namnPa(p)}`, en: `Open ${namnPa(p)}` })} />
            </span>
            {p.do_not_contact ? (
              // En ikon med namn, inte en etikett: etiketten kapade personens namn
              // i en kolumn på 200 px. Orden står kvar i panelen och i mobillistan.
              <span
                className="inline-flex shrink-0 text-danger"
                role="img"
                aria-label={text({ sv: "Kontakta inte", en: "Do not contact" })}
                title={text({ sv: "Kontakta inte", en: "Do not contact" })}
              >
                <Ban size={15} strokeWidth={2} aria-hidden="true" />
              </span>
            ) : null}
          </span>
        )
      },
      {
        key: "title",
        header: <Kolumnrubrik ikon={Briefcase}>{text({ sv: "Titel", en: "Title" })}</Kolumnrubrik>,
        width: pixel(110),
        renderCell: (p) => <span className="text-ink2">{p.title ?? ""}</span>
      },
      {
        key: "company",
        header: <Kolumnrubrik ikon={Building2}>{text({ sv: "Bolag", en: "Company" })}</Kolumnrubrik>,
        width: pixel(196),
        renderCell: (p) =>
          p.company_id && bolagsnamn[p.company_id] ? (
            <Postchip
              namn={bolagsnamn[p.company_id]}
              href={bolagHref(p.company_id)}
              vikt="lugn"
              label={text({ sv: `Öppna ${bolagsnamn[p.company_id]}`, en: `Open ${bolagsnamn[p.company_id]}` })}
            />
          ) : null
      },
      {
        key: "email",
        header: <Kolumnrubrik ikon={Mail}>{text({ sv: "E-post", en: "Email" })}</Kolumnrubrik>,
        width: pixel(176),
        renderCell: (p) => (p.email ? <Lankpiller slag="epost" varde={p.email} passiv={p.do_not_contact} /> : null)
      },
      {
        key: "phone",
        header: <Kolumnrubrik ikon={Phone}>{text({ sv: "Telefon", en: "Phone" })}</Kolumnrubrik>,
        width: pixel(152),
        renderCell: (p) => (p.mobile ?? p.phone ? <Lankpiller slag="telefon" varde={(p.mobile ?? p.phone)!} passiv={p.do_not_contact} /> : null)
      },
      {
        key: "source",
        header: <Kolumnrubrik ikon={Plug}>{text({ sv: "Källa", en: "Source" })}</Kolumnrubrik>,
        width: pixel(96),
        renderCell: (p) => <Kallpiller kalla={text(personensKalla(p))} />
      },
      {
        key: "updated_at",
        header: <Kolumnrubrik ikon={Clock}>{text({ sv: "Ändrad", en: "Updated" })}</Kolumnrubrik>,
        width: pixel(158),
        renderCell: (p) => (p.updated_at ? <Timestamp value={p.updated_at} format="relative" /> : null)
      }
    ],
    [text, namnPa, oppna, bolagsnamn, bolagHref]
  );

  // ---- Delarna --------------------------------------------------------------

  const nyPerson = () => setFormular({ person: null, fokus: null });
  const ettBolag = bolagsval !== ALLA ? (bolagsnamn[bolagsval] ?? null) : null;

  const tomt = fraga ? (
    <EmptyState
      icon={<Icon icon={SearchX} size="lg" color="secondary" />}
      title={text({ sv: `Inga personer matchar ”${fraga}”`, en: `No people match “${fraga}”` })}
      description={text({ sv: "Sökningen går på förnamn, efternamn, e-post och titel.", en: "The search covers first name, last name, email and title." })}
      actions={<Button label={text({ sv: "Rensa sökningen", en: "Clear the search" })} variant="secondary" onClick={() => setSok("")} />}
    />
  ) : ettBolag ? (
    <EmptyState
      icon={<Icon icon={Building2} size="lg" color="secondary" />}
      title={text({ sv: `Inga personer hos ${ettBolag}`, en: `No people at ${ettBolag}` })}
      description={text({ sv: "Lägg till en person och välj bolaget, så hamnar den här.", en: "Add a person and pick the company, and they show up here." })}
      actions={<Button label={text({ sv: "Visa alla personer", en: "Show all people" })} variant="secondary" onClick={() => setBolagsval(ALLA)} />}
    />
  ) : (
    <EmptyState
      icon={<Icon icon={Users} size="lg" color="secondary" />}
      title={text({ sv: "Inga personer än", en: "No people yet" })}
      description={text({ sv: "Personer följer med när ni synkar in kontakter från ert CRM, eller läggs till för hand.", en: "People arrive when you sync contacts from your CRM, or are added by hand." })}
      actions={<Button label={text({ sv: "Ny person", en: "New person" })} variant="primary" icon={<Icon icon={Plus} size="sm" />} onClick={nyPerson} />}
    />
  );

  const iUrvalet = !fraga && bolagsval === ALLA ? totalt : null;
  const laggTill = (
    <button type="button" onClick={nyPerson} className="crm-lagg-till-rad">
      <Icon icon={Plus} size="sm" color="inherit" />
      <span>{text({ sv: "Lägg till person", en: "Add person" })}</span>
    </button>
  );
  const utanBolag = rader.filter((p) => !p.company_id).length;
  const fot = (
    <div className="crm-raknefot" role="status">
      <span>
        <span className="crm-raknefot-etikett">{text({ sv: "Visar", en: "Showing" })}</span> <span className="crm-raknefot-tal">{tal(rader.length)}</span>
        {iUrvalet != null && iUrvalet > rader.length ? (
          <>
            {" "}
            <span className="crm-raknefot-etikett">{text({ sv: "av", en: "of" })}</span> <span className="crm-raknefot-tal">{tal(iUrvalet)}</span>
          </>
        ) : null}
      </span>
      {bolagsval === ALLA && utanBolag > 0 ? (
        <span>
          <span className="crm-raknefot-etikett">{text({ sv: "Utan bolag bland dem", en: "Without a company among them" })}</span>{" "}
          <span className="crm-raknefot-tal">{tal(utanBolag)}</span>
        </span>
      ) : null}
      {nasta ? (
        <span className="ml-auto">
          <Button
            size="sm"
            variant="secondary"
            label={
              iUrvalet != null && iUrvalet > rader.length
                ? text({ sv: `Visa ${tal(Math.min(SIDSTORLEK, iUrvalet - rader.length))} till`, en: `Show ${tal(Math.min(SIDSTORLEK, iUrvalet - rader.length))} more` })
                : text({ sv: "Visa fler", en: "Show more" })
            }
            isLoading={laddarFler}
            onClick={() => void hamta(nasta)}
          />
        </span>
      ) : null}
    </div>
  );

  const bolagsvaljare = (
    <Selector
      label={text({ sv: "Bolag", en: "Company" })}
      isLabelHidden
      variant="secondary"
      size="md"
      startIcon={Building2}
      value={bolagsval}
      onChange={(v) => v && setBolagsval(v)}
      options={[
        { value: ALLA, label: text({ sv: "Alla bolag", en: "All companies" }) },
        { type: "divider" as const },
        ...bolagen.map((b) => ({ value: b.id, label: b.namn }))
      ]}
      hasSearch
      searchPlaceholder={text({ sv: "Sök bolag", en: "Search companies" })}
    />
  );

  return (
    <Sida
      objekt="personer"
      rubrik={text({ sv: "Personer", en: "People" })}
      antal={totalt == null ? undefined : tal(totalt)}
      atgarder={<Button variant="primary" label={text({ sv: "Ny person", en: "New person" })} icon={<Icon icon={Plus} size="sm" />} onClick={nyPerson} />}
      vyrad={bolagsvaljare}
      vyradHoger={
        <>
          <div className="min-w-0 flex-1 sm:w-[260px] sm:flex-none">
            <TextInput
              type="search"
              label={text({ sv: "Sök personer", en: "Search people" })}
              isLabelHidden
              placeholder={text({ sv: "Sök namn, e-post eller titel", en: "Search name, email or title" })}
              startIcon="search"
              hasClear
              value={sok}
              onChange={(v) => setSok(v)}
              width="100%"
              controlClassName="crm-sokfalt"
            />
          </div>
          <Selector
            label={text({ sv: "Sortera", en: "Sort" })}
            isLabelHidden
            variant="ghost"
            size="md"
            startIcon={sortering === "name" ? ArrowDownAZ : Clock}
            value={sortering}
            onChange={(v) => v && setSortering(v as Sortering)}
            options={[
              { value: "name", label: text({ sv: "Efternamn", en: "Last name" }), description: text({ sv: "A till Ö", en: "A to Z" }) },
              {
                value: "updated",
                label: text({ sv: "Ändringsordning", en: "Change order" }),
                description: text({ sv: "Äldst ändrade först, som API:t listar", en: "Oldest change first, as the API lists" })
              }
            ]}
          />
        </>
      }
    >
      <div className="crm-personer">
        {fel ? (
          <div className="p-4 sm:p-6">
            <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta(null)} />} />
          </div>
        ) : laddar && rader.length === 0 ? (
          <Tabellskelett rader={10} kolumner={smal ? 2 : 7} markering={!smal} label={text({ sv: "Hämtar personer", en: "Loading people" })} />
        ) : smal ? (
          rader.length === 0 ? (
            <div className="py-10">{tomt}</div>
          ) : (
            <>
              <div className="px-2">
                <List hasDividers density="balanced" edge="padded">
                  {rader.map((p) => {
                    const namn = namnPa(p);
                    const bolag = p.company_id ? bolagsnamn[p.company_id] : null;
                    return (
                      <ListItem
                        key={p.id}
                        label={<span className="font-semibold text-ink">{namn}</span>}
                        description={[p.title, bolag].filter(Boolean).join(" · ") || undefined}
                        startContent={<Avatar name={namn} size={32} tooltip={false} className={`crm-avatar ${tonklass(tonFor(namn))}`} />}
                        endContent={p.do_not_contact ? <Badge variant="error" label={text({ sv: "Kontakta inte", en: "Do not contact" })} /> : undefined}
                        onClick={() => oppna(p)}
                        isSelected={post?.id === p.id}
                      />
                    );
                  })}
                </List>
              </div>
              {laggTill}
              {fot}
            </>
          )
        ) : (
          <div className={laddar ? "crm-tabell crm-tabell-laddar" : "crm-tabell"}>
            <Table<Personpost>
              data={rader}
              columns={kolumner}
              idKey="id"
              density="balanced"
              dividers="rows"
              hasHover
              textOverflow="truncate"
              plugins={{ selection: markering }}
              rowCount={iUrvalet ?? undefined}
              emptyState={<div className="py-12">{tomt}</div>}
            />
            {rader.length > 0 ? (
              <>
                {laggTill}
                {fot}
              </>
            ) : null}
          </div>
        )}

        {!smal && (selectionState.hasSelection || jobb) ? (
          <div className="crm-atgardsrad-plats">
            <div className="crm-atgardsrad">
              {jobb ? (
                <div className="flex min-w-[320px] items-center gap-3 px-2" role="status" aria-live="polite">
                  <span className="whitespace-nowrap text-[0.875rem] font-semibold tabular-nums text-ink">
                    {jobb.slag === "radera"
                      ? text({ sv: `Tar bort ${jobb.klara} av ${jobb.totalt}`, en: `Deleting ${jobb.klara} of ${jobb.totalt}` })
                      : text({ sv: `Ändrar ${jobb.klara} av ${jobb.totalt}`, en: `Changing ${jobb.klara} of ${jobb.totalt}` })}
                  </span>
                  <div className="flex-1">
                    <ProgressBar label={text({ sv: "Förlopp", en: "Progress" })} isLabelHidden value={jobb.klara} max={jobb.totalt} />
                  </div>
                </div>
              ) : (
                <TableSelectionToolbar
                  selection={selectionState}
                  size="md"
                  variant="transparent"
                  label={text({ sv: "Åtgärder för markerade personer", en: "Actions for selected people" })}
                  renderSelectionLabel={(n) => <span className="tabular-nums">{text({ sv: n === 1 ? "1 markerad" : `${n} markerade`, en: `${n} selected` })}</span>}
                  clearLabel={text({ sv: "Avmarkera", en: "Unselect" })}
                  startContent={
                    <>
                      <Button
                        label={text({ sv: "Kontakta inte", en: "Do not contact" })}
                        variant="ghost"
                        size="md"
                        icon={<Icon icon={Ban} size="sm" />}
                        onClick={() => void kontaktaInte([...selectionState.selectedKeys])}
                      />
                      <Button
                        label={text({ sv: "Ta bort", en: "Delete" })}
                        variant="ghost"
                        size="md"
                        icon={<Icon icon={Trash2} size="sm" />}
                        className="crm-farlig"
                        onClick={() => setRadera(rader.filter((p) => selectionState.selectedKeys.has(p.id)))}
                      />
                    </>
                  }
                />
              )}
            </div>
          </div>
        ) : null}
      </div>

      <PersonPanel
        person={post}
        laddar={postId != null && post == null}
        bolagsnamn={post?.company_id ? (bolagsnamn[post.company_id] ?? null) : null}
        bolagHref={bolagHref}
        stang={() => sattPost(null)}
        redigera={(falt) => post && setFormular({ person: post, fokus: falt ?? null })}
        taBort={(p) => setRadera([p])}
      />

      <PersonFormular
        oppen={formular != null}
        person={formular?.person ?? null}
        bolag={bolagen}
        fokus={formular?.fokus}
        stang={() => setFormular(null)}
        sparat={(p, ny) => {
          setFormular(null);
          setRader((forr) => forr.map((r) => (r.id === p.id ? p : r)));
          if (ny) oppna(p);
          else if (post?.id === p.id) setPost(p);
          visa({
            body: ny
              ? text({ sv: `${namnPa(p)} är skapad.`, en: `${namnPa(p)} is created.` })
              : text({ sv: `${namnPa(p)} är sparad.`, en: `${namnPa(p)} is saved.` }),
            uniqueID: "crm-person-sparad"
          });
          void hamta(null);
        }}
      />

      <AlertDialog
        isOpen={radera != null}
        onOpenChange={(o) => !o && setRadera(null)}
        title={
          radera?.length === 1
            ? text({ sv: `Ta bort ${namnPa(radera[0])}?`, en: `Delete ${namnPa(radera[0])}?` })
            : text({ sv: `Ta bort ${radera?.length ?? 0} personer?`, en: `Delete ${radera?.length ?? 0} people?` })
        }
        description={
          radera?.length === 1
            ? text({
                sv: "Personen flyttas till papperskorgen och kan återställas i 30 dagar. Därefter töms den.",
                en: "The person moves to the trash and can be restored for 30 days. After that it is emptied."
              })
            : text({
                sv: "Personerna flyttas till papperskorgen och kan återställas i 30 dagar. Därefter töms de.",
                en: "The people move to the trash and can be restored for 30 days. After that they are emptied."
              })
        }
        actionLabel={text({ sv: "Ta bort", en: "Delete" })}
        cancelLabel={text({ sv: "Avbryt", en: "Cancel" })}
        onAction={() => radera && void taBort(radera)}
      />
    </Sida>
  );
}
