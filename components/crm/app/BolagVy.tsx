"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowDownAZ, Building2, Clock, Globe, Hash, MapPin, Plus, SearchX, Tag, Trash2, UserRound } from "lucide-react";
import { AlertDialog } from "@astryxdesign/core/AlertDialog";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Button } from "@astryxdesign/core/Button";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { DropdownMenu, type DropdownMenuOption } from "@astryxdesign/core/DropdownMenu";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { List, ListItem } from "@astryxdesign/core/List";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { Selector } from "@astryxdesign/core/Selector";
import {
  Table,
  TableSelectionToolbar,
  pixel,
  proportional,
  useTableSelection,
  useTableSelectionState,
  type TableColumn
} from "@astryxdesign/core/Table";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { useToast } from "@astryxdesign/core/Toast";
import { BolagFormular, type Bolagsfalt } from "@/components/crm/app/BolagFormular";
import { BolagPanel } from "@/components/crm/app/BolagPanel";
import {
  Kolumnrubrik,
  Lankpiller,
  Personchip,
  Postchip,
  Prick,
  RELATIONSTON,
  Relationsetikett,
  Tabellskelett,
  tonFor,
  tonklass,
  useBestallning,
  useSmal,
  utanBolagsform,
  Vyval
} from "@/components/crm/app/kit";
import { Felruta, Sida } from "@/components/crm/app/Sida";
import { CrmFel, RELATIONER, crmAnrop, orgnrVisning, type Bolag, type Oversikt, type Relation, type Sida as Svarssida } from "@/lib/crm/api";
import { useLocale, type Localized } from "@/lib/i18n";

type Filter = "alla" | Relation;
type Sortering = "name" | "updated";

/** Vyerna i vyraden. Partner, leverantör och övrigt visas bara när de har bolag. */
const ALLTID: Filter[] = ["alla", "customer", "prospect", "former_customer"];
const IBLAND: Filter[] = ["partner", "supplier", "other"];
/** Översiktens nycklar är databasens (svenska) relationsnamn. */
const RAKNENYCKEL: Record<Filter, string> = {
  alla: "alla",
  customer: "kund",
  former_customer: "tidigare_kund",
  prospect: "prospekt",
  partner: "partner",
  supplier: "leverantor",
  other: "ovrigt"
};

const SIDSTORLEK = 50;
/** Hur många ändringar som går mot API:t samtidigt när flera bolag ändras. */
const SAMTIDIGA = 4;

type Massjobb = { slag: "relation" | "radera"; klara: number; totalt: number };

/** Ett fel från API:t som en kort mening, för utfallet efter en åtgärd. */
const feltext = (e: unknown): Localized => (e instanceof CrmFel ? e.text : { sv: "Okänt fel.", en: "Unknown error." });

/**
 * Kör en ändring per bolag, några åt gången, och rapporterar förloppet. Ett bolag
 * som faller stoppar inte de andra: utfallet säger vilka som gick och vilka som föll.
 */
async function iMangd(ids: string[], gor: (id: string) => Promise<unknown>, framsteg: (klara: number) => void) {
  const klara: string[] = [];
  const fall: { id: string; fel: unknown }[] = [];
  let nasta = 0;
  let gjorda = 0;
  const arbetare = async () => {
    while (nasta < ids.length) {
      const id = ids[nasta++];
      try {
        await gor(id);
        klara.push(id);
      } catch (fel) {
        fall.push({ id, fel });
      }
      framsteg(++gjorda);
    }
  };
  await Promise.all(Array.from({ length: Math.min(SAMTIDIGA, ids.length) }, arbetare));
  return { klara, fall };
}

/**
 * Bolagslistan (DESIGN-CRM.md § Sidhuvud och vyrad, § Tabellen, § Postens panel).
 *
 * Postens panel följer adressen: `?bolag=<id>` öppnar den, så att kommandopaletten,
 * översiktens "Senast ändrade" och en delad länk landar på rätt bolag, och så att
 * panelen står kvar efter en omladdning. `?ny=1` öppnar dialogen Nytt bolag.
 */
