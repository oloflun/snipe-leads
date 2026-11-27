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
import { Prick } from "@/components/crm/app/kit";
import { STEGTYPER, type Affarssteg, type Stegtyp, type Tavelsteg } from "@/lib/crm/affar";
import { CrmFel, crmAnrop } from "@/lib/crm/api";
import { useLocale, type Localized } from "@/lib/i18n";

/** En rad i utkastet: ett sparat steg (med id) eller ett nytt. */
type Rad = { nyckel: string; id: string | null; namn: string; sannolikhet: string; typ: Stegtyp; affarer: number };

const MAX_NAMN = 60;

const tillRad = (s: Affarssteg & { count?: number }): Rad => ({ nyckel: s.id, id: s.id, namn: s.name, sannolikhet: String(s.probability), typ: s.type, affarer: s.count ?? 0 });

/**
 * Stegen på affärstavlan: byt namn, ordning, sannolikhet och typ, lägg till och
 * ta bort (`/v1/deal-stages`). Ändringarna samlas i ett utkast och sparas med
 * ett klick; Avbryt lämnar tavlan som den var.
 *
 * API:ts regler prövas här först, så att felet står vid raden: namnen ska vara
 * olika, ett steg med affärer går inte att ta bort, och det ska alltid finnas
 * minst ett öppet, ett vunnet och ett förlorat steg.
 */
