"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Building2, CalendarX2, Clock, RotateCcw, Trash2, UserRound } from "lucide-react";
import { Button } from "@astryxdesign/core/Button";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { List, ListItem } from "@astryxdesign/core/List";
import { Table, pixel, proportional, type TableColumn } from "@astryxdesign/core/Table";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { useToast } from "@astryxdesign/core/Toast";
import { Kolumnrubrik, Krocklank, Personchip, Postchip, Tabellskelett, useSmal } from "@/components/crm/app/kit";
import { Felruta } from "@/components/crm/app/Sida";
import { CrmFel, crmAnrop, type Sida as Svarssida } from "@/lib/crm/api";
import { useLocale, type Localized } from "@/lib/i18n";

/** En raderad post som papperskorgen visar den: namn, när den raderades och när den töms. */
type Rad = { id: string; namn: string; deleted_at: string | null; purge_at: string | null };

type Raderad = { id: string; deleted_at?: string | null; purge_at?: string | null };

const SIDSTORLEK = 50;
const DYGN = 864e5;

/** "om 12 dagar", "i morgon", "i dag": när posten töms för gott. */
function tomsOm(purge: string | null, text: (l: Localized) => string): string {
  if (!purge) return text({ sv: "Okänt", en: "Unknown" });
  const dagar = Math.ceil((new Date(purge).getTime() - Date.now()) / DYGN);
  if (dagar <= 0) return text({ sv: "i dag", en: "today" });
  if (dagar === 1) return text({ sv: "i morgon", en: "tomorrow" });
  return text({ sv: `om ${dagar} dagar`, en: `in ${dagar} days` });
}

/**
 * Papperskorgen för bolag eller personer: en vy i listans vyrad, hämtad med
 * `only_deleted=true` (senast raderad först). Varje rad visar namnet, när
 * posten raderades och när den töms, med åtgärden Återställ. Krockar
 * återställningen (409: numret eller adressen finns nu på en annan post)
 * står skälet på raden, med en väg till den posten.
 */