export function BolagVy() {
  const { text, locale } = useLocale();
  const visa = useToast();
  const smal = useSmal();
  const params = useSearchParams();
  const postId = params?.get("bolag") ?? null;
  const sprak = locale === "sv" ? "sv-SE" : "en-GB";
  const tal = useCallback((n: number) => n.toLocaleString(sprak), [sprak]);

  const [filter, setFilter] = useState<Filter>("alla");
  const [sortering, setSortering] = useState<Sortering>("name");
  const [sok, setSok] = useState("");
  const [fraga, setFraga] = useState("");
  const [rader, setRader] = useState<Bolag[]>([]);
  const [nasta, setNasta] = useState<string | null>(null);
  const [antal, setAntal] = useState<Record<string, number> | null>(null);
  const [laddar, setLaddar] = useState(true);
  const [laddarFler, setLaddarFler] = useState(false);
  const [fel, setFel] = useState<unknown>(null);
  const [post, setPost] = useState<Bolag | null>(null);
  const [formular, setFormular] = useState<{ bolag: Bolag | null; fokus: Bolagsfalt | null } | null>(null);
  const [valda, setValda] = useState<Set<string>>(new Set());
  const [jobb, setJobb] = useState<Massjobb | null>(null);
  const [radera, setRadera] = useState<Bolag[] | null>(null);
  /** Markeringsläget i mobillistan (under 640 px finns ingen tabell med kryssrutor). */
  const [valjer, setValjer] = useState(false);
  const omgang = useRef(0);

  // ---- Adressen styr panelen ------------------------------------------------

  /** Byter `?bolag=` utan ny sidladdning; Next läser historiken och useSearchParams följer med. */
  const sattPost = useCallback((id: string | null) => {
    const q = new URLSearchParams(window.location.search);
    if (id) q.set("bolag", id);
    else q.delete("bolag");
    const s = q.toString();
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${s ? `?${s}` : ""}`);
  }, []);

  const oppna = useCallback(
    (b: Bolag) => {
      setPost(b);
      sattPost(b.id);
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
    // Alltid färskt från API:t: listraden kan vara äldre än posten.
    crmAnrop<Bolag>(`/v1/companies/${encodeURIComponent(postId)}`)
      .then((b) => aktuell && setPost(b))
      .catch((e) => {
        if (!aktuell) return;
        sattPost(null);
        visa({ type: "error", body: text(feltext(e)), uniqueID: "crm-bolag-saknas" });
      });
    return () => {
      aktuell = false;
    };
    // rader läses bara för att visa listraden direkt; en ny lista ska inte hämta om posten.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postId]);

  useBestallning("ny", () => setFormular({ bolag: null, fokus: null }));

  // ---- Hämtning -------------------------------------------------------------

  // Sökningen väntar tills man slutat skriva, så att varje tangent inte blir ett anrop.
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
      const q = new URLSearchParams({ limit: String(SIDSTORLEK), sort: sortering });
      if (filter !== "alla") q.set("relation", filter);
      if (fraga) q.set("q", fraga);
      if (markor) q.set("cursor", markor);
      try {
        const [sida, oversikt] = await Promise.all([
          crmAnrop<Svarssida<Bolag>>(`/v1/companies?${q}`),
          markor ? Promise.resolve(null) : crmAnrop<Oversikt>("/oversikt")
        ]);
        if (denna !== omgang.current) return;
        setRader((forr) => (markor ? [...forr, ...sida.data] : sida.data));
        setNasta(sida.next_cursor);
        if (oversikt) setAntal(oversikt.bolag);
      } catch (e) {
        if (denna === omgang.current) setFel(e);
      } finally {
        if (denna === omgang.current) {
          setLaddar(false);
          setLaddarFler(false);
        }
      }
    },
    [filter, fraga, sortering]
  );

  useEffect(() => {
    void hamta(null);
  }, [hamta]);

  // En ny lista är ett nytt urval: markeringen gäller inte längre.
  useEffect(() => {
    setValda(new Set());
  }, [filter, fraga, sortering]);

  // ---- Markering ------------------------------------------------------------

  const { selectionConfig, selectionState } = useTableSelectionState<Bolag>({
    data: rader,
    idKey: "id",
    selectedKeys: valda,
    setSelectedKeys: setValda
  });
  const markering = useTableSelection<Bolag>({
    ...selectionConfig,
    getRowLabel: (b) => b.name ?? b.id
  });

  const namnPa = useCallback(
    (id: string) => rader.find((r) => r.id === id)?.name ?? (post?.id === id ? post.name : null) ?? text({ sv: "Namnlöst bolag", en: "Unnamed company" }),
    [rader, post, text]
  );

  /** "Fiktiv Telefoni AB (Posten finns inte.)", högst tre, sedan "och 2 till". */
  const fallna = useCallback(
    (fall: { id: string; fel: unknown }[]) => {
      const visade = fall.slice(0, 3).map((f) => `${namnPa(f.id)} (${text(feltext(f.fel)).replace(/\.$/, "")})`);
      const rest = fall.length - visade.length;
      return visade.join(", ") + (rest > 0 ? text({ sv: ` och ${rest} till`, en: ` and ${rest} more` }) : "");
    },
    [namnPa, text]
  );

  async function andraRelation(ids: string[], relation: Relation) {
    if (!ids.length || jobb) return;
    // Varje bolags relation före ändringen, så att Ångra kan sätta tillbaka den.
    const forut = new Map(ids.map((id) => [id, rader.find((r) => r.id === id)?.relation ?? (post?.id === id ? post.relation : null)]));
    setJobb({ slag: "relation", klara: 0, totalt: ids.length });
    const { klara, fall } = await iMangd(
      ids,
      (id) => crmAnrop<Bolag>(`/v1/companies/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ relation }) }),
      (n) => setJobb((j) => (j ? { ...j, klara: n } : j))
    );
    setJobb(null);
    const rel = text(RELATIONER[relation]).toLocaleLowerCase(sprak);
    const angra = async () => {
      const tillbaka = klara.filter((id) => forut.get(id) && forut.get(id) !== relation);
      const ut = await iMangd(
        tillbaka,
        (id) => crmAnrop<Bolag>(`/v1/companies/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ relation: forut.get(id) }) }),
        () => undefined
      );
      visa({
        type: ut.fall.length ? "error" : "info",
        body: ut.fall.length
          ? text({ sv: `${ut.klara.length} av ${tillbaka.length} fick tillbaka sin relation. Föll: ${fallna(ut.fall)}.`, en: `${ut.klara.length} of ${tillbaka.length} got their relation back. Failed: ${fallna(ut.fall)}.` })
          : text({ sv: "Relationen är återställd.", en: "The relation is restored." }),
        uniqueID: "crm-bolag-relation"
      });
      void hamta(null);
    };
    if (fall.length === 0) {
      visa({
        body:
          klara.length === 1
            ? text({ sv: `${namnPa(klara[0])} är nu ${rel}.`, en: `${namnPa(klara[0])} is now ${rel}.` })
            : text({ sv: `${klara.length} bolag är nu ${rel}.`, en: `${klara.length} companies are now ${rel}.` }),
        endContent: <Button size="sm" variant="secondary" label={text({ sv: "Ångra", en: "Undo" })} onClick={() => void angra()} />,
        autoHideDuration: 10000,
        uniqueID: "crm-bolag-relation"
      });
    } else {
      visa({
        type: "error",
        body: text({
          sv: `${klara.length} av ${ids.length} bolag ändrades. Föll: ${fallna(fall)}.`,
          en: `${klara.length} of ${ids.length} companies changed. Failed: ${fallna(fall)}.`
        }),
        uniqueID: "crm-bolag-relation"
      });
    }
    setValda(new Set(fall.map((f) => f.id)));
    if (post && klara.includes(post.id)) setPost({ ...post, relation });
    void hamta(null);
  }

  async function taBort(lista: Bolag[]) {
    const ids = lista.map((b) => b.id);
    setRadera(null);
    if (!ids.length || jobb) return;
    setJobb({ slag: "radera", klara: 0, totalt: ids.length });
    const { klara, fall } = await iMangd(
      ids,
      (id) => crmAnrop<null>(`/v1/companies/${encodeURIComponent(id)}`, { method: "DELETE" }),
      (n) => setJobb((j) => (j ? { ...j, klara: n } : j))
    );
    setJobb(null);
    if (post && klara.includes(post.id)) sattPost(null);
    setValda(new Set(fall.map((f) => f.id)));

    const aterstall = async () => {
      const ut = await iMangd(klara, (id) => crmAnrop<Bolag>(`/v1/companies/${encodeURIComponent(id)}/restore`, { method: "POST" }), () => undefined);
      visa({
        type: ut.fall.length ? "error" : "info",
        body: ut.fall.length
          ? text({ sv: `${ut.klara.length} av ${klara.length} återställdes. Föll: ${fallna(ut.fall)}.`, en: `${ut.klara.length} of ${klara.length} restored. Failed: ${fallna(ut.fall)}.` })
          : klara.length === 1
            ? text({ sv: "Bolaget är återställt.", en: "The company is restored." })
            : text({ sv: `${klara.length} bolag är återställda.`, en: `${klara.length} companies are restored.` }),
        uniqueID: "crm-bolag-radera"
      });
      void hamta(null);
    };

    const namn = klara.length === 1 ? namnPa(klara[0]) : null;
    visa({
      type: fall.length ? "error" : "info",
      body: fall.length
        ? text({
            sv: `${klara.length} av ${ids.length} bolag flyttades till papperskorgen. Föll: ${fallna(fall)}.`,
            en: `${klara.length} of ${ids.length} companies moved to the trash. Failed: ${fallna(fall)}.`
          })
        : text({
            sv: namn ? `${namn} ligger i papperskorgen i 30 dagar.` : `${klara.length} bolag ligger i papperskorgen i 30 dagar.`,
            en: namn ? `${namn} is in the trash for 30 days.` : `${klara.length} companies are in the trash for 30 days.`
          }),
      endContent: klara.length ? <Button size="sm" variant="secondary" label={text({ sv: "Ångra", en: "Undo" })} onClick={() => void aterstall()} /> : undefined,
      autoHideDuration: 10000,
      uniqueID: "crm-bolag-radera"
    });
    void hamta(null);
  }

  // ---- Kolumnerna -----------------------------------------------------------

  const kolumner = useMemo<TableColumn<Bolag>[]>(
    () => [
      {
        key: "name",
        header: <Kolumnrubrik ikon={Building2}>{text({ sv: "Bolag", en: "Company" })}</Kolumnrubrik>,
        // Kolumnbredderna summerar till 1 094 px plus kryssrutan, så att tabellen
        // ryms i bladet vid 1 440 px utan att någon kolumn trycks ihop.
        width: proportional(1, { minWidth: 200 }),
        renderCell: (b) => (
          <Postchip
            namn={b.name ?? text({ sv: "Namnlöst bolag", en: "Unnamed company" })}
            onClick={() => oppna(b)}
            label={text({ sv: `Öppna ${b.name ?? "bolaget"}`, en: `Open ${b.name ?? "the company"}` })}
          />
        )
      },
      {
        key: "org_number",
        header: <Kolumnrubrik ikon={Hash}>{text({ sv: "Org.nr", en: "Org. no." })}</Kolumnrubrik>,
        width: pixel(126),
        renderCell: (b) => <span className="tabular-nums text-ink2">{orgnrVisning(b.org_number)}</span>
      },
      {
        key: "relation",
        header: <Kolumnrubrik ikon={Tag}>{text({ sv: "Relation", en: "Relation" })}</Kolumnrubrik>,
        width: pixel(138),
        renderCell: (b) => <Relationsetikett relation={b.relation} />
      },
      {
        key: "website",
        header: <Kolumnrubrik ikon={Globe}>{text({ sv: "Webbplats", en: "Website" })}</Kolumnrubrik>,
        width: pixel(188),
        renderCell: (b) => (b.website || b.domain ? <Lankpiller slag="webb" varde={b.domain ?? b.website ?? ""} /> : null)
      },
      {
        key: "city",
        header: <Kolumnrubrik ikon={MapPin}>{text({ sv: "Ort", en: "City" })}</Kolumnrubrik>,
        width: pixel(108),
        renderCell: (b) => <span className="text-ink2">{b.address.city ?? ""}</span>
      },
      {
        key: "owner",
        header: <Kolumnrubrik ikon={UserRound}>{text({ sv: "Ansvarig", en: "Owner" })}</Kolumnrubrik>,
        width: pixel(152),
        renderCell: (b) => (b.owner ? <Personchip namn={b.owner} storlek="md" vikt="lugn" /> : null)
      },
      // Källan står inte i listan: åtta kolumner fick inte plats på 1440 px utan
      // att organisationsnummer eller webbadress kapades. Den finns i postens
      // panel, fliken Källa.
      {
        key: "updated_at",
        header: <Kolumnrubrik ikon={Clock}>{text({ sv: "Ändrad", en: "Updated" })}</Kolumnrubrik>,
        width: pixel(152),
        renderCell: (b) => (b.updated_at ? <Timestamp value={b.updated_at} format="relative" /> : null)
      }
    ],
    [text, oppna]
  );

  // ---- Räkningen ------------------------------------------------------------

  const totalt = antal?.alla;
  const iFiltret = antal && !fraga ? (antal[RAKNENYCKEL[filter]] ?? 0) : null;
  const kunder = antal?.kund ?? 0;
  const vyer = [...ALLTID, ...IBLAND.filter((f) => (antal?.[RAKNENYCKEL[f]] ?? 0) > 0)];
  const vynamn = (f: Filter) => (f === "alla" ? text({ sv: "Alla", en: "All" }) : text(RELATIONER[f]));
  const vyetikett = (f: Filter) => (antal ? `${vynamn(f)}  ${tal(antal[RAKNENYCKEL[f]] ?? 0)}` : vynamn(f));

  const nyttBolag = () => setFormular({ bolag: null, fokus: null });

  const relationsval: DropdownMenuOption[] = (Object.keys(RELATIONER) as Relation[]).map((r) => ({
    label: text(RELATIONER[r]),
    icon: <Prick ton={RELATIONSTON[r].prick} />,
    onClick: () => void andraRelation([...selectionState.selectedKeys], r)
  }));

  // ---- Delarna --------------------------------------------------------------

  const tomt = fraga ? (
    <EmptyState
      icon={<Icon icon={SearchX} size="lg" color="secondary" />}
      title={text({ sv: `Inga bolag matchar ”${fraga}”`, en: `No companies match “${fraga}”` })}
      description={
        filter === "alla"
          ? text({ sv: "Sökningen går på namn, organisationsnummer, webbplats och ort.", en: "The search covers name, organisation number, website and city." })
          : text({ sv: "Sökningen gäller bara den valda vyn. Prova Alla.", en: "The search only covers the selected view. Try All." })
      }
      actions={<Button label={text({ sv: "Rensa sökningen", en: "Clear the search" })} variant="secondary" onClick={() => setSok("")} />}
    />
  ) : filter !== "alla" ? (
    <EmptyState
      icon={<Icon icon={Tag} size="lg" color="secondary" />}
      title={text({ sv: `Inga bolag med relationen ${vynamn(filter).toLocaleLowerCase(sprak)}`, en: `No companies with the relation ${vynamn(filter).toLocaleLowerCase(sprak)}` })}
      description={text({ sv: "Ändra relationen på ett bolag så hamnar det här.", en: "Change a company's relation and it shows up here." })}
      actions={<Button label={text({ sv: "Visa alla bolag", en: "Show all companies" })} variant="secondary" onClick={() => setFilter("alla")} />}
    />
  ) : (
    <EmptyState
      icon={<Icon icon={Building2} size="lg" color="secondary" />}
      title={text({ sv: "Inga bolag än", en: "No companies yet" })}
      description={text({
        sv: "Synka in kundstocken från ert CRM, eller lägg till det första bolaget för hand.",
        en: "Sync your customer base from your CRM, or add the first company by hand."
      })}
      actions={<Button label={text({ sv: "Nytt bolag", en: "New company" })} variant="primary" icon={<Icon icon={Plus} size="sm" />} onClick={nyttBolag} />}
    />
  );

  const laggTill = (
    <button type="button" onClick={nyttBolag} className="crm-lagg-till-rad">
      <Icon icon={Plus} size="sm" color="inherit" />
      <span>{text({ sv: "Lägg till bolag", en: "Add company" })}</span>
    </button>
  );

  const fot = (
    <div className="crm-raknefot" role="status">
      <span>
        <span className="crm-raknefot-etikett">{text({ sv: "Visar", en: "Showing" })}</span>{" "}
        <span className="crm-raknefot-tal">{tal(rader.length)}</span>
        {iFiltret != null && iFiltret > rader.length ? (
          <>
            {" "}
            <span className="crm-raknefot-etikett">{text({ sv: "av", en: "of" })}</span> <span className="crm-raknefot-tal">{tal(iFiltret)}</span>
          </>
        ) : null}
      </span>
      {filter === "alla" && !fraga && totalt ? (
        <span>
          <span className="crm-raknefot-etikett">{text({ sv: "Kunder", en: "Customers" })}</span>{" "}
          <span className="crm-raknefot-tal">{tal(kunder)}</span>{" "}
          <span className="crm-raknefot-etikett">{`(${Math.round((kunder / totalt) * 100)} %)`}</span>
        </span>
      ) : null}
      {nasta ? (
        <span className="ml-auto">
          <Button
            size="sm"
            variant="secondary"
            label={
              iFiltret != null && iFiltret > rader.length
                ? text({ sv: `Visa ${tal(Math.min(SIDSTORLEK, iFiltret - rader.length))} till`, en: `Show ${tal(Math.min(SIDSTORLEK, iFiltret - rader.length))} more` })
                : text({ sv: "Visa fler", en: "Show more" })
            }
            isLoading={laddarFler}
            onClick={() => void hamta(nasta)}
          />
        </span>
      ) : null}
    </div>
  );

  const pagar = jobb != null;

  return (
    <Sida
      objekt="bolag"
      rubrik={text({ sv: "Bolag", en: "Companies" })}
      antal={totalt == null ? undefined : tal(totalt)}
      atgarder={<Button variant="primary" label={text({ sv: "Nytt bolag", en: "New company" })} icon={<Icon icon={Plus} size="sm" />} onClick={nyttBolag} />}
      vyrad={
        smal ? (
          <Selector
            label={text({ sv: "Vy", en: "View" })}
            isLabelHidden
            variant="secondary"
            size="md"
            value={filter}
            onChange={(v) => v && setFilter(v as Filter)}
            options={vyer.map((f) => ({ value: f, label: vyetikett(f) }))}
          />
        ) : (
          <Vyval
            value={filter}
            onChange={setFilter}
            label={text({ sv: "Vy", en: "View" })}
            val={vyer.map((f) => ({ v: f, namn: vynamn(f), antal: antal ? tal(antal[RAKNENYCKEL[f]] ?? 0) : undefined }))}
          />
        )
      }
      vyradHoger={
        <>
          <div className="min-w-0 flex-1 sm:w-[260px] sm:flex-none">
            <TextInput
              type="search"
              label={text({ sv: "Sök bolag", en: "Search companies" })}
              isLabelHidden
              placeholder={text({ sv: "Sök namn, nummer eller ort", en: "Search name, number or city" })}
              startIcon="search"
              hasClear
              value={sok}
              onChange={(v) => setSok(v)}
              width="100%"
              controlClassName="crm-sokfalt"
            />
          </div>
          {smal ? (
            <Button
              variant={valjer ? "secondary" : "ghost"}
              size="md"
              label={valjer ? text({ sv: "Klar", en: "Done" }) : text({ sv: "Välj", en: "Select" })}
              onClick={() => {
                if (valjer) setValda(new Set());
                setValjer(!valjer);
              }}
            />
          ) : null}
          <Selector
            label={text({ sv: "Sortera", en: "Sort" })}
            isLabelHidden
            variant="ghost"
            size="md"
            startIcon={sortering === "name" ? ArrowDownAZ : Clock}
            value={sortering}
            onChange={(v) => v && setSortering(v as Sortering)}
            options={[
              { value: "name", label: text({ sv: "Namn", en: "Name" }), description: text({ sv: "A till Ö", en: "A to Z" }) },
              {
                value: "updated",
                label: text({ sv: "Ändringsordning", en: "Change order" }),
                description: text({ sv: "Det som ändrades för längst sedan står först", en: "What changed longest ago comes first" })
              }
            ]}
          />
        </>
      }
    >
      <div className="crm-bolag">
        {fel ? (
          <div className="p-4 sm:p-6">
            <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta(null)} />} />
          </div>
        ) : laddar && rader.length === 0 ? (
          <Tabellskelett rader={10} kolumner={smal ? 2 : 7} markering={!smal} label={text({ sv: "Hämtar bolag", en: "Loading companies" })} />
        ) : smal ? (
          rader.length === 0 ? (
            <div className="py-10">{tomt}</div>
          ) : (
            <>
              <div className="px-2">
              <List hasDividers density="balanced" edge="padded">
                {rader.map((b) => {
                  const namn = b.name ?? text({ sv: "Namnlöst bolag", en: "Unnamed company" });
                  const vald = valda.has(b.id);
                  const vaxla = (pa: boolean) =>
                    setValda((forr) => {
                      const ny = new Set(forr);
                      if (pa) ny.add(b.id);
                      else ny.delete(b.id);
                      return ny;
                    });
                  return (
                    <ListItem
                      key={b.id}
                      label={<span className="font-semibold text-ink">{namn}</span>}
                      description={[b.address.city, b.owner].filter(Boolean).join(" · ") || undefined}
                      startContent={
                        valjer ? (
                          // 44 px tryckyta runt kryssrutan; klicket stannar här så att raden inte växlar en gång till.
                          <span className="-my-1 inline-flex size-11 items-center justify-center" onClick={(e) => e.stopPropagation()}>
                            <CheckboxInput label={text({ sv: `Markera ${namn}`, en: `Select ${namn}` })} isLabelHidden value={vald} onChange={vaxla} />
                          </span>
                        ) : (
                          <span aria-hidden className="inline-flex">
                            <Avatar name={utanBolagsform(namn)} size={32} shape="rounded" tooltip={false} className={`crm-avatar ${tonklass(tonFor(utanBolagsform(namn)))}`} />
                          </span>
                        )
                      }
                      endContent={<Relationsetikett relation={b.relation} />}
                      onClick={() => (valjer ? vaxla(!vald) : oppna(b))}
                      isSelected={valjer ? false : post?.id === b.id}
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
            <Table<Bolag>
              data={rader}
              columns={kolumner}
              idKey="id"
              density="balanced"
              dividers="rows"
              hasHover
              textOverflow="truncate"
              plugins={{ selection: markering }}
              rowCount={iFiltret ?? undefined}
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

        {/* Åtgärdsraden flyter längst ned i bladet medan något är markerat. */}
        {(!smal || valjer) && (selectionState.hasSelection || pagar) ? (
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
                  label={text({ sv: "Åtgärder för markerade bolag", en: "Actions for selected companies" })}
                  renderSelectionLabel={(n) => (
                    <span className="tabular-nums">{text({ sv: n === 1 ? "1 markerat" : `${n} markerade`, en: `${n} selected` })}</span>
                  )}
                  clearLabel={text({ sv: "Avmarkera", en: "Unselect" })}
                  startContent={
                    <>
                      <DropdownMenu
                        button={{ label: text({ sv: "Ändra relation", en: "Change relation" }), variant: "ghost", size: "md", icon: <Icon icon={Tag} size="sm" /> }}
                        items={relationsval}
                        placement="above"
                      />
                      <Button
                        label={text({ sv: "Ta bort", en: "Delete" })}
                        variant="ghost"
                        size="md"
                        icon={<Icon icon={Trash2} size="sm" />}
                        className="crm-farlig"
                        onClick={() => setRadera(rader.filter((b) => selectionState.selectedKeys.has(b.id)))}
                      />
                    </>
                  }
                />
              )}
            </div>
          </div>
        ) : null}
      </div>

      <BolagPanel
        bolag={post}
        laddar={postId != null && post == null}
        stang={() => sattPost(null)}
        redigera={(falt) => post && setFormular({ bolag: post, fokus: falt ?? null })}
        taBort={(b) => setRadera([b])}
      />

      <BolagFormular
        oppen={formular != null}
        bolag={formular?.bolag ?? null}
        fokus={formular?.fokus}
        stang={() => setFormular(null)}
        sparat={(b, nytt) => {
          setFormular(null);
          setRader((forr) => forr.map((r) => (r.id === b.id ? b : r)));
          if (nytt) oppna(b);
          else if (post?.id === b.id) setPost(b);
          visa({
            body: nytt
              ? text({ sv: `${b.name ?? "Bolaget"} är skapat.`, en: `${b.name ?? "The company"} is created.` })
              : text({ sv: `${b.name ?? "Bolaget"} är sparat.`, en: `${b.name ?? "The company"} is saved.` }),
            uniqueID: "crm-bolag-sparat"
          });
          void hamta(null);
        }}
      />

      <AlertDialog
        isOpen={radera != null}
        onOpenChange={(o) => !o && setRadera(null)}
        title={
          radera?.length === 1
            ? text({ sv: `Ta bort ${radera[0].name ?? "bolaget"}?`, en: `Delete ${radera[0].name ?? "the company"}?` })
            : text({ sv: `Ta bort ${radera?.length ?? 0} bolag?`, en: `Delete ${radera?.length ?? 0} companies?` })
        }
        description={
          radera?.length === 1
            ? text({
                sv: "Bolaget flyttas till papperskorgen och kan återställas i 30 dagar. Därefter töms det.",
                en: "The company moves to the trash and can be restored for 30 days. After that it is emptied."
              })
            : text({
                sv: "Bolagen flyttas till papperskorgen och kan återställas i 30 dagar. Därefter töms de.",
                en: "The companies move to the trash and can be restored for 30 days. After that they are emptied."
              })
        }
        actionLabel={text({ sv: "Ta bort", en: "Delete" })}
        cancelLabel={text({ sv: "Avbryt", en: "Cancel" })}
        onAction={() => radera && void taBort(radera)}
      />
    </Sida>
  );
}
