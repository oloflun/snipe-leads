"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { Dialog, DialogHeader } from "@astryxdesign/core/Dialog";
import { Drawer, DrawerHeader } from "@astryxdesign/core/Drawer";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { FormLayout } from "@astryxdesign/core/FormLayout";
import { Layout, LayoutContent, LayoutFooter } from "@astryxdesign/core/Layout";
import { Link } from "@astryxdesign/core/Link";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { Selector } from "@astryxdesign/core/Selector";
import { HStack, VStack } from "@astryxdesign/core/Stack";
import { TabList, Tab } from "@astryxdesign/core/TabList";
import { Table, pixel, proportional, type TableColumn } from "@astryxdesign/core/Table";
import { Text } from "@astryxdesign/core/Text";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { Felruta, Sida, Uppgift } from "@/components/crm/app/Sida";
import {
  CrmFel,
  RELATIONER,
  crmAnrop,
  orgnrVisning,
  type Bolag,
  type Oversikt,
  type Person,
  type Relation,
  type Sida as Svarssida
} from "@/lib/crm/api";
import { useLocale } from "@/lib/i18n";

type Filter = "alla" | Relation;

const FLIKAR: Filter[] = ["alla", "customer", "former_customer", "prospect"];
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
const RELATIONSFARG: Record<Relation, "green" | "gray" | "yellow" | "blue"> = {
  customer: "green",
  former_customer: "gray",
  prospect: "yellow",
  partner: "blue",
  supplier: "blue",
  other: "gray"
};

