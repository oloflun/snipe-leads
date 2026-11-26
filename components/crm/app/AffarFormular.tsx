"use client";

import { useEffect, useRef, useState } from "react";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import type { ISODateString } from "@astryxdesign/core/Calendar";
import { DateInput } from "@astryxdesign/core/DateInput";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { Selector } from "@astryxdesign/core/Selector";
import { HStack } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";
import { TextInput } from "@astryxdesign/core/TextInput";
import { CrmFel, crmAnrop, type Person, type Sida } from "@/lib/crm/api";
import type { Affar, Affarssteg } from "@/lib/crm/affar";
import { FALTKODER, kodtext } from "@/lib/crm/felkoder";
import { useLocale, type Localized } from "@/lib/i18n";

/** Fälten i dialogen, med API:ts namn. Panelens "Lägg till" öppnar dialogen på ett av dem. */
export type Affarsfalt = "name" | "company_id" | "person_id" | "stage_id" | "amount" | "probability" | "expected_close_date" | "owner" | "lost_reason";

type Varden = {
  name: string;
  company_id: string;
  person_id: string;
  stage_id: string;
  amount: string;
  probability: string;
  expected_close_date: string;
  owner: string;
  lost_reason: string;
};

/** Selectorns värde för "inget valt"; skickas som `null`. */
const INGET = "inget";
const TAL: (keyof Varden)[] = ["amount", "probability"];

const iso = (v: string): ISODateString | undefined => (/^\d{4}-\d{2}-\d{2}$/.test(v) ? (v as ISODateString) : undefined);

function varden(a: Affar | null, stegId: string | null, bolagId: string | null): Varden {
  return {
    name: a?.name ?? "",
    company_id: a?.company_id ?? bolagId ?? INGET,
    person_id: a?.person_id ?? INGET,
    stage_id: a?.stage_id ?? stegId ?? "",
    // Tusental med mellanslag, som beloppet skrivs: 720 000.
    amount: a?.amount == null ? "" : String(a.amount).replace(/\B(?=(\d{3})+(?!\d))/g, " "),
    probability: a?.probability == null ? "" : String(a.probability),
    expected_close_date: a?.expected_close_date ?? "",
    owner: a?.owner ?? "",
    lost_reason: a?.lost_reason ?? ""
  };
}

/**
 * Dialogen för att skapa eller ändra en affär, i samma form som bolagets. Den
 * skickar bara det som ändrats (`PATCH /v1/deals/{id}`; ett tömt fält blir
 * `null`), eller de ifyllda fälten vid en ny affär (`POST /v1/deals`). Fält
 * som API:t inte kunde tolka visas vid rätt fält.
 */
