"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Plus, Trash2 } from "lucide-react";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { Selector } from "@astryxdesign/core/Selector";
import { HStack } from "@astryxdesign/core/Stack";
import { TextInput } from "@astryxdesign/core/TextInput";
import { STEGTON } from "@/components/crm/app/AffarPanel";
import { Prick, useSmal } from "@/components/crm/app/kit";
import { STEGTYPER, type Affar, type Affarssteg, type Stegtyp, type Tavelsteg } from "@/lib/crm/affar";
import { CrmFel, crmAnrop, type Sida as Svarssida } from "@/lib/crm/api";
import { useLocale, type Localized } from "@/lib/i18n";

/** En rad i utkastet: ett sparat steg (med id) eller ett nytt. */
type Rad = { nyckel: string; id: string | null; namn: string; sannolikhet: string; typ: Stegtyp; affarer: number };
/** Felets plats: radens nyckel och fältet (`namn` eller `tal`). */
type Felnyckel = `${string}:${"namn" | "tal"}`;

const MAX_NAMN = 60;
const TYPER: Stegtyp[] = ["open", "won", "lost"];
const gemener = (s: string) => s.trim().toLocaleLowerCase("sv");

const tillRad = (s: Affarssteg & { count?: number }): Rad => ({ nyckel: s.id, id: s.id, namn: s.name, sannolikhet: String(s.probability), typ: s.type, affarer: s.count ?? 0 });

/**
 * I vilken ordning typbytena kan skickas så att tavlan efter varje anrop har
 * ett öppet, ett vunnet och ett förlorat steg (API:t prövar `stage_required`
 * efter varje ändring). `typer` är lägets typer, de nya stegen inräknade.
 * `null` när ingen ordning finns: två steg som byter typ med varandra.
 */
export function typordning(typer: Map<string, Stegtyp>, byten: { id: string; till: Stegtyp }[]): string[] | null {
  const nu = new Map(typer);
  const kvar = [...byten];
  const ordning: string[] = [];
  while (kvar.length) {
    const plats = kvar.findIndex((b) => {
      const efter = new Map(nu).set(b.id, b.till);
      return TYPER.every((t) => [...efter.values()].includes(t));
    });
    if (plats < 0) return null;
    const [b] = kvar.splice(plats, 1);
    nu.set(b.id, b.till);
    ordning.push(b.id);
  }
  return ordning;
}

/**
 * Stegen på affärstavlan: byt namn, ordning, sannolikhet och typ, lägg till och
 * ta bort (`/v1/deal-stages`). Ändringarna samlas i ett utkast och sparas med
 * ett klick; Avbryt lämnar tavlan som den var.
 *
 * API:ts regler prövas här först, så att felet står vid raden: namnen ska vara
 * olika, ett steg med affärer (också raderade som går att återställa) går inte
 * att ta bort, och det ska alltid finnas minst ett öppet, ett vunnet och ett
 * förlorat steg. API:t tar en ändring i taget och prövar reglerna efter varje:
 * sparningen lägger därför ändringarna i en ordning där varje mellanläge är
 * giltigt (se `spara`).
 */