export function BolagVy() {
  const { text, locale } = useLocale();
  const [filter, setFilter] = useState<Filter>("alla");
  const [sok, setSok] = useState("");
  const [fraga, setFraga] = useState("");
  const [rader, setRader] = useState<Bolag[]>([]);
  const [nasta, setNasta] = useState<string | null>(null);
  const [antal, setAntal] = useState<Record<string, number> | null>(null);
  const [laddar, setLaddar] = useState(true);
  const [fel, setFel] = useState<unknown>(null);
  const [oppet, setOppet] = useState<Bolag | null>(null);
  const [nytt, setNytt] = useState(false);
  const omgang = useRef(0);

  // Sökningen väntar tills man slutat skriva, så att varje tangent inte blir ett anrop.
  useEffect(() => {
    const t = window.setTimeout(() => setFraga(sok.trim()), 250);
    return () => window.clearTimeout(t);
  }, [sok]);

  const hamta = useCallback(
    async (markor: string | null) => {
      const denna = ++omgang.current;
      setLaddar(true);
      setFel(null);
      const q = new URLSearchParams({ limit: "50", sort: "name" });
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
        if (denna === omgang.current) setLaddar(false);
      }
    },
    [filter, fraga]
  );

  useEffect(() => {
    void hamta(null);
  }, [hamta]);

  const kolumner = useMemo<TableColumn<Bolag>[]>(
    () => [
      {
        key: "name",
        header: text({ sv: "Bolag", en: "Company" }),
        width: proportional(3, { minWidth: 200 }),
        renderCell: (b) => (
          <Link href="#" color="primary" weight="medium" onClick={(e) => { e.preventDefault(); setOppet(b); }}>
            {b.name ?? text({ sv: "Namnlöst bolag", en: "Unnamed company" })}
          </Link>
        )
      },
      {
        key: "org_number",
        header: text({ sv: "Org.nr", en: "Org. no." }),
        width: pixel(132),
        renderCell: (b) => <Text hasTabularNumbers>{orgnrVisning(b.org_number)}</Text>
      },
      {
        key: "relation",
        header: text({ sv: "Relation", en: "Relation" }),
        width: pixel(140),
        renderCell: (b) => <Badge variant={RELATIONSFARG[b.relation]} label={text(RELATIONER[b.relation])} />
      },
      { key: "city", header: text({ sv: "Ort", en: "City" }), width: proportional(1.5, { minWidth: 110 }), renderCell: (b) => b.address.city ?? "" },
      { key: "owner", header: text({ sv: "Ansvarig", en: "Owner" }), width: proportional(1.5, { minWidth: 120 }), renderCell: (b) => b.owner ?? "" },
      { key: "source", header: text({ sv: "Källa", en: "Source" }), width: pixel(120), renderCell: (b) => b.external_ids[0]?.connection ?? b.source ?? "" },
      {
        key: "updated_at",
        header: text({ sv: "Ändrad", en: "Updated" }),
        width: pixel(170),
        renderCell: (b) => (b.updated_at ? <Timestamp value={b.updated_at} format="auto" /> : null)
      }
    ],
    [text]
  );

  const totalt = antal?.alla;
  return (
    <Sida
      rubrik={text({ sv: "Bolag", en: "Companies" })}
      antal={totalt == null ? undefined : text({ sv: `${totalt} bolag`, en: `${totalt} companies` })}
      atgarder={<Button variant="primary" label={text({ sv: "Nytt bolag", en: "New company" })} onClick={() => setNytt(true)} />}
      verktyg={
        <HStack justify="between" align="end" gap={4} wrap="wrap">
          <TabList value={filter} onChange={(v) => setFilter(v as Filter)} role="tablist">
            {FLIKAR.map((f) => (
              <Tab
                key={f}
                value={f}
                panelId="crm-bolag-lista"
                label={f === "alla" ? text({ sv: "Alla", en: "All" }) : text(RELATIONER[f])}
                endContent={
                  antal ? (
                    <Text type="supporting" color="secondary" hasTabularNumbers>
                      {antal[RAKNENYCKEL[f]] ?? 0}
                    </Text>
                  ) : undefined
                }
              />
            ))}
          </TabList>
          <div className="w-full pb-2 sm:w-72">
            <TextInput
              type="search"
              size="sm"
              label={text({ sv: "Sök bolag", en: "Search companies" })}
              isLabelHidden
              placeholder={text({ sv: "Sök namn, nummer eller ort", en: "Search name, number or city" })}
              startIcon="search"
              hasClear
              value={sok}
              onChange={setSok}
              width="100%"
            />
          </div>
        </HStack>
      }
    >
      <div id="crm-bolag-lista" role="tabpanel">
        {laddar ? <ProgressBar label={text({ sv: "Hämtar bolag", en: "Loading companies" })} isLabelHidden isIndeterminate /> : null}
        {fel ? (
          <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta(null)} />} />
        ) : (
          <Table
            data={rader}
            columns={kolumner}
            idKey="id"
            density="compact"
            hasHover
            textOverflow="truncate"
            emptyState={
              laddar ? (
                false
              ) : fraga || filter !== "alla" ? (
                <EmptyState
                  isCompact
                  title={text({ sv: "Inga bolag matchar", en: "No companies match" })}
                  description={text({ sv: "Ändra sökningen eller välj en annan flik.", en: "Change the search or pick another tab." })}
                />
              ) : (
                <EmptyState
                  title={text({ sv: "Inga bolag än", en: "No companies yet" })}
                  description={text({
                    sv: "Synka in er kundstock från ert CRM, eller lägg till det första bolaget för hand.",
                    en: "Sync your customer base from your CRM, or add the first company by hand."
                  })}
                  actions={<Button variant="primary" label={text({ sv: "Nytt bolag", en: "New company" })} onClick={() => setNytt(true)} />}
                />
              )
            }
          />
        )}
        {nasta && !fel ? (
          <HStack justify="center" padding={4}>
            <Button label={text({ sv: "Visa fler", en: "Show more" })} isLoading={laddar} onClick={() => void hamta(nasta)} />
          </HStack>
        ) : null}
      </div>

      <Bolagspanel bolag={oppet} stang={() => setOppet(null)} sprak={locale} />
      <NyttBolag
        oppen={nytt}
        stang={() => setNytt(false)}
        skapat={(b) => {
          setNytt(false);
          setOppet(b);
          void hamta(null);
        }}
      />
    </Sida>
  );
}

