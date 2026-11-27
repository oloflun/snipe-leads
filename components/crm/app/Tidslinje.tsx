"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import NextLink from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  ArrowUpRight,
  CalendarCheck,
  CalendarClock,
  CalendarX2,
  ClipboardCheck,
  Eraser,
  Flag,
  Handshake,
  History,
  LifeBuoy,
  ListTodo,
  Mail,
  MapPin,
  MoreHorizontal,
  Pencil,
  Phone,
  Plus,
  Reply,
  RotateCcw,
  Send,
  StickyNote,
  Target,
  Trash2,
  type LucideIcon
} from "lucide-react";
import { Button } from "@astryxdesign/core/Button";
import type { ISODateString } from "@astryxdesign/core/Calendar";
import { CheckboxInput } from "@astryxdesign/core/CheckboxInput";
import { DateInput } from "@astryxdesign/core/DateInput";
import { DropdownMenu } from "@astryxdesign/core/DropdownMenu";
import { EmptyState } from "@astryxdesign/core/EmptyState";
import { Icon } from "@astryxdesign/core/Icon";
import { IconButton } from "@astryxdesign/core/IconButton";
import { Selector } from "@astryxdesign/core/Selector";
import { Skeleton } from "@astryxdesign/core/Skeleton";
import { Text } from "@astryxdesign/core/Text";
import { TextArea } from "@astryxdesign/core/TextArea";
import { TextInput } from "@astryxdesign/core/TextInput";
import { Timestamp } from "@astryxdesign/core/Timestamp";
import { useToast } from "@astryxdesign/core/Toast";
import { Objektikon, type Ton } from "@/components/crm/app/kit";
import { FORLUSTORSAKER, belopp, type Forlustorsak } from "@/lib/crm/affar";
import { CrmFel, SYSTEMNAMN, crmAnrop, type Bolag } from "@/lib/crm/api";
import { faltetikett, uppraknat } from "@/lib/crm/felkoder";
import { useLocale, type Localized } from "@/lib/i18n";

/** En rad på tidslinjen som API:t lämnar den (`tidslinjepost_ut` i crm_v1_tidslinje.py). */
export type Tidslinjepost = {
  key: string;
  type: string;
  at: string;
  origin: "crm" | "iris" | "support";
  title: string | null;
  text: string | null;
  data: Record<string, unknown>;
  link: { kind: string; id: string } | null;
};

type Objekt = "companies" | "people" | "deals";
type Skriver = "anteckning" | "uppgift" | "aktivitet" | "utfall";
type Utfallskod = "no_answer" | "call_back" | "not_interested" | "do_not_contact" | "meeting_booked" | "won";

/**
 * Utfallen som sätts på bolaget och verkställs i leadsflödet hos Iris
 * (`POST /v1/companies/{id}/outcome`), med vad vart och ett leder till.
 */
const UTFALL: Record<Utfallskod, { namn: Localized; foljd: Localized }> = {
  no_answer: {
    namn: { sv: "Ej svar", en: "No answer" },
    foljd: { sv: "Sparas på leadet hos Iris. Har leadet ett telefonnummer kommer det tillbaka i återkopplingslistan om två arbetsdagar.", en: "Saved on the lead with Iris. If the lead has a phone number it returns to the follow-up list in two working days." }
  },
  call_back: {
    namn: { sv: "Återkom", en: "Call back" },
    foljd: { sv: "Sparas på leadet hos Iris. Har leadet ett telefonnummer kommer det tillbaka i återkopplingslistan den dagen.", en: "Saved on the lead with Iris. If the lead has a phone number it returns to the follow-up list on that day." }
  },
  not_interested: {
    namn: { sv: "Ej intresserad", en: "Not interested" },
    foljd: { sv: "Väntande utskick till bolagets leads stoppas.", en: "Pending sends to the company's leads are stopped." }
  },
  do_not_contact: {
    namn: { sv: "Kontakta inte", en: "Do not contact" },
    foljd: { sv: "Alla utskick stoppas och adressen spärras. Bolaget märks Kontakta inte.", en: "All sends are stopped and the address is blocked. The company is marked Do not contact." }
  },
  meeting_booked: {
    namn: { sv: "Möte bokat", en: "Meeting booked" },
    foljd: { sv: "Väntande utskick stoppas och leadet står som möte bokat.", en: "Pending sends are stopped and the lead shows as meeting booked." }
  },
  won: {
    namn: { sv: "Vunnen", en: "Won" },
    foljd: { sv: "Bolaget blir kund här, och väntande utskick stoppas.", en: "The company becomes a customer here, and pending sends are stopped." }
  }
};
type Aktivitetstyp = "call" | "meeting" | "email" | "visit" | "other";

/** Det som skrivs i CRM:et och går att ändra och ta bort härifrån: tidslinjens länk, API:ts väg och formuläret. */
const SKRIVBART: Record<string, { vag: string; skriver: Exclude<Skriver, "utfall">; vad: Localized }> = {
  note: { vag: "notes", skriver: "anteckning", vad: { sv: "Anteckningen", en: "The note" } },
  task: { vag: "tasks", skriver: "uppgift", vad: { sv: "Uppgiften", en: "The task" } },
  activity: { vag: "activities", skriver: "aktivitet", vad: { sv: "Aktiviteten", en: "The activity" } }
};

