"use client";

import { useEffect, useRef, useState } from "react";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import type { ISODateString } from "@astryxdesign/core/Calendar";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { DateInput } from "@astryxdesign/core/DateInput";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { Selector } from "@astryxdesign/core/Selector";
import { HStack } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Krocklank } from "@/components/crm/app/kit";
import { CrmFel, RELATIONER, crmAnrop, orgnrVisning, type Bolag, type Relation } from "@/lib/crm/api";
import { FALTKODER, kodtext } from "@/lib/crm/felkoder";
import { useLocale, type Localized } from "@/lib/i18n";

/**
 * Fälten i dialogen, med samma namn som API:ts (adressens delar utan `address.`).
 * Panelens "Lägg till" öppnar dialogen med fokus på ett av dem.
 */
export type Bolagsfalt =
  | "name"
  | "org_number"
  | "relation"
  | "website"
  | "email"
  | "phone"
  | "street"
  | "postal_code"
  | "city"
  | "owner"
  | "customer_since"
  | "contract_end"
  | "do_not_contact"
  | "legal_form"
  | "vat_number"
  | "sni_code"
  | "employees"
  | "revenue_sek";

type Varden = {
  name: string;
  org_number: string;
  relation: Relation;
  website: string;
  email: string;
  phone: string;
  street: string;
  postal_code: string;
  city: string;
  owner: string;
  customer_since: string;
  contract_end: string;
  do_not_contact: boolean;
  legal_form: string;
  vat_number: string;
  sni_code: string;
  employees: string;
  revenue_sek: string;
};

const ADRESS: Bolagsfalt[] = ["street", "postal_code", "city"];
const TAL: Bolagsfalt[] = ["employees", "revenue_sek"];

function varden(b: Bolag | null): Varden {
  return {
    name: b?.name ?? "",
    org_number: b?.org_number ? orgnrVisning(b.org_number) : "",
    relation: b?.relation ?? "customer",
    website: b?.website ?? "",
    email: b?.email ?? "",
    phone: b?.phone ?? "",
    street: b?.address.street ?? "",
    postal_code: b?.address.postal_code ?? "",
    city: b?.address.city ?? "",
    owner: b?.owner ?? "",
    customer_since: b?.customer_since ?? "",
    contract_end: b?.contract_end ?? "",
    do_not_contact: b?.do_not_contact ?? false,
    legal_form: b?.legal_form ?? "",
    vat_number: b?.vat_number ?? "",
    sni_code: b?.sni_code ?? "",
    employees: b?.employees == null ? "" : String(b.employees),
    revenue_sek: b?.revenue_sek == null ? "" : String(b.revenue_sek)
  };
}

const iso = (v: string): ISODateString | undefined => (/^\d{4}-\d{2}-\d{2}$/.test(v) ? (v as ISODateString) : undefined);

/** API:ts fältnamn (`address.city`) till dialogens (`city`). */
const dialogfalt = (api: string): Bolagsfalt => api.replace(/^address\./, "") as Bolagsfalt;

/**
 * Dialogen för att skapa eller ändra ett bolag (DESIGN-CRM.md § Postens panel,
 * Redigera). Den skickar bara de fält som ändrats (`PATCH /v1/companies/{id}`;
 * ett tömt fält blir `null`), eller de ifyllda vid ett nytt bolag
 * (`POST /v1/companies`). Fält som API:t inte kunde tolka visas vid rätt fält.
 */