/** Postens detaljer i en panel till höger. Listan ligger kvar bakom. */
function Bolagspanel({ bolag, stang, sprak }: Readonly<{ bolag: Bolag | null; stang: () => void; sprak: "sv" | "en" }>) {
  const { text } = useLocale();
  const [personer, setPersoner] = useState<Person[] | null>(null);
  const id = bolag?.id;

  useEffect(() => {
    setPersoner(null);
    if (!id) return;
    let aktuell = true;
    crmAnrop<Svarssida<Person>>(`/v1/people?company_id=${id}&limit=50&sort=name`)
      .then((s) => aktuell && setPersoner(s.data))
      .catch(() => aktuell && setPersoner([]));
    return () => {
      aktuell = false;
    };
  }, [id]);

  const kronor = (v: number | null) =>
    v == null ? "" : new Intl.NumberFormat(sprak === "sv" ? "sv-SE" : "en-GB", { style: "currency", currency: "SEK", maximumFractionDigits: 0 }).format(v);
  const a = bolag?.address;
  const adress = a ? [a.co ? `c/o ${a.co}` : null, a.street, [a.postal_code, a.city].filter(Boolean).join(" ")].filter(Boolean).join(", ") : "";

  return (
    <Drawer isOpen={bolag != null} onOpenChange={(o) => !o && stang()} label={text({ sv: "Bolagets uppgifter", en: "Company details" })} width={440}>
      {bolag ? (
        <Layout
          header={
            <DrawerHeader
              title={bolag.name ?? text({ sv: "Namnlöst bolag", en: "Unnamed company" })}
              subtitle={orgnrVisning(bolag.org_number) || undefined}
              onOpenChange={(o) => !o && stang()}
              endContent={<Badge variant={RELATIONSFARG[bolag.relation]} label={text(RELATIONER[bolag.relation])} />}
            />
          }
          content={
            <LayoutContent>
              <VStack gap={5}>
                <VStack gap={3}>
                  <Uppgift etikett={text({ sv: "Webbplats", en: "Website" })}>
                    {bolag.website ? (
                      <Link href={bolag.website} isExternalLink>
                        {bolag.domain ?? bolag.website}
                      </Link>
                    ) : null}
                  </Uppgift>
                  <Uppgift etikett={text({ sv: "E-post", en: "Email" })}>{bolag.email}</Uppgift>
                  <Uppgift etikett={text({ sv: "Telefon", en: "Phone" })}>{bolag.phone}</Uppgift>
                  <Uppgift etikett={text({ sv: "Adress", en: "Address" })}>{adress}</Uppgift>
                </VStack>
                <VStack gap={3}>
                  <Uppgift etikett={text({ sv: "Ansvarig", en: "Owner" })}>{bolag.owner}</Uppgift>
                  <Uppgift etikett={text({ sv: "Kund sedan", en: "Customer since" })}>{bolag.customer_since}</Uppgift>
                  <Uppgift etikett={text({ sv: "Avtalsslut", en: "Contract end" })}>{bolag.contract_end}</Uppgift>
                  <Uppgift etikett={text({ sv: "Får kontaktas", en: "May be contacted" })}>
                    {bolag.do_not_contact ? text({ sv: "Nej, kontakta inte", en: "No, do not contact" }) : text({ sv: "Ja", en: "Yes" })}
                  </Uppgift>
                </VStack>
                <VStack gap={3}>
                  <Uppgift etikett={text({ sv: "Momsregistreringsnummer", en: "VAT number" })}>{bolag.vat_number}</Uppgift>
                  <Uppgift etikett={text({ sv: "Bolagsform", en: "Legal form" })}>
                    {bolag.sole_proprietor ? text({ sv: "Enskild firma", en: "Sole proprietorship" }) : bolag.legal_form}
                  </Uppgift>
                  <Uppgift etikett={text({ sv: "SNI-kod", en: "SNI code" })}>{bolag.sni_code}</Uppgift>
                  <Uppgift etikett={text({ sv: "Anställda", en: "Employees" })}>{bolag.employees}</Uppgift>
                  <Uppgift etikett={text({ sv: "Omsättning", en: "Revenue" })}>{kronor(bolag.revenue_sek)}</Uppgift>
                </VStack>
                <VStack gap={2}>
                  <Text weight="semibold">{text({ sv: "Personer", en: "People" })}</Text>
                  {personer == null ? (
                    <ProgressBar label={text({ sv: "Hämtar personer", en: "Loading people" })} isLabelHidden isIndeterminate />
                  ) : personer.length === 0 ? (
                    <Text color="secondary">{text({ sv: "Inga personer är knutna till bolaget.", en: "No people are linked to this company." })}</Text>
                  ) : (
                    personer.map((p) => (
                      <VStack key={p.id} gap={0}>
                        <Text weight="medium">{[p.first_name, p.last_name].filter(Boolean).join(" ") || p.email}</Text>
                        <Text type="supporting" color="secondary">
                          {[p.title, p.email, p.mobile ?? p.phone].filter(Boolean).join(" · ")}
                        </Text>
                      </VStack>
                    ))
                  )}
                </VStack>
                <VStack gap={2}>
                  <Text weight="semibold">{text({ sv: "Källa", en: "Source" })}</Text>
                  {bolag.external_ids.length === 0 ? (
                    <Text color="secondary">
                      {bolag.source === "api" ? text({ sv: "Skapad över API:t.", en: "Created over the API." }) : text({ sv: "Skapad i Snajp.", en: "Created in Snajp." })}
                    </Text>
                  ) : (
                    bolag.external_ids.map((x) => (
                      <HStack key={`${x.connection}:${x.id}`} justify="between" gap={3}>
                        <Text>{x.connection}</Text>
                        <Text type="code" color="secondary">
                          {x.id}
                        </Text>
                      </HStack>
                    ))
                  )}
                </VStack>
              </VStack>
            </LayoutContent>
          }
        />
      ) : null}
    </Drawer>
  );
}