/** Dagen i läsarens tidszon, som `ÅÅÅÅ-MM-DD`. */
function lokalDag(v: string): string {
  const d = new Date(v);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Fältet som knyter en ny anteckning, uppgift eller aktivitet till posten. */
const KOPPLING: Record<Objekt, string> = { companies: "company_id", people: "person_id", deals: "deal_id" };

const AKTIVITETER: Record<Aktivitetstyp, { ikon: LucideIcon; namn: Localized }> = {
  call: { ikon: Phone, namn: { sv: "Samtal", en: "Call" } },
  meeting: { ikon: CalendarCheck, namn: { sv: "Möte", en: "Meeting" } },
  email: { ikon: Mail, namn: { sv: "Mejl", en: "Email" } },
  visit: { ikon: MapPin, namn: { sv: "Besök", en: "Visit" } },
  other: { ikon: Activity, namn: { sv: "Annat", en: "Other" } }
};

/** Samtalets utfall i leadsflödet (app/leads/samtal.py). */
const SAMTALSUTFALL: Record<string, Localized> = {
  ej_svar: { sv: "Ej svar", en: "No answer" },
  aterkom: { sv: "Återkom", en: "Call back" },
  ej_intresserad: { sv: "Ej intresserad", en: "Not interested" },
  kontakta_inte: { sv: "Kontakta inte", en: "Do not contact" },
  mote: { sv: "Möte bokat", en: "Meeting booked" },
  vunnen: { sv: "Vunnen", en: "Won" }
};

/** Leadets lägen hos Iris. Ett läge som saknas här skrivs inte ut som kod. */
export const LEADLAGE: Record<string, Localized> = {
  meeting: { sv: "Möte bokat", en: "Meeting booked" },
  won: { sv: "Vunnen", en: "Won" },
  lost: { sv: "Ej intresserad", en: "Not interested" },
  new: { sv: "Ny", en: "New" },
  ready: { sv: "Klar att skicka", en: "Ready to send" },
  recommended: { sv: "Rekommenderad", en: "Recommended" },
  researching: { sv: "Under research", en: "Being researched" },
  queued: { sv: "I kö", en: "Queued" },
  contacted: { sv: "Kontaktad", en: "Contacted" },
  replied: { sv: "Har svarat", en: "Has replied" },
  suppressed: { sv: "Kontaktas inte", en: "Not contacted" }
};

const KALLA: Record<string, Localized> = {
  api: { sv: "API", en: "API" },
  app: { sv: "Appen", en: "The app" },
  synk: { sv: "Synk", en: "Sync" },
  system: { sv: "Systemet", en: "The system" }
};

const str = (v: unknown): string | null => (typeof v === "string" && v ? v : null);
const iso = (v: string): ISODateString | undefined => (/^\d{4}-\d{2}-\d{2}$/.test(v) ? (v as ISODateString) : undefined);

/** Aktivitetens utfall: API:ts kod (`won`, `call_back`) med sitt ord, fri text som den står. */
const UTFALLSORD: Record<string, Localized> = {
  no_answer: { sv: "Ej svar", en: "No answer" },
  call_back: { sv: "Återkom", en: "Call back" },
  not_interested: { sv: "Ej intresserad", en: "Not interested" },
  do_not_contact: { sv: "Kontakta inte", en: "Do not contact" },
  meeting_booked: { sv: "Möte bokat", en: "Meeting booked" },
  won: { sv: "Vunnen", en: "Won" }
};
const utfallsord = (v: string | null, text: (l: Localized) => string) => (v && UTFALLSORD[v] ? text(UTFALLSORD[v]) : v);

/** Radens ikon, färg och mening. Loggen bär fältnamn, aldrig värden. */
function rad(p: Tidslinjepost, text: (l: Localized) => string, sprak: "sv" | "en"): { ikon: LucideIcon; ton: Ton; vad: string; under?: string } {
  const titel = p.title ?? "";
  /** "Mejl skickat: <ämnet>", eller bara etiketten när raden saknar rubrik. */
  const med = (etikett: Localized) => (titel ? `${text(etikett)}: ${titel}` : text(etikett));
  switch (p.type) {
    case "record_created":
      return { ikon: Plus, ton: "mossa", vad: text({ sv: "Skapades", en: "Created" }) };
    case "record_updated": {
      const falt = Array.isArray(p.data.fields) ? (p.data.fields as string[]) : [];
      if (!falt.length) return { ikon: Pencil, ton: "bla", vad: text({ sv: "Ändrades", en: "Changed" }) };
      const lista = uppraknat(falt.map((f) => text(faltetikett(f))), text({ sv: "och", en: "and" }));
      return { ikon: Pencil, ton: "bla", vad: text({ sv: `${lista} ändrades`, en: `${lista} changed` }) };
    }
    case "record_deleted":
      return { ikon: Trash2, ton: "mineral", vad: text({ sv: "Raderades", en: "Deleted" }) };
    case "record_restored":
      return { ikon: RotateCcw, ton: "ockra", vad: text({ sv: "Återställdes", en: "Restored" }) };
    case "record_purged":
      return { ikon: Eraser, ton: "mineral", vad: text({ sv: "Tömdes ur papperskorgen", en: "Emptied from the trash" }) };
    case "note":
      return { ikon: StickyNote, ton: "ockra", vad: titel || text({ sv: "Anteckning", en: "Note" }) };
    case "task": {
      const forfaller = str(p.data.due);
      const under = p.data.done
        ? text({ sv: "Klar", en: "Done" })
        : forfaller
          ? text({ sv: `Förfaller ${dag(forfaller, sprak)}`, en: `Due ${dag(forfaller, sprak)}` })
          : undefined;
      return { ikon: p.data.done ? ClipboardCheck : ListTodo, ton: "bla", vad: med({ sv: "Uppgift", en: "Task" }), under };
    }
    case "activity": {
      const typ = AKTIVITETER[(str(p.data.activity_type) ?? "other") as Aktivitetstyp] ?? AKTIVITETER.other;
      const minuter = typeof p.data.duration_minutes === "number" ? text({ sv: `${p.data.duration_minutes} min`, en: `${p.data.duration_minutes} min` }) : null;
      return { ikon: typ.ikon, ton: "mossa", vad: titel || text(typ.namn), under: [text(typ.namn), minuter, utfallsord(str(p.data.result), text)].filter(Boolean).join(" · ") };
    }
    case "deal_created":
    case "deal_closed": {
      const pengar = typeof p.data.amount === "number" ? belopp(p.data.amount, str(p.data.currency), sprak) : null;
      return {
        ikon: Handshake,
        ton: "sigill",
        vad: p.type === "deal_created" ? med({ sv: "Affär skapad", en: "Deal created" }) : med({ sv: "Affär avslutad", en: "Deal closed" }),
        under: [pengar, FORLUSTORSAKER[str(p.data.lost_reason_code) as Forlustorsak] ? text(FORLUSTORSAKER[str(p.data.lost_reason_code) as Forlustorsak]) : null, str(p.data.lost_reason)].filter(Boolean).join(" · ") || undefined
      };
    }
    case "lead_created":
      return { ikon: Target, ton: "ockra", vad: med({ sv: "Lead hos Iris", en: "Lead with Iris" }) };
    case "lead_status": {
      const till = LEADLAGE[str(p.data.to) ?? ""];
      return { ikon: Flag, ton: "ockra", vad: till ? text({ sv: `Leadet är nu: ${text(till)}`, en: `The lead is now: ${text(till)}` }) : text({ sv: "Leadets läge ändrades", en: "The lead's status changed" }) };
    }
    case "email_sent":
      return { ikon: Send, ton: "bla", vad: med({ sv: "Mejl skickat", en: "Email sent" }) };
    case "followup_sent":
      return { ikon: Send, ton: "bla", vad: med({ sv: "Uppföljning skickad", en: "Follow-up sent" }) };
    case "reply_received":
      return { ikon: Reply, ton: "mossa", vad: titel ? text({ sv: `Svar från ${titel}`, en: `Reply from ${titel}` }) : text({ sv: "Svar på mejlet", en: "Reply to the email" }) };
    case "conversation_stage":
      return { ikon: Flag, ton: "ockra", vad: text({ sv: "Konversationen bytte steg", en: "The conversation changed stage" }) };
    case "meeting_booked":
      return { ikon: CalendarCheck, ton: "mossa", vad: text({ sv: "Möte bokat", en: "Meeting booked" }) };
    case "handed_over":
      return { ikon: Handshake, ton: "sigill", vad: text({ sv: "Överlämnat till säljare", en: "Handed over to sales" }) };
    case "call": {
      const utfall = SAMTALSUTFALL[str(p.data.outcome) ?? ""];
      const aterkom = str(p.data.call_back_on);
      return {
        ikon: Phone,
        ton: "mossa",
        vad: utfall ? text({ sv: `Samtal: ${text(utfall)}`, en: `Call: ${text(utfall)}` }) : text({ sv: "Samtal", en: "Call" }),
        under: aterkom ? text({ sv: `Återkom ${dag(aterkom, sprak)}`, en: `Call back ${dag(aterkom, sprak)}` }) : undefined
      };
    }
    case "support_ticket":
      return { ikon: LifeBuoy, ton: "mineral", vad: med({ sv: "Supportärende", en: "Support ticket" }) };
    default:
      return { ikon: History, ton: "mineral", vad: titel || text({ sv: "Händelse", en: "Event" }) };
  }
}

/** "1 dec." eller "1 dec. 2027". */
function dag(v: string, sprak: "sv" | "en"): string {
  const d = new Date(v.length <= 10 ? `${v}T12:00:00` : v);
  const iAr = d.getFullYear() === new Date().getFullYear();
  return d.toLocaleDateString(sprak === "sv" ? "sv-SE" : "en-GB", iAr ? { day: "numeric", month: "short" } : { day: "numeric", month: "short", year: "numeric" });
}

/** Var raden bor: Iris, Supporten, eller för CRM:ets egna rader vem eller vad som gjorde dem. Okänt skrivs inte ut. */
function varifran(p: Tidslinjepost, text: (l: Localized) => string): string | null {
  if (p.origin === "iris") return "Iris";
  if (p.origin === "support") return text({ sv: "Supporten", en: "Support" });
  const kalla = str(p.data.source);
  const aktor = str(p.data.actor);
  if (kalla === "synk" && aktor?.startsWith("anslutning:")) {
    const namn = aktor.slice("anslutning:".length);
    return text({ sv: `Synk från ${SYSTEMNAMN[namn] ?? namn}`, en: `Sync from ${SYSTEMNAMN[namn] ?? namn}` });
  }
  if (kalla) return text(KALLA[kalla] ?? { sv: kalla, en: kalla });
  return str(p.data.author) ?? str(p.data.owner);
}

/**
 * Postens historik (Twentys Timeline, i panelens form): allt som hänt med
 * bolaget, personen eller affären på ett ställe, nyast först. CRM:ets egna
 * ändringar, anteckningar, uppgifter och aktiviteter, och för bolag och
 * personer det som hänt hos Iris och supporten (`GET /v1/<objekt>/{id}/timeline`).
 *
 * Överst skrivs nytt: en anteckning, en uppgift eller en aktivitet, knuten till
 * posten. Öppna uppgifter står kvar som en lista att bocka av tills de är klara.
 * Ett bolag som är ett lead hos Iris får också Utfall, som verkställs i leadsflödet.
 */
export function Tidslinje({
  objekt,
  id,
  andrad,
  harLead = false,
  bolagAndrat
}: Readonly<{
  objekt: Objekt;
  id: string;
  andrad?: string | null;
  /** Bolaget har ett lead hos Iris: då går ett utfall att sätta, och det gäller leadet också. */
  harLead?: boolean;
  /** Utfallet ändrade bolaget (kund, kontakta inte): panelen bakom får den nya posten. */
  bolagAndrat?: (b: Bolag) => void;
}>) {
  const { text, locale } = useLocale();
  // Panelen ligger under <bas>/<vy>; en affär på tidslinjen öppnas i <bas>/affarer.
  const bas = (usePathname() ?? "/crm/bolag").replace(/\/[^/]+\/?$/, "");
  const visa = useToast();
  const [poster, setPoster] = useState<Tidslinjepost[] | null>(null);
  const [fel, setFel] = useState<unknown>(null);
  const [omgang, setOmgang] = useState(0);
  const [skriver, setSkriver] = useState<Skriver | null>(null);
  // Posten som ändras i formuläret (`/v1/notes/<id>`). Tom när formuläret skriver något nytt.
  const [redigerar, setRedigerar] = useState<string | null>(null);
  const [sparar, setSparar] = useState(false);
  const [bockar, setBockar] = useState<string | null>(null);
  // Formulärens fält. Tömda när något sparats eller avbrutits.
  const [brodtext, setBrodtext] = useState("");
  const [rubrik, setRubrik] = useState("");
  const [forfaller, setForfaller] = useState("");
  const [typ, setTyp] = useState<Aktivitetstyp>("call");
  const [utfall, setUtfall] = useState<Utfallskod>("no_answer");
  const [saknas, setSaknas] = useState(false);
  const knapprad = useRef<HTMLDivElement>(null);
  const hadeFormular = useRef(false);

  // När formuläret stängs (sparat eller avbrutet) går fokus tillbaka till skrivytans knappar,
  // i stället för att försvinna med knappen som hade det.
  useEffect(() => {
    if (skriver) {
      hadeFormular.current = true;
      return;
    }
    if (!hadeFormular.current) return;
    hadeFormular.current = false;
    knapprad.current?.querySelector<HTMLElement>("button")?.focus();
  }, [skriver]);

  useEffect(() => {
    let aktuell = true;
    setFel(null);
    crmAnrop<{ data: Tidslinjepost[] }>(`/v1/${objekt}/${encodeURIComponent(id)}/timeline?limit=200`)
      .then((s) => aktuell && setPoster(s.data))
      .catch((e) => aktuell && setFel(e));
    return () => {
      aktuell = false;
    };
  }, [objekt, id, andrad, omgang]);

  // En ny post börjar med stängda formulär.
  useEffect(() => {
    setPoster(null);
    setSkriver(null);
  }, [objekt, id]);

  const stang = useCallback(() => {
    setSkriver(null);
    setRedigerar(null);
    setBrodtext("");
    setRubrik("");
    setForfaller("");
    setTyp("call");
    setUtfall("no_answer");
    setSaknas(false);
  }, []);

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    if (!skriver || sparar) return;
    if (skriver === "utfall") return void sparaUtfall();
    let vag = "/v1/notes";
    let kropp: Record<string, unknown>;
    // En ändring skickar också tömda fält (null), en ny post bara det som fyllts i.
    const tomt = redigerar ? null : undefined;
    if (skriver === "anteckning") {
      if (!brodtext.trim()) return setSaknas(true);
      kropp = { body: brodtext.trim() };
    } else if (skriver === "uppgift") {
      if (!rubrik.trim()) return setSaknas(true);
      vag = "/v1/tasks";
      // Förfallodagen är en dag: klockan nio på morgonen, lokal tid.
      kropp = { title: rubrik.trim(), due_at: forfaller ? new Date(`${forfaller}T09:00:00`).toISOString() : tomt };
    } else {
      if (!rubrik.trim()) return setSaknas(true);
      vag = "/v1/activities";
      kropp = { type: typ, subject: rubrik.trim(), body: brodtext.trim() || tomt };
    }
    setSparar(true);
    try {
      await crmAnrop<unknown>(redigerar ?? vag, {
        method: redigerar ? "PATCH" : "POST",
        body: JSON.stringify(redigerar ? kropp : { ...kropp, [KOPPLING[objekt]]: id })
      });
      // Utfallet sägs där det startades: formuläret stängs, och raden står sedan i historiken.
      const vad: Record<Exclude<Skriver, "utfall">, Localized> = {
        anteckning: { sv: "Anteckningen är sparad.", en: "The note is saved." },
        uppgift: { sv: "Uppgiften är sparad.", en: "The task is saved." },
        aktivitet: { sv: "Aktiviteten är sparad.", en: "The activity is saved." }
      };
      visa({ body: text(vad[skriver]), uniqueID: "crm-tidslinje" });
      stang();
      setOmgang((n) => n + 1);
    } catch (orsak) {
      visa({
        type: "error",
        body: text(orsak instanceof CrmFel ? orsak.text : { sv: "Det gick inte att spara. Försök igen.", en: "Could not save. Try again." }),
        uniqueID: "crm-tidslinje"
      });
    } finally {
      setSparar(false);
    }
  }

  /** Öppnar formuläret på en befintlig anteckning, uppgift eller aktivitet, med postens hela innehåll (tidslinjen bär bara ett utdrag). */
  async function andra(p: Tidslinjepost) {
    const slag = p.link ? SKRIVBART[p.link.kind] : undefined;
    if (!p.link || !slag) return;
    const vag = `/v1/${slag.vag}/${encodeURIComponent(p.link.id)}`;
    try {
      const post = await crmAnrop<Record<string, unknown>>(vag);
      setBrodtext(str(post.body) ?? "");
      setRubrik(str(post.title) ?? str(post.subject) ?? "");
      setForfaller(str(post.due_at) ? lokalDag(str(post.due_at)!) : "");
      setTyp(((str(post.type) ?? "other") in AKTIVITETER ? str(post.type) : "other") as Aktivitetstyp);
      setSaknas(false);
      setRedigerar(vag);
      setSkriver(slag.skriver);
    } catch (orsak) {
      visa({ type: "error", body: text(orsak instanceof CrmFel ? orsak.text : { sv: "Posten gick inte att öppna.", en: "The record could not be opened." }), uniqueID: "crm-tidslinje" });
    }
  }

  /** Tar bort en anteckning, uppgift eller aktivitet. Den ligger i papperskorgen i 30 dagar, och går att ta tillbaka direkt. */
  async function taBort(p: Tidslinjepost) {
    const slag = p.link ? SKRIVBART[p.link.kind] : undefined;
    if (!p.link || !slag) return;
    const vag = `/v1/${slag.vag}/${encodeURIComponent(p.link.id)}`;
    try {
      await crmAnrop<null>(vag, { method: "DELETE" });
    } catch (orsak) {
      visa({ type: "error", body: text(orsak instanceof CrmFel ? orsak.text : { sv: "Det gick inte att ta bort.", en: "Could not delete." }), uniqueID: "crm-tidslinje" });
      return;
    }
    if (redigerar === vag) stang();
    setOmgang((n) => n + 1);
    const angra = async () => {
      try {
        await crmAnrop<unknown>(`${vag}/restore`, { method: "POST" });
      } catch (orsak) {
        visa({ type: "error", body: text(orsak instanceof CrmFel ? orsak.text : { sv: "Det gick inte att ta tillbaka.", en: "Could not restore." }), uniqueID: "crm-tidslinje" });
      }
      setOmgang((n) => n + 1);
    };
    visa({
      body: text({ sv: `${text(slag.vad)} är borttagen.`, en: `${text(slag.vad)} is removed.` }),
      endContent: <Button size="sm" variant="secondary" label={text({ sv: "Ångra", en: "Undo" })} onClick={() => void angra()} />,
      autoHideDuration: 10000,
      uniqueID: "crm-tidslinje"
    });
  }

  /** Radens meny: Ändra och Ta bort, för det som skrivits i CRM:et. Mejl, samtal och ärenden bor hos Iris och supporten och ändras där. */
  const meny = (p: Tidslinjepost) =>
    p.origin === "crm" && p.link && SKRIVBART[p.link.kind] ? (
      <DropdownMenu
        placement="below"
        renderTrigger={(props) => (
          <IconButton
            {...props}
            size="sm"
            variant="ghost"
            icon={<Icon icon={MoreHorizontal} size="sm" />}
            label={text({ sv: `Åtgärder för ${p.title ?? text(SKRIVBART[p.link!.kind].vad).toLocaleLowerCase(locale)}`, en: `Actions for ${p.title ?? text(SKRIVBART[p.link!.kind].vad).toLocaleLowerCase(locale)}` })}
          />
        )}
        items={[
          { label: text({ sv: "Ändra", en: "Edit" }), icon: <Icon icon={Pencil} size="sm" />, onClick: () => void andra(p) },
          { label: text({ sv: "Ta bort", en: "Delete" }), icon: <Icon icon={Trash2} size="sm" />, onClick: () => void taBort(p) }
        ]}
      />
    ) : null;

  /** Utfallet verkställs på bolagets leads hos Iris och på posten. Svaret säger hur många leads det gällde. */
  async function sparaUtfall() {
    if (utfall === "call_back" && !forfaller) return setSaknas(true);
    setSparar(true);
    try {
      const svar = await crmAnrop<{ company: Bolag; lead_ids: string[] }>(`/v1/companies/${encodeURIComponent(id)}/outcome`, {
        method: "POST",
        body: JSON.stringify({ outcome: utfall, ...(utfall === "call_back" ? { call_back_on: forfaller } : {}), ...(brodtext.trim() ? { note: brodtext.trim() } : {}) })
      });
      const n = svar.lead_ids.length;
      const namn = text(UTFALL[utfall].namn);
      visa({
        body:
          n === 0
            ? text({ sv: `${namn} är sparat på bolaget. Bolaget har inget lead hos Iris.`, en: `${namn} is saved on the company. The company has no lead with Iris.` })
            : text({ sv: `${namn} är sparat, och gäller också ${n === 1 ? "bolagets lead" : `bolagets ${n} leads`} hos Iris.`, en: `${namn} is saved, and also applies to the company's ${n === 1 ? "lead" : `${n} leads`} with Iris.` }),
        uniqueID: "crm-tidslinje"
      });
      bolagAndrat?.(svar.company);
      stang();
      setOmgang((x) => x + 1);
    } catch (orsak) {
      visa({
        type: "error",
        body: text(orsak instanceof CrmFel ? orsak.text : { sv: "Utfallet gick inte att spara. Försök igen.", en: "The outcome could not be saved. Try again." }),
        uniqueID: "crm-tidslinje"
      });
    } finally {
      setSparar(false);
    }
  }

  async function bocka(p: Tidslinjepost, klar: boolean) {
    if (!p.link || bockar) return;
    setBockar(p.key);
    // Raden bockas direkt; API:ts svar avgör om den står kvar så.
    setPoster((forr) => forr?.map((x) => (x.key === p.key ? { ...x, data: { ...x.data, done: klar } } : x)) ?? forr);
    try {
      await crmAnrop<unknown>(`/v1/tasks/${encodeURIComponent(p.link.id)}`, { method: "PATCH", body: JSON.stringify({ status: klar ? "done" : "todo" }) });
      // En felbockning går att ta tillbaka: uppgiften står annars bara som klar i flödet, utan kryssruta.
      visa({
        body: klar
          ? text({ sv: `${p.title ?? "Uppgiften"} är klar.`, en: `${p.title ?? "The task"} is done.` })
          : text({ sv: `${p.title ?? "Uppgiften"} står under Att göra igen.`, en: `${p.title ?? "The task"} is back under To do.` }),
        endContent: klar ? <Button size="sm" variant="secondary" label={text({ sv: "Ångra", en: "Undo" })} onClick={() => void bocka(p, false)} /> : undefined,
        autoHideDuration: 8000,
        uniqueID: "crm-tidslinje"
      });
    } catch (orsak) {
      visa({
        type: "error",
        body: text(orsak instanceof CrmFel ? orsak.text : { sv: "Uppgiften gick inte att ändra.", en: "The task could not be changed." }),
        uniqueID: "crm-tidslinje"
      });
    } finally {
      setBockar(null);
      setOmgang((n) => n + 1);
    }
  }

  const attGora = useMemo(
    () =>
      (poster ?? [])
        .filter((p) => p.type === "task" && p.origin === "crm" && p.data.done !== true && p.link)
        .sort((a, b) => (str(a.data.due) ?? "9").localeCompare(str(b.data.due) ?? "9")),
    [poster]
  );
  // Öppna uppgifter står i Att göra. I flödet står de först när de är klara, så att samma rad inte visas två gånger.
  const flode = useMemo(() => (poster ?? []).filter((p) => !(p.type === "task" && p.origin === "crm" && p.data.done !== true && p.link)), [poster]);
  const idag = new Date().toISOString();

  const knapp = (slag: Skriver, ikon: LucideIcon, namn: Localized) => (
    <Button size="sm" variant="secondary" label={text(namn)} icon={<Icon icon={ikon} size="sm" />} onClick={() => setSkriver(slag)} />
  );
  const fot = (
    <div className="flex items-center justify-end gap-2">
      <Button size="sm" variant="ghost" label={text({ sv: "Avbryt", en: "Cancel" })} onClick={stang} />
      <Button size="sm" type="submit" variant="primary" label={text({ sv: "Spara", en: "Save" })} isLoading={sparar} />
    </div>
  );
  const kravs = saknas ? { type: "error" as const, message: text({ sv: "Skriv något först.", en: "Write something first." }) } : undefined;

  const skrivyta =
    skriver == null ? (
      <div ref={knapprad} className="flex flex-wrap gap-2">
        {knapp("anteckning", StickyNote, { sv: "Anteckning", en: "Note" })}
        {knapp("uppgift", ListTodo, { sv: "Uppgift", en: "Task" })}
        {knapp("aktivitet", Phone, { sv: "Aktivitet", en: "Activity" })}
        {objekt === "companies" && harLead ? knapp("utfall", Flag, { sv: "Utfall", en: "Outcome" }) : null}
      </div>
    ) : (
      <form
        onSubmit={spara}
        className="crm-skrivyta flex flex-col gap-3"
        noValidate
        // Escape avbryter skrivytan, inte hela panelen: annars stängs posten och det skrivna försvinner med den.
        onKeyDown={(e) => {
          if (e.key !== "Escape") return;
          e.preventDefault();
          e.stopPropagation();
          stang();
        }}
      >
        {skriver === "anteckning" ? (
          <TextArea
            label={redigerar ? text({ sv: "Ändra anteckningen", en: "Edit the note" }) : text({ sv: "Ny anteckning", en: "New note" })}
            placeholder={text({ sv: "Vad kom ni fram till?", en: "What did you agree on?" })}
            rows={4}
            value={brodtext}
            onChange={(v) => {
              setBrodtext(v);
              setSaknas(false);
            }}
            width="100%"
            status={kravs}
            hasAutoFocus
          />
        ) : null}
        {skriver === "uppgift" ? (
          <>
            <TextInput
              label={redigerar ? text({ sv: "Ändra uppgiften", en: "Edit the task" }) : text({ sv: "Ny uppgift", en: "New task" })}
              placeholder={text({ sv: "Skicka offerten", en: "Send the quote" })}
              value={rubrik}
              onChange={(v) => {
                setRubrik(v);
                setSaknas(false);
              }}
              width="100%"
              status={kravs}
              hasAutoFocus
            />
            <DateInput
              label={text({ sv: "Förfaller", en: "Due" })}
              value={iso(forfaller)}
              onChange={(v) => setForfaller(v ?? "")}
              weekStartsOn="mon"
              format="date"
              hasClear
              isOptional
              width="100%"
            />
          </>
        ) : null}
        {skriver === "aktivitet" ? (
          <>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-[150px_1fr]">
              <Selector
                label={text({ sv: "Slag", en: "Kind" })}
                value={typ}
                onChange={(v) => v && setTyp(v as Aktivitetstyp)}
                options={(Object.keys(AKTIVITETER) as Aktivitetstyp[]).map((a) => ({ value: a, label: text(AKTIVITETER[a].namn) }))}
                width="100%"
              />
              <TextInput
                label={text({ sv: "Vad hände?", en: "What happened?" })}
                placeholder={text({ sv: "Gick igenom offerten", en: "Went through the quote" })}
                value={rubrik}
                onChange={(v) => {
                  setRubrik(v);
                  setSaknas(false);
                }}
                width="100%"
                status={kravs}
                hasAutoFocus
              />
            </div>
            <TextArea label={text({ sv: "Anteckning", en: "Note" })} rows={3} value={brodtext} onChange={setBrodtext} width="100%" isOptional />
          </>
        ) : null}
        {skriver === "utfall" ? (
          <>
            <div className={`grid grid-cols-1 gap-3 ${utfall === "call_back" ? "sm:grid-cols-2" : ""}`}>
              <Selector
                label={text({ sv: "Utfall", en: "Outcome" })}
                value={utfall}
                onChange={(v) => {
                  if (!v) return;
                  setUtfall(v as Utfallskod);
                  setSaknas(false);
                }}
                options={(Object.keys(UTFALL) as Utfallskod[]).map((u) => ({ value: u, label: text(UTFALL[u].namn) }))}
                width="100%"
              />
              {utfall === "call_back" ? (
                <DateInput
                  label={text({ sv: "Återkom den", en: "Call back on" })}
                  value={iso(forfaller)}
                  onChange={(v) => {
                    setForfaller(v ?? "");
                    setSaknas(false);
                  }}
                  weekStartsOn="mon"
                  format="date"
                  width="100%"
                  status={saknas ? { type: "error" as const, message: text({ sv: "Välj en dag.", en: "Choose a day." }) } : undefined}
                />
              ) : null}
            </div>
            {/* Vad utfallet leder till, innan det sparas: det gäller bolagets leads hos Iris också. */}
            <Text type="supporting" color="secondary">
              {text(UTFALL[utfall].foljd)}
            </Text>
            <TextArea label={text({ sv: "Anteckning", en: "Note" })} rows={3} value={brodtext} onChange={setBrodtext} width="100%" isOptional />
          </>
        ) : null}
        {fot}
      </form>
    );

  let innehall: React.ReactNode;
  if (fel && !poster) {
    innehall = (
      <div className="flex flex-col items-start gap-3 py-2">
        <Text color="secondary">{text(fel instanceof CrmFel ? fel.text : { sv: "Historiken gick inte att hämta.", en: "The history could not be loaded." })}</Text>
        <Button size="sm" variant="secondary" label={text({ sv: "Försök igen", en: "Try again" })} onClick={() => setOmgang((n) => n + 1)} />
      </div>
    );
  } else if (!poster) {
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
  } else if (flode.length === 0 && attGora.length > 0) {
    innehall = null;
  } else if (flode.length === 0) {
    innehall = (
      <EmptyState
        isCompact
        icon={<Icon icon={History} size="lg" color="secondary" />}
        title={text({ sv: "Ingen händelse än", en: "No events yet" })}
        description={text({
          sv: "Anteckningar, uppgifter, samtal och varje ändring av posten samlas här.",
          en: "Notes, tasks, calls and every change to the record are collected here."
        })}
      />
    );
  } else {
    innehall = (
      <ol className="crm-tidslinje" aria-label={text({ sv: "Historik, nyast först", en: "History, newest first" })}>
        {flode.map((p) => {
          const r = rad(p, text, locale);
          const kalla = varifran(p, text);
          // Raden leder vidare dit saken finns: affären i CRM:et, leadet och konversationen i Leads.
          // Leadet öppnas i CRM:ets Iris-panel (steg 4.2); konversationen bor kvar i dagens Leads tills den vyn finns.
          const iLeads = p.link?.kind === "conversation";
          const affar =
            p.link?.kind === "deal"
              ? `${bas}/affarer?affar=${encodeURIComponent(p.link.id)}`
              : p.link?.kind === "lead"
                ? `${bas}/iris/leads?lead=${encodeURIComponent(p.link.id)}`
                : p.link?.kind === "conversation"
                  ? `/dashboard/leads?vy=konversationer&trad=${encodeURIComponent(p.link.id)}`
                  : null;
          return (
            <li key={p.key} className="crm-tidslinje-rad">
              <span className="crm-tidslinje-ikon">
                <Objektikon ikon={r.ikon} ton={r.ton} storlek={24} />
              </span>
              <span className="order-last -mr-1.5 -mt-1 shrink-0">{meny(p)}</span>
              <span className="flex min-w-0 flex-1 flex-col gap-0.5 pb-4">
                {affar ? (
                  <NextLink
                    href={affar}
                    className="crm-tidslinje-lank inline-flex items-center gap-1 text-[0.875rem] text-ink"
                    title={iLeads ? text({ sv: "Öppna i Leads", en: "Open in Leads" }) : undefined}
                  >
                    <span className="min-w-0">{r.vad}</span>
                    {/* Pilen säger att raden leder vidare, också på pekskärm där inget hovras. */}
                    <Icon icon={ArrowUpRight} size="xsm" color="secondary" />
                    {iLeads ? <span className="sr-only">{text({ sv: ", öppnas i Leads", en: ", opens in Leads" })}</span> : null}
                  </NextLink>
                ) : (
                  <span className="text-[0.875rem] text-ink [overflow-wrap:anywhere]">{r.vad}</span>
                )}
                {p.text ? <span className="crm-tidslinje-text">{p.text}</span> : null}
                <span className="flex flex-wrap items-center gap-x-1.5 text-[0.8125rem] text-ink-muted">
                  {r.under ? (
                    <>
                      <span>{r.under}</span>
                      <span aria-hidden>·</span>
                    </>
                  ) : null}
                  {kalla ? (
                    <>
                      <span>{kalla}</span>
                      <span aria-hidden>·</span>
                    </>
                  ) : null}
                  <Timestamp value={p.at} format="relative" />
                </span>
              </span>
            </li>
          );
        })}
      </ol>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {skrivyta}

      {attGora.length > 0 ? (
        <section aria-label={text({ sv: "Att göra", en: "To do" })} className="flex flex-col gap-1">
          <Text type="label" color="secondary" weight="medium">
            {text({ sv: "Att göra", en: "To do" })}
          </Text>
          <ul className="flex flex-col">
            {attGora.map((p) => {
              const forfallodag = str(p.data.due);
              const sen = forfallodag != null && forfallodag < idag;
              return (
                <li key={p.key} className="crm-attgora flex items-center gap-2 py-1.5">
                  <CheckboxInput
                    label={text({ sv: `Klar: ${p.title ?? "uppgiften"}`, en: `Done: ${p.title ?? "the task"}` })}
                    isLabelHidden
                    value={false}
                    onChange={(v, e) => {
                      // Raden försvinner när den bockats: fokus går till nästa uppgift, annars till skrivytans knappar.
                      const rad = e.target.closest("li");
                      const granne = (rad?.nextElementSibling ?? rad?.previousElementSibling)?.querySelector<HTMLElement>("input");
                      void bocka(p, v);
                      window.setTimeout(() => (granne?.isConnected ? granne : knapprad.current?.querySelector<HTMLElement>("button"))?.focus(), 60);
                    }}
                  />
                  <span className="min-w-0 flex-1 truncate text-[0.875rem] text-ink">{p.title}</span>
                  {forfallodag ? (
                    <span className={`inline-flex shrink-0 items-center gap-1 text-[0.8125rem] tabular-nums ${sen ? "text-danger" : "text-ink-muted"}`}>
                      {/* En passerad dag har en egen ikon: färgen ensam bär inte betydelsen. */}
                      <Icon icon={sen ? CalendarX2 : CalendarClock} size="xsm" color="inherit" />
                      <span>{dag(forfallodag, locale)}</span>
                      {sen ? <span className="sr-only">{text({ sv: ", har passerat", en: ", has passed" })}</span> : null}
                    </span>
                  ) : null}
                  <span className="-mr-1.5 shrink-0">{meny(p)}</span>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      {innehall}

      {flode.length > 0 ? (
        <Text type="supporting" color="secondary">
          {objekt === "deals"
            ? text({ sv: "Ändringar visas med vilka fält som ändrades. Värdena står i affärens uppgifter.", en: "Changes show which fields changed. The values are in the deal's details." })
            : text({
                sv: "Mejl, samtal och ärenden bor kvar hos Iris och supporten och visas här. Ändringar visas med vilka fält som ändrades.",
                en: "Emails, calls and tickets stay with Iris and support and are shown here. Changes show which fields changed."
              })}
        </Text>
      ) : null}
    </div>
  );
}