export function Papperskorg<T extends Raderad>({
  objekt,
  fraga,
  namnPa,
  oppnaPost,
  aterstalld
}: Readonly<{
  objekt: "companies" | "people";
  /** Sökningen i vyraden. */
  fraga: string;
  namnPa: (post: T) => string;
  /** Öppnar en levande post, den som nu har numret, i listans panel. */
  oppnaPost: (id: string) => void;
  /** En post är återställd: listan bakom kan hämta om. */
  aterstalld?: (post: T) => void;
}>) {
  const { text, locale } = useLocale();
  const visa = useToast();
  const smal = useSmal();
  const tal = useCallback((n: number) => n.toLocaleString(locale === "sv" ? "sv-SE" : "en-GB"), [locale]);
  const bolag = objekt === "companies";
  const [rader, setRader] = useState<T[]>([]);
  const [nasta, setNasta] = useState<string | null>(null);
  const [laddar, setLaddar] = useState(true);
  const [laddarFler, setLaddarFler] = useState(false);
  const [fel, setFel] = useState<unknown>(null);
  const [arbetar, setArbetar] = useState<string | null>(null);
  const [krockar, setKrockar] = useState<Record<string, { text: Localized; krock: string | null }>>({});
  const omgang = useRef(0);

  const hamta = useCallback(
    async (markor: string | null) => {
      const denna = ++omgang.current;
      if (markor) setLaddarFler(true);
      else setLaddar(true);
      setFel(null);
      const q = new URLSearchParams({ only_deleted: "true", limit: String(SIDSTORLEK) });
      if (fraga) q.set("q", fraga);
      if (markor) q.set("cursor", markor);
      try {
        const sida = await crmAnrop<Svarssida<T>>(`/v1/${objekt}?${q}`);
        if (denna !== omgang.current) return;
        setRader((forr) => (markor ? [...forr, ...sida.data] : sida.data));
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
    [objekt, fraga]
  );

  useEffect(() => {
    void hamta(null);
  }, [hamta]);

  async function aterstall(post: T) {
    if (arbetar) return;
    setArbetar(post.id);
    setKrockar((k) => {
      const ny = { ...k };
      delete ny[post.id];
      return ny;
    });
    try {
      await crmAnrop<unknown>(`/v1/${objekt}/${encodeURIComponent(post.id)}/restore`, { method: "POST" });
      setRader((forr) => forr.filter((r) => r.id !== post.id));
      visa({
        body: text({ sv: `${namnPa(post)} är återställd.`, en: `${namnPa(post)} is restored.` }),
        endContent: <Button size="sm" variant="secondary" label={text({ sv: "Öppna", en: "Open" })} onClick={() => oppnaPost(post.id)} />,
        uniqueID: "crm-papperskorg"
      });
      aterstalld?.(post);
    } catch (e) {
      if (e instanceof CrmFel && e.status === 409) {
        setKrockar((k) => ({
          ...k,
          [post.id]: {
            text: bolag
              ? { sv: "Går inte att återställa: organisationsnumret finns nu på ett annat bolag.", en: "Cannot be restored: the organisation number now belongs to another company." }
              : { sv: "Går inte att återställa: e-postadressen finns nu på en annan person.", en: "Cannot be restored: the email address now belongs to another person." },
            krock: e.krockarMed
          }
        }));
      } else {
        visa({
          type: "error",
          body: text(e instanceof CrmFel ? e.text : { sv: "Det gick inte att återställa posten.", en: "Could not restore the record." }),
          uniqueID: "crm-papperskorg"
        });
      }
    } finally {
      setArbetar(null);
    }
  }

  const lista: (Rad & { post: T })[] = useMemo(
    () => rader.map((r) => ({ id: r.id, namn: namnPa(r), deleted_at: r.deleted_at ?? null, purge_at: r.purge_at ?? null, post: r })),
    [rader, namnPa]
  );

  const krockrad = (id: string) => {
    const k = krockar[id];
    if (!k) return null;
    return (
      <span className="flex flex-col items-start">
        <span role="status" className="text-[0.8125rem] text-danger">
          {text(k.text)}
        </span>
        {k.krock ? (
          <Krocklank
            etikett={bolag ? text({ sv: "Öppna bolaget som har numret", en: "Open the company that has the number" }) : text({ sv: "Öppna personen som har adressen", en: "Open the person who has the address" })}
            onClick={() => oppnaPost(k.krock!)}
          />
        ) : null}
      </span>
    );
  };

  const knapp = (r: Rad & { post: T }) => (
    <Button
      size="sm"
      variant="secondary"
      label={text({ sv: "Återställ", en: "Restore" })}
      icon={<Icon icon={RotateCcw} size="sm" />}
      isLoading={arbetar === r.id}
      onClick={() => void aterstall(r.post)}
      aria-label={text({ sv: `Återställ ${r.namn}`, en: `Restore ${r.namn}` })}
    />
  );

  const kolumner = useMemo<TableColumn<Rad & { post: T }>[]>(
    () => [
      {
        key: "namn",
        header: <Kolumnrubrik ikon={bolag ? Building2 : UserRound}>{bolag ? text({ sv: "Bolag", en: "Company" }) : text({ sv: "Namn", en: "Name" })}</Kolumnrubrik>,
        width: proportional(1, { minWidth: 220 }),
        renderCell: (r) => (
          <span className="flex min-w-0 flex-col items-start py-1.5">
            {bolag ? <Postchip namn={r.namn} vikt="stark" /> : <Personchip namn={r.namn} vikt="stark" />}
            {krockrad(r.id)}
          </span>
        )
      },
      {
        key: "deleted_at",
        header: <Kolumnrubrik ikon={Trash2}>{text({ sv: "Raderad", en: "Deleted" })}</Kolumnrubrik>,
        width: pixel(168),
        renderCell: (r) => (r.deleted_at ? <Timestamp value={r.deleted_at} format="relative" /> : null)
      },
      {
        key: "purge_at",
        header: <Kolumnrubrik ikon={CalendarX2}>{text({ sv: "Töms", en: "Emptied" })}</Kolumnrubrik>,
        width: pixel(148),
        renderCell: (r) => (
          <span className="text-ink2" title={r.purge_at ? new Date(r.purge_at).toLocaleDateString(locale === "sv" ? "sv-SE" : "en-GB") : undefined}>
            {tomsOm(r.purge_at, text)}
          </span>
        )
      },
      {
        key: "atgard",
        header: <span className="sr-only">{text({ sv: "Åtgärd", en: "Action" })}</span>,
        width: pixel(148),
        align: "end",
        renderCell: knapp
      }
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [text, bolag, krockar, arbetar, locale]
  );

  const tomt = (
    <EmptyState
      icon={<Icon icon={Trash2} size="lg" color="secondary" />}
      title={fraga ? text({ sv: `Inget i papperskorgen matchar ”${fraga}”`, en: `Nothing in the trash matches “${fraga}”` }) : text({ sv: "Papperskorgen är tom", en: "The trash is empty" })}
      description={
        bolag
          ? text({ sv: "Ett borttaget bolag ligger här i 30 dagar och kan återställas. Därefter töms det.", en: "A deleted company stays here for 30 days and can be restored. After that it is emptied." })
          : text({ sv: "En borttagen person ligger här i 30 dagar och kan återställas. Därefter töms den.", en: "A deleted person stays here for 30 days and can be restored. After that it is emptied." })
      }
    />
  );

  const fot = (
    <div className="crm-raknefot" role="status">
      <span>
        <span className="crm-raknefot-etikett">{text({ sv: "I papperskorgen", en: "In the trash" })}</span>{" "}
        <span className="crm-raknefot-tal">{tal(lista.length)}</span>
        {nasta ? <span className="crm-raknefot-etikett">{text({ sv: " och fler", en: " and more" })}</span> : null}
      </span>
      <span className="inline-flex items-center gap-1.5">
        <Icon icon={Clock} size="xsm" color="secondary" />
        <span className="crm-raknefot-etikett">{text({ sv: "Töms 30 dagar efter raderingen", en: "Emptied 30 days after deletion" })}</span>
      </span>
      {nasta ? (
        <span className="ml-auto">
          <Button size="sm" variant="secondary" label={text({ sv: "Visa fler", en: "Show more" })} isLoading={laddarFler} onClick={() => void hamta(nasta)} />
        </span>
      ) : null}
    </div>
  );

  if (fel) {
    return (
      <div className="p-4 sm:p-6">
        <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta(null)} />} />
      </div>
    );
  }
  if (laddar && lista.length === 0) {
    return <Tabellskelett rader={5} kolumner={smal ? 2 : 4} markering={false} label={text({ sv: "Hämtar papperskorgen", en: "Loading the trash" })} />;
  }
  if (lista.length === 0) return <div className="py-12">{tomt}</div>;

  if (smal) {
    return (
      <>
        <div className="px-2">
          <List hasDividers density="balanced" edge="padded">
            {lista.map((r) => (
              <ListItem
                key={r.id}
                label={<span className="font-semibold text-ink">{r.namn}</span>}
                description={
                  <span className="flex flex-col gap-1">
                    <span>{text({ sv: `Töms ${tomsOm(r.purge_at, text)}`, en: `Emptied ${tomsOm(r.purge_at, text)}` })}</span>
                    {krockrad(r.id)}
                  </span>
                }
                endContent={knapp(r)}
              />
            ))}
          </List>
        </div>
        {fot}
      </>
    );
  }

  return (
    <div className={laddar ? "crm-tabell crm-tabell-utan-val crm-tabell-laddar" : "crm-tabell crm-tabell-utan-val"}>
      <Table<Rad & { post: T }> data={lista} columns={kolumner} idKey="id" density="balanced" dividers="rows" hasHover textOverflow="wrap" />
      {fot}
    </div>
  );
}
