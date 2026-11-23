"use client";

import { useCallback, useEffect, useState } from "react";
import type { Localized } from "@/lib/i18n";
import { leadsAnrop } from "@/lib/leads/suite";
import { LEADS_UPPDATERADE } from "@/lib/leads/utkast";

/**
 * Leads › Konversationer (Antons beställning 2026-11-22). Kontraktet står i
 * snajp-support/app/api/leads_konversationer.py; steget och händelserna i
 * snajp-support/app/leads/konversation.py.
 */

export type Steg = "svarat" | "mote" | "aterkom" | "ej_intresserad" | "kontakta_inte";

export const STEG: Steg[] = ["svarat", "mote", "aterkom", "ej_intresserad", "kontakta_inte"];

export const STEG_ETIKETT: Record<Steg, Localized> = {
  svarat: { sv: "Svarat", en: "Replied" },
  mote: { sv: "Möte bokat", en: "Meeting booked" },
  aterkom: { sv: "Återkom", en: "Follow up later" },
  ej_intresserad: { sv: "Ej intresserad", en: "Not interested" },
  kontakta_inte: { sv: "Kontakta inte", en: "Do not contact" }
};

/** Samma färger som Skickat och Iris-listan: blått på väg mot affär, grönt
 *  bokat, gult väntar på oss, rött nej. */
export const STEG_PRICK: Record<Steg, string> = {
  svarat: "bg-chart-blue",
  mote: "bg-moss",
  aterkom: "bg-ochre",
  ej_intresserad: "bg-danger",
  kontakta_inte: "bg-danger"
};

export type Konversationsrad = {
  thread_id: string;
  prospect_id: string;
  company_name: string | null;
  contact_name: string | null;
  contact_email: string | null;
  steg: Steg;
  svarsklass: string | null;
  aterkom_datum: string | null;
  aterkom_forfallet: boolean;
  senaste_svar: { utdrag: string; tid: string | null } | null;
  utkast: { message_id: string; subject: string | null; tid: string | null; flaggat: boolean } | null;
  olasta: number;
  antal_meddelanden: number;
  att_gora: boolean;
  senast: string | null;
};

export type Konversationslista = {
  konversationer: Konversationsrad[];
  antal: Record<string, number>;
  sammanfattning: { nya_svar: number; utkast_vantar: number; moten: number; aterkom_idag: number };
};

export type TradMeddelande = {
  id: string;
  typ: "svar" | "skickat" | "kasserat" | "utkast";
  subject: string | null;
  body: string;
  tid: string | null;
  kasserad_at: string | null;
};

export type ExterntMejl = {
  nyckel: string;
  kalla: "citat" | "manuell";
  riktning: "outbound" | "inbound";
  avsandare: string | null;
  text: string;
  amne?: string | null;
  tid: string;
  tid_ur_citat: boolean;
};

export type TradHandelse = {
  id: string;
  typ: string;
  kalla: "kod" | "manuell";
  detalj: Record<string, unknown>;
  tid: string;
  olast: boolean;
};

export type Trad = {
  trad: {
    id: string;
    prospect_id: string;
    company_name: string | null;
    contact_name: string | null;
    contact_role: string | null;
    contact_email: string | null;
    contact_phone: string | null;
    website: string | null;
    status: string | null;
    steg: Steg;
    svarsklass: string | null;
    aterkom_datum: string | null;
  };
  meddelanden: TradMeddelande[];
  externa: ExterntMejl[];
  samtal: { id: string; utfall: string; anteckning: string | null; aterkom_datum: string | null; tid: string }[];
  handelser: TradHandelse[];
  utkast: {
    message_id: string;
    subject: string;
    brodtext: string;
    svans: string;
    tid: string | null;
    handlingar: string[];
    ko_status: string | null;
  } | null;
  generering: { pagar: boolean; fel: string | null; startad_at: string | null };
  /** Datumet för att höra av sig igen har infallit (Återkom, eller återkontakten efter ett nej). */
  aterkom_forfallet?: boolean;
  forslag_mote: boolean;
  signatur?: import("@/components/leads/IrisGranskning").Signatur;
};

