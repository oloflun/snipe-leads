"use client";

import { useCallback, useEffect, useState } from "react";
import NextLink from "next/link";
import { ArrowLeftRight, ArrowUpRight, CalendarClock, History, ListTodo, Mail, MailOpen, Phone, Plus, StickyNote, type LucideIcon } from "lucide-react";
import { Button } from "@astryxdesign/core/Button";
import type { ISODateString } from "@astryxdesign/core/Calendar";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { DateInput } from "@astryxdesign/core/DateInput";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { Text } from "@astryxdesign/core/Text";
import { TextArea } from "@astryxdesign/core/TextArea";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { Objektikon, useSkrivratt, type Ton } from "@/components/crm/app/kit";
import { CrmFel, dagtext } from "@/lib/crm/api";
import { irisAnrop, meddelaLeadsUppdaterade } from "@/lib/crm/iris/anrop";
import { SAMTALSUTFALL, STATUS_ETIKETT, type Leadhandelse } from "@/lib/crm/iris/lead";
import { useLocale, type Localized } from "@/lib/i18n";

/** Händelsens ikon, ton och namn. */
const SLAG: Record<Leadhandelse["typ"], { ikon: LucideIcon; ton: Ton; namn: Localized }> = {
  skapad: { ikon: Plus, ton: "mossa", namn: { sv: "Hittad av Iris", en: "Found by Iris" } },
  status: { ikon: ArrowLeftRight, ton: "bla", namn: { sv: "Status", en: "Status" } },
  mejl_ut: { ikon: Mail, ton: "ockra", namn: { sv: "Mejl skickat", en: "Email sent" } },
  mejl_in: { ikon: MailOpen, ton: "mossa", namn: { sv: "Svar", en: "Reply" } },
  anteckning: { ikon: StickyNote, ton: "ockra", namn: { sv: "Anteckning", en: "Note" } },
  uppgift: { ikon: ListTodo, ton: "mineral", namn: { sv: "Uppgift", en: "Task" } },
  samtal: { ikon: Phone, ton: "sigill", namn: { sv: "Samtal", en: "Call" } }
};

const iso = (v: string): ISODateString | undefined => (/^\d{4}-\d{2}-\d{2}$/.test(v) ? (v as ISODateString) : undefined);

/**
 * Leadets historik i panelen (LR-069). Leadet är ett prospekt hos Iris, inte en
 * post i CRM:ets register, och har därför ingen tidslinje i CRM:ets API: historiken
 * läses ur leads-API:t (`GET /leads/prospects/{id}/tidslinje`), samma som dagens
 * låda visar, och ritas i CRM:ets tidslinjeform (`.crm-tidslinje`, `.crm-skrivyta`).
 *
 * Skrivytan: anteckning (högst 4 000 tecken) och uppgift (titel, förfallodag).
 * En öppen uppgift bockas av i raden; avbockningen är optimistisk och återställs
 * vid fel.
 */
