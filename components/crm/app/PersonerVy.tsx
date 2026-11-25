"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@astryxdesign/core/Button";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Link } from "@astryxdesign/core/Link";
import { ProgressBar } from "@astryxdesign/core/ProgressBar";
import { HStack } from "@astryxdesign/core/Stack";
import { Table, pixel, proportional, type TableColumn } from "@astryxdesign/core/Table";
import { Text } from "@astryxdesign/core/Text";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { Felruta, Sida } from "@/components/crm/app/Sida";
import { crmAnrop, type Bolag, type Oversikt, type Person, type Sida as Svarssida } from "@/lib/crm/api";
import { useLocale } from "@/lib/i18n";

export function PersonerVy() {
  const { text } = useLocale();
  const [sok, setSok] = useState("");
  const [fraga, setFraga] = useState("");
  const [rader, setRader] = useState<Person[]>([]);
  const [bolagsnamn, setBolagsnamn] = useState<Record<string, string>>({});
  const [nasta, setNasta] = useState<string | null>(null);
  const [totalt, setTotalt] = useState<number | null>(null);
  const [laddar, setLaddar] = useState(true);
  const [fel, setFel] = useState<unknown>(null);
  const omgang = useRef(0);

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
      if (fraga) q.set("q", fraga);
      if (markor) q.set("cursor", markor);
      try {
        // Personens rad bär bara bolagets id. Namnen slås upp ur bolagslistan,
        // högst 500 åt gången: ett större register visar bolaget först när
        // API:t skickar namnet med personen.
        const [sida, oversikt, bolag] = await Promise.all([
          crmAnrop<Svarssida<Person>>(`/v1/people?${q}`),
          markor ? Promise.resolve(null) : crmAnrop<Oversikt>("/oversikt"),
          markor ? Promise.resolve(null) : crmAnrop<Svarssida<Bolag>>("/v1/companies?limit=500&sort=name")
        ]);
        if (denna !== omgang.current) return;
        setRader((forr) => (markor ? [...forr, ...sida.data] : sida.data));
        setNasta(sida.next_cursor);
        if (oversikt) setTotalt(oversikt.personer);
        if (bolag) setBolagsnamn(Object.fromEntries(bolag.data.map((b) => [b.id, b.name ?? ""])));
      } catch (e) {
        if (denna === omgang.current) setFel(e);
      } finally {
        if (denna === omgang.current) setLaddar(false);
      }
    },
    [fraga]
  );

  useEffect(() => {
    void hamta(null);
  }, [hamta]);

  const kolumner = useMemo<TableColumn<Person>[]>(
    () => [
      {
        key: "name",
        header: text({ sv: "Namn", en: "Name" }),
        width: proportional(2, { minWidth: 170 }),
        renderCell: (p) => <Text weight="medium">{[p.first_name, p.last_name].filter(Boolean).join(" ") || p.email || ""}</Text>
      },
      { key: "title", header: text({ sv: "Titel", en: "Title" }), width: proportional(1, { minWidth: 100 }), renderCell: (p) => p.title ?? "" },
      {
        key: "company",
        header: text({ sv: "Bolag", en: "Company" }),
        width: proportional(2, { minWidth: 170 }),
        renderCell: (p) => (p.company_id ? (bolagsnamn[p.company_id] ?? "") : "")
      },
      {
        key: "email",
        header: text({ sv: "E-post", en: "Email" }),
        width: proportional(2.5, { minWidth: 200 }),
        renderCell: (p) => (p.email ? <Link href={`mailto:${p.email}`} color="primary">{p.email}</Link> : null)
      },
      {
        key: "phone",
        header: text({ sv: "Telefon", en: "Phone" }),
        width: pixel(150),
        renderCell: (p) => <Text hasTabularNumbers>{p.mobile ?? p.phone ?? ""}</Text>
      },
      {
        key: "updated_at",
        header: text({ sv: "Ändrad", en: "Updated" }),
        width: pixel(170),
        renderCell: (p) => (p.updated_at ? <Timestamp value={p.updated_at} format="auto" /> : null)
      }
    ],
    [text, bolagsnamn]
  );

  return (
    <Sida
      rubrik={text({ sv: "Personer", en: "People" })}
      antal={totalt == null ? undefined : text({ sv: `${totalt} personer`, en: `${totalt} people` })}
      verktyg={
        <div className="w-full pb-3 sm:w-72">
          <TextInput
            type="search"
            size="sm"
            label={text({ sv: "Sök personer", en: "Search people" })}
            isLabelHidden
            placeholder={text({ sv: "Sök namn eller e-post", en: "Search name or email" })}
            startIcon="search"
            hasClear
            value={sok}
            onChange={setSok}
            width="100%"
          />
        </div>
      }
    >
      {laddar ? <ProgressBar label={text({ sv: "Hämtar personer", en: "Loading people" })} isLabelHidden isIndeterminate /> : null}
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
            ) : fraga ? (
              <EmptyState isCompact title={text({ sv: "Inga personer matchar", en: "No people match" })} description={text({ sv: "Ändra sökningen.", en: "Change the search." })} />
            ) : (
              <EmptyState
                title={text({ sv: "Inga personer än", en: "No people yet" })}
                description={text({
                  sv: "Personer följer med när ni synkar in kontakter från ert CRM.",
                  en: "People arrive when you sync contacts from your CRM."
                })}
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
    </Sida>
  );
}