export function Stegdialog({ oppen, steg, stang, sparat }: Readonly<{ oppen: boolean; steg: Tavelsteg[]; stang: () => void; sparat: (andrat: boolean) => void }>) {
  const { text } = useLocale();
  const [rader, setRader] = useState<Rad[]>([]);
  const [radfel, setRadfel] = useState<Record<string, Localized>>({});
  const [allmant, setAllmant] = useState<Localized | null>(null);
  const [sparar, setSparar] = useState(false);
  const lopnr = useRef(0);
  const lista = useRef<HTMLOListElement>(null);

  useEffect(() => {
    if (!oppen) return;
    setRader(steg.map(tillRad));
    setRadfel({});
    setAllmant(null);
    // Utkastet börjar i tavlans läge när dialogen öppnas, inte varje gång tavlan hämtas om.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [oppen]);

  const andra = (nyckel: string, del: Partial<Rad>) => {
    setRader((forr) => forr.map((r) => (r.nyckel === nyckel ? { ...r, ...del } : r)));
    setRadfel((f) => Object.fromEntries(Object.entries(f).filter(([k]) => k !== nyckel)));
    setAllmant(null);
  };

  const flytta = (index: number, steglangd: -1 | 1) => {
    setRader((forr) => {
      const mal = index + steglangd;
      if (mal < 0 || mal >= forr.length) return forr;
      const ny = [...forr];
      [ny[index], ny[mal]] = [ny[mal], ny[index]];
      return ny;
    });
  };

  const laggTill = () => {
    const nyckel = `ny${++lopnr.current}`;
    setRader((forr) => {
      // Ett nytt steg är öppet och hamnar efter det sista öppna, före Vunnen och Förlorad.
      const sista = forr.map((r) => r.typ).lastIndexOf("open");
      const plats = sista < 0 ? forr.length : sista + 1;
      return [...forr.slice(0, plats), { nyckel, id: null, namn: "", sannolikhet: "50", typ: "open", affarer: 0 }, ...forr.slice(plats)];
    });
    window.setTimeout(() => lista.current?.querySelector<HTMLInputElement>(`[data-steg="${nyckel}"] input`)?.focus(), 60);
  };

  const taBort = (nyckel: string) => {
    setRader((forr) => forr.filter((r) => r.nyckel !== nyckel));
    setAllmant(null);
  };

  /** Det som API:t skulle säga nej till, prövat i utkastet. */
  function provat(): boolean {
    const fel: Record<string, Localized> = {};
    const sedda = new Map<string, string>();
    for (const r of rader) {
      const namn = r.namn.trim();
      const tal = Number(r.sannolikhet);
      if (!namn) fel[r.nyckel] = { sv: "Steget behöver ett namn.", en: "The stage needs a name." };
      else if (namn.length > MAX_NAMN) fel[r.nyckel] = { sv: "Namnet får vara högst 60 tecken.", en: "The name may be at most 60 characters." };
      else if (sedda.has(namn.toLocaleLowerCase("sv"))) fel[r.nyckel] = { sv: "Två steg kan inte heta samma sak.", en: "Two stages cannot have the same name." };
      else if (r.sannolikhet.trim() === "" || !Number.isInteger(tal) || tal < 0 || tal > 100) fel[r.nyckel] = { sv: "Sannolikheten ska vara ett heltal från 0 till 100.", en: "The probability must be a whole number from 0 to 100." };
      sedda.set(namn.toLocaleLowerCase("sv"), r.nyckel);
    }
    setRadfel(fel);
    const saknad = (["open", "won", "lost"] as const).find((t) => !rader.some((r) => r.typ === t));
    if (saknad) {
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
    setSparar(true);
    setAllmant(null);
    const fore = new Map(steg.map((s) => [s.id, s]));
    const kvar = new Set(rader.map((r) => r.id).filter(Boolean));
    let andrat = false;
    let vid: string | null = null;
    try {
      // Ordningen: skapa nya först (så att det sista steget av en typ har sin ersättare innan det ändras eller tas bort), ändra, ta bort, ordna.
      const nya = new Map<string, string>();
      for (const r of rader) {
        if (r.id) continue;
        vid = r.nyckel;
        const ny = await crmAnrop<Affarssteg>("/v1/deal-stages", { method: "POST", body: JSON.stringify({ name: r.namn.trim(), probability: Number(r.sannolikhet), type: r.typ }) });
        nya.set(r.nyckel, ny.id);
        andrat = true;
      }
      for (const r of rader) {
        if (!r.id) continue;
        const s = fore.get(r.id);
        if (!s) continue;
        const del: Record<string, unknown> = {};
        if (r.namn.trim() !== s.name) del.name = r.namn.trim();
        if (Number(r.sannolikhet) !== s.probability) del.probability = Number(r.sannolikhet);
        if (r.typ !== s.type) del.type = r.typ;
        if (!Object.keys(del).length) continue;
        vid = r.nyckel;
        await crmAnrop<Affarssteg>(`/v1/deal-stages/${encodeURIComponent(r.id)}`, { method: "PATCH", body: JSON.stringify(del) });
        andrat = true;
      }
      vid = null;
      for (const s of steg) {
        if (kvar.has(s.id)) continue;
        await crmAnrop<null>(`/v1/deal-stages/${encodeURIComponent(s.id)}`, { method: "DELETE" });
        andrat = true;
      }
      // API:t lägger ett nytt steg sist: ordningen skickas när den skiljer sig från det.
      const ordning = rader.map((r) => r.id ?? nya.get(r.nyckel)!);
      const nu = [...steg.filter((s) => kvar.has(s.id)).map((s) => s.id), ...nya.values()];
      if (ordning.some((id, i) => id !== nu[i])) {
        await crmAnrop<unknown>("/v1/deal-stages/reorder", { method: "POST", body: JSON.stringify({ ids: ordning }) });
        andrat = true;
      }
      sparat(andrat);
      stang();
    } catch (orsak) {
      const besked: Localized = orsak instanceof CrmFel ? orsak.text : { sv: "Okänt fel.", en: "Unknown error." };
      if (vid) setRadfel({ [vid]: besked });
      // Det som hann sparas står kvar: utkastet läses om från API:t, så att dialogen visar det som gäller.
      setAllmant(
        andrat
          ? { sv: `${besked.sv} Det som hann sparas står kvar.`, en: `${besked.en} What was saved before that remains.` }
          : besked
      );
      if (andrat) {
        sparat(true);
        try {
          const svar = await crmAnrop<{ data: Affarssteg[] }>("/v1/deal-stages");
          const antal = new Map(steg.map((s) => [s.id, s.count]));
          setRader(svar.data.map((s) => tillRad({ ...s, count: antal.get(s.id) ?? 0 })));
          setRadfel({});
        } catch {
          // Utkastet står kvar som det var.
        }
      }
    } finally {
      setSparar(false);
    }
  }

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
              <ol ref={lista} className="flex flex-col">
                {rader.map((r, i) => {
                  const namn = r.namn.trim() || text({ sv: "steget", en: "the stage" });
                  const last = r.affarer > 0;
                  return (
                    <li key={r.nyckel} data-steg={r.nyckel} className="crm-stegrad">
                      <span className="crm-stegrad-flytt">
                        <IconButton
                          size="sm"
                          variant="ghost"
                          icon={<Icon icon={ChevronUp} size="sm" />}
                          label={text({ sv: `Flytta upp ${namn}`, en: `Move ${namn} up` })}
                          isDisabled={i === 0 || sparar}
                          onClick={() => flytta(i, -1)}
                        />
                        <IconButton
                          size="sm"
                          variant="ghost"
                          icon={<Icon icon={ChevronDown} size="sm" />}
                          label={text({ sv: `Flytta ned ${namn}`, en: `Move ${namn} down` })}
                          isDisabled={i === rader.length - 1 || sparar}
                          onClick={() => flytta(i, 1)}
                        />
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
                          status={radfel[r.nyckel] ? { type: "error", message: text(radfel[r.nyckel]) } : undefined}
                        />
                      </span>
                      <span className="crm-stegrad-tal">
                        <TextInput
                          label={text({ sv: `Sannolikhet i procent för ${namn}`, en: `Probability in percent for ${namn}` })}
                          isLabelHidden
                          inputMode="numeric"
                          value={r.sannolikhet}
                          onChange={(v) => andra(r.nyckel, { sannolikhet: v.replace(/[^\d]/g, "").slice(0, 3) })}
                          width="100%"
                          isDisabled={sparar}
                        />
                      </span>
                      <span className="crm-stegrad-typ">
                        <Selector
                          label={text({ sv: `Typ för ${namn}`, en: `Type for ${namn}` })}
                          isLabelHidden
                          value={r.typ}
                          onChange={(v) => v && andra(r.nyckel, { typ: v as Stegtyp })}
                          options={(Object.keys(STEGTYPER) as Stegtyp[]).map((t) => ({ value: t, label: text(STEGTYPER[t]), icon: <Prick ton={STEGTON[t].ton} /> }))}
                          width="100%"
                          isDisabled={sparar}
                        />
                      </span>
                      <span className="crm-stegrad-bort">
                        <IconButton
                          size="sm"
                          variant="ghost"
                          icon={<Icon icon={Trash2} size="sm" />}
                          label={
                            last
                              ? text({ sv: `${namn} har affärer och går inte att ta bort. Flytta dem först.`, en: `${namn} has deals and cannot be deleted. Move them first.` })
                              : text({ sv: `Ta bort ${namn}`, en: `Delete ${namn}` })
                          }
                          isDisabled={last || sparar}
                          onClick={() => taBort(r.nyckel)}
                        />
                      </span>
                    </li>
                  );
                })}
              </ol>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                <Button size="sm" variant="secondary" label={text({ sv: "Lägg till steg", en: "Add stage" })} icon={<Icon icon={Plus} size="sm" />} isDisabled={sparar} onClick={laggTill} />
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