export function AffarFormular({
  oppen,
  affar,
  steg,
  bolag,
  forvalStegId,
  forvalBolagId,
  fokus,
  stang,
  sparat
}: Readonly<{
  oppen: boolean;
  /** Affären som ändras, eller `null` för en ny. */
  affar: Affar | null;
  steg: Affarssteg[];
  /** Bolagen att knyta affären till: id och namn. */
  bolag: { id: string; namn: string }[];
  /** Steget en ny affär börjar i (kolumnen där "Lägg till affär" trycktes). */
  forvalStegId?: string | null;
  forvalBolagId?: string | null;
  fokus?: Affarsfalt | null;
  stang: () => void;
  sparat: (a: Affar, ny: boolean) => void;
}>) {
  const { text } = useLocale();
  const forstaSteg = forvalStegId ?? steg.find((s) => s.type === "open")?.id ?? steg[0]?.id ?? null;
  const [v, setV] = useState<Varden>(() => varden(affar, forstaSteg, forvalBolagId ?? null));
  const [falt, setFalt] = useState<Partial<Record<Affarsfalt, Localized>>>({});
  const [allmant, setAllmant] = useState<Localized | null>(null);
  const [sparar, setSparar] = useState(false);
  const rot = useRef<HTMLFormElement>(null);
  const ursprung = useRef<Varden>(v);
  const ny = affar == null;
  // Bolagets personer, att välja kontaktperson bland. Hämtas när bolaget väljs.
  const [personer, setPersoner] = useState<{ id: string; namn: string }[]>([]);
  const valtBolag = v.company_id === INGET ? null : v.company_id;

  useEffect(() => {
    setPersoner([]);
    if (!oppen || !valtBolag) return;
    let aktuell = true;
    crmAnrop<Sida<Person>>(`/v1/people?${new URLSearchParams({ company_id: valtBolag, limit: "100", sort: "name" })}`)
      .then((s) => {
        if (!aktuell) return;
        setPersoner(s.data.map((p) => ({ id: p.id, namn: [p.first_name, p.last_name].filter(Boolean).join(" ") || p.email || p.id })));
      })
      .catch(() => undefined);
    return () => {
      aktuell = false;
    };
  }, [oppen, valtBolag]);

  useEffect(() => {
    if (!oppen) return;
    const start = varden(affar, forstaSteg, forvalBolagId ?? null);
    ursprung.current = start;
    setV(start);
    setFalt({});
    setAllmant(null);
    const t = window.setTimeout(() => {
      const mal = rot.current?.querySelector<HTMLElement>(`[data-falt="${fokus ?? "name"}"] input, [data-falt="${fokus ?? "name"}"] button`);
      mal?.focus();
    }, 60);
    return () => window.clearTimeout(t);
    // Stegen laddas en gång per vy: förvalet läses när dialogen öppnas.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [oppen, affar, fokus, forvalStegId, forvalBolagId]);

  const satt = <K extends keyof Varden>(k: K, varde: Varden[K]) => {
    setV((f) => ({ ...f, [k]: varde }));
    setFalt((f) => (f[k as Affarsfalt] ? { ...f, [k]: undefined } : f));
  };
  const status = (k: Affarsfalt) => (falt[k] ? { type: "error" as const, message: text(falt[k]!) } : undefined);

  // Ett misslyckat Spara flyttar fokus till det första fältet som behöver rättas.
  const felFokus = useRef(false);
  const visaFel = (f: Partial<Record<Affarsfalt, Localized>>) => {
    felFokus.current = true;
    setFalt(f);
  };
  useEffect(() => {
    if (!felFokus.current) return;
    felFokus.current = false;
    const t = window.setTimeout(() => {
      const forsta = [...(rot.current?.querySelectorAll<HTMLElement>("[data-falt]") ?? [])].find((el) => falt[el.dataset.falt as Affarsfalt]);
      forsta?.querySelector<HTMLElement>("input, textarea, button")?.focus({ preventScroll: true });
      forsta?.scrollIntoView({ block: "center" });
    }, 0);
    return () => window.clearTimeout(t);
  }, [falt]);

  /** Tal som de skrivs: "120 000" och "120000 kr" är 120000. Returnerar `undefined` för det som inte är ett tal. */
  const tal = (s: string): number | null | undefined => {
    const ren = s.replace(/[\s  ]|kr|sek|%/gi, "");
    if (!ren) return null;
    return /^\d+$/.test(ren) ? Number(ren) : undefined;
  };

  function kropp(): Record<string, unknown> | null {
    const ut: Record<string, unknown> = {};
    const fel: Partial<Record<Affarsfalt, Localized>> = {};
    for (const k of Object.keys(v) as (keyof Varden)[]) {
      const nu = v[k];
      if (!ny && nu === ursprung.current[k]) continue;
      let varde: unknown;
      if (TAL.includes(k)) {
        const t = tal(nu);
        if (t === undefined || (k === "probability" && t != null && t > 100)) {
          fel[k as Affarsfalt] =
            k === "amount"
              ? { sv: "Skriv beloppet i hela kronor, till exempel 120 000.", en: "Enter the amount in whole kronor, for example 120 000." }
              : { sv: "Skriv ett tal mellan 0 och 100.", en: "Enter a number between 0 and 100." };
          continue;
        }
        varde = t;
      } else {
        varde = nu === INGET ? null : nu.trim() || null;
      }
      if (ny && varde == null) continue;
      ut[k] = varde;
    }
    if (Object.keys(fel).length) {
      visaFel(fel);
      return null;
    }
    return ut;
  }

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    if (sparar) return;
    if (!v.name.trim()) {
      visaFel({ name: { sv: "Affären behöver ett namn.", en: "The deal needs a name." } });
      return;
    }
    const k = kropp();
    if (!k) return;
    if (!ny && Object.keys(k).length === 0) {
      stang();
      return;
    }
    setSparar(true);
    setFalt({});
    setAllmant(null);
    try {
      const svar =
        affar == null
          ? await crmAnrop<Affar>("/v1/deals", { method: "POST", body: JSON.stringify(k) })
          : await crmAnrop<Affar>(`/v1/deals/${encodeURIComponent(affar.id)}`, { method: "PATCH", body: JSON.stringify(k) });
      sparat(svar, ny);
    } catch (orsak) {
      if (orsak instanceof CrmFel && orsak.falt.length) {
        visaFel(Object.fromEntries(orsak.falt.map((f) => [f.field as Affarsfalt, kodtext(FALTKODER, f.code)])));
      } else if (orsak instanceof CrmFel && orsak.kod === "company_not_found") {
        visaFel({ company_id: { sv: "Bolaget finns inte längre. Välj ett annat.", en: "The company no longer exists. Choose another." } });
      } else if (orsak instanceof CrmFel && orsak.kod === "person_not_found") {
        visaFel({ person_id: { sv: "Personen finns inte längre. Välj en annan.", en: "The person no longer exists. Choose another." } });
      } else if (orsak instanceof CrmFel && orsak.kod === "stage_not_found") {
        visaFel({ stage_id: { sv: "Steget finns inte längre. Välj ett annat.", en: "The stage no longer exists. Choose another." } });
      } else {
        setAllmant(orsak instanceof CrmFel ? orsak.text : { sv: "Det gick inte att spara. Försök igen.", en: "Could not save. Try again." });
      }
    } finally {
      setSparar(false);
    }
  }

  const fel = Object.values(falt).filter(Boolean).length;
  const valtSteg = steg.find((s) => s.id === v.stage_id);
  const hel = (k: Affarsfalt, barn: React.ReactNode) => (
    <div data-falt={k} className="sm:col-span-2">
      {barn}
    </div>
  );
  const halv = (k: Affarsfalt, barn: React.ReactNode) => <div data-falt={k}>{barn}</div>;
  const felrad =
    fel === 1
      ? text({ sv: "Ett fält behöver rättas innan affären kan sparas.", en: "One field needs fixing before the deal can be saved." })
      : text({ sv: `${fel} fält behöver rättas innan affären kan sparas.`, en: `${fel} fields need fixing before the deal can be saved.` });

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && stang()} purpose="form" width={600}>
      <Layout
        header={
          <DialogHeader
            title={ny ? text({ sv: "Ny affär", en: "New deal" }) : text({ sv: "Redigera affär", en: "Edit deal" })}
            subtitle={affar?.name ?? undefined}
            onOpenChange={(o) => !o && stang()}
          />
        }
        content={
          <LayoutContent>
            <form id="crm-affarsformular" ref={rot} onSubmit={spara} noValidate className="flex flex-col gap-6">
              {allmant ? <Banner status="error" container="card" title={text({ sv: "Det gick inte att spara", en: "Could not save" })} description={text(allmant)} /> : null}
              {/* Statusregionen finns från början, så att skärmläsaren annonserar när den fylls. */}
              <div role="status" className="sr-only">
                {fel > 0 ? felrad : ""}
              </div>
              {fel > 0 ? (
                <Text color="secondary" type="supporting">
                  {felrad}
                </Text>
              ) : null}
              <div className="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2">
                {hel(
                  "name",
                  <TextInput
                    label={text({ sv: "Namn", en: "Name" })}
                    placeholder={text({ sv: "Telefoniavtal 2027", en: "Telephony contract 2027" })}
                    value={v.name}
                    onChange={(x) => satt("name", x)}
                    width="100%"
                    status={status("name")}
                  />
                )}
                {hel(
                  "company_id",
                  <Selector
                    label={text({ sv: "Bolag", en: "Company" })}
                    value={v.company_id}
                    onChange={(x) => {
                      if (!x || x === v.company_id) return;
                      // Kontaktpersonen hör till bolaget: ett nytt bolag börjar utan.
                      setV((f) => ({ ...f, company_id: x, person_id: INGET }));
                      setFalt((f) => ({ ...f, company_id: undefined, person_id: undefined }));
                    }}
                    options={[
                      { value: INGET, label: text({ sv: "Inget bolag", en: "No company" }) },
                      { type: "divider" as const },
                      ...bolag.map((b) => ({ value: b.id, label: b.namn }))
                    ]}
                    hasSearch
                    searchPlaceholder={text({ sv: "Sök bolag", en: "Search companies" })}
                    width="100%"
                    status={status("company_id")}
                  />
                )}
                {valtBolag && (personer.length > 0 || v.person_id !== INGET)
                  ? hel(
                      "person_id",
                      <Selector
                        label={text({ sv: "Kontaktperson", en: "Contact person" })}
                        value={v.person_id}
                        onChange={(x) => x && satt("person_id", x)}
                        options={[
                          { value: INGET, label: text({ sv: "Ingen kontaktperson", en: "No contact person" }) },
                          { type: "divider" as const },
                          ...personer.map((p) => ({ value: p.id, label: p.namn })),
                          // Den sparade personen står kvar medan bolagets personer hämtas.
                          ...(v.person_id !== INGET && !personer.some((p) => p.id === v.person_id)
                            ? [{ value: v.person_id, label: text({ sv: "Vald person", en: "Selected person" }) }]
                            : [])
                        ]}
                        hasSearch={personer.length > 8}
                        width="100%"
                        status={status("person_id")}
                      />
                    )
                  : null}
                {halv(
                  "stage_id",
                  <Selector
                    label={text({ sv: "Steg", en: "Stage" })}
                    value={v.stage_id}
                    onChange={(x) => x && satt("stage_id", x)}
                    options={steg.map((s) => ({ value: s.id, label: s.name }))}
                    width="100%"
                    status={status("stage_id")}
                  />
                )}
                {halv(
                  "amount",
                  <TextInput
                    label={text({ sv: "Belopp i kronor", en: "Amount in kronor" })}
                    inputMode="numeric"
                    placeholder="120 000"
                    value={v.amount}
                    onChange={(x) => satt("amount", x)}
                    width="100%"
                    status={status("amount")}
                    isOptional
                  />
                )}
                {halv(
                  "expected_close_date",
                  <DateInput
                    label={text({ sv: "Väntat avslut", en: "Expected close" })}
                    value={iso(v.expected_close_date)}
                    onChange={(x) => satt("expected_close_date", x ?? "")}
                    weekStartsOn="mon"
                    format="date"
                    hasClear
                    isOptional
                    width="100%"
                    status={status("expected_close_date")}
                  />
                )}
                {halv(
                  "probability",
                  <TextInput
                    label={text({ sv: "Sannolikhet i procent", en: "Probability in percent" })}
                    // Ett tomt fält följer steget: platshållaren säger vilken sannolikhet det ger.
                    placeholder={valtSteg ? text({ sv: `Stegets: ${valtSteg.probability}`, en: `The stage's: ${valtSteg.probability}` }) : undefined}
                    inputMode="numeric"
                    value={v.probability}
                    onChange={(x) => satt("probability", x)}
                    width="100%"
                    status={status("probability")}
                    isOptional
                  />
                )}
                {hel(
                  "owner",
                  <TextInput
                    label={text({ sv: "Ansvarig", en: "Owner" })}
                    value={v.owner}
                    onChange={(x) => satt("owner", x)}
                    width="100%"
                    status={status("owner")}
                    isOptional
                  />
                )}
                {valtSteg?.type === "lost" || v.lost_reason
                  ? hel(
                      "lost_reason",
                      <TextInput
                        label={text({ sv: "Förlustorsak", en: "Lost reason" })}
                        description={text({ sv: "Varför affären inte blev av.", en: "Why the deal did not happen." })}
                        value={v.lost_reason}
                        onChange={(x) => satt("lost_reason", x)}
                        width="100%"
                        status={status("lost_reason")}
                        isOptional
                      />
                    )
                  : null}
              </div>
            </form>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Avbryt", en: "Cancel" })} variant="ghost" onClick={stang} />
              <Button
                type="submit"
                form="crm-affarsformular"
                variant="primary"
                label={ny ? text({ sv: "Skapa affären", en: "Create deal" }) : text({ sv: "Spara ändringarna", en: "Save changes" })}
                isLoading={sparar}
              />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
