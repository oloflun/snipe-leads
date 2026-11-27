"use client";

import { useEffect, useRef, useState } from "react";
import { ListFilter } from "lucide-react";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { Icon } from "@astryxdesign/core/Icon";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { Selector } from "@astryxdesign/core/Selector";
import { HStack } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";
import { TextArea } from "@astryxdesign/core/TextArea";
import { TextInput } from "@astryxdesign/core/TextInput";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { PROXYKODER } from "@/lib/crm/felkoder";
import { lista, rader, type Overskrivningar, type Startad, type Startsvar } from "@/lib/crm/iris/korning";
import { useLocale, type Localized } from "@/lib/i18n";
import { icpEtiketter, type IcpNyckel } from "@/lib/leads/icpLabels";
import { lasStruktur, sparaStruktur, type Struktur } from "@/lib/leads/struktur";

type Falt = "antal" | IcpNyckel | "min" | "max" | "egna";
type Omfattning = "research_and_draft" | "research";

const LISTFALT: IcpNyckel[] = ["industries", "exclude_industries", "geography", "roles", "must_have", "deal_breakers"];
/** Fältens ledtext utöver exemplet (LK-004): listorna delas på komma, nischen säger vad den är. */
const LEDTEXT: Partial<Record<IcpNyckel, Localized>> = {
  industries: { sv: "Komma emellan.", en: "Comma separated." },
  must_have: { sv: "Nischen: det varje bolag måste ha.", en: "The niche: what every company must have." }
};

/** Högst så här många egna bolag per körning (schemas.py:LeadsBatchRequest.company_names). */
const EGNA_TAK = 50;

/**
 * Pydantics 422 är en lista med `loc` per fel. Felet hamnar vid sitt fält när
 * platsen går att läsa, annars i rutan överst (LK-001: aldrig "[object Object]").
 */
function serverfel(detail: unknown): { falt: Partial<Record<Falt, string>>; ovrigt: string | null } {
  const falt: Partial<Record<Falt, string>> = {};
  const ovrigt: string[] = [];
  if (Array.isArray(detail)) {
    for (const d of detail) {
      const loc = Array.isArray((d as { loc?: unknown })?.loc) ? ((d as { loc: unknown[] }).loc.map(String) as string[]) : [];
      const msg = String((d as { msg?: unknown })?.msg ?? d);
      const sist = loc[loc.length - 1] ?? "";
      const mal: Falt | null =
        sist === "limit" ? "antal" : loc.includes("company_names") ? "egna" : sist === "anstallda_min" ? "min" : sist === "anstallda_max" ? "max" : (LISTFALT as string[]).includes(sist) ? (sist as Falt) : null;
      if (mal) falt[mal] = msg;
      else ovrigt.push(msg);
    }
    return { falt, ovrigt: ovrigt.length ? ovrigt.join(" ") : null };
  }
  if (typeof detail === "string") {
    // Serverns egen kontroll av storleken (LeadsRunOverrides): meningen står vid Anställda, högst.
    if (/anställda/i.test(detail) && /större än/i.test(detail)) return { falt: { max: detail }, ovrigt: null };
    return { falt, ovrigt: detail };
  }
  if (detail && typeof detail === "object" && typeof (detail as { message?: unknown }).message === "string") {
    return { falt, ovrigt: (detail as { message: string }).message };
  }
  return { falt, ovrigt: null };
}

/**
 * Kör Iris (LK-001 till LK-013, LK-135): dialogen som startar en körning, byggd
 * som BolagFormular. Samma fält, gränser och anrop som dagens formulär
 * (components/leads/LeadsRunForm.tsx): antal leverbara leads 1 till 200,
 * omfattning, utkastens struktur A eller B, och filtret som bara gäller den här
 * körningen (aldrig den sparade målgruppen), med egna bolag.
 *
 * `POST /leads/runs/batch` svarar 202 innan sökningen börjar. Dialogen stängs
 * när körningen är överlämnad, och vyn bakom (KorningarVy) följer sökningen och
 * körningen där den startades. Dialogen stängs inte medan den skickar.
 */