export function BolagFormular({
  oppen,
  bolag,
  fokus,
  stang,
  sparat,
  oppnaPost
}: Readonly<{
  oppen: boolean;
  /** Bolaget som ändras, eller `null` för ett nytt. */
  bolag: Bolag | null;
  /** Fältet som får fokus när dialogen öppnas. */
  fokus?: Bolagsfalt | null;
  stang: () => void;
  sparat: (b: Bolag, nytt: boolean) => void;
  /** Öppnar en annan post: den som redan har numret vid en krock. */
  oppnaPost?: (id: string) => void;
}>) {
  const { text } = useLocale();
  const [v, setV] = useState<Varden>(() => varden(bolag));
  const [falt, setFalt] = useState<Partial<Record<Bolagsfalt, Localized>>>({});
  const [allmant, setAllmant] = useState<Localized | null>(null);
  const [sparar, setSparar] = useState(false);
  /** Vid 409: posten som redan har numret, när API:t kan peka ut den. */
  const [krock, setKrock] = useState<string | null>(null);
  const rot = useRef<HTMLFormElement>(null);
  const ursprung = useRef<Varden>(varden(bolag));
  const nytt = bolag == null;
  const privatperson = bolag?.private_person === true;

  useEffect(() => {
    if (!oppen) return;
    const start = varden(bolag);
    ursprung.current = start;
    setV(start);
    setFalt({});
    setAllmant(null);
    setKrock(null);
    // Panelens "Lägg till" pekar ut ett fält: fokus dit när dialogen hunnit montera.
    const t = window.setTimeout(() => {
      const mal = rot.current?.querySelector<HTMLElement>(`[data-falt="${fokus ?? "name"}"] input, [data-falt="${fokus ?? "name"}"] button`);
      mal?.focus();
    }, 60);
    return () => window.clearTimeout(t);
  }, [oppen, bolag, fokus]);

  const satt = <K extends keyof Varden>(k: K, varde: Varden[K]) => {
    setV((f) => ({ ...f, [k]: varde }));
    setFalt((f) => (f[k as Bolagsfalt] ? { ...f, [k]: undefined } : f));
  };

  // Ett misslyckat Spara flyttar fokus till det första fältet som behöver rättas,
  // i formulärets ordning, så att felet inte ligger ovanför i en rullad dialog.
  const felFokus = useRef(false);
  const visaFel = (f: Partial<Record<Bolagsfalt, Localized>>) => {
    felFokus.current = true;
    setFalt(f);
  };
  useEffect(() => {
    if (!felFokus.current) return;
    felFokus.current = false;
    const t = window.setTimeout(() => {
      const forsta = [...(rot.current?.querySelectorAll<HTMLElement>("[data-falt]") ?? [])].find((el) => falt[el.dataset.falt as Bolagsfalt]);
      const mal = forsta?.querySelector<HTMLElement>("input, textarea, button");
      mal?.focus({ preventScroll: true });
      // Mitt i dialogen, så att felmeddelandet under fältet syns helt.
      forsta?.scrollIntoView({ block: "center" });
    }, 0);
    return () => window.clearTimeout(t);
  }, [falt]);

  const status = (k: Bolagsfalt) => (falt[k] ? { type: "error" as const, message: text(falt[k]!) } : undefined);

  function kropp(): Record<string, unknown> | null {
    const lokala: Partial<Record<Bolagsfalt, Localized>> = {};
    const ut: Record<string, unknown> = {};
    const adress: Record<string, unknown> = {};
    for (const k of Object.keys(v) as (keyof Varden)[]) {
      const nu = v[k];
      if (!nytt && nu === ursprung.current[k]) continue;
      let varde: unknown = typeof nu === "string" ? nu.trim() || null : nu;
      if (nytt && (varde == null || varde === false)) continue;
      if (TAL.includes(k) && typeof varde === "string") {
        const tal = Number(varde.replace(/\s/g, ""));
        if (!Number.isInteger(tal)) {
          lokala[k] = FALTKODER.tal_ogiltigt;
          continue;
        }
        varde = tal;
      }
      if (ADRESS.includes(k)) adress[k] = varde;
      else ut[k] = varde;
    }
    if (Object.keys(adress).length) ut.address = adress;
    if (Object.keys(lokala).length) {
      visaFel(lokala);
      return null;
    }
    return ut;
  }

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    if (sparar) return;
    if (!v.name.trim()) {
      visaFel({ name: { sv: "Bolaget behöver ett namn.", en: "The company needs a name." } });
      return;
    }
    const k = kropp();
    if (!k) return;
    if (!nytt && Object.keys(k).length === 0) {
      stang();
      return;
    }
    setSparar(true);
    setFalt({});
    setAllmant(null);
    setKrock(null);
    try {
      const svar = bolag == null
        ? await crmAnrop<Bolag>("/v1/companies", { method: "POST", body: JSON.stringify(k) })
        : await crmAnrop<Bolag>(`/v1/companies/${encodeURIComponent(bolag.id)}`, { method: "PATCH", body: JSON.stringify(k) });
      sparat(svar, nytt);
    } catch (orsak) {
      if (orsak instanceof CrmFel && orsak.falt.length) {
        visaFel(Object.fromEntries(orsak.falt.map((f) => [dialogfalt(f.field), kodtext(FALTKODER, f.code)])));
      } else if (orsak instanceof CrmFel && orsak.status === 409) {
        // Det enda som kan krocka på ett bolag är organisationsnumret.
        setKrock(orsak.krockarMed);
        visaFel({
          org_number: {
            sv: "Ett annat bolag har redan det här organisationsnumret. Ändra numret eller sök upp det bolaget.",
            en: "Another company already has this organisation number. Change the number or look up that company."
          }
        });
      } else {
        setAllmant(orsak instanceof CrmFel ? orsak.text : { sv: "Det gick inte att spara. Försök igen.", en: "Could not save. Try again." });
      }
    } finally {
      setSparar(false);
    }
  }

  const relationer = (Object.keys(RELATIONER) as Relation[]).map((r) => ({ value: r, label: text(RELATIONER[r]) }));
  const titel = nytt ? text({ sv: "Nytt bolag", en: "New company" }) : text({ sv: "Redigera bolag", en: "Edit company" });
  const fel = Object.values(falt).filter(Boolean).length;

  const grupp = (rubrik: string, barn: React.ReactNode) => (
    <fieldset className="crm-formgrupp">
      <legend className="mb-3 text-[0.8125rem] font-semibold text-ink-muted">{rubrik}</legend>
      <div className="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2">{barn}</div>
    </fieldset>
  );
  const hel = (k: Bolagsfalt, barn: React.ReactNode) => (
    <div data-falt={k} className="sm:col-span-2">
      {barn}
    </div>
  );
  const halv = (k: Bolagsfalt, barn: React.ReactNode) => <div data-falt={k}>{barn}</div>;
  const textfalt = (k: Exclude<keyof Varden, "relation" | "do_not_contact">, etikett: Localized, mer?: Partial<React.ComponentProps<typeof TextInput>>) => (
    <TextInput
      label={text(etikett)}
      value={v[k]}
      onChange={(x) => satt(k, x)}
      width="100%"
      status={status(k)}
      {...mer}
    />
  );

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && stang()} purpose="form" width={640}>
      <Layout
        header={
          <DialogHeader
            title={titel}
            subtitle={bolag?.name ?? undefined}
            onOpenChange={(o) => !o && stang()}
          />
        }
        content={
          <LayoutContent>
            <form id="crm-bolagsformular" ref={rot} onSubmit={spara} noValidate className="flex flex-col gap-6">
              {allmant ? <Banner status="error" container="card" title={text({ sv: "Det gick inte att spara", en: "Could not save" })} description={text(allmant)} /> : null}
              {/* Statusregionen finns från början, så att skärmläsaren annonserar när den fylls. */}
              <div role="status" className="sr-only">
                {fel > 0
                  ? fel === 1
                    ? text({ sv: "Ett fält behöver rättas innan bolaget kan sparas.", en: "One field needs fixing before the company can be saved." })
                    : text({ sv: `${fel} fält behöver rättas innan bolaget kan sparas.`, en: `${fel} fields need fixing before the company can be saved.` })
                  : ""}
              </div>
              {fel > 0 ? (
                <Text color="secondary" type="supporting">
                  {fel === 1
                    ? text({ sv: "Ett fält behöver rättas innan bolaget kan sparas.", en: "One field needs fixing before the company can be saved." })
                    : text({ sv: `${fel} fält behöver rättas innan bolaget kan sparas.`, en: `${fel} fields need fixing before the company can be saved.` })}
                </Text>
              ) : null}
              {grupp(
                text({ sv: "Allmänt", en: "General" }),
                <>
                  {hel("name", textfalt("name", { sv: "Bolagsnamn", en: "Company name" }, { isRequired: true }))}
                  {halv(
                    "org_number",
                    <>
                      {textfalt(
                        "org_number",
                        { sv: "Organisationsnummer", en: "Organisation number" },
                        { inputMode: "numeric", placeholder: "556036-0793", isOptional: true }
                      )}
                      {krock && falt.org_number && oppnaPost ? (
                        <Krocklank
                          etikett={text({ sv: "Öppna posten som redan har numret", en: "Open the record that already has the number" })}
                          onClick={() => {
                            stang();
                            oppnaPost(krock);
                          }}
                        />
                      ) : null}
                    </>
                  )}
                  {halv(
                    "relation",
                    <Selector
                      label={text({ sv: "Relation", en: "Relation" })}
                      value={v.relation}
                      onChange={(x) => x && satt("relation", x as Relation)}
                      options={relationer}
                      width="100%"
                      status={status("relation")}
                    />
                  )}
                </>
              )}
              {grupp(
                text({ sv: "Kontakt", en: "Contact" }),
                <>
                  {hel("website", textfalt("website", { sv: "Webbplats", en: "Website" }, { type: "url", placeholder: "exempel.se", isOptional: true }))}
                  {halv("email", textfalt("email", { sv: "E-post", en: "Email" }, { type: "email", isOptional: true }))}
                  {halv("phone", textfalt("phone", { sv: "Telefon", en: "Phone" }, { type: "tel", isOptional: true }))}
                  {hel("street", textfalt("street", { sv: "Gatuadress", en: "Street address" }, { isOptional: true }))}
                  {halv("postal_code", textfalt("postal_code", { sv: "Postnummer", en: "Postal code" }, { inputMode: "numeric", isOptional: true }))}
                  {halv("city", textfalt("city", { sv: "Ort", en: "City" }, { isOptional: true }))}
                </>
              )}
              {grupp(
                text({ sv: "Affär", en: "Business" }),
                <>
                  {hel("owner", textfalt("owner", { sv: "Ansvarig", en: "Owner" }, { isOptional: true }))}
                  {halv(
                    "customer_since",
                    <DateInput
                      label={text({ sv: "Kund sedan", en: "Customer since" })}
                      value={iso(v.customer_since)}
                      onChange={(x) => satt("customer_since", x ?? "")}
                      weekStartsOn="mon"
                      format="date"
                      hasClear
                      isOptional
                      width="100%"
                      status={status("customer_since")}
                    />
                  )}
                  {halv(
                    "contract_end",
                    <DateInput
                      label={text({ sv: "Avtalsslut", en: "Contract end" })}
                      value={iso(v.contract_end)}
                      onChange={(x) => satt("contract_end", x ?? "")}
                      weekStartsOn="mon"
                      format="date"
                      hasClear
                      isOptional
                      width="100%"
                      status={status("contract_end")}
                    />
                  )}
                  {hel(
                    "do_not_contact",
                    privatperson ? (
                      // En privatperson kontaktas aldrig: API:t håller spärren på, och rutan går inte att slå av.
                      <CheckboxInput
                        label={text({ sv: "Kontakta inte", en: "Do not contact" })}
                        description={text({
                          sv: "Posten är en privatperson och kontaktas aldrig. Spärren går inte att slå av.",
                          en: "The record is a private person and is never contacted. The block cannot be turned off."
                        })}
                        disabledMessage={text({ sv: "Privatpersoner kontaktas aldrig.", en: "Private persons are never contacted." })}
                        value
                        isDisabled
                      />
                    ) : (
                      <CheckboxInput
                        label={text({ sv: "Kontakta inte", en: "Do not contact" })}
                        description={text({
                          sv: "Bolaget tas inte med i utskick och leadslistor.",
                          en: "The company is left out of mailings and lead lists."
                        })}
                        value={v.do_not_contact}
                        onChange={(x) => satt("do_not_contact", x)}
                      />
                    )
                  )}
                </>
              )}
              {grupp(
                text({ sv: "Bolagsfakta", en: "Company facts" }),
                <>
                  {halv("legal_form", textfalt("legal_form", { sv: "Bolagsform", en: "Legal form" }, { placeholder: "AB", isOptional: true }))}
                  {halv("vat_number", textfalt("vat_number", { sv: "Momsregistreringsnummer", en: "VAT number" }, { isOptional: true }))}
                  {halv("sni_code", textfalt("sni_code", { sv: "SNI-kod", en: "SNI code" }, { inputMode: "numeric", isOptional: true }))}
                  {halv("employees", textfalt("employees", { sv: "Anställda", en: "Employees" }, { inputMode: "numeric", isOptional: true }))}
                  {hel("revenue_sek", textfalt("revenue_sek", { sv: "Omsättning i kronor", en: "Revenue in SEK" }, { inputMode: "numeric", isOptional: true }))}
                </>
              )}
            </form>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Avbryt", en: "Cancel" })} variant="ghost" onClick={stang} />
              <Button
                type="submit"
                form="crm-bolagsformular"
                variant="primary"
                label={nytt ? text({ sv: "Skapa bolaget", en: "Create company" }) : text({ sv: "Spara ändringarna", en: "Save changes" })}
                isLoading={sparar}
              />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
