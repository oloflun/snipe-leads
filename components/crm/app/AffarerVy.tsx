"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CalendarClock, CalendarX2, Plus, SearchX } from "lucide-react";
import { AlertDialog } from "@astryxdesign/core/AlertDialog";
import { Avatar } from "@astryxdesign/core/Avatar";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { Selector } from "@astryxdesign/core/Selector";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { Text } from "@astryxdesign/core/Text";
import { TextInput } from "@astryxdesign/core/TextInput";
import { useToast } from "@astryxdesign/core/Toast";
import { AffarFormular, type Affarsfalt } from "@/components/crm/app/AffarFormular";
import { AffarPanel, STEGTON } from "@/components/crm/app/AffarPanel";
import { Postchip, Prick, tonFor, tonklass, useBestallning, useSmal, Vyval } from "@/components/crm/app/kit";
import { Papperskorg } from "@/components/crm/app/Papperskorg";
import { Felruta, Sida } from "@/components/crm/app/Sida";
import { STEGTYPER, belopp, sannolikhet, summa, type Affar, type Affarssteg, type Tavelsteg, type Tavla } from "@/lib/crm/affar";
import { CrmFel, crmAnrop, dagtext, idagLokalt, type Bolag, type Sida as Svarssida } from "@/lib/crm/api";
import { useLocale, type Localized } from "@/lib/i18n";

type Vy = "tavla" | "papperskorg";

/** Var ett draget kort hamnar: i ett steg, före ett annat kort eller sist. */
type Mal = { stegId: string; foreId: string | null };

const feltext = (e: unknown): Localized => (e instanceof CrmFel ? e.text : { sv: "Okänt fel.", en: "Unknown error." });

/** Stegets antal och summa räknas om ur korten, så att tavlan stämmer direkt efter en flytt. */
function raknat(s: Tavelsteg, deals: Affar[]): Tavelsteg {
  const per: Record<string, number> = {};
  for (const a of deals) per[a.currency || "SEK"] = (per[a.currency || "SEK"] ?? 0) + (a.amount ?? 0);
  return { ...s, deals, count: deals.length, amount_by_currency: per, amount_total: Object.values(per).reduce((x, y) => x + y, 0) };
}

/** Tavlan med affären flyttad till `mal`: det som visas medan API:t sparar. */
function flyttad(tavla: Tavla, id: string, mal: Mal): Tavla {
  const affar = tavla.stages.flatMap((s) => s.deals).find((a) => a.id === id);
  if (!affar) return tavla;
  return {
    stages: tavla.stages.map((s) => {
      const utan = s.deals.filter((a) => a.id !== id);
      if (s.id !== mal.stegId) return utan.length === s.deals.length ? s : raknat(s, utan);
      const plats = mal.foreId ? utan.findIndex((a) => a.id === mal.foreId) : -1;
      const flyttat = { ...affar, stage_id: s.id };
      return raknat(s, plats < 0 ? [...utan, flyttat] : [...utan.slice(0, plats), flyttat, ...utan.slice(plats)]);
    })
  };
}

/** Så många sidor bolagsnamn hämtas till korten och formulärets väljare (500 per sida). */
const MAX_NAMNSIDOR = 10;

/**
 * Affärerna som en tavla: stegen som kolumner, affärerna som kort i stegets
 * ordning (`GET /v1/deals/board`). Ett kort dras till ett annat steg eller en
 * annan plats (`POST /v1/deals/{id}/move`); tavlan visar flytten direkt och
 * lägger tillbaka kortet om API:t säger nej. Under 640 px står stegen under
 * varandra, och steget byts i affärens panel.
 *
 * `?affar=<id>` öppnar panelen och `?ny=1` dialogen, som i Bolag och Personer.
 * `?nybolag=<id>` öppnar dialogen med bolaget valt (från bolagets panel).
 */