export function KorIris({ oppen, stang, startad }: Readonly<{ oppen: boolean; stang: () => void; startad: (s: Startad) => void }>) {
  const { text, locale } = useLocale();
  const { impersonation } = useDashboard();
  const etik = icpEtiketter(locale);
  const [antal, setAntal] = useState("3");
  // Utkast är standard: Iris levererar leads med utkast (Alunix 2026-09-29). Bara research är ett val.
  const [omfattning, setOmfattning] = useState<Omfattning>("research_and_draft");
  const [struktur, setStruktur] = useState<Struktur>("a");
  const [filterOppet, setFilterOppet] = useState(false);
  const [listor, setListor] = useState<Record<IcpNyckel, string>>({ industries: "", exclude_industries: "", geography: "", roles: "", must_have: "", deal_breakers: "" });
  const [min, setMin] = useState("");
  const [max, setMax] = useState("");
  const [egna, setEgna] = useState("");
  const [fel, setFel] = useState<Partial<Record<Falt, string>>>({});
  const [allmant, setAllmant] = useState<string | null>(null);
  const [skickar, setSkickar] = useState(false);
  const rot = useRef<HTMLFormElement>(null);

  // Ett nytt öppnande börjar om felen men behåller det som fyllts i (LK-004: värdena överlever).
  useEffect(() => {
    if (!oppen) return;
    setFel({});
    setAllmant(null);
    setStruktur(lasStruktur());
    const t = window.setTimeout(() => rot.current?.querySelector<HTMLElement>('[data-falt="antal"] input')?.focus(), 60);
    return () => window.clearTimeout(t);
  }, [oppen]);

  const egnaBolag = rader(egna);
  const tal = (v: string) => (v.trim() && Number.isFinite(Number(v.trim())) ? Number(v.trim()) : undefined);
  const aktivaFilter = LISTFALT.filter((k) => lista(listor[k])).length + (tal(min) != null ? 1 : 0) + (tal(max) != null ? 1 : 0) + (egnaBolag.length ? 1 : 0);
  const n = Number(antal);
  const antalOk = Number.isInteger(n) && n >= 1 && n <= 200;

  function overskrivningar(): Overskrivningar | null {
    // Tomma fält skickas inte: null betyder "använd den sparade målgruppen", inte "inga branscher".
    const o: Overskrivningar = {};
    for (const k of LISTFALT) {
      const l = lista(listor[k]);
      if (l) o[k] = l;
    }
    if (tal(min) != null) o.anstallda_min = tal(min);
    if (tal(max) != null) o.anstallda_max = tal(max);
    return Object.keys(o).length ? o : null;
  }

  function kontrollera(): Partial<Record<Falt, string>> {
    const f: Partial<Record<Falt, string>> = {};
    if (!antalOk) f.antal = text({ sv: "Ange ett helt antal från 1 till 200.", en: "Enter a whole number from 1 to 200." });
    for (const [k, v] of [["min", min], ["max", max]] as const) {
      const x = tal(v);
      if (v.trim() && (x == null || !Number.isInteger(x) || x < 0)) f[k] = text({ sv: "Ange ett helt tal, 0 eller mer.", en: "Enter a whole number, 0 or more." });
    }
    const a = tal(min);
    const b = tal(max);
    if (!f.min && !f.max && a != null && b != null && a > b) {
      f.max = text({ sv: `Minsta antal anställda (${a}) är större än största (${b}).`, en: `The minimum number of employees (${a}) is larger than the maximum (${b}).` });
    }
    if (egnaBolag.length > EGNA_TAK) f.egna = text({ sv: `Högst ${EGNA_TAK} bolag per körning. Du har skrivit ${egnaBolag.length}.`, en: `At most ${EGNA_TAK} companies per run. You have entered ${egnaBolag.length}.` });
    return f;
  }

  function visaFel(f: Partial<Record<Falt, string>>) {
    setFel(f);
    if (f.min || f.max || f.egna || LISTFALT.some((k) => f[k])) setFilterOppet(true);
    window.setTimeout(() => {
      const forsta = [...(rot.current?.querySelectorAll<HTMLElement>("[data-falt]") ?? [])].find((el) => f[el.dataset.falt as Falt]);
      forsta?.querySelector<HTMLElement>("input, textarea, button")?.focus({ preventScroll: true });
      forsta?.scrollIntoView({ block: "center" });
    }, 30);
  }

  async function starta(e: React.FormEvent) {
    e.preventDefault();
    if (skickar) return;
    setAllmant(null);
    const lokala = kontrollera();
    if (Object.keys(lokala).length) {
      visaFel(lokala);
      return;
    }
    setFel({});
    setSkickar(true);
    const o = overskrivningar();
    try {
      const svar = await fetch("/api/snajp-support/leads/runs/batch", {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          limit: n,
          scope: omfattning,
          // Bara research skriver inga utkast: strukturen är då A, som i dagens formulär.
          struktur: omfattning === "research_and_draft" ? struktur : "a",
          is_test: false,
          company_names: egnaBolag,
          ...(o ? { overrides: o } : {})
        })
      });
      const kropp = (await svar.json().catch(() => null)) as (Startsvar & { detail?: unknown; error?: string; kod?: string }) | null;
      if (!svar.ok) {
        const { falt, ovrigt } = serverfel(kropp?.detail);
        const proxy = kropp?.kod ? PROXYKODER[kropp.kod] : undefined;
        if (Object.keys(falt).length) visaFel(falt);
        setAllmant(ovrigt ?? (proxy ? text(proxy) : kropp?.error) ?? text({ sv: `Körningen startade inte (HTTP ${svar.status}). Försök igen.`, en: `The run did not start (HTTP ${svar.status}). Try again.` }));
        return;
      }
      const jobb = kropp?.jobs ?? [];
      if (!jobb.length) {
        setAllmant(text({ sv: "Körningen startade inte. Försök igen.", en: "The run did not start. Try again." }));
        return;
      }
      if (omfattning === "research_and_draft") sparaStruktur(struktur);
      // `fase: soker`: ett sökjobb som vyn följer. Annars barnjobben direkt (äldre väg).
      startad(
        kropp?.fase === "soker"
          ? { jobbId: jobb[0].job_id, antal: egnaBolag.length ? Math.min(egnaBolag.length, n) : n, egna: egnaBolag.length > 0, scope: omfattning, struktur: omfattning === "research_and_draft" ? struktur : "a" }
          : { jobbId: jobb[0].job_id, antal: jobb.length, egna: true, scope: omfattning, struktur, barn: jobb.map((j) => j.job_id) }
      );
    } catch {
      setAllmant(text({ sv: "Nätverksfel. Körningen startade inte. Försök igen.", en: "Network error. The run did not start. Try again." }));
    } finally {
      setSkickar(false);
    }
  }

  const status = (k: Falt) => (fel[k] ? { type: "error" as const, message: fel[k]! } : undefined);
  const antalFel = Object.values(fel).filter(Boolean).length;

  // Förhandsbeskedet: vad som händer när knappen trycks, i en mening (LK-013 innan start).
  const omf = omfattning === "research_and_draft" ? text({ sv: `research och utkast i struktur ${struktur.toUpperCase()}`, en: `research and drafts in structure ${struktur.toUpperCase()}` }) : text({ sv: "bara research, inga utkast", en: "research only, no drafts" });
  const malgrupp = overskrivningar()
    ? text({ sv: "med filtret nedan, bara för den här körningen", en: "with the filter below, for this run only" })
    : text({ sv: "i den sparade målgruppen", en: "in the saved target group" });
  const besked = egnaBolag.length
    ? egnaBolag.length === 1
      ? text({ sv: `Iris researchar bolaget du skrivit in, ${omf}. Ingen sökning körs.`, en: `Iris researches the company you entered, ${omf}. No search runs.` })
      : text({ sv: `Iris researchar de ${Math.min(egnaBolag.length, antalOk ? n : egnaBolag.length)} första av bolagen du skrivit in, ${omf}. Ingen sökning körs.`, en: `Iris researches the first ${Math.min(egnaBolag.length, antalOk ? n : egnaBolag.length)} of the companies you entered, ${omf}. No search runs.` })
    : antalOk
      ? n === 1
        ? text({ sv: `Iris letar 1 leverbart lead ${malgrupp}, med ${omf}.`, en: `Iris looks for 1 deliverable lead ${malgrupp}, with ${omf}.` })
        : text({ sv: `Iris letar ${n} leverbara leads ${malgrupp}, med ${omf}.`, en: `Iris looks for ${n} deliverable leads ${malgrupp}, with ${omf}.` })
      : null;

  const listfalt = (k: IcpNyckel) => (
    <div key={k} data-falt={k}>
      <TextInput
        label={etik[k].label}
        description={LEDTEXT[k] ? text(LEDTEXT[k]!) : undefined}
        placeholder={etik[k].hint}
        value={listor[k]}
        onChange={(v) => {
          setListor((l) => ({ ...l, [k]: v }));
          if (fel[k]) setFel((f) => ({ ...f, [k]: undefined }));
        }}
        width="100%"
        isOptional
        status={status(k)}
      />
    </div>
  );

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && !skickar && stang()} purpose="form" width={640}>
      <Layout
        header={
          <DialogHeader
            title={text({ sv: "Kör Iris", en: "Run Iris" })}
            subtitle={text({ sv: "Iris letar bolag, researchar dem och skriver utkast du granskar.", en: "Iris finds companies, researches them and writes drafts you review." })}
            onOpenChange={(o) => !o && !skickar && stang()}
          />
        }
        content={
          <LayoutContent>
            <form id="crm-kor-iris" ref={rot} onSubmit={(e) => void starta(e)} noValidate className="flex flex-col gap-6">
              {allmant ? <Banner status="error" container="card" title={text({ sv: "Körningen startade inte", en: "The run did not start" })} description={allmant} /> : null}
              {/* Statusregionen finns från början, så att skärmläsaren annonserar när den fylls. */}
              <div role="status" className="sr-only">
                {antalFel > 0
                  ? antalFel === 1
                    ? text({ sv: "Ett fält behöver rättas innan körningen kan starta.", en: "One field needs fixing before the run can start." })
                    : text({ sv: `${antalFel} fält behöver rättas innan körningen kan starta.`, en: `${antalFel} fields need fixing before the run can start.` })
                  : ""}
              </div>
              {impersonation ? (
                <Text color="secondary" type="supporting">
                  {text({ sv: "Du tittar som kunden. Körningen märks som test och syns som test i listan.", en: "You are viewing as the customer. The run is marked as a test and shows as a test in the list." })}
                </Text>
              ) : null}

              <fieldset className="crm-formgrupp">
                <legend className="mb-3 text-[0.8125rem] font-semibold text-ink-muted">{text({ sv: "Körningen", en: "The run" })}</legend>
                <div className="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2">
                  <div data-falt="antal">
                    <TextInput
                      label={text({ sv: "Antal leads", en: "Number of leads" })}
                      description={text({ sv: "1 till 200. Räknar leverbara leads, inte bolag som prövas.", en: "1 to 200. Counts deliverable leads, not companies tried." })}
                      inputMode="numeric"
                      value={antal}
                      onChange={(v) => {
                        setAntal(v.replace(/[^\d]/g, "").slice(0, 3));
                        if (fel.antal) setFel((f) => ({ ...f, antal: undefined }));
                      }}
                      width="100%"
                      isRequired
                      status={status("antal")}
                    />
                  </div>
                  <div data-falt="omfattning">
                    <Selector
                      label={text({ sv: "Omfattning", en: "Scope" })}
                      value={omfattning}
                      onChange={(v) => v && setOmfattning(v as Omfattning)}
                      options={[
                        { value: "research_and_draft", label: text({ sv: "Research och utkast", en: "Research and drafts" }), description: text({ sv: "Ett utkast till varje lead, att granska", en: "A draft for every lead, to review" }) },
                        { value: "research", label: text({ sv: "Bara research", en: "Research only" }), description: text({ sv: "Leads utan utkast", en: "Leads without drafts" }) }
                      ]}
                      width="100%"
                    />
                  </div>
                  {omfattning === "research_and_draft" ? (
                    <div data-falt="struktur" className="sm:col-span-2">
                      {/* LK-135: A eller B, senaste valet minns per webbläsare. */}
                      <Selector
                        label={text({ sv: "Mejlens struktur", en: "Email structure" })}
                        value={struktur}
                        onChange={(v) => (v === "a" || v === "b") && setStruktur(v)}
                        options={[
                          { value: "a", label: text({ sv: "A, utförlig", en: "A, detailed" }), description: text({ sv: "En ingång om dem, vad agenten gör, erbjudandet och en inbjudan.", en: "An opening about them, what the agent does, the offer and an invitation." }) },
                          { value: "b", label: text({ sv: "B, kort och rakt på", en: "B, short and direct" }), description: text({ sv: "Ett kort mejl som slutar med en fråga. Samma signatur, fot och granskning som A.", en: "A short email that ends with a question. Same signature, footer and review as A." }) }
                        ]}
                        width="100%"
                      />
                    </div>
                  ) : null}
                </div>
              </fieldset>

              <div className="flex flex-col gap-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Text color="secondary" type="supporting">
                    {text({ sv: "Filtret gäller bara den här körningen och ändrar inte den sparade målgruppen.", en: "The filter applies to this run only and does not change the saved target group." })}
                  </Text>
                  <Button
                    variant={aktivaFilter ? "secondary" : "ghost"}
                    size="md"
                    icon={<Icon icon={ListFilter} size="sm" />}
                    label={filterOppet ? text({ sv: "Dölj filter", en: "Hide filters" }) : aktivaFilter ? text({ sv: `Filtrera ${aktivaFilter}`, en: `Filter ${aktivaFilter}` }) : text({ sv: "Filtrera", en: "Filter" })}
                    aria-expanded={filterOppet}
                    aria-controls="crm-kor-iris-filter"
                    onClick={() => setFilterOppet((v) => !v)}
                  />
                </div>
                {filterOppet ? (
                  <fieldset id="crm-kor-iris-filter" className="crm-formgrupp">
                    <legend className="mb-3 text-[0.8125rem] font-semibold text-ink-muted">{text({ sv: "Filtrera körningen", en: "Filter the run" })}</legend>
                    <div className="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2">
                      {LISTFALT.map(listfalt)}
                      <div data-falt="min">
                        <TextInput
                          label={text({ sv: "Anställda, minst", en: "Employees, at least" })}
                          inputMode="numeric"
                          value={min}
                          onChange={(v) => {
                            setMin(v);
                            if (fel.min) setFel((f) => ({ ...f, min: undefined }));
                          }}
                          width="100%"
                          isOptional
                          status={status("min")}
                        />
                      </div>
                      <div data-falt="max">
                        <TextInput
                          label={text({ sv: "Anställda, högst", en: "Employees, at most" })}
                          inputMode="numeric"
                          value={max}
                          onChange={(v) => {
                            setMax(v);
                            if (fel.max) setFel((f) => ({ ...f, max: undefined }));
                          }}
                          width="100%"
                          isOptional
                          status={status("max")}
                        />
                      </div>
                      <div data-falt="egna" className="sm:col-span-2">
                        <TextArea
                          label={text({ sv: "Egna bolag", en: "Own companies" })}
                          description={text({ sv: "Ett per rad, högst 50. Tomt: Iris letar själv.", en: "One per line, at most 50. Empty: Iris searches on its own." })}
                          placeholder={text({ sv: "Exempelbolaget AB", en: "Example Company Ltd" })}
                          rows={3}
                          value={egna}
                          onChange={(v) => {
                            setEgna(v);
                            if (fel.egna) setFel((f) => ({ ...f, egna: undefined }));
                          }}
                          width="100%"
                          isOptional
                          status={status("egna")}
                        />
                      </div>
                    </div>
                  </fieldset>
                ) : null}
              </div>

              {besked ? (
                <p className="crm-kallkort rounded-[12px] px-4 py-3 text-[0.875rem] leading-relaxed text-ink2" role="note">
                  {besked}
                </p>
              ) : null}
            </form>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Avbryt", en: "Cancel" })} variant="ghost" onClick={stang} isDisabled={skickar} />
              <Button type="submit" form="crm-kor-iris" variant="primary" label={text({ sv: "Starta körningen", en: "Start the run" })} isLoading={skickar} />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
