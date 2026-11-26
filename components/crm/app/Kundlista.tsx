"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Building2, CalendarCheck, Hash, SearchX, Sparkles, Target } from "lucide-react";
import { Badge } from "@astryxdesign/core/Badge";
import { Button } from "@astryxdesign/core/Button";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { List, ListItem } from "@astryxdesign/core/List";
import { Table, pixel, proportional, type TableColumn } from "@astryxdesign/core/Table";
import { Kolumnrubrik, Postchip, Prick, Privatpersonetikett, Tabellskelett, useSmal } from "@/components/crm/app/kit";
import { Felruta } from "@/components/crm/app/Sida";
import { crmAnrop, dagtext, orgnrVisning } from "@/lib/crm/api";
import { useLocale } from "@/lib/i18n";

/** Varifrån kunden kommer: det egna registret, eller ett lead som Iris vunnit. */
export type Kundursprung = "own" | "iris" | "all";

/** En rad i den samlade kundlistan (`GET /v1/customers`). */
export type Kundrad = {
  origin: "own" | "iris";
  /** Bolaget i registret. Saknas för en kund som bara finns som vunnet lead hos Iris. */
  company_id: string | null;
  lead_id: string | null;
  name: string | null;
  org_number: string | null;
  customer_since: string | null;
  private_person: boolean;
};

export type Kundsvar = { data: Kundrad[]; counts: { own: number; iris: number } };

/**
 * Den samlade kundlistan: egna kunder och kunder som Iris vunnit, i en lista
 * (Antons beslut 2026-11-26: registren hålls isär, men ska gå att se ihop).
 * Listan sätts ihop när den läses. Ett vunnet lead kopieras inte in i
 * registret, och ett lead som är samma bolag som en egen kund står en gång, som egen.
 *
 * En rad med ett bolag i registret öppnar bolagets panel. En kund som bara
 * finns hos Iris har ingen post här och går inte att öppna.
 */
