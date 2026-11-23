"use client";

import { useState } from "react";
import { BolagsSok } from "@/components/leads/BolagsSok";
import { KonversationsRuta, Konversationer, NotisKnapp } from "@/components/leads/Konversationer";
import { Uppfoljningar } from "@/components/leads/Uppfoljningar";
import { flik, flikAktiv, flikInaktiv, fliklista, rubrikSida } from "@/components/ui";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Förhandsvisning (2026-11-22): Leads › Konversationer, översiktsrutan,
 * notiserna, uppföljningarna och bolagssökningen med syntetiska bolag, ingen
 * databas. Samma mönster som /forhandsvisning/leads-skickat: anropen mot
 * /api/snajp-support/ besvaras här i webbläsaren.
 *
 * Fallet är formen på det som hände i main 2026-11-17/18 (svar, ett utkast
 * som påstår en inbjudan och ett mejl från en egen Gmail i citatet), med
 * påhittade bolag och personer.
 */

const nu = Date.now();
const iso = (timmar: number) => new Date(nu - timmar * 36e5).toISOString();

const SIGNATUR = {
  namn: "Kim Exempel",
  titel: "Sälj",
  bolag: "Exempelbolaget AB",
  text: "Kim Exempel\nSälj\n\nExempelbolaget AB"
};

const FOT = "\n\n--\nExempelbolaget AB\nVill du inte få fler mejl från oss: https://example.test/avregistrera/x";

const CITAT = `Toppen!

Hälsningar
Per

18 nov. 2026 kl. 12:56 skrev Kim Exempel <kim@exempelbolaget.test>:

> Perfekt, har skickat en inbjudan till dig!
>
> Allt gott!
> Kim
>
> 17 nov. 2026 kl. 13:00 skrev Per Påhitt <per@fiktivtelefoni.test>:
>
>> Inga problem. Inte möjligt denna vecka men måndag efter kl 10 går bra.`;

const TRAD_ETT = {
  trad: {
    id: "t1", prospect_id: "p1", company_name: "Fiktiv Telefoni AB", contact_name: "Per Påhitt", contact_role: "Grundare",
    contact_email: "per@fiktivtelefoni.test", contact_phone: "010-000 00 00", website: "fiktivtelefoni.test",
    status: "replied", steg: "svarat", svarsklass: "fraga", aterkom_datum: null
  },
  meddelanden: [
    { id: "m1", typ: "skickat", subject: "Frågorna om telefoni och drift", body: `Hej Per,\n\nFrågor om telefoni och drift tar tid från teamet. Vår supportagent svarar på dem åt er, dygnet runt.\n\nSvara på mejlet så bokar vi 20 minuter.${FOT}`, tid: iso(24 * 31), kasserad_at: null },
    { id: "m2", typ: "skickat", subject: "En tanke om konversationer", body: `Hej Per,\n\nJag undrar om mitt förra mejl hann fram. Är det något ni funderar på just nu?${FOT}`, tid: iso(24 * 10), kasserad_at: null },
    { id: "m3", typ: "svar", subject: null, body: "Tja!\n\nDrog en demobokning via kontaktformuläret men ingen har hört av sig. Kontakta mig gärna.\n\nHälsningar\nPer", tid: iso(24 * 5 + 3), kasserad_at: null },
    { id: "m4", typ: "kasserat", subject: "Re: demo", body: "Hej Per,\n\nTack för att du hörde av dig. Passar det med ett samtal i veckan?", tid: iso(24 * 5 + 2), kasserad_at: iso(24 * 5) },
    { id: "m5", typ: "svar", subject: null, body: CITAT, tid: iso(24 * 4), kasserad_at: null }
  ],
  externa: [
    { nyckel: "x1", kalla: "citat", riktning: "outbound", avsandare: "kim@exempelbolaget.test", text: "Perfekt, har skickat en inbjudan till dig!\n\nAllt gott!\nKim", tid: iso(24 * 4 + 1), tid_ur_citat: true }
  ],
  samtal: [],
  handelser: [
    { id: "h1", typ: "svar", kalla: "kod", detalj: {}, tid: iso(24 * 5 + 3), olast: false },
    { id: "h2", typ: "klassad", kalla: "kod", detalj: { klass: "fraga" }, tid: iso(24 * 5 + 3), olast: false },
    { id: "h3", typ: "utkast", kalla: "kod", detalj: {}, tid: iso(24 * 5 + 2), olast: false },
    { id: "h4", typ: "svar", kalla: "kod", detalj: {}, tid: iso(24 * 4), olast: true },
    { id: "h5", typ: "utkast_ersatt", kalla: "kod", detalj: {}, tid: iso(24 * 4), olast: false },
    { id: "h6", typ: "utkast", kalla: "kod", detalj: {}, tid: iso(24 * 4), olast: true }
  ],
  utkast: {
    message_id: "m6",
    subject: "Re: demo",
    brodtext: "Hej Per,\n\nTack, måndag efter kl 10 passar bra. Jag har skickat en inbjudan till måndag kl 10, säg till om tiden inte fungerar.",
    svans: `${SIGNATUR.text}${FOT}`,
    tid: iso(24 * 4),
    handlingar: ["Jag har skickat en inbjudan till måndag kl 10"],
    ko_status: null
  },
  generering: { pagar: false, fel: null, startad_at: null },
  forslag_mote: true,
  signatur: SIGNATUR
};

