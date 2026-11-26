"use client";

import { useEffect, useRef, useState } from "react";
import { Banner } from "@astryxdesign/core/Banner";
import { Button } from "@astryxdesign/core/Button";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { Selector } from "@astryxdesign/core/Selector";
import { HStack } from "@astryxdesign/core/Stack";
import { Text } from "@astryxdesign/core/Text";
import { TextInput } from "@astryxdesign/core/TextInput";
import { CrmFel, crmAnrop } from "@/lib/crm/api";
import { FALTKODER, kodtext } from "@/lib/crm/felkoder";
import { GRUNDER, personnamn, type Personpost, type RattsligGrund } from "@/lib/crm/person";
import { useLocale, type Localized } from "@/lib/i18n";

/** Fälten i dialogen, med samma namn som API:ts. Panelens "Lägg till" öppnar dialogen på ett av dem. */
export type Personfalt =
  | "first_name"
  | "last_name"
  | "title"
  | "company_id"
  | "email"
  | "phone"
  | "mobile"
  | "legal_basis"
  | "do_not_contact";

type Varden = {
  first_name: string;
  last_name: string;
  title: string;
  company_id: string;
  email: string;
  phone: string;
  mobile: string;
  legal_basis: string;
  do_not_contact: boolean;
};

/** Selectorns värde för "inget valt"; skickas som `null`. */
const INGET = "inget";

function varden(p: Personpost | null, bolagId?: string | null): Varden {
  return {
    first_name: p?.first_name ?? "",
    last_name: p?.last_name ?? "",
    title: p?.title ?? "",
    company_id: p?.company_id ?? bolagId ?? INGET,
    email: p?.email ?? "",
    phone: p?.phone ?? "",
    mobile: p?.mobile ?? "",
    legal_basis: p?.legal_basis ?? INGET,
    do_not_contact: p?.do_not_contact ?? false
  };
}

/**
 * Dialogen för att skapa eller ändra en person, i samma form som bolagets.
 * Den skickar bara de fält som ändrats (`PATCH /v1/people/{id}`; ett tömt fält
 * blir `null`), eller de ifyllda vid en ny person (`POST /v1/people`). Fält som
 * API:t inte kunde tolka visas vid rätt fält; en krock gäller e-postadressen.
 */