export function LeadHistorik({ id, omgang = 0 }: Readonly<{ id: string; omgang?: number }>) {
  const { text, locale } = useLocale();
  const skriv = useSkrivratt("test");
  const [handelser, setHandelser] = useState<Leadhandelse[] | null>(null);
  const [fel, setFel] = useState<unknown>(null);
  const [skriver, setSkriver] = useState<"anteckning" | "uppgift" | null>(null);
  const [anteckning, setAnteckning] = useState("");
  const [titel, setTitel] = useState("");
  const [forfaller, setForfaller] = useState("");
  const [sparar, setSparar] = useState(false);
  const [skrivfel, setSkrivfel] = useState<string | null>(null);
  const [besked, setBesked] = useState("");

  const hamta = useCallback(async () => {
    try {
      const svar = await irisAnrop<{ handelser?: Leadhandelse[] }>(`/leads/prospects/${encodeURIComponent(id)}/tidslinje`);
      setHandelser(svar.handelser ?? []);
      setFel(null);
    } catch (e) {
      setFel(e);
    }
  }, [id]);

  useEffect(() => {
    setHandelser(null);
    void hamta();
  }, [hamta, omgang]);

  const stang = () => {
    setSkriver(null);
    setAnteckning("");
    setTitel("");
    setForfaller("");
    setSkrivfel(null);
  };

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    if (sparar) return;
    const anteckningen = skriver === "anteckning";
    if (anteckningen ? !anteckning.trim() : !titel.trim()) {
      setSkrivfel(anteckningen ? text({ sv: "Skriv något först.", en: "Write something first." }) : text({ sv: "Uppgiften behöver en titel.", en: "The task needs a title." }));
      return;
    }
    setSparar(true);
    setSkrivfel(null);
    try {
      if (anteckningen) {
        await irisAnrop(`/leads/prospects/${encodeURIComponent(id)}/anteckningar`, { method: "POST", body: JSON.stringify({ text: anteckning.trim() }) });
      } else {
        await irisAnrop(`/leads/prospects/${encodeURIComponent(id)}/uppgifter`, { method: "POST", body: JSON.stringify({ titel: titel.trim(), forfaller: forfaller || null }) });
      }
      setBesked(anteckningen ? text({ sv: "Anteckningen är sparad.", en: "The note is saved." }) : text({ sv: "Uppgiften är sparad.", en: "The task is saved." }));
      stang();
      meddelaLeadsUppdaterade("crm-iris");
      await hamta();
    } catch (fel) {
      setSkrivfel(text(fel instanceof CrmFel ? fel.text : { sv: "Det gick inte att spara.", en: "Could not save." }));
    } finally {
      setSparar(false);
    }
  }

  async function bocka(h: Leadhandelse, klar: boolean) {
    if (!h.id) return;
    setHandelser((l) => l?.map((x) => (x.typ === "uppgift" && x.id === h.id ? { ...x, klar } : x)) ?? null);
    try {
      await irisAnrop(`/leads/uppgifter/${encodeURIComponent(h.id)}`, { method: "PATCH", body: JSON.stringify({ klar }) });
      setBesked(klar ? text({ sv: `${h.rubrik} är klar.`, en: `${h.rubrik} is done.` }) : text({ sv: `${h.rubrik} är öppen igen.`, en: `${h.rubrik} is open again.` }));
      meddelaLeadsUppdaterade("crm-iris");
    } catch (fel) {
      setHandelser((l) => l?.map((x) => (x.typ === "uppgift" && x.id === h.id ? { ...x, klar: !klar } : x)) ?? null);
      setBesked(text(fel instanceof CrmFel ? fel.text : { sv: "Uppgiften sparades inte.", en: "The task was not saved." }));
    }
  }

  /** Statusraden bär råa nycklar ("new → ready"); de översätts här. Samtalets rubrik är utfallets nyckel. */
  const rubrik = (h: Leadhandelse) => {
    if (h.typ === "status") {
      return h.rubrik
        .split("→")
        .map((d) => {
          const k = d.trim();
          return STATUS_ETIKETT[k] ? text(STATUS_ETIKETT[k]) : k;
        })
        .join(" → ");
    }
    if (h.typ === "samtal") return SAMTALSUTFALL[h.rubrik] ? text(SAMTALSUTFALL[h.rubrik]) : h.rubrik;
    if (h.typ === "anteckning") return text(SLAG.anteckning.namn);
    return h.rubrik ? `${text(SLAG[h.typ].namn)}: ${h.rubrik}` : text(SLAG[h.typ].namn);
  };

  const skrivyta =
    skriver == null ? (
      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="secondary" label={text({ sv: "Anteckning", en: "Note" })} icon={<Icon icon={StickyNote} size="sm" />} isDisabled={!skriv.far} tooltip={skriv.skal ?? undefined} onClick={() => setSkriver("anteckning")} />
        <Button size="sm" variant="secondary" label={text({ sv: "Uppgift", en: "Task" })} icon={<Icon icon={ListTodo} size="sm" />} isDisabled={!skriv.far} tooltip={skriv.skal ?? undefined} onClick={() => setSkriver("uppgift")} />
      </div>
    ) : (
      <form
        onSubmit={spara}
        noValidate
        className="crm-skrivyta flex flex-col gap-3"
        onKeyDown={(e) => {
          if (e.key !== "Escape") return;
          e.preventDefault();
          e.stopPropagation();
          stang();
        }}
      >
        {skriver === "anteckning" ? (
          <TextArea
            label={text({ sv: "Ny anteckning", en: "New note" })}
            placeholder={text({ sv: "Vad kom ni fram till?", en: "What did you agree on?" })}
            rows={4}
            value={anteckning}
            onChange={(v) => {
              setAnteckning(v.slice(0, 4000));
              setSkrivfel(null);
            }}
            width="100%"
            status={skrivfel ? { type: "error", message: skrivfel } : undefined}
            hasAutoFocus
          />
        ) : (
          <>
            <TextInput
              label={text({ sv: "Ny uppgift", en: "New task" })}
              placeholder={text({ sv: "Ring och fråga om offerten", en: "Call and ask about the quote" })}
              value={titel}
              onChange={(v) => {
                setTitel(v.slice(0, 200));
                setSkrivfel(null);
              }}
              width="100%"
              status={skrivfel ? { type: "error", message: skrivfel } : undefined}
              hasAutoFocus
            />
            <DateInput label={text({ sv: "Förfaller", en: "Due" })} value={iso(forfaller)} onChange={(v) => setForfaller(v ?? "")} weekStartsOn="mon" format="date" hasClear isOptional width="100%" />
          </>
        )}
        <div className="flex items-center justify-end gap-2">
          <Button size="sm" variant="ghost" label={text({ sv: "Avbryt", en: "Cancel" })} onClick={stang} isDisabled={sparar} />
          <Button size="sm" type="submit" variant="primary" label={text({ sv: "Spara", en: "Save" })} isLoading={sparar} />
        </div>
      </form>
    );

  const oppna = (handelser ?? []).filter((h) => h.typ === "uppgift" && !h.klar && h.id);
  const flode = (handelser ?? []).filter((h) => !(h.typ === "uppgift" && !h.klar && h.id));
  const idag = new Date().toISOString().slice(0, 10);

  let innehall: React.ReactNode;
  if (fel && !handelser) {
    innehall = (
      <div className="flex flex-col items-start gap-3 py-2">
        <Text color="secondary">{text(fel instanceof CrmFel ? fel.text : { sv: "Historiken gick inte att hämta.", en: "The history could not be loaded." })}</Text>
        <Button size="sm" variant="secondary" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => void hamta()} />
      </div>
    );
  } else if (!handelser) {
    innehall = (
      <div className="flex flex-col gap-5 py-1" role="status" aria-busy="true" aria-label={text({ sv: "Hämtar historiken", en: "Loading the history" })}>
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="flex items-start gap-3">
            <Skeleton width={24} height={24} radius={2} index={i} />
            <span className="flex flex-1 flex-col gap-2 pt-1">
              <Skeleton width={`${45 + ((i * 17) % 35)}%`} height={10} radius="rounded" index={i} />
              <Skeleton width="30%" height={8} radius="rounded" index={i} />
            </span>
          </div>
        ))}
      </div>
    );
  } else if (flode.length === 0 && oppna.length === 0) {
    innehall = (
      <EmptyState
        isCompact
        icon={<Icon icon={History} size="lg" color="secondary" />}
        title={text({ sv: "Inget har hänt med bolaget än", en: "Nothing has happened with the company yet" })}
        description={text({ sv: "Statusbyten, mejl, samtal, anteckningar och uppgifter samlas här.", en: "Status changes, emails, calls, notes and tasks are collected here." })}
      />
    );
  } else {
    innehall = (
      <ol className="crm-tidslinje" aria-label={text({ sv: "Historik, nyast först", en: "History, newest first" })}>
        {flode.map((h, i) => {
          const s = SLAG[h.typ];
          const uppgiften = h.typ === "uppgift";
          return (
            <li key={`${h.typ}-${h.id ?? i}-${h.nar}`} className="crm-tidslinje-rad">
              <span className="crm-tidslinje-ikon">
                <Objektikon ikon={s.ikon} ton={s.ton} storlek={24} />
              </span>
              <span className="flex min-w-0 flex-1 flex-col gap-0.5 pb-4">
                <span className={`text-[0.875rem] text-ink [overflow-wrap:anywhere] ${uppgiften && h.klar ? "line-through" : ""}`}>{rubrik(h)}</span>
                {h.text && !uppgiften ? <span className="crm-tidslinje-text">{h.text}</span> : null}
                <span className="flex flex-wrap items-center gap-x-1.5 text-[0.8125rem] text-ink-muted">
                  {uppgiften && h.klar ? (
                    <>
                      <span>{text({ sv: "Klar", en: "Done" })}</span>
                      <span aria-hidden>·</span>
                    </>
                  ) : null}
                  <Timestamp value={h.nar} format="relative" />
                </span>
              </span>
              {uppgiften && h.klar && h.id ? (
                <span className="shrink-0">
                  <CheckboxInput label={text({ sv: `Öppna igen: ${h.rubrik}`, en: `Reopen: ${h.rubrik}` })} isLabelHidden value isDisabled={!skriv.far} onChange={(v) => void bocka(h, v)} />
                </span>
              ) : null}
            </li>
          );
        })}
      </ol>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div role="status" className="sr-only">
        {besked}
      </div>
      {skrivyta}
      {oppna.length > 0 ? (
        <section aria-label={text({ sv: "Att göra", en: "To do" })} className="flex flex-col gap-1">
          <Text type="label" color="secondary" weight="medium">
            {text({ sv: "Att göra", en: "To do" })}
          </Text>
          <ul className="flex flex-col">
            {oppna.map((h) => {
              const sen = h.text != null && h.text < idag;
              return (
                <li key={h.id} className="crm-attgora flex items-center gap-2 py-1.5">
                  <CheckboxInput label={text({ sv: `Klar: ${h.rubrik}`, en: `Done: ${h.rubrik}` })} isLabelHidden value={false} isDisabled={!skriv.far} onChange={(v) => void bocka(h, v)} />
                  <span className="min-w-0 flex-1 truncate text-[0.875rem] text-ink">{h.rubrik}</span>
                  {h.text ? (
                    <span className={`inline-flex shrink-0 items-center gap-1 text-[0.8125rem] tabular-nums ${sen ? "text-danger" : "text-ink-muted"}`}>
                      <Icon icon={CalendarClock} size="xsm" color="inherit" />
                      <span>{dagtext(h.text, locale, true)}</span>
                      {sen ? <span className="sr-only">{text({ sv: ", har passerat", en: ", has passed" })}</span> : null}
                    </span>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}
      {innehall}
      {(handelser ?? []).some((h) => h.typ === "mejl_in") ? (
        <NextLink href="/dashboard/att-gora" className="crm-tidslinje-lank inline-flex items-center gap-1 text-[0.875rem] text-ink">
          <span>{text({ sv: "Svara under Att göra i dagens app", en: "Reply under To do in today's app" })}</span>
          <Icon icon={ArrowUpRight} size="xsm" color="secondary" />
        </NextLink>
      ) : null}
    </div>
  );
}