const LISTA = {
  konversationer: [
    { thread_id: "t1", prospect_id: "p1", company_name: "Fiktiv Telefoni AB", contact_name: "Per Påhitt", contact_email: "per@fiktivtelefoni.test", steg: "svarat", svarsklass: "fraga", aterkom_datum: null, aterkom_forfallet: false, senaste_svar: { utdrag: "Toppen! Hälsningar Per", tid: iso(24 * 4) }, utkast: { message_id: "m6", subject: "Re: demo", tid: iso(24 * 4), flaggat: true }, olasta: 2, antal_meddelanden: 4, att_gora: true, senast: iso(24 * 4) },
    { thread_id: "t2", prospect_id: "p2", company_name: "Låtsasbygg i Norr AB", contact_name: null, contact_email: "info@latsasbygg.test", steg: "aterkom", svarsklass: "aterkom", aterkom_datum: new Date(nu).toISOString().slice(0, 10), aterkom_forfallet: true, senaste_svar: { utdrag: "Hej, kan vi ta det nästa vecka?", tid: iso(30) }, utkast: null, olasta: 0, antal_meddelanden: 2, att_gora: true, senast: iso(30) },
    { thread_id: "t3", prospect_id: "p3", company_name: "Exempelflytt AB", contact_name: "Lena Låtsas", contact_email: "lena@exempelflytt.test", steg: "mote", svarsklass: "positivt", aterkom_datum: null, aterkom_forfallet: false, senaste_svar: { utdrag: "Låter bra, boka gärna in oss torsdag.", tid: iso(70) }, utkast: null, olasta: 0, antal_meddelanden: 3, att_gora: false, senast: iso(70) },
    { thread_id: "t4", prospect_id: "p4", company_name: "Påhittade Rör AB", contact_name: null, contact_email: "info@pahittaderor.test", steg: "ej_intresserad", svarsklass: "negativt", aterkom_datum: null, aterkom_forfallet: false, senaste_svar: { utdrag: "Tack, men vi är inte intresserade.", tid: iso(120) }, utkast: null, olasta: 0, antal_meddelanden: 2, att_gora: false, senast: iso(120) }
  ],
  antal: { att_gora: 2, alla: 4, utkast: 1, svarat: 1, mote: 1, aterkom: 1, ej_intresserad: 1, kontakta_inte: 0 },
  sammanfattning: { nya_svar: 1, utkast_vantar: 1, moten: 1, aterkom_idag: 1 }
};

const NOTISER = {
  notiser: [
    { id: "n1", typ: "utkast", tid: iso(24 * 4), last: false, thread_id: "t1", prospect_id: "p1", company_name: "Fiktiv Telefoni AB", klass: "fraga" },
    { id: "n2", typ: "svar", tid: iso(24 * 4), last: false, thread_id: "t1", prospect_id: "p1", company_name: "Fiktiv Telefoni AB", klass: null },
    { id: "n3", typ: "mote", tid: iso(70), last: true, thread_id: "t3", prospect_id: "p3", company_name: "Exempelflytt AB", klass: null }
  ],
  olasta: 2
};

const UPPF = {
  vantar: [
    { prospect_id: "p5", thread_id: "t5", company_name: "Testmåleri AB", contact_email: "info@testmaleri.test", skickade: 1, senast_skickat: iso(24 * 6), nummer: 1, av: 4, queue_item_id: "q5", ko_status: "awaiting_review", subject: "Om mitt förra mejl", body: "Hej,\n\nJag skrev förra veckan om frågorna som kommer efter kl. 17. Är det något ni vill titta på?" }
  ],
  skrivs: [{ prospect_id: "p6", thread_id: "t6", company_name: "Fiktiva Fönster AB", contact_email: null, skickade: 2, senast_skickat: iso(24 * 9), nummer: 2, av: 4 }],
  forfallna: [{ prospect_id: "p7", thread_id: "t7", company_name: "Provbygget AB", contact_email: "info@provbygget.test", skickade: 1, senast_skickat: iso(24 * 8), nummer: 1, av: 4, nasta: iso(24 * 4), avstangd: false }],
  kommande: [{ prospect_id: "p8", thread_id: "t8", company_name: "Låtsasel i Norr AB", contact_email: "kontakt@latsasel.test", skickade: 2, senast_skickat: iso(24), nummer: 2, av: 4, nasta: new Date(nu + 5 * 864e5).toISOString(), avstangd: false }],
  fel: [],
  skickade: [{ message_id: "s1", prospect_id: "p9", company_name: "Exempelrör AB", contact_email: "info@exempelror.test", subject: "Återkommer kort", body: "", skickat_at: iso(50), nummer: 1, av: 4, svarat: false }],
  automatiskt: true
};