export function PersonFormular({
  oppen,
  person,
  bolag,
  fokus,
  stang,
  sparat
}: Readonly<{
  oppen: boolean;
  /** Personen som ändras, eller `null` för en ny. */
  person: Personpost | null;
  /** Bolagen att knyta personen till: id och namn. */
  bolag: { id: string; namn: string }[];
  fokus?: Personfalt | null;
  stang: () => void;
  sparat: (p: Personpost, ny: boolean) => void;
}>) {
  const { text } = useLocale();
  const [v, setV] = useState<Varden>(() => varden(person));
  const [falt, setFalt] = useState<Partial<Record<Personfalt, Localized>>>({});
  const [allmant, setAllmant] = useState<Localized | null>(null);
  const [sparar, setSparar] = useState(false);
  const rot = useRef<HTMLFormElement>(null);
  const ursprung = useRef<Varden>(varden(person));
  const ny = person == null;

  useEffect(() => {
    if (!oppen) return;
    const start = varden(person);
    ursprung.current = start;
    setV(start);
    setFalt({});
    setAllmant(null);
    const t = window.setTimeout(() => {
      const mal = rot.current?.querySelector<HTMLElement>(`[data-falt="${fokus ?? "first_name"}"] input, [data-falt="${fokus ?? "first_name"}"] button`);
      mal?.focus();
    }, 60);
    return () => window.clearTimeout(t);
  }, [oppen, person, fokus]);

  const satt = <K extends keyof Varden>(k: K, varde: Varden[K]) => {
    setV((f) => ({ ...f, [k]: varde }));
    setFalt((f) => (f[k as Personfalt] ? { ...f, [k]: undefined } : f));
  };
  const status = (k: Personfalt) => (falt[k] ? { type: "error" as const, message: text(falt[k]!) } : undefined);

  // Ett misslyckat Spara flyttar fokus till det första fältet som behöver rättas.
  const felFokus = useRef(false);
  const visaFel = (f: Partial<Record<Personfalt, Localized>>) => {
    felFokus.current = true;
    setFalt(f);
  };
  useEffect(() => {
    if (!felFokus.current) return;
    felFokus.current = false;
    const t = window.setTimeout(() => {
      const forsta = [...(rot.current?.querySelectorAll<HTMLElement>("[data-falt]") ?? [])].find((el) => falt[el.dataset.falt as Personfalt]);
      const mal = forsta?.querySelector<HTMLElement>("input, textarea, button");
      mal?.focus({ preventScroll: true });
      // Mitt i dialogen, så att felmeddelandet under fältet syns helt.
      forsta?.scrollIntoView({ block: "center" });
    }, 0);
    return () => window.clearTimeout(t);
  }, [falt]);

  function kropp(): Record<string, unknown> {
    const ut: Record<string, unknown> = {};
    for (const k of Object.keys(v) as (keyof Varden)[]) {
      const nu = v[k];
      if (!ny && nu === ursprung.current[k]) continue;
      const varde = nu === INGET ? null : typeof nu === "string" ? nu.trim() || null : nu;
      if (ny && (varde == null || varde === false)) continue;
      ut[k] = varde;
    }
    return ut;
  }

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    if (sparar) return;
    if (!personnamn({ first_name: v.first_name.trim(), last_name: v.last_name.trim(), email: v.email.trim() })) {
      visaFel({ first_name: { sv: "Personen behöver ett namn eller en e-postadress.", en: "The person needs a name or an email address." } });
      return;
    }
    const k = kropp();
    if (!ny && Object.keys(k).length === 0) {
      stang();
      return;
    }
    setSparar(true);
    setFalt({});
    setAllmant(null);
    try {
      const svar = person == null
        ? await crmAnrop<Personpost>("/v1/people", { method: "POST", body: JSON.stringify(k) })
        : await crmAnrop<Personpost>(`/v1/people/${encodeURIComponent(person.id)}`, { method: "PATCH", body: JSON.stringify(k) });
      sparat(svar, ny);
    } catch (orsak) {
      if (orsak instanceof CrmFel && orsak.falt.length) {
        visaFel(Object.fromEntries(orsak.falt.map((f) => [f.field as Personfalt, kodtext(FALTKODER, f.code)])));
      } else if (orsak instanceof CrmFel && orsak.status === 409) {
        // Det som kan krocka på en person är e-postadressen. API:ts text gäller
        // både bolag och personer; här står det som gäller just personen.
        visaFel({
          email: {
            sv: "En annan person har redan den här e-postadressen. Ändra adressen eller sök upp den personen.",
            en: "Another person already has this email address. Change the address or look up that person."
          }
        });
      } else if (orsak instanceof CrmFel && orsak.kod === "company_not_found") {
        visaFel({ company_id: orsak.text });
      } else {
        setAllmant(orsak instanceof CrmFel ? orsak.text : { sv: "Det gick inte att spara. Försök igen.", en: "Could not save. Try again." });
      }
    } finally {
      setSparar(false);
    }
  }

  const fel = Object.values(falt).filter(Boolean).length;
  const grupp = (rubrik: string, barn: React.ReactNode) => (
    <fieldset className="crm-formgrupp">
      <legend className="mb-3 text-[0.8125rem] font-semibold text-ink-muted">{rubrik}</legend>
      <div className="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2">{barn}</div>
    </fieldset>
  );
  const hel = (k: Personfalt, barn: React.ReactNode) => (
    <div data-falt={k} className="sm:col-span-2">
      {barn}
    </div>
  );
  const halv = (k: Personfalt, barn: React.ReactNode) => <div data-falt={k}>{barn}</div>;
  const textfalt = (k: Exclude<keyof Varden, "company_id" | "legal_basis" | "do_not_contact">, etikett: Localized, mer?: Partial<React.ComponentProps<typeof TextInput>>) => (
    <TextInput label={text(etikett)} value={v[k]} onChange={(x) => satt(k, x)} width="100%" status={status(k)} isOptional {...mer} />
  );

  const namn = person ? personnamn(person) : null;

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && stang()} purpose="form" width={600}>
      <Layout
        header={
          <DialogHeader
            title={ny ? text({ sv: "Ny person", en: "New person" }) : text({ sv: "Redigera person", en: "Edit person" })}
            subtitle={namn ?? undefined}
            onOpenChange={(o) => !o && stang()}
          />
        }
        content={
          <LayoutContent>
            <form id="crm-personformular" ref={rot} onSubmit={spara} noValidate className="flex flex-col gap-6">
              {allmant ? <Banner status="error" container="card" title={text({ sv: "Det gick inte att spara", en: "Could not save" })} description={text(allmant)} /> : null}
              {/* Statusregionen finns från början, så att skärmläsaren annonserar när den fylls. */}
              <div role="status" className="sr-only">
                {fel > 0
                  ? fel === 1
                    ? text({ sv: "Ett fält behöver rättas innan personen kan sparas.", en: "One field needs fixing before the person can be saved." })
                    : text({ sv: `${fel} fält behöver rättas innan personen kan sparas.`, en: `${fel} fields need fixing before the person can be saved.` })
                  : ""}
              </div>
              {fel > 0 ? (
                <Text color="secondary" type="supporting">
                  {fel === 1
                    ? text({ sv: "Ett fält behöver rättas innan personen kan sparas.", en: "One field needs fixing before the person can be saved." })
                    : text({ sv: `${fel} fält behöver rättas innan personen kan sparas.`, en: `${fel} fields need fixing before the person can be saved.` })}
                </Text>
              ) : null}
              {grupp(
                text({ sv: "Person", en: "Person" }),
                <>
                  {halv("first_name", textfalt("first_name", { sv: "Förnamn", en: "First name" }, { isOptional: false }))}
                  {halv("last_name", textfalt("last_name", { sv: "Efternamn", en: "Last name" }))}
                  {halv("title", textfalt("title", { sv: "Titel", en: "Title" }, { placeholder: text({ sv: "VD", en: "CEO" }) }))}
                  {halv(
                    "company_id",
                    <Selector
                      label={text({ sv: "Bolag", en: "Company" })}
                      value={v.company_id}
                      onChange={(x) => x && satt("company_id", x)}
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
                </>
              )}
              {grupp(
                text({ sv: "Kontakt", en: "Contact" }),
                <>
                  {hel("email", textfalt("email", { sv: "E-post", en: "Email" }, { type: "email" }))}
                  {halv("mobile", textfalt("mobile", { sv: "Mobil", en: "Mobile" }, { type: "tel" }))}
                  {halv("phone", textfalt("phone", { sv: "Telefon", en: "Phone" }, { type: "tel" }))}
                </>
              )}
              {grupp(
                text({ sv: "Behandling", en: "Processing" }),
                <>
                  {hel(
                    "legal_basis",
                    <Selector
                      label={text({ sv: "Rättslig grund", en: "Legal basis" })}
                      description={text({
                        sv: "Varför ni får spara personen (GDPR artikel 6).",
                        en: "Why you may store the person (GDPR article 6)."
                      })}
                      value={v.legal_basis}
                      onChange={(x) => x && satt("legal_basis", x)}
                      options={[
                        { value: INGET, label: text({ sv: "Inte angiven", en: "Not stated" }) },
                        ...(Object.keys(GRUNDER) as RattsligGrund[]).map((g) => ({ value: g, label: text(GRUNDER[g]) }))
                      ]}
                      width="100%"
                      status={status("legal_basis")}
                    />
                  )}
                  {hel(
                    "do_not_contact",
                    <CheckboxInput
                      label={text({ sv: "Kontakta inte", en: "Do not contact" })}
                      description={text({
                        sv: "Personen tas inte med i utskick och listor.",
                        en: "The person is left out of mailings and lists."
                      })}
                      value={v.do_not_contact}
                      onChange={(x) => satt("do_not_contact", x)}
                    />
                  )}
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
                form="crm-personformular"
                variant="primary"
                label={ny ? text({ sv: "Skapa personen", en: "Create person" }) : text({ sv: "Spara ändringarna", en: "Save changes" })}
                isLoading={sparar}
              />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