/** Händelseloggens rader i klartext. Typerna speglar check-villkoret i 149. */
export function handelseText(h: TradHandelse, text: (v: Localized) => string): string {
  const d = h.detalj ?? {};
  switch (h.typ) {
    case "svar":
      return d.besvarat_i_brevladan
        ? text({ sv: "Nytt svar kom in, redan besvarat från brevlådan", en: "A new reply arrived, already answered from the mailbox" })
        : d.last_i_brevladan
          ? text({ sv: "Nytt svar kom in, öppnat i brevlådan men obesvarat", en: "A new reply arrived, opened in the mailbox but unanswered" })
          : text({ sv: "Nytt svar kom in", en: "A new reply arrived" });
    case "klassad":
      return text({ sv: `Iris läste svaret som: ${klassText(String(d.klass ?? ""), text)}`, en: `Iris read the reply as: ${klassText(String(d.klass ?? ""), text)}` });
    case "utkast":
      return d.omskrivet
        ? text({ sv: "Iris skrev om svarsutkastet", en: "Iris rewrote the reply draft" })
        : d.oppnat
          ? text({
              sv: "Iris skrev ett svarsutkast: svaret låg öppnat men obesvarat i brevlådan",
              en: "Iris wrote a reply draft: the reply was opened but unanswered in the mailbox"
            })
          : text({ sv: "Iris skrev ett svarsutkast", en: "Iris wrote a reply draft" });
    case "utkast_ersatt":
      return text({ sv: "Ett väntande utkast ersattes av ett nytt", en: "A waiting draft was replaced by a new one" });
    case "utkast_kasserat":
      return String(d.orsak ?? "").startsWith("svar:")
        ? text({ sv: "Utkastet kasserades när ett nytt svar kom in", en: "The draft was discarded when a new reply arrived" })
        : String(d.orsak ?? "").startsWith("steg:")
          ? text({ sv: "Utkastet kasserades när steget byttes", en: "The draft was discarded when the stage changed" })
          : text({ sv: "Utkastet kasserades", en: "The draft was discarded" });
    case "utkast_aterstallt":
      return text({ sv: "Ett kasserat utkast återställdes", en: "A discarded draft was restored" });
    case "utkast_redigerat":
      return text({ sv: "Utkastet redigerades", en: "The draft was edited" });
    case "generering_startad":
      return text({ sv: "Skriv om startades", en: "Rewrite started" });
    case "generering_fel":
      return text({ sv: `Omskrivningen gick inte: ${String(d.fel ?? "")}`, en: `The rewrite failed: ${String(d.fel ?? "")}` });
    case "skickat":
      return d.utfall === "requeued"
        ? text({ sv: "Svaret godkändes och skickas när sändfönstret öppnar", en: "The reply was approved and sends when the window opens" })
        : text({ sv: "Svaret skickades", en: "The reply was sent" });
    case "steg":
      return text({
        sv: `Steget ändrades till ${STEG_ETIKETT[d.till as Steg] ? text(STEG_ETIKETT[d.till as Steg]) : String(d.till ?? "")}`,
        en: `Stage changed to ${STEG_ETIKETT[d.till as Steg] ? text(STEG_ETIKETT[d.till as Steg]) : String(d.till ?? "")}`
      });
    case "mote":
      return text({ sv: "Möte bokat", en: "Meeting booked" });
    case "overlamnat":
      return Array.isArray(d.eskalerat) && d.eskalerat.includes("besvarat_i_brevladan")
        ? text({
            sv: "Svaret var redan besvarat från brevlådan: Iris skrev inget utkast",
            en: "The reply was already answered from the mailbox: Iris wrote no draft"
          })
        : text({ sv: "Iris lämnade över till en människa", en: "Iris handed over to a person" });
    case "extern":
      return text({ sv: "Ett mejl utanför Snajp lades in", en: "An email sent outside Snajp was added" });
    default:
      return h.typ;
  }
}

const KLASS: Record<string, Localized> = {
  positivt: { sv: "positivt", en: "positive" },
  aterkom: { sv: "återkom senare", en: "follow up later" },
  invandning: { sv: "invändning", en: "objection" },
  fraga: { sv: "fråga", en: "question" },
  negativt: { sv: "nej", en: "no" },
  avregistrering: { sv: "vill inte bli kontaktad", en: "unsubscribe" },
  autosvar: { sv: "autosvar", en: "auto-reply" },
  avbrutet: { sv: "avbrutet", en: "stopped" }
};

export function klassText(klass: string, text: (v: Localized) => string): string {
  return KLASS[klass] ? text(KLASS[klass]) : klass;
}

export type Notis = {
  id: string;
  typ: "svar" | "utkast" | "mote" | "overlamnat";
  tid: string;
  last: boolean;
  thread_id: string | null;
  prospect_id: string;
  company_name: string | null;
  klass: string | null;
  /** Svaret låg öppnat men obesvarat i brevlådan när Iris skrev utkastet. */
  oppnat?: boolean;
};

export const NOTIS_ETIKETT: Record<Notis["typ"], Localized> = {
  svar: { sv: "Nytt svar", en: "New reply" },
  utkast: { sv: "Nytt svarsutkast", en: "New reply draft" },
  mote: { sv: "Möte bokat", en: "Meeting booked" },
  overlamnat: { sv: "Iris lämnar över", en: "Iris hands over" }
};

/** Notisens rubrik. Ett utkast på ett svar som någon öppnat utan att svara
 *  sägs rakt ut, så att det inte glöms (Anton 2026-11-23). */
export function notisEtikett(n: Notis): Localized {
  if (n.typ === "utkast" && n.oppnat) {
    return { sv: "Obesvarat i brevlådan: utkast klart", en: "Unanswered in the mailbox: draft ready" };
  }
  return NOTIS_ETIKETT[n.typ] ?? { sv: n.typ, en: n.typ };
}

/** Signalen att notiserna ändrats (lästa, nya): räknaren i railen hämtar om. */
export const NOTISER_UPPDATERADE = "snipra:notiser-uppdaterade";

export function meddelaNotiser(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(NOTISER_UPPDATERADE));
}

/** Antalet olästa notiser. Pollas varje minut när fliken syns, och direkt
 *  när något i Leads ändrats. Av i demon: där finns inga riktiga svar. */
export function useNotisantal(aktiv: boolean): number {
  const [antal, setAntal] = useState(0);
  const hamta = useCallback(async () => {
    try {
      const svar = await leadsAnrop<{ olasta?: number }>("/leads/notiser/antal");
      setAntal(svar.olasta ?? 0);
    } catch {
      // En räknare som inte går att läsa visar ingenting, inte ett fel.
    }
  }, []);
  useEffect(() => {
    if (!aktiv) return;
    void hamta();
    const uppdatera = () => void hamta();
    window.addEventListener(NOTISER_UPPDATERADE, uppdatera);
    window.addEventListener(LEADS_UPPDATERADE, uppdatera);
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") void hamta();
    }, 60_000);
    return () => {
      window.removeEventListener(NOTISER_UPPDATERADE, uppdatera);
      window.removeEventListener(LEADS_UPPDATERADE, uppdatera);
      window.clearInterval(id);
    };
  }, [aktiv, hamta]);
  return aktiv ? antal : 0;
}