function svar(kropp: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(kropp), { status, headers: { "Content-Type": "application/json" } }));
}

function installeraFetch() {
  if (typeof window === "undefined" || (window as { __forhandsvisning?: boolean }).__forhandsvisning) return;
  (window as { __forhandsvisning?: boolean }).__forhandsvisning = true;
  const riktig = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.includes("/api/snajp-support/")) return riktig(input, init);
    if (url.includes("/leads/notiser/antal")) return svar({ olasta: NOTISER.olasta });
    if (url.includes("/leads/notiser")) return svar(NOTISER);
    if (url.includes("/leads/uppfoljningar/skapa")) return svar({ count: 1, jobs: [], hoppade: { inget_skickat: ["x"] } }, 202);
    if (url.includes("/leads/uppfoljningar")) return svar(UPPF);
    if (url.includes("/leads/sok")) {
      return svar({
        traffar: [
          { id: "p1", company_name: "Fiktiv Telefoni AB", ort: "Göteborg", contact_name: "Per Påhitt", contact_email: "per@fiktivtelefoni.test", orgnr: "000000-0000", status: "replied", arkiverad: false, skickade: 2, senast_skickat: iso(240), thread_id: "t1", svarat: true },
          { id: "p7", company_name: "Fiktiva Fönster AB", ort: "Umeå", contact_name: null, contact_email: null, orgnr: null, status: "contacted", arkiverad: false, skickade: 1, senast_skickat: iso(200), thread_id: "t6", svarat: false }
        ]
      });
    }
    if (url.includes("/leads/konversationer/t1/utkast/skicka")) {
      return svar({ utfall: "blocked", besked: "Utskick görs i main. Det här är en förhandsvisning.", skal: null });
    }
    if (/\/leads\/konversationer\/t\d\/last/.test(url)) return svar({ lasta: 0, olasta: 2 });
    if (/\/leads\/konversationer\/t\d/.test(url) && (init?.method ?? "GET") !== "GET") return svar({ ok: true });
    if (/\/leads\/konversationer\/t\d$/.test(url.split("?")[0])) return svar(TRAD_ETT);
    if (url.includes("/leads/konversationer")) return svar(LISTA);
    return svar({});
  };
}

export default function Page() {
  installeraFetch();
  const { text } = useLocale();
  const [vy, setVy] = useState<"oversikt" | "konversationer" | "uppfoljningar">("konversationer");
  const [trad, setTrad] = useState<string | null>("t1");

  return (
    <main className="appyta mx-auto min-h-dvh max-w-6xl bg-paper px-4 py-10 text-ink sm:px-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className={rubrikSida}>Leads</h1>
        <div className="flex flex-wrap items-center gap-2">
          <BolagsSok onValj={() => undefined} />
          <NotisKnapp antal={2} onOppna={(t) => { setVy("konversationer"); setTrad(t); }} />
        </div>
      </div>
      <div className={cn(fliklista, "mt-6")} role="tablist">
        {(["oversikt", "konversationer", "uppfoljningar"] as const).map((v) => (
          <button key={v} type="button" role="tab" aria-selected={vy === v} onClick={() => setVy(v)} className={cn(flik, vy === v ? flikAktiv : flikInaktiv)}>
            {text(
              v === "oversikt"
                ? { sv: "Översikt", en: "Overview" }
                : v === "konversationer"
                  ? { sv: "Konversationer", en: "Conversations" }
                  : { sv: "Uppföljningar", en: "Follow-ups" }
            )}
          </button>
        ))}
      </div>
      <div className="mt-6">
        {vy === "oversikt" ? (
          <KonversationsRuta onOppna={(t) => { setVy("konversationer"); setTrad(t); }} />
        ) : vy === "konversationer" ? (
          <Konversationer trad={trad} onTrad={setTrad} />
        ) : (
          <Uppfoljningar />
        )}
      </div>
    </main>
  );
}