export function Kundlista({
  ursprung,
  fraga,
  oppnaPost,
  antal
}: Readonly<{
  ursprung: Kundursprung;
  fraga: string;
  oppnaPost: (id: string) => void;
  /** Antalen per ursprung, till väljaren i vyraden. */
  antal?: (a: Kundsvar["counts"]) => void;
}>) {
  const { text, locale } = useLocale();
  const smal = useSmal();
  const sprak = locale === "sv" ? "sv-SE" : "en-GB";
  const [svar, setSvar] = useState<Kundsvar | null>(null);
  const [laddar, setLaddar] = useState(true);
  const [fel, setFel] = useState<unknown>(null);
  const omgang = useRef(0);
  const antalRef = useRef(antal);
  antalRef.current = antal;

  const hamta = useCallback(async () => {
    const denna = ++omgang.current;
    setLaddar(true);
    setFel(null);
    const q = new URLSearchParams({ origin: ursprung, limit: "500" });
    if (fraga) q.set("q", fraga);
    try {
      const s = await crmAnrop<Kundsvar>(`/v1/customers?${q}`);
      if (denna !== omgang.current) return;
      setSvar(s);
      antalRef.current?.(s.counts);
    } catch (e) {
      if (denna === omgang.current) setFel(e);
    } finally {
      if (denna === omgang.current) setLaddar(false);
    }
  }, [ursprung, fraga]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  const namnPa = useCallback((k: Kundrad) => k.name ?? text({ sv: "Namnlös kund", en: "Unnamed customer" }), [text]);
  const nyckel = (k: Kundrad) => k.company_id ?? `lead:${k.lead_id}`;

  const ursprungsmarke = useCallback(
    (k: Kundrad) =>
      k.origin === "iris" ? (
        <Badge variant="yellow" label={text({ sv: "Iris", en: "Iris" })} icon={<Prick ton="ockra" />} />
      ) : (
        <Badge variant="neutral" label={text({ sv: "Egen", en: "Own" })} icon={<Prick ton="bla" />} />
      ),
    [text]
  );

  type Rad = Kundrad & { id: string };
  const rader: Rad[] = useMemo(() => (svar?.data ?? []).map((k) => ({ ...k, id: nyckel(k) })), [svar]);

  const kolumner = useMemo<TableColumn<Rad>[]>(
    () => [
      {
        key: "name",
        header: <Kolumnrubrik ikon={Building2}>{text({ sv: "Kund", en: "Customer" })}</Kolumnrubrik>,
        width: proportional(1, { minWidth: 220 }),
        renderCell: (k) =>
          k.company_id ? (
            <Postchip namn={namnPa(k)} onClick={() => oppnaPost(k.company_id!)} label={text({ sv: `Öppna ${namnPa(k)}`, en: `Open ${namnPa(k)}` })} />
          ) : (
            <Postchip namn={namnPa(k)} />
          )
      },
      {
        key: "org_number",
        header: <Kolumnrubrik ikon={Hash}>{text({ sv: "Org.nr", en: "Org. no." })}</Kolumnrubrik>,
        width: pixel(140),
        renderCell: (k) => <span className="tabular-nums text-ink2">{orgnrVisning(k.org_number)}</span>
      },
      {
        key: "origin",
        header: <Kolumnrubrik ikon={Sparkles}>{text({ sv: "Ursprung", en: "Origin" })}</Kolumnrubrik>,
        width: pixel(200),
        // En privatperson kontaktas aldrig: märkningen står bredvid ursprunget, som i bolagslistan.
        renderCell: (k) => (
          <span className="inline-flex items-center gap-2">
            {ursprungsmarke(k)}
            {k.private_person ? <Privatpersonetikett /> : null}
            {k.origin === "own" && k.lead_id ? <span className="text-[0.8125rem] text-ink-muted">{text({ sv: "också lead hos Iris", en: "also a lead with Iris" })}</span> : null}
          </span>
        )
      },
      {
        key: "customer_since",
        header: <Kolumnrubrik ikon={CalendarCheck}>{text({ sv: "Kund sedan", en: "Customer since" })}</Kolumnrubrik>,
        width: pixel(160),
        renderCell: (k) => (k.customer_since ? <span className="tabular-nums text-ink2">{dagtext(k.customer_since, locale)}</span> : null)
      }
    ],
    [text, locale, namnPa, oppnaPost, ursprungsmarke]
  );

  if (fel) {
    return (
      <div className="p-4 sm:p-6">
        <Felruta fel={fel} igen={<Button size="sm" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />} />
      </div>
    );
  }
  if (laddar && !svar) {
    return <Tabellskelett rader={8} kolumner={smal ? 2 : 4} markering={false} label={text({ sv: "Hämtar kunderna", en: "Loading the customers" })} />;
  }

  const tomt = fraga ? (
    <EmptyState
      icon={<Icon icon={SearchX} size="lg" color="secondary" />}
      title={text({ sv: `Inga kunder matchar ”${fraga}”`, en: `No customers match “${fraga}”` })}
      description={text({ sv: "Sökningen går på namn och organisationsnummer.", en: "The search covers name and organisation number." })}
    />
  ) : (
    <EmptyState
      icon={<Icon icon={Target} size="lg" color="secondary" />}
      title={ursprung === "iris" ? text({ sv: "Iris har inte vunnit någon kund än", en: "Iris has not won a customer yet" }) : text({ sv: "Inga kunder än", en: "No customers yet" })}
      description={text({
        sv: "Ett lead som blir kund hos Iris hamnar här av sig självt. Det kopieras inte in i registret.",
        en: "A lead that becomes a customer with Iris shows up here by itself. It is not copied into the register."
      })}
    />
  );

  const egna = svar?.counts.own ?? 0;
  const iris = svar?.counts.iris ?? 0;
  const fot = (
    <div className="crm-raknefot" role="status">
      <span>
        <span className="crm-raknefot-etikett">{text({ sv: "Visar", en: "Showing" })}</span> <span className="crm-raknefot-tal">{rader.length.toLocaleString(sprak)}</span>
      </span>
      <span>
        <span className="crm-raknefot-etikett">{text({ sv: "Egna", en: "Own" })}</span> <span className="crm-raknefot-tal">{egna.toLocaleString(sprak)}</span>
      </span>
      <span>
        <span className="crm-raknefot-etikett">{text({ sv: "Vunna av Iris", en: "Won by Iris" })}</span> <span className="crm-raknefot-tal">{iris.toLocaleString(sprak)}</span>
      </span>
    </div>
  );

  if (rader.length === 0) return <div className="py-12">{tomt}</div>;

  if (smal) {
    return (
      <>
        <div className="px-2">
          <List hasDividers density="balanced" edge="padded">
            {rader.map((k) => (
              <ListItem
                key={k.id}
                label={<span className="font-semibold text-ink">{namnPa(k)}</span>}
                description={[orgnrVisning(k.org_number), k.customer_since ? dagtext(k.customer_since, locale) : null].filter(Boolean).join(" · ") || undefined}
                endContent={ursprungsmarke(k)}
                onClick={k.company_id ? () => oppnaPost(k.company_id!) : undefined}
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
      <Table<Rad> data={rader} columns={kolumner} idKey="id" density="balanced" dividers="rows" hasHover textOverflow="truncate" />
      {fot}
    </div>
  );
}