export function Stegdialog({
  oppen,
  steg,
  stang,
  sparat
}: Readonly<{ oppen: boolean; steg: Tavelsteg[]; stang: () => void; /** `helt` är falskt när bara en del hann sparas. */ sparat: (andrat: boolean, helt: boolean) => void }>) {
  const { text } = useLocale();
  const smal = useSmal();
  const knapp = smal ? "md" : "sm";
  const [rader, setRader] = useState<Rad[]>([]);
  const [radfel, setRadfel] = useState<Partial<Record<Felnyckel, Localized>>>({});
  const [allmant, setAllmant] = useState<Localized | null>(null);
  const [sparar, setSparar] = useState(false);
  const [kollar, setKollar] = useState<string | null>(null);
  // Sägs upp för skärmläsare när ett steg flyttats eller tagits bort: regionen finns hela tiden och byter bara text.
  const [besked, setBesked] = useState("");
  const lopnr = useRef(0);
  const lista = useRef<HTMLOListElement>(null);

  useEffect(() => {
    if (!oppen) return;
    setRader(steg.map(tillRad));
    setRadfel({});
    setAllmant(null);
    setBesked("");
    // Utkastet börjar i tavlans läge när dialogen öppnas, inte varje gång tavlan hämtas om.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [oppen]);

  const fokusera = (valjare: string) => window.setTimeout(() => lista.current?.querySelector<HTMLElement>(valjare)?.focus(), 60);

  const andra = (nyckel: string, del: Partial<Rad>) => {
    setRader((forr) => forr.map((r) => (r.nyckel === nyckel ? { ...r, ...del } : r)));
    setRadfel((f) => Object.fromEntries(Object.entries(f).filter(([k]) => !k.startsWith(`${nyckel}:`))));
    setAllmant(null);
  };

  const flytta = (index: number, steglangd: -1 | 1) => {
    const mal = index + steglangd;
    if (mal < 0 || mal >= rader.length) return;
    const ny = [...rader];
    [ny[index], ny[mal]] = [ny[mal], ny[index]];
    setRader(ny);
    const r = rader[index];
    const namn = r.namn.trim() || text({ sv: "Steget", en: "The stage" });
    setBesked(text({ sv: `${namn}, steg ${mal + 1} av ${ny.length}`, en: `${namn}, stage ${mal + 1} of ${ny.length}` }));
    // Raden byter plats i dokumentet och tappar fokus: det läggs tillbaka på samma knapp, eller på den andra när raden nått kanten.
    const vid = (riktning: "upp" | "ned") => `[data-steg="${r.nyckel}"] [data-flytt="${riktning}"] button:not(:disabled), [data-steg="${r.nyckel}"] [data-flytt="${riktning}"]:not(:disabled)`;
    const kant = steglangd < 0 ? mal === 0 : mal === ny.length - 1;
    fokusera(vid(kant ? (steglangd < 0 ? "ned" : "upp") : steglangd < 0 ? "upp" : "ned"));
  };

  const laggTill = () => {
    const nyckel = `ny${++lopnr.current}`;
    setRader((forr) => {
      // Ett nytt steg är öppet och hamnar efter det sista öppna, före Vunnen och Förlorad.
      const sista = forr.map((r) => r.typ).lastIndexOf("open");
      const plats = sista < 0 ? forr.length : sista + 1;
      return [...forr.slice(0, plats), { nyckel, id: null, namn: "", sannolikhet: "50", typ: "open", affarer: 0 }, ...forr.slice(plats)];
    });
    fokusera(`[data-steg="${nyckel}"] input`);
  };

  /**
   * Tar bort raden ur utkastet. Ett sparat steg frågas först om raderade
   * affärer: tavlan räknar bara de levande, men API:t säger nej också när
   * papperskorgen har en affär i steget.
   */
  async function taBort(r: Rad) {
    if (kollar) return;
    if (r.id) {
      setKollar(r.nyckel);
      try {
        const raderade = await crmAnrop<Svarssida<Affar>>(`/v1/deals?only_deleted=true&limit=1&stage_id=${encodeURIComponent(r.id)}`);
        if (raderade.data.length) {
          setRadfel((f) => ({
            ...f,
            [`${r.nyckel}:namn`]: {
              sv: "Steget har affärer i papperskorgen. Återställ dem eller vänta tills de tömts, så går steget att ta bort.",
              en: "The stage has deals in the trash. Restore them or wait until they are purged, then the stage can be deleted."
            }
          }));
          return;
        }
      } catch {
        // Frågan gick inte att ställa: API:t prövar regeln igen när utkastet sparas.
      } finally {
        setKollar(null);
      }
    }
    const index = rader.findIndex((x) => x.nyckel === r.nyckel);
    const granne = rader[index + 1] ?? rader[index - 1];
    setRader((forr) => forr.filter((x) => x.nyckel !== r.nyckel));
    setAllmant(null);
    setBesked(text({ sv: `${r.namn.trim() || "Steget"} tas bort när du sparar.`, en: `${r.namn.trim() || "The stage"} is deleted when you save.` }));
    fokusera(granne ? `[data-steg="${granne.nyckel}"] input` : "[data-lagg-till] button, [data-lagg-till]");
  }

  /** Det som API:t skulle säga nej till, prövat i utkastet. */
  function provat(): boolean {
    const fel: Partial<Record<Felnyckel, Localized>> = {};
    const sedda = new Set<string>();
    for (const r of rader) {
      const namn = r.namn.trim();
      const tal = Number(r.sannolikhet);
      if (!namn) fel[`${r.nyckel}:namn`] = { sv: "Steget behöver ett namn.", en: "The stage needs a name." };
      else if (namn.length > MAX_NAMN) fel[`${r.nyckel}:namn`] = { sv: "Namnet får vara högst 60 tecken.", en: "The name may be at most 60 characters." };
      else if (sedda.has(gemener(namn))) fel[`${r.nyckel}:namn`] = { sv: "Två steg kan inte heta samma sak.", en: "Two stages cannot have the same name." };
      if (r.sannolikhet.trim() === "" || !Number.isInteger(tal) || tal < 0 || tal > 100)
        fel[`${r.nyckel}:tal`] = { sv: "0 till 100", en: "0 to 100" };
      sedda.add(gemener(namn));
    }
    setRadfel(fel);
    if (TYPER.some((t) => !rader.some((r) => r.typ === t))) {
      setAllmant({
        sv: "Tavlan behöver minst ett öppet steg, ett vunnet och ett förlorat. Det är så en affär avslutas.",
        en: "The board needs at least one open stage, one won and one lost. That is how a deal is closed."
      });
      return false;
    }
    return Object.keys(fel).length === 0;
  }

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    if (sparar || !provat()) return;
    const fore = new Map(steg.map((s) => [s.id, s]));
    const kvar = new Set(rader.map((r) => r.id).filter(Boolean));
    const bort = steg.filter((s) => !kvar.has(s.id));

    // Typbytenas ordning prövas innan något skickas. De nya stegen skapas först och räknas därför in.
    const typer = new Map<string, Stegtyp>([...steg.map((s) => [s.id, s.type] as [string, Stegtyp]), ...rader.filter((r) => !r.id).map((r) => [r.nyckel, r.typ] as [string, Stegtyp])]);
    const byten = rader.filter((r) => r.id && fore.get(r.id) && fore.get(r.id)!.type !== r.typ).map((r) => ({ id: r.id!, till: r.typ }));
    const ordnadeByten = typordning(typer, byten);
    if (!ordnadeByten) {
      setAllmant({
        sv: "Två steg byter typ med varandra, och tavlan skulle för ett ögonblick sakna ett vunnet eller förlorat steg. Byt namn på stegen i stället, eller spara ett typbyte i taget med ett extra steg emellan.",
        en: "Two stages swap type with each other, and the board would for a moment lack a won or lost stage. Rename the stages instead, or save one type change at a time with an extra stage in between."
      });
      return;
    }

    setSparar(true);
    setAllmant(null);
    let andrat = false;
    let vid: Felnyckel | null = null;
    const namnNu = new Map(steg.map((s) => [s.id, s.name]));
    const patch = async (id: string, del: Record<string, unknown>) => {
      await crmAnrop<Affarssteg>(`/v1/deal-stages/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(del) });
      andrat = true;
    };
    try {
      // 1. Namnen är unika i varje mellanläge. Ett sparat steg vars nuvarande namn ska bäras av en ANNAN rad
      //    (två steg som byter namn, eller ett nytt steg med namnet på ett som tas bort) får först ett tillfälligt namn.
      const onskade = new Map(rader.map((r) => [gemener(r.namn), r.id ?? r.nyckel]));
      let n = 0;
      for (const s of steg) {
        const tar = onskade.get(gemener(s.name));
        if (tar == null || tar === s.id) continue;
        const tillfalligt = `${s.name.slice(0, MAX_NAMN - 8)} (${++n})`;
        vid = kvar.has(s.id) ? `${s.id}:namn` : null;
        await patch(s.id, { name: tillfalligt });
        namnNu.set(s.id, tillfalligt);
      }
      // 2. Nya steg skapas, så att det sista steget av en typ har sin ersättare innan det ändras eller tas bort.
      const nya = new Map<string, string>();
      for (const r of rader) {
        if (r.id) continue;
        vid = `${r.nyckel}:namn`;
        const ny = await crmAnrop<Affarssteg>("/v1/deal-stages", { method: "POST", body: JSON.stringify({ name: r.namn.trim(), probability: Number(r.sannolikhet), type: r.typ }) });
        nya.set(r.nyckel, ny.id);
        andrat = true;
      }
      // 3. Namn och sannolikhet på de sparade stegen.
      for (const r of rader) {
        const s = r.id ? fore.get(r.id) : undefined;
        if (!r.id || !s) continue;
        const del: Record<string, unknown> = {};
        if (r.namn.trim() !== namnNu.get(r.id)) del.name = r.namn.trim();
        if (Number(r.sannolikhet) !== s.probability) del.probability = Number(r.sannolikhet);
        if (!Object.keys(del).length) continue;
        vid = "name" in del ? `${r.nyckel}:namn` : `${r.nyckel}:tal`;
        await patch(r.id, del);
      }
      // 4. Typbytena, i ordningen som håller tavlan hel.
      for (const id of ordnadeByten) {
        vid = `${id}:namn`;
        await patch(id, { type: rader.find((r) => r.id === id)!.typ });
      }
      // 5. Borttagningarna. Utkastet har alla tre typerna kvar, så varje mellanläge har det också.
      vid = null;
      for (const s of bort) {
        await crmAnrop<null>(`/v1/deal-stages/${encodeURIComponent(s.id)}`, { method: "DELETE" });
        andrat = true;
      }
      // 6. Ordningen. API:t lägger ett nytt steg sist: den skickas när den skiljer sig från det.
      const ordning = rader.map((r) => r.id ?? nya.get(r.nyckel)!);
      const nu = [...steg.filter((s) => kvar.has(s.id)).map((s) => s.id), ...nya.values()];
      if (ordning.some((id, i) => id !== nu[i])) {
        await crmAnrop<unknown>("/v1/deal-stages/reorder", { method: "POST", body: JSON.stringify({ ids: ordning }) });
        andrat = true;
      }
      sparat(andrat, true);
      stang();
    } catch (orsak) {
      let fel: Localized = orsak instanceof CrmFel ? orsak.text : { sv: "Okänt fel.", en: "Unknown error." };
      if (orsak instanceof CrmFel && orsak.kod === "stage_in_use") {
        fel = {
          sv: "Ett steg som skulle tas bort har affärer, levande eller i papperskorgen. Flytta, återställ eller töm dem först.",
          en: "A stage that was to be deleted has deals, live or in the trash. Move, restore or purge them first."
        };
      }
      // Det som hann sparas står kvar: utkastet läses om från API:t, så att dialogen visar det som gäller.
      setAllmant(andrat ? { sv: `${fel.sv} Det som hann sparas står kvar.`, en: `${fel.en} What was saved before that remains.` } : fel);
      if (andrat) {
        sparat(true, false);
        try {
          const svar = await crmAnrop<{ data: Affarssteg[] }>("/v1/deal-stages");
          const antal = new Map(steg.map((s) => [s.id, s.count]));
          setRader(svar.data.map((s) => tillRad({ ...s, count: antal.get(s.id) ?? 0 })));
          setRadfel({});
        } catch {
          // Utkastet står kvar som det var.
        }
      } else if (vid) {
        setRadfel({ [vid]: fel });
      }
    } finally {
      setSparar(false);
    }
  }

  const status = (nyckel: Felnyckel) => (radfel[nyckel] ? { type: "error" as const, message: text(radfel[nyckel]!) } : undefined);
  const last = sparar || kollar != null;

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && !sparar && stang()} purpose="form" width={680}>
      <Layout
        header={
          <DialogHeader
            title={text({ sv: "Stegen på tavlan", en: "The stages on the board" })}
            subtitle={text({ sv: "Ordningen här är kolumnernas ordning. Sannolikheten gäller affärer som inte har en egen.", en: "The order here is the order of the columns. The probability applies to deals without their own." })}
            onOpenChange={(o) => !o && !sparar && stang()}
          />
        }
        content={
          <LayoutContent>
            <form id="crm-stegformular" onSubmit={spara} noValidate className="flex flex-col gap-4">
              <div role="alert">{allmant ? <Banner status="error" container="card" title={text({ sv: "Det gick inte att spara", en: "Could not save" })} description={text(allmant)} /> : null}</div>
              <span role="status" className="sr-only">
                {besked}
              </span>
              <ol ref={lista} className="flex flex-col">
                {rader.map((r, i) => {
                  const namn = r.namn.trim() || text({ sv: "steget", en: "the stage" });
                  const harAffarer = r.affarer > 0;
                  return (
                    <li key={r.nyckel} data-steg={r.nyckel} className="crm-stegrad">
                      <span className="crm-stegrad-flytt">
                        <span data-flytt="upp" className="inline-flex">
                          <IconButton
                            size={knapp}
                            variant="ghost"
                            icon={<Icon icon={ChevronUp} size="sm" />}
                            label={text({ sv: `Flytta upp ${namn}`, en: `Move ${namn} up` })}
                            isDisabled={i === 0 || last}
                            onClick={() => flytta(i, -1)}
                          />
                        </span>
                        <span data-flytt="ned" className="inline-flex">
                          <IconButton
                            size={knapp}
                            variant="ghost"
                            icon={<Icon icon={ChevronDown} size="sm" />}
                            label={text({ sv: `Flytta ned ${namn}`, en: `Move ${namn} down` })}
                            isDisabled={i === rader.length - 1 || last}
                            onClick={() => flytta(i, 1)}
                          />
                        </span>
                      </span>
                      <span className="crm-stegrad-namn">
                        <TextInput
                          label={text({ sv: `Namn på steg ${i + 1}`, en: `Name of stage ${i + 1}` })}
                          isLabelHidden
                          placeholder={text({ sv: "Stegets namn", en: "Stage name" })}
                          value={r.namn}
                          onChange={(v) => andra(r.nyckel, { namn: v })}
                          width="100%"
                          isDisabled={sparar}
                          status={status(`${r.nyckel}:namn`)}
                        />
                      </span>
                      <span className="crm-stegrad-tal" data-fel={radfel[`${r.nyckel}:tal`] ? "true" : undefined}>
                        <TextInput
                          label={text({ sv: `Sannolikhet i procent för ${namn}`, en: `Probability in percent for ${namn}` })}
                          isLabelHidden
                          inputMode="numeric"
                          value={r.sannolikhet}
                          onChange={(v) => andra(r.nyckel, { sannolikhet: v.replace(/[^\d]/g, "").slice(0, 3) })}
                          width="100%"
                          isDisabled={sparar}
                          status={status(`${r.nyckel}:tal`)}
                        />
                      </span>
                      <span className="crm-stegrad-typ">
                        <Selector
                          label={text({ sv: `Typ för ${namn}`, en: `Type for ${namn}` })}
                          isLabelHidden
                          value={r.typ}
                          onChange={(v) => v && andra(r.nyckel, { typ: v as Stegtyp })}
                          options={TYPER.map((t) => ({ value: t, label: text(STEGTYPER[t]), icon: <Prick ton={STEGTON[t].ton} /> }))}
                          width="100%"
                          isDisabled={sparar}
                        />
                      </span>
                      <span className="crm-stegrad-bort">
                        <IconButton
                          size={knapp}
                          variant="ghost"
                          icon={<Icon icon={Trash2} size="sm" />}
                          label={
                            harAffarer
                              ? text({ sv: `${namn} har affärer och går inte att ta bort. Flytta dem först.`, en: `${namn} has deals and cannot be deleted. Move them first.` })
                              : text({ sv: `Ta bort ${namn}`, en: `Delete ${namn}` })
                          }
                          isLoading={kollar === r.nyckel}
                          isDisabled={harAffarer || last}
                          onClick={() => void taBort(r)}
                        />
                      </span>
                    </li>
                  );
                })}
              </ol>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                <span data-lagg-till className="inline-flex">
                  <Button size="sm" variant="secondary" label={text({ sv: "Lägg till steg", en: "Add stage" })} icon={<Icon icon={Plus} size="sm" />} isDisabled={last} onClick={laggTill} />
                </span>
                {rader.some((r) => r.affarer > 0) ? (
                  <span className="text-[0.8125rem] text-ink-muted">
                    {text({ sv: "Ett steg med affärer går inte att ta bort. Flytta affärerna först.", en: "A stage with deals cannot be deleted. Move the deals first." })}
                  </span>
                ) : null}
              </div>
            </form>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Avbryt", en: "Cancel" })} variant="ghost" isDisabled={sparar} onClick={stang} />
              <Button type="submit" form="crm-stegformular" variant="primary" label={text({ sv: "Spara", en: "Save" })} isLoading={sparar} />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