function NyttBolag({ oppen, stang, skapat }: Readonly<{ oppen: boolean; stang: () => void; skapat: (b: Bolag) => void }>) {
  const { text } = useLocale();
  const [namn, setNamn] = useState("");
  const [orgnr, setOrgnr] = useState("");
  const [relation, setRelation] = useState<Relation>("customer");
  const [sparar, setSparar] = useState(false);
  const [fel, setFel] = useState<CrmFel | null>(null);

  useEffect(() => {
    if (oppen) {
      setNamn("");
      setOrgnr("");
      setRelation("customer");
      setFel(null);
    }
  }, [oppen]);

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    if (!namn.trim() || sparar) return;
    setSparar(true);
    setFel(null);
    try {
      skapat(
        await crmAnrop<Bolag>("/v1/companies", {
          method: "POST",
          body: JSON.stringify({ name: namn.trim(), org_number: orgnr.trim() || null, relation })
        })
      );
    } catch (orsak) {
      setFel(orsak instanceof CrmFel ? orsak : new CrmFel({ sv: "Det gick inte att spara.", en: "Could not save." }, 0, null));
    } finally {
      setSparar(false);
    }
  }

  return (
    <Dialog isOpen={oppen} onOpenChange={(o) => !o && stang()} purpose="form" width={440}>
      <Layout
        header={<DialogHeader title={text({ sv: "Nytt bolag", en: "New company" })} onOpenChange={(o) => !o && stang()} />}
        content={
          <LayoutContent>
            <form id="crm-nytt-bolag" onSubmit={spara}>
              <FormLayout>
            <TextInput label={text({ sv: "Bolagsnamn", en: "Company name" })} value={namn} onChange={setNamn} isRequired hasAutoFocus width="100%" />
            <TextInput
              label={text({ sv: "Organisationsnummer", en: "Organisation number" })}
              description={text({
                sv: "Tio siffror. Finns numret redan uppdateras det bolaget i stället.",
                en: "Ten digits. If the number already exists, that company is updated instead."
              })}
              value={orgnr}
              onChange={setOrgnr}
              inputMode="numeric"
              placeholder="556036-0793"
              isOptional
              width="100%"
              status={fel ? { type: "error", message: text(fel.text) } : undefined}
            />
            <Selector
              label={text({ sv: "Relation", en: "Relation" })}
              value={relation}
              onChange={(v) => v && setRelation(v as Relation)}
              options={(Object.keys(RELATIONER) as Relation[]).map((r) => ({ value: r, label: text(RELATIONER[r]) }))}
              width="100%"
            />
              </FormLayout>
            </form>
          </LayoutContent>
        }
        footer={
          <LayoutFooter>
            <HStack justify="end" gap={2}>
              <Button label={text({ sv: "Avbryt", en: "Cancel" })} onClick={stang} />
              <Button type="submit" form="crm-nytt-bolag" variant="primary" label={text({ sv: "Spara bolaget", en: "Save company" })} isLoading={sparar} isDisabled={!namn.trim()} />
            </HStack>
          </LayoutFooter>
        }
      />
    </Dialog>
  );
}