export function AffarerVy({ bas = "/crm" }: Readonly<{ bas?: string }>) {
  const { text, locale } = useLocale();
  const visa = useToast();
  const smal = useSmal();
  const params = useSearchParams();
  const adressensPost = params?.get("affar") ?? null;
  const [postId, setPostId] = useState<string | null>(adressensPost);
  useEffect(() => {
    setPostId(adressensPost);
  }, [adressensPost]);
  const sprak = locale === "sv" ? "sv-SE" : "en-GB";

  const [vy, setVy] = useState<Vy>("tavla");
  const [tavla, setTavla] = useState<Tavla | null>(null);
  const [fel, setFel] = useState<unknown>(null);
  const [bolag, setBolag] = useState<{ id: string; namn: string }[]>([]);
  const [sok, setSok] = useState("");
  const [post, setPost] = useState<Affar | null>(null);
  const [formular, setFormular] = useState<{ affar: Affar | null; fokus: Affarsfalt | null; stegId: string | null; bolagId?: string | null } | null>(null);
  const [radera, setRadera] = useState<Affar | null>(null);
  const [dras, setDras] = useState<string | null>(null);
  const [mal, setMal] = useState<Mal | null>(null);
  const [flyttar, setFlyttar] = useState(false);
  const omgang = useRef(0);

  // ---- Hämtning -------------------------------------------------------------

  const hamta = useCallback(async () => {
    const denna = ++omgang.current;
    setFel(null);
    try {
      const ny = await crmAnrop<Tavla>("/v1/deals/board");
      if (denna === omgang.current) setTavla(ny);
    } catch (e) {
      if (denna === omgang.current) setFel(e);
    }
  }, []);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  // Bolagens namn, till korten och till formulärets väljare. Tavlan bär bara id:n.
  // Listan hämtas sida för sida (en stor kundstock har fler än 500 bolag), och visas medan den växer.
  useEffect(() => {
    let aktuell = true;
    (async () => {
      let markor: string | null = null;
      for (let sida = 0; sida < MAX_NAMNSIDOR && aktuell; sida++) {
        const q = new URLSearchParams({ limit: "500", sort: "name" });
        if (markor) q.set("cursor", markor);
        let svar: Svarssida<Bolag>;
        try {
          svar = await crmAnrop<Svarssida<Bolag>>(`/v1/companies?${q}`);
        } catch {
          return;
        }
        if (!aktuell) return;
        const nya = svar.data.map((b) => ({ id: b.id, namn: b.name ?? "" })).filter((b) => b.namn);
        setBolag((forr) => (sida === 0 ? nya : [...forr, ...nya]));
        markor = svar.next_cursor;
        if (!markor) return;
      }
    })();
    return () => {
      aktuell = false;
    };
  }, []);

  // Ett bolag på tavlan som inte kom med i namnlistan (fler bolag än listan rymmer) hämtas för sig, en gång.
  const efterfragade = useRef(new Set<string>());
  useEffect(() => {
    if (!tavla || bolag.length === 0) return;
    const kanda = new Set(bolag.map((b) => b.id));
    const saknas = [...new Set(tavla.stages.flatMap((s) => s.deals.map((a) => a.company_id)))].filter((id): id is string => !!id && !kanda.has(id) && !efterfragade.current.has(id));
    for (const id of saknas.slice(0, 50)) {
      efterfragade.current.add(id);
      crmAnrop<Bolag>(`/v1/companies/${encodeURIComponent(id)}`)
        .then((b) => b.name && setBolag((forr) => (forr.some((x) => x.id === b.id) ? forr : [...forr, { id: b.id, namn: b.name! }])))
        .catch(() => undefined);
    }
  }, [tavla, bolag]);

  const bolagsnamn = useMemo(() => {
    const karta = new Map(bolag.map((b) => [b.id, b.namn]));
    return (id: string) => karta.get(id) ?? null;
  }, [bolag]);

  const steg: Affarssteg[] = useMemo(() => tavla?.stages ?? [], [tavla]);
  const alla = useMemo(() => tavla?.stages.flatMap((s) => s.deals) ?? [], [tavla]);

  // ---- Adressen styr panelen ------------------------------------------------

  const sattPost = useCallback((id: string | null) => {
    setPostId(id);
    const q = new URLSearchParams(window.location.search);
    if (id) q.set("affar", id);
    else q.delete("affar");
    const s = q.toString();
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${s ? `?${s}` : ""}`);
  }, []);

  useEffect(() => {
    if (!postId) {
      setPost(null);
      return;
    }
    let aktuell = true;
    setPost((nu) => (nu?.id === postId ? nu : (alla.find((a) => a.id === postId) ?? null)));
    crmAnrop<Affar>(`/v1/deals/${encodeURIComponent(postId)}`)
      .then((a) => aktuell && setPost(a))
      .catch((e) => {
        if (!aktuell) return;
        sattPost(null);
        visa({ type: "error", body: text(feltext(e)), uniqueID: "crm-affar-saknas" });
      });
    return () => {
      aktuell = false;
    };
    // Tavlan läses bara för att visa kortets uppgifter direkt; en ny tavla ska inte hämta om affären.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postId]);

  useBestallning("ny", () => setFormular({ affar: null, fokus: null, stegId: null }));
  // Från bolagets panel: en ny affär med bolaget redan valt (`?nybolag=<id>`).
  useBestallning("nybolag", (bolagId) => setFormular({ affar: null, fokus: null, stegId: null, bolagId }));

  // ---- Sökningen -------------------------------------------------------------

  const fraga = sok.trim().toLocaleLowerCase(sprak);
  const matchar = useCallback(
    (a: Affar) => !fraga || [a.name, a.owner, a.company_id ? bolagsnamn(a.company_id) : null].some((v) => (v ?? "").toLocaleLowerCase(sprak).includes(fraga)),
    [fraga, bolagsnamn, sprak]
  );

  // ---- Flytt ----------------------------------------------------------------

  const flyttarRef = useRef(false);

  const namnPa = useCallback((a: Affar | undefined) => a?.name ?? text({ sv: "Affären", en: "The deal" }), [text]);

  /**
   * Flyttar en affär och visar utfallet. Tavlan ritas om direkt; säger API:t nej
   * läggs kortet tillbaka och skälet visas. `tyst` är Ångra: ingen ny Ångra-knapp.
   */
  const flytta = useCallback(
    async (id: string, till: Mal, tyst = false) => {
      if (!tavla || flyttarRef.current) return;
      const fran = tavla.stages.find((s) => s.deals.some((a) => a.id === id));
      const affar = fran?.deals.find((a) => a.id === id);
      const mot = tavla.stages.find((s) => s.id === till.stegId);
      if (!fran || !affar || !mot || till.foreId === id) return;
      // Kortet som stod närmast under, för att kunna lägga tillbaka på samma plats.
      const gammalNasta = fran.deals[fran.deals.findIndex((a) => a.id === id) + 1]?.id ?? null;
      // "Samma plats" avgörs bland korten som syns: med en sökning ligger dolda kort emellan, och ett
      // släpp där kortet redan låg ska inte flytta det förbi dem.
      const synligaKort = fran.deals.filter(matchar);
      const synligNasta = synligaKort[synligaKort.findIndex((a) => a.id === id) + 1]?.id ?? null;
      if (fran.id === mot.id && (gammalNasta === till.foreId || (fraga && synligNasta === till.foreId))) return;

      // Äldre tavelhämtningar kastas: de får inte skriva över flytten medan den sparas.
      omgang.current += 1;
      setTavla(flyttad(tavla, id, till));
      setPost((nu) => (nu?.id === id ? { ...nu, stage_id: mot.id } : nu));
      flyttarRef.current = true;
      setFlyttar(true);
      const skicka = (kropp: Record<string, string>) => crmAnrop<Affar>(`/v1/deals/${encodeURIComponent(id)}/move`, { method: "POST", body: JSON.stringify(kropp) });
      try {
        let sparad: Affar;
        try {
          sparad = await skicka(till.foreId ? { stage_id: mot.id, before_id: till.foreId } : { stage_id: mot.id });
        } catch (orsak) {
          // Ångra pekar på kortet som låg under. Har det hunnit flyttas läggs affären sist i steget i stället.
          if (!(tyst && till.foreId && orsak instanceof CrmFel && orsak.status === 422)) throw orsak;
          sparad = await skicka({ stage_id: mot.id });
        }
        setPost((nu) => (nu?.id === id ? sparad : nu));
        if (fran.id !== mot.id) {
          visa({
            body: text({ sv: `${namnPa(affar)} står nu i ${mot.name}.`, en: `${namnPa(affar)} is now in ${mot.name}.` }),
            endContent: tyst ? undefined : (
              <Button size="sm" variant="secondary" label={text({ sv: "Ångra", en: "Undo" })} onClick={() => void angra(id, { stegId: fran.id, foreId: gammalNasta })} />
            ),
            autoHideDuration: 8000,
            uniqueID: "crm-affar-flytt"
          });
        }
      } catch (e) {
        // Tavlan hämtas om nedan: en gammal ögonblicksbild hade kunnat ta bort något som hunnit komma till.
        setPost((nu) => (nu?.id === id ? affar : nu));
        visa({
          type: "error",
          body: text({ sv: `${namnPa(affar)} gick inte att flytta. ${text(feltext(e))}`, en: `${namnPa(affar)} could not be moved. ${text(feltext(e))}` }),
          uniqueID: "crm-affar-flytt"
        });
      } finally {
        flyttarRef.current = false;
        setFlyttar(false);
        void hamta();
      }
    },
    // angra anropar flytta och flytta visar angra: den läses genom en ref.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [tavla, hamta, namnPa, text, visa, matchar, fraga]
  );
  const flyttaRef = useRef(flytta);
  flyttaRef.current = flytta;
  /** Ångra väntar ut en flytt som pågår (högst fem sekunder), så att den inte försvinner utan besked. */
  const angra = async (id: string, till: Mal) => {
    for (let i = 0; i < 50 && flyttarRef.current; i++) await new Promise((klar) => window.setTimeout(klar, 100));
    await flyttaRef.current(id, till, true);
  };

  /** Ett steg upp eller ned inom steget: tangentbordets och telefonens väg till samma ordning som dragningen ger. */
  const flyttaPlats = (a: Affar, upp: boolean) => {
    const s = tavla?.stages.find((x) => x.deals.some((d) => d.id === a.id));
    if (!s) return;
    const i = s.deals.findIndex((d) => d.id === a.id);
    if (upp ? i <= 0 : i >= s.deals.length - 1) return;
    void flytta(a.id, { stegId: s.id, foreId: upp ? s.deals[i - 1].id : (s.deals[i + 2]?.id ?? null) });
  };
  const platsFor = (a: Affar | null) => {
    const s = a ? tavla?.stages.find((x) => x.deals.some((d) => d.id === a.id)) : undefined;
    return s && a ? { plats: s.deals.findIndex((d) => d.id === a.id) + 1, antal: s.deals.length } : null;
  };

  /** Stänger panelen och lämnar fokus på affärens kort (som kan ha bytt kolumn), annars på Ny affär. */
  const stangPanel = (id: string | null) => {
    sattPost(null);
    window.setTimeout(() => {
      const kort = id ? document.querySelector<HTMLElement>(`[data-kort="${CSS.escape(id)}"]`) : null;
      (kort ?? document.querySelector<HTMLElement>("[data-ny-affar] button, button[data-ny-affar]"))?.focus();
    }, 80);
  };

  // ---- Dra och släpp --------------------------------------------------------

  /** Platsen under pekaren: före det första kort vars mitt ligger under den, annars sist. */
  const malFor = (e: React.DragEvent<HTMLElement>, stegId: string): Mal => {
    const kort = [...e.currentTarget.querySelectorAll<HTMLElement>("[data-kort]")].filter((k) => k.dataset.kort !== dras);
    const under = kort.find((k) => {
      const r = k.getBoundingClientRect();
      return e.clientY < r.top + r.height / 2;
    });
    return { stegId, foreId: under?.dataset.kort ?? null };
  };

  const slapp = () => {
    setDras(null);
    setMal(null);
  };

  // ---- Skapa, spara, ta bort ------------------------------------------------

  async function taBort(a: Affar) {
    setRadera(null);
    try {
      await crmAnrop<null>(`/v1/deals/${encodeURIComponent(a.id)}`, { method: "DELETE" });
    } catch (e) {
      visa({ type: "error", body: text(feltext(e)), uniqueID: "crm-affar-radera" });
      return;
    }
    if (post?.id === a.id) stangPanel(null);
    const aterstall = async () => {
      try {
        await crmAnrop<Affar>(`/v1/deals/${encodeURIComponent(a.id)}/restore`, { method: "POST" });
        visa({ body: text({ sv: "Affären är återställd.", en: "The deal is restored." }), uniqueID: "crm-affar-radera" });
      } catch (e) {
        visa({ type: "error", body: text(feltext(e)), uniqueID: "crm-affar-radera" });
      }
      void hamta();
    };
    visa({
      body: text({ sv: `${namnPa(a)} ligger i papperskorgen i 30 dagar.`, en: `${namnPa(a)} is in the trash for 30 days.` }),
      endContent: <Button size="sm" variant="secondary" label={text({ sv: "Ångra", en: "Undo" })} onClick={() => void aterstall()} />,
      autoHideDuration: 10000,
      uniqueID: "crm-affar-radera"
    });
    void hamta();
  }

  // ---- Det som visas --------------------------------------------------------

  const synliga = useMemo(() => (tavla?.stages ?? []).map((s) => (fraga ? raknat(s, s.deals.filter(matchar)) : s)), [tavla, fraga, matchar]);
  const traffar = synliga.reduce((n, s) => n + s.count, 0);

  const oppna = steg.length ? (tavla?.stages ?? []).filter((s) => s.type === "open") : [];
  const oppnaAntal = oppna.reduce((n, s) => n + s.count, 0);
  // Öppet värde och viktat värde (belopp gånger sannolikhet), i kronor. Annan valuta räknas inte in.
  const sek = oppna.flatMap((s) => s.deals.filter((a) => (a.currency || "SEK") === "SEK").map((a) => ({ a, s })));
  const oppetVarde = sek.reduce((n, { a }) => n + (a.amount ?? 0), 0);
  const viktat = Math.round(sek.reduce((n, { a, s }) => n + ((a.amount ?? 0) * (sannolikhet(a, s) ?? 0)) / 100, 0));

  const idag = idagLokalt();
  const nyAffar = (stegId: string | null = null) => setFormular({ affar: null, fokus: null, stegId });

  const kort = (a: Affar, s: Tavelsteg) => {
    const bolaget = a.company_id ? bolagsnamn(a.company_id) : null;
    const pengar = belopp(a.amount, a.currency, locale);
    const sen = s.type === "open" && a.expected_close_date != null && a.expected_close_date.slice(0, 10) < idag;
    const namn = a.name ?? text({ sv: "Namnlös affär", en: "Unnamed deal" });
    return (
      <div
        key={a.id}
        role="button"
        tabIndex={0}
        data-kort={a.id}
        data-dras={dras === a.id || undefined}
        data-vald={post?.id === a.id || undefined}
        className="crm-tavla-kort"
        draggable={!smal && !flyttar}
        onClick={() => {
          setPost(a);
          sattPost(a.id);
        }}
        onKeyDown={(e) => {
          if (e.key !== "Enter" && e.key !== " ") return;
          e.preventDefault();
          setPost(a);
          sattPost(a.id);
        }}
        onDragStart={(e) => {
          e.dataTransfer.effectAllowed = "move";
          e.dataTransfer.setData("text/plain", a.id);
          setDras(a.id);
        }}
        onDragEnd={slapp}
      >
        <span className="flex items-start gap-2">
          <span className="line-clamp-2 min-w-0 flex-1 text-[0.875rem] font-semibold leading-5 text-ink">
            <span className="sr-only">{text({ sv: "Öppna ", en: "Open " })}</span>
            {namn}
          </span>
          {a.owner ? (
            <span className="inline-flex shrink-0" title={text({ sv: `Ansvarig: ${a.owner}`, en: `Owner: ${a.owner}` })}>
              <span aria-hidden className="inline-flex">
                <Avatar name={a.owner} size={20} tooltip={false} className={`crm-avatar ${tonklass(tonFor(a.owner))}`} />
              </span>
              <span className="sr-only">{text({ sv: `, ansvarig ${a.owner}`, en: `, owner ${a.owner}` })}</span>
            </span>
          ) : null}
        </span>
        {bolaget ? <Postchip namn={bolaget} vikt="lugn" storlek="sm" /> : null}
        {pengar || a.expected_close_date ? (
          <span className="flex items-center justify-between gap-2 text-[0.8125rem]">
            <span className="font-semibold tabular-nums text-ink">{pengar ?? ""}</span>
            {a.expected_close_date ? (
              <span
                className={`inline-flex items-center gap-1 tabular-nums ${sen ? "text-danger" : "text-ink-muted"}`}
                title={sen ? text({ sv: "Väntat avslut har passerat", en: "The expected close date has passed" }) : text({ sv: "Väntat avslut", en: "Expected close" })}
              >
                {/* Ett passerat datum har en egen ikon: färgen ensam bär inte betydelsen. */}
                <Icon icon={sen ? CalendarX2 : CalendarClock} size="xsm" color="inherit" />
                <span>{dagtext(a.expected_close_date, locale, true)}</span>
                {sen ? <span className="sr-only">{text({ sv: ", har passerat", en: ", has passed" })}</span> : null}
              </span>
            ) : null}
          </span>
        ) : null}
      </div>
    );
  };

  const linje = <div aria-hidden className="crm-tavla-slapp" />;

  const kolumn = (s: Tavelsteg) => {
    const malHar = mal?.stegId === s.id;
    return (
      <section
        key={s.id}
        className="crm-tavla-kolumn"
        data-mal={(dras != null && malHar) || undefined}
        aria-label={text({ sv: `${s.name}, ${s.count === 1 ? "1 affär" : `${s.count} affärer`}`, en: `${s.name}, ${s.count === 1 ? "1 deal" : `${s.count} deals`}` })}
        onDragOver={(e) => {
          if (!dras) return;
          e.preventDefault();
          e.dataTransfer.dropEffect = "move";
          const nytt = malFor(e, s.id);
          setMal((nu) => (nu?.stegId === nytt.stegId && nu.foreId === nytt.foreId ? nu : nytt));
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setMal((nu) => (nu?.stegId === s.id ? null : nu));
        }}
        onDrop={(e) => {
          e.preventDefault();
          const id = dras ?? e.dataTransfer.getData("text/plain");
          const till = malFor(e, s.id);
          slapp();
          if (id) void flytta(id, till);
        }}
      >
        <header className="crm-tavla-huvud">
          <Prick ton={STEGTON[s.type].ton} />
          <Text as="h2" weight="semibold" maxLines={1}>
            {s.name}
            {/* Stegets typ sägs i ord för skärmläsaren: pricken visar den bara med färg. */}
            {s.type !== "open" ? <span className="sr-only">{`, ${text(STEGTYPER[s.type]).toLocaleLowerCase(sprak)}`}</span> : null}
          </Text>
          <Badge variant="neutral" label={<span className="tabular-nums">{s.count}</span>} />
          <span className="ml-auto whitespace-nowrap text-[0.8125rem] tabular-nums text-ink-muted">{s.count ? summa(s.amount_by_currency, locale) : ""}</span>
        </header>
        <div className="crm-tavla-kortlista">
          {s.deals.map((a) => (
            <div key={a.id} className="flex flex-col gap-2">
              {dras && malHar && mal?.foreId === a.id ? linje : null}
              {kort(a, s)}
            </div>
          ))}
          {dras && malHar && mal?.foreId == null ? linje : null}
        </div>
        {s.type === "open" && !fraga ? (
          <button type="button" className="crm-tavla-lagg-till" onClick={() => nyAffar(s.id)} aria-label={text({ sv: `Lägg till affär i ${s.name}`, en: `Add deal to ${s.name}` })}>
            <Icon icon={Plus} size="sm" color="inherit" />
            <span>{text({ sv: "Lägg till affär", en: "Add deal" })}</span>
          </button>
        ) : null}
      </section>
    );
  };

  const skelett = (
    <div className="crm-tavla" role="status" aria-busy="true" aria-label={text({ sv: "Hämtar affärerna", en: "Loading the deals" })}>
      {Array.from({ length: smal ? 2 : 5 }, (_, k) => (
        <div key={k} className="crm-tavla-kolumn">
          <div className="crm-tavla-huvud">
            <Skeleton width={8} height={8} radius="rounded" index={k} />
            <Skeleton width={`${40 + ((k * 17) % 30)}%`} height={10} radius="rounded" index={k} />
          </div>
          {Array.from({ length: 3 - (k % 3) }, (_, i) => (
            <div key={i} className="crm-tavla-kort">
              <Skeleton width={`${60 + ((i * 13 + k * 7) % 30)}%`} height={10} radius="rounded" index={i + k} />
              <Skeleton width="45%" height={8} radius="rounded" index={i + k} />
              <Skeleton width="30%" height={8} radius="rounded" index={i + k} />
            </div>
          ))}
        </div>
      ))}
    </div>
  );

  const vyer: { v: Vy; namn: string }[] = [
    { v: "tavla", namn: text({ sv: "Tavla", en: "Board" }) },
    { v: "papperskorg", namn: text({ sv: "Papperskorg", en: "Trash" }) }
  ];

  return (
    <Sida
      objekt="affarer"
      utfyllnad={vy === "tavla" ? "tavla" : "tabell"}
      rubrik={text({ sv: "Affärer", en: "Deals" })}
      antal={tavla ? oppnaAntal.toLocaleString(sprak) : undefined}
      atgarder={
        <span data-ny-affar>
          <Button variant="primary" label={text({ sv: "Ny affär", en: "New deal" })} icon={<Icon icon={Plus} size="sm" />} onClick={() => nyAffar()} />
        </span>
      }
      vyrad={
        smal ? (
          <Selector
            label={text({ sv: "Vy", en: "View" })}
            isLabelHidden
            variant="secondary"
            size="md"
            value={vy}
            onChange={(v) => v && setVy(v as Vy)}
            options={vyer.map((f) => ({ value: f.v, label: f.namn }))}
          />
        ) : (
          <>
            <Vyval value={vy} onChange={setVy} label={text({ sv: "Vy", en: "View" })} val={vyer} />
            {vy === "tavla" && tavla && oppnaAntal > 0 ? (
              <span className="ml-3 hidden items-center gap-x-5 text-[0.8125rem] lg:inline-flex" role="status">
                <span>
                  <span className="crm-raknefot-etikett">{text({ sv: "Öppet värde", en: "Open value" })}</span>{" "}
                  <span className="crm-raknefot-tal">{belopp(oppetVarde, "SEK", locale)}</span>
                </span>
                <span title={text({ sv: "Beloppen gånger sannolikheten att affären vinns", en: "The amounts times the probability that the deal is won" })}>
                  <span className="crm-raknefot-etikett">{text({ sv: "Viktat", en: "Weighted" })}</span>{" "}
                  <span className="crm-raknefot-tal">{belopp(viktat, "SEK", locale)}</span>
                </span>
              </span>
            ) : null}
          </>
        )
      }
      vyradHoger={
        <div className="min-w-0 flex-1 sm:w-[260px] sm:flex-none">
          <TextInput
            type="search"
            label={text({ sv: "Sök affärer", en: "Search deals" })}
            isLabelHidden
            placeholder={text({ sv: "Sök affär, bolag eller ansvarig", en: "Search deal, company or owner" })}
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
      {vy === "papperskorg" ? (
        <Papperskorg<Affar>
          objekt="deals"
          fraga={sok.trim()}
          namnPa={(a) => a.name ?? text({ sv: "Namnlös affär", en: "Unnamed deal" })}
          oppnaPost={(id) => {
            setVy("tavla");
            sattPost(id);
          }}
          aterstalld={() => void hamta()}
        />
      ) : fel && !tavla ? (
        <div className="p-4 sm:p-6">
          <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />} />
        </div>
      ) : !tavla ? (
        skelett
      ) : fraga && traffar === 0 ? (
        <div className="py-12">
          <EmptyState
            icon={<Icon icon={SearchX} size="lg" color="secondary" />}
            title={text({ sv: `Inga affärer matchar ”${sok.trim()}”`, en: `No deals match “${sok.trim()}”` })}
            description={text({ sv: "Sökningen går på affärens namn, bolaget och den ansvariga.", en: "The search covers the deal's name, the company and the owner." })}
            actions={<Button label={text({ sv: "Rensa sökningen", en: "Clear the search" })} variant="secondary" onClick={() => setSok("")} />}
          />
        </div>
      ) : (
        <div className="crm-tavla" onDragEnd={slapp}>
          {synliga.map(kolumn)}
        </div>
      )}

      <AffarPanel
        affar={post}
        laddar={postId != null && post == null}
        steg={steg}
        bolagsnamn={bolagsnamn}
        bolagVag={`${bas}/bolag`}
        personVag={`${bas}/personer`}
        flyttar={flyttar}
        plats={platsFor(post)}
        flyttaPlats={flyttaPlats}
        stang={() => stangPanel(post?.id ?? null)}
        redigera={(falt) => post && setFormular({ affar: post, fokus: falt ?? null, stegId: null })}
        flytta={(a, stegId) => void flytta(a.id, { stegId, foreId: null })}
        taBort={(a) => setRadera(a)}
      />

      <AffarFormular
        oppen={formular != null}
        affar={formular?.affar ?? null}
        steg={steg}
        bolag={bolag}
        forvalStegId={formular?.stegId}
        forvalBolagId={formular?.bolagId}
        fokus={formular?.fokus}
        stang={() => setFormular(null)}
        sparat={(a, ny) => {
          setFormular(null);
          if (ny) {
            setPost(a);
            sattPost(a.id);
          } else if (post?.id === a.id) setPost(a);
          visa({
            body: ny
              ? text({ sv: `${a.name ?? "Affären"} är skapad.`, en: `${a.name ?? "The deal"} is created.` })
              : text({ sv: `${a.name ?? "Affären"} är sparad.`, en: `${a.name ?? "The deal"} is saved.` }),
            uniqueID: "crm-affar-sparad"
          });
          void hamta();
        }}
      />

      <AlertDialog
        isOpen={radera != null}
        onOpenChange={(o) => !o && setRadera(null)}
        title={text({ sv: `Ta bort ${radera?.name ?? "affären"}?`, en: `Delete ${radera?.name ?? "the deal"}?` })}
        description={text({
          sv: "Affären flyttas till papperskorgen och kan återställas i 30 dagar. Därefter töms den.",
          en: "The deal moves to the trash and can be restored for 30 days. After that it is emptied."
        })}
        actionLabel={text({ sv: "Ta bort", en: "Delete" })}
        cancelLabel={text({ sv: "Avbryt", en: "Cancel" })}
        onAction={() => radera && void taBort(radera)}
      />
    </Sida>
  );
}
