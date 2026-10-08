"use client";

import { Check, ChevronDown, Loader2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { EmptyState, SkeletonRows, btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import type { EmailStudioData } from "@/lib/data/emails";
import { EXEMPELBOLAG } from "@/lib/demo/iris-exempel";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { offertForUtkast } from "@/lib/leads/offert";
import { LEADS_UPPDATERADE, meddelaLeadsUppdaterade } from "@/lib/leads/utkast";
import { cn } from "@/lib/utils";
import { BekraftaUtskick, forstaMening } from "@/components/leads/BekraftaUtskick";
import { useLocale, type Localized } from "@/lib/i18n";

const UTAN_AMNE: Localized = { sv: "Utan ämnesrad", en: "No subject line" };

/**
 * Iris › Granskning — utkasten Iris skrivit, i väntan på ett ja eller nej.
 *
 * Portad från `leads-webb/components/vyer/GranskningVy.tsx` till huvudappens
 * API-konventioner: samma `/api/snajp-support/leads/queue` och
 * `/api/snajp-support/leads/queue/{id}/{approve|reject}` som
 * `components/leads/LeadsControls.tsx` redan anropar, inte leads-webbs egna
 * proxy/session. Godkännande släpper utkastet till schemaläggaren —
 * backendens språk- och tidsgrindar körs en gång till vid utskick, så ett ja
 * här går aldrig förbi dem.
 *
 * Ett klick på ett poständer öppnar samma editor som Iris › Bolag mejlutkast
 * gör (EmailStudioEditor), så granskningen är mer än en rå textrad.
 */

type KöItem = {
  id: string;
  subject?: string | null;
  body?: string | null;
  prospect_email?: string | null;
  company_name?: string | null;
  created_at?: string | null;
  scheduled_at?: string | null;
  /** Backenden delar mejlet (signatur.dela_utkast): brödtexten redigeras och
   *  skrivs om av AI-knapparna; svansen (signatur + lagstadgad fot) visas men
   *  rörs aldrig, och PUT lägger tillbaka den. */
  brodtext?: string | null;
  svans?: string | null;
  contact_name?: string | null;
  lagesbeskrivning?: string | null;
  signaler?: string[] | string | null;
};

/** Tenantens mejlsignatur, normaliserad av backenden (app/leads/signatur.py).
 *  `text` är blocket som redan ligger sist i brödtexten; logotypen finns bara
 *  i mejlets HTML-del, så vyn renderar den här för att granskaren ska se det
 *  mottagaren ser. */
export type Signatur = {
  text: string;
  namn: string;
  titel?: string;
  telefon?: string;
  epost?: string;
  ort?: string;
  webb?: string;
  bolag?: string;
  logotyp_url?: string;
};

/**
 * Det som står efter brödtexten i det skickade mejlet, renderat som
 * mottagaren ser det: signaturen i samma ordning som HTML-delen
 * (signatur._signatur_html, som speglar Gmail-signaturen) med loggan mellan
 * kontaktraderna och orten, och den lagstadgade foten i liten grå text.
 * Står direkt under textrutan, som fortsättningen på mejlet — förut låg
 * signaturen som råtext i rutan och kunde skrivas om bort av AI-knapparna.
 */
export function MejlSvans({ signatur, svans }: Readonly<{ signatur: Signatur | null; svans: string }>) {
  const { text } = useLocale();
  const sig = signatur && svans.startsWith(signatur.text) ? signatur : null;
  const fot = (sig ? svans.slice(sig.text.length) : svans).trim();
  if (!sig && !fot) return null;
  const webbHref = sig?.webb ? (sig.webb.startsWith("http") ? sig.webb : `https://${sig.webb}`) : null;
  return (
    <div className="mt-2 rounded-card border border-ink/12 bg-paper px-5 py-4">
      <p className="text-[0.75rem] font-medium text-ink-subtle">
        {text({
          sv: "Läggs till sist i mejlet, så som mottagaren ser det",
          en: "Added at the end of the email, as the recipient sees it"
        })}
      </p>
      {sig ? (
        <div className="mt-3 font-[Arial,Helvetica,sans-serif] text-[0.8125rem] leading-[1.5] text-ink">
          <p className="font-bold">{sig.namn}</p>
          {sig.titel ? <p>{sig.titel}</p> : null}
          {sig.telefon ? <p>{sig.telefon}</p> : null}
          {sig.epost ? <p>{sig.epost}</p> : null}
          {sig.logotyp_url ? (
            // eslint-disable-next-line @next/next/no-img-element -- extern absolut
            // URL (samma som i mejlets HTML-del); next/image kräver domänkonfig.
            <img
              src={sig.logotyp_url}
              alt={sig.bolag ?? sig.namn}
              width={120}
              className="my-3 block h-auto w-[120px]"
            />
          ) : (
            <span className="block h-3" aria-hidden />
          )}
          {sig.ort ? <p>{sig.ort}</p> : null}
          {sig.webb && webbHref ? (
            <p>
              <a href={webbHref} target="_blank" rel="noreferrer" className="underline underline-offset-2">
                {sig.webb}
              </a>
            </p>
          ) : null}
          {sig.bolag ? <p className="mt-3">{sig.bolag}</p> : null}
        </div>
      ) : null}
      {fot ? <p className="mt-4 whitespace-pre-wrap text-[0.75rem] leading-5 text-ink-subtle">{fot}</p> : null}
    </div>
  );
}

/** Klipp förhandsvisningen vid senaste ordgräns före 220 tecken, så att
 *  texten inte huggs av mitt i ett ord. Finns inget mellanslag efter index
 *  150 klipps den vid 220 som förut. */
function klippVidOrdgrans(text: string): string {
  const stycke = text.slice(0, 220);
  const sistaMellanslag = stycke.lastIndexOf(" ");
  return sistaMellanslag > 150 ? stycke.slice(0, sistaMellanslag) : stycke;
}

/** Brödtexten — det enda granskaren och AI-knapparna arbetar på. Äldre
 *  backend utan delningen ger hela mejlet, som förut. */
function brodtextFor(post: KöItem): string {
  return post.brodtext ?? post.body ?? "";
}

/** Läget hos bolaget, som AI-knapparna (Förbättra, Personalisera …) skriver
 *  om utifrån. Utan det fick de bara bolagsnamnet och kunde inte göra mejlet
 *  mer personligt än det redan var. */
function signalFor(post: KöItem): string | null {
  const signaler = Array.isArray(post.signaler)
    ? post.signaler
    : typeof post.signaler === "string" && post.signaler.trim()
      ? [post.signaler]
      : [];
  const delar = [post.lagesbeskrivning?.trim(), signaler.length ? `Signaler: ${signaler.join("; ")}` : null];
  const ifyllda = delar.filter((d): d is string => Boolean(d));
  return ifyllda.length ? ifyllda.join(" ") : null;
}

/** `offer` är kundens erbjudande (Inställningar → Affärskontext). Utan det
 *  hittade Personalisera och Förbättra på vad avsändaren säljer — uppmätt
 *  2026-10-07 mot Vertex: "Vårt verktyg hjälper byggföretag att hitta
 *  bostadsrättsföreningar", ur ingenting. */
function tillStudioData(post: KöItem, utanAmne: string, offer: string | null): EmailStudioData {
  return {
    source: "database",
    businessContext: null,
    email: {
      id: post.id,
      subject: post.subject || utanAmne,
      body: brodtextFor(post),
      variantLength: "medium",
      variantType: "cold_outreach",
      status: "draft",
      companyId: null,
      contactId: null,
      companyName: post.company_name ?? null,
      signal: signalFor(post),
      offer,
      cta: null,
      contactName: post.contact_name ?? null
    }
  };
}

/** Demons kö: de sex fixturbolagens utkast, oavsett vilken omgång som visas i Bolag. */
function demoKo(): KöItem[] {
  return EXEMPELBOLAG.map((b) => ({
    id: b.id,
    subject: b.draft.subject,
    body: b.draft.body,
    prospect_email: `${b.contactFirstName.toLowerCase()}@${b.website}`,
    company_name: b.companyName
  }));
}

/**
 * `onAntal` säger till översikten hur många utkast som väntar (nyckeltalet).
 * Multivalet (Sebbe 2026-10-06): markera flera och godkänn eller avvisa i
 * ett svep — varje post går ändå genom samma endpoint och samma grindar som
 * ett enskilt beslut, i tur och ordning.
 *
 * `kompakt` (Leads › Översikt, Sebbe 2026-10-07): de `max` senaste utkasten
 * som enradiga poster, nyast först; ett klick öppnar utkastet och det går att
 * godkänna och skicka direkt därifrån. "Visa alla" expanderar till hela kön
 * med flervalet.
 */
export function IrisGranskning({
  demo = false,
  onAntal,
  kompakt = false,
  max = 3
}: Readonly<{ demo?: boolean; onAntal?: (antal: number) => void; kompakt?: boolean; max?: number }>) {
  const { text } = useLocale();
  const [allaVisas, setAllaVisas] = useState(false);
  const [poster, setPoster] = useState<KöItem[] | null>(null);
  const [signatur, setSignatur] = useState<Signatur | null>(null);
  const [offer, setOffer] = useState<string | null>(null);
  const [fel, setFel] = useState<Localized | null>(null);
  const [pagar, setPagar] = useState<string | null>(null);
  const [oppen, setOppen] = useState<string | null>(null);
  const [besked, setBesked] = useState<Record<string, "approve" | "reject">>({});
  const [valda, setValda] = useState<Set<string>>(new Set());
  const [svep, setSvep] = useState<"approve" | "reject" | null>(null);
  // Granskarens redigering per utkast (editorn rapporterar varje ändring,
  // egen eller AI:ns). Sparas i utkastet före godkännandet, så att det är
  // den texten som skickas.
  const [andrat, setAndrat] = useState<Record<string, { subject: string; brodtext: string }>>({});
  // Vad som hände med det senaste godkännandet: skickat, väntar på
  // sändfönstret eller stoppat av en sändspärr.
  const [utfall, setUtfall] = useState<Localized | null>(null);

  useEffect(() => {
    if (poster !== null) onAntal?.(poster.length);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [poster]);

  function vaxla(id: string) {
    setValda((nu) => {
      const nasta = new Set(nu);
      if (nasta.has(id)) nasta.delete(id);
      else nasta.add(id);
      return nasta;
    });
  }

  async function hamta() {
    setFel(null);
    if (demo) {
      setPoster(demoKo());
      return;
    }
    try {
      const response = await fetch("/api/snajp-support/leads/queue", { cache: "no-store" });
      const svar = await readJsonBody<{ items?: KöItem[]; signatur?: Signatur | null }>(response);
      if (!response.ok) {
        setFel({
          sv: `Kön kunde inte hämtas (status ${response.status}).`,
          en: `The queue could not be fetched (status ${response.status}).`
        });
        setPoster([]);
        return;
      }
      setPoster(svar?.items ?? []);
      setSignatur(svar?.signatur ?? null);
    } catch (orsak) {
      const m = felmeddelande(orsak);
      setFel({ sv: m, en: m });
      setPoster([]);
    }
  }

  useEffect(() => {
    void hamta();
    // Ett saknat erbjudande stoppar inte granskningen: knapparna körs då
    // utan bakgrund, som förut.
    if (!demo) void offertForUtkast().then(setOffer, () => setOffer(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demo]);

  // En massåtgärd i Iris-listan (Skapa om, Skicka, Arkivera …) eller ett
  // beslut i lådan ändrar kön: hämta om. Den egna signalen ignoreras — hamta
  // har redan körts.
  useEffect(() => {
    const uppdatera = (e: Event) => {
      if ((e as CustomEvent<string>).detail !== "granskning") void hamta();
    };
    window.addEventListener(LEADS_UPPDATERADE, uppdatera);
    return () => window.removeEventListener(LEADS_UPPDATERADE, uppdatera);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demo]);

  async function sparaAndring(post: KöItem): Promise<boolean> {
    const ny = andrat[post.id];
    if (!ny || (ny.subject === (post.subject ?? "") && ny.brodtext === brodtextFor(post))) return true;
    const response = await fetch(`/api/snajp-support/leads/queue/${post.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ny)
    });
    if (response.ok) return true;
    const svar = await readJsonBody<{ detail?: string }>(response);
    const orsak = typeof svar?.detail === "string" ? svar.detail : `status ${response.status}`;
    setFel({ sv: `Ändringen kunde inte sparas (${orsak}).`, en: `The edit could not be saved (${orsak}).` });
    return false;
  }

  /** Utfallet returneras så att "Godkänn N valda" kan sammanfatta alla, i
   *  stället för att varje post skriver över föregående posts besked. */
  async function avgor(id: string, handling: "approve" | "reject"): Promise<"skickat" | "vantar" | "stoppat" | "fel" | "klar"> {
    setPagar(id);
    setFel(null);
    setUtfall(null);
    if (demo) {
      // Demon avgör bara lokalt state — inget skickas, se docstringen.
      await new Promise((r) => setTimeout(r, 250));
      setBesked((f) => ({ ...f, [id]: handling }));
      setPoster((f) => (f ? f.filter((p) => p.id !== id) : f));
      setPagar(null);
      return "klar";
    }
    try {
      const post = poster?.find((p) => p.id === id);
      if (handling === "approve" && post && !(await sparaAndring(post))) return "fel";
      const response = await fetch(`/api/snajp-support/leads/queue/${id}/${handling}`, {
        method: "POST"
      });
      if (!response.ok) {
        setFel({
          sv: `Åtgärden misslyckades (status ${response.status}).`,
          en: `The action failed (status ${response.status}).`
        });
        return "fel";
      }
      let utfall: "skickat" | "vantar" | "stoppat" | "klar" = "klar";
      if (handling === "approve") {
        const svar = await readJsonBody<{ utfall?: string; besked?: string }>(response);
        const mottagare = post?.prospect_email ?? post?.company_name ?? "";
        const skal = svar?.besked?.split(": ").slice(1).join(": ");
        if (svar?.utfall === "sent") {
          setUtfall({ sv: `Skickat till ${mottagare}.`, en: `Sent to ${mottagare}.` });
          utfall = "skickat";
        } else if (svar?.utfall === "requeued") {
          setUtfall({
            sv: `Godkänt. Mejlet till ${mottagare} skickas när sändfönstret öppnar (vardagar 08–16).`,
            en: `Approved. The email to ${mottagare} goes out when the sending window opens (weekdays 08–16).`
          });
          utfall = "vantar";
        } else {
          utfall = "stoppat";
          setFel({
            sv: `Inte skickat${skal ? `: ${skal}` : "."}`,
            en: `Not sent${skal ? `: ${skal}` : "."}`
          });
        }
      }
      setAndrat((f) => {
        const { [id]: _bort, ...resten } = f;
        return resten;
      });
      await hamta();
      // Listan och nyckeltalen (godkända som väntar, skickade) hämtar om.
      meddelaLeadsUppdaterade("granskning");
      return utfall;
    } catch (orsak) {
      const m = felmeddelande(orsak);
      setFel({ sv: m, en: m });
      return "fel";
    } finally {
      setPagar(null);
    }
  }

  // Massgodkännandet bekräftas på sidan med mottagarlistan (kritik 3), inte
  // i webbläsarens confirm-ruta som inte sa till vem.
  // Kritik 4: avvisningen bekräftas på samma sätt, med namnen.
  const [bekrafta, setBekrafta] = useState<{ typ: "skicka" | "avvisa"; ids: string[] } | null>(null);

  async function avgorValda(handling: "approve" | "reject", ids: string[] = [...valda]) {
    setBekrafta(null);
    if (ids.length === 0 || svep) return;
    setSvep(handling);
    try {
      // I tur och ordning, inte parallellt: varje beslut går genom samma
      // endpoint och grindar som ett enskilt klick.
      const utfall: Awaited<ReturnType<typeof avgor>>[] = [];
      for (const id of ids) {
        // eslint-disable-next-line no-await-in-loop
        utfall.push(await avgor(id, handling));
      }
      setValda(new Set());
      if (handling === "approve" && utfall.length > 1) {
        const antal = (u: string) => utfall.filter((x) => x === u).length;
        const [skickat, vantar, ej] = [antal("skickat"), antal("vantar"), antal("stoppat") + antal("fel")];
        const delar = [
          skickat ? { sv: `${skickat} skickade`, en: `${skickat} sent` } : null,
          vantar ? { sv: `${vantar} väntar på sändfönstret`, en: `${vantar} waiting for the sending window` } : null
        ].filter((d): d is Localized => d !== null);
        const sammanfattning: Localized = {
          sv: delar.map((d) => d.sv).join(", ") || "Inget skickat",
          en: delar.map((d) => d.en).join(", ") || "Nothing sent"
        };
        if (ej) {
          setUtfall(null);
          setFel({
            sv: `${sammanfattning.sv}. ${ej} skickades inte: en sändspärr sa nej eller anropet föll. Öppna dem en i taget för skälet.`,
            en: `${sammanfattning.en}. ${ej} were not sent: a send guard said no or the request failed. Open them one at a time to see why.`
          });
        } else {
          setFel(null);
          setUtfall({ sv: `${sammanfattning.sv}.`, en: `${sammanfattning.en}.` });
        }
      }
    } finally {
      setSvep(null);
    }
  }

  // Kön kommer äldst först (scheduled_at); den kompakta rutan visar de senaste.
  const ordnade =
    kompakt && poster
      ? [...poster].sort((a, b) =>
          (b.created_at ?? b.scheduled_at ?? "").localeCompare(a.created_at ?? a.scheduled_at ?? "")
        )
      : poster;
  const begransad = kompakt && !allaVisas;
  const visade = ordnade && begransad ? ordnade.slice(0, max) : ordnade;

  return (
    <div>
      {demo && !kompakt ? (
        <p className="mb-6 text-[13px] leading-6 text-ink-subtle">{text({ sv: "Exempelutkast.", en: "Example drafts." })}</p>
      ) : null}

      {fel ? (
        <p role="alert" className="mb-5 max-w-[70ch] text-[0.875rem] text-danger">
          {text(fel)}
        </p>
      ) : null}
      {utfall ? (
        <p role="status" className="mb-5 max-w-[70ch] text-[0.875rem] text-moss">
          {text(utfall)}
        </p>
      ) : null}

      {poster && poster.length > 1 && !begransad ? (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <label className="inline-flex min-h-9 items-center gap-2 text-[0.8125rem] font-medium text-ink-muted">
            <input
              type="checkbox"
              checked={valda.size === poster.length}
              onChange={() => setValda(valda.size === poster.length ? new Set() : new Set(poster.map((p) => p.id)))}
              className="h-4 w-4 accent-ink"
            />
            {text({ sv: "Markera alla", en: "Select all" })}
          </label>
          {valda.size > 0 ? (
            <>
              <button
                type="button"
                disabled={svep !== null || pagar !== null}
                onClick={() => setBekrafta({ typ: "skicka", ids: [...valda] })}
                className={cn(btnPrimary, btnLiten)}
              >
                {svep === "approve" ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <Check className="h-4 w-4" aria-hidden />
                )}
                {text({ sv: `Godkänn och skicka ${valda.size} valda`, en: `Approve and send ${valda.size} selected` })}
              </button>
              <button
                type="button"
                disabled={svep !== null || pagar !== null}
                onClick={() => setBekrafta({ typ: "avvisa", ids: [...valda] })}
                className={cn(btnSecondary, btnLiten)}
              >
                <X className="h-4 w-4" aria-hidden />
                {text({ sv: `Avvisa ${valda.size} valda`, en: `Reject ${valda.size} selected` })}
              </button>
            </>
          ) : null}
        </div>
      ) : null}

      {bekrafta && poster && !kompakt ? (
        <div className={kompakt ? "mt-3" : "mb-4"}>
          <BekraftaUtskick
            typ={bekrafta.typ}
            poster={poster
              .filter((p) => bekrafta.ids.includes(p.id))
              .map((p) => ({
                id: p.id,
                bolag: p.company_name ?? null,
                mottagare: p.prospect_email ?? null,
                amne: p.subject ?? null,
                utdrag: forstaMening(brodtextFor(p))
              }))}
            upptagen={svep !== null}
            onBekrafta={() => void avgorValda(bekrafta.typ === "skicka" ? "approve" : "reject", bekrafta.ids)}
            onAvbryt={() => setBekrafta(null)}
          />
        </div>
      ) : null}

      {poster === null || visade === null ? (
        <SkeletonRows />
      ) : poster.length === 0 ? (
        kompakt ? (
          <p className="text-[0.875rem] text-ink-subtle">{text({ sv: "Inga utkast väntar på dig.", en: "No drafts are waiting for you." })}</p>
        ) : (
          <EmptyState title={text({ sv: "Inga utkast väntar på dig", en: "No drafts are waiting for you" })} />
        )
      ) : (
        <div className={cn("divide-y divide-ink/15", !kompakt && "border-y border-ink/15")}>
          {visade.map((post) => {
            const öppen = oppen === post.id;
            return (
              <article key={post.id} className={kompakt ? "py-3" : "py-5"}>
                <div className="flex items-start gap-3">
                {begransad ? null : (
                <label className="mt-1 inline-flex shrink-0">
                  <input
                    type="checkbox"
                    checked={valda.has(post.id)}
                    onChange={() => vaxla(post.id)}
                    aria-label={text({ sv: `Markera ${post.company_name ?? post.subject ?? "utkastet"}`, en: `Select ${post.company_name ?? post.subject ?? "the draft"}` })}
                    className="h-4 w-4 accent-ink"
                  />
                </label>
                )}
                <button
                  type="button"
                  onClick={() => setOppen(öppen ? null : post.id)}
                  aria-expanded={öppen}
                  className="focus-ring block w-full rounded-input text-left"
                >
                  <div className={cn("flex justify-between gap-x-6 gap-y-2", kompakt ? "items-start" : "flex-wrap items-baseline")}>
                    <div className="min-w-0">
                      {/* h3: kön renderas under sektionsrubriken "Utkast att
                          godkänna" i Att göra (components/leads/AttGora.tsx). */}
                      <h3 className={cn("truncate font-semibold text-ink", kompakt ? "text-[0.9375rem]" : "text-[1.0625rem]")}>
                        {post.subject || text(UTAN_AMNE)}
                      </h3>
                      <p className={cn("mt-0.5 truncate text-ink-subtle", kompakt ? "text-[0.8125rem]" : "text-[0.875rem]")}>
                        {[post.company_name, post.prospect_email].filter(Boolean).join(" · ") || text({ sv: "Okänd mottagare", en: "Unknown recipient" })}
                      </p>
                    </div>
                    {kompakt ? (
                      <ChevronDown
                        aria-hidden
                        className={cn("mt-0.5 h-4 w-4 shrink-0 text-ink-muted transition-transform", öppen && "rotate-180")}
                      />
                    ) : (
                      <span className="shrink-0 text-[0.8125rem] font-medium text-warning">
                        {öppen ? text({ sv: "Dölj utkastet", en: "Hide draft" }) : text({ sv: "Öppna utkastet", en: "Open draft" })}
                      </span>
                    )}
                  </div>
                </button>
                </div>

                {!öppen && !kompakt && brodtextFor(post) ? (
                  <p className="mt-3 max-w-[72ch] whitespace-pre-wrap text-[0.9375rem] leading-7 text-ink-muted">
                    {brodtextFor(post).length > 220 ? `${klippVidOrdgrans(brodtextFor(post))}…` : brodtextFor(post)}
                  </p>
                ) : null}

                {öppen ? (
                  <div className="mt-4">
                    <EmailStudioEditor
                      data={tillStudioData(post, text(UTAN_AMNE), offer)}
                      compact
                      onAndring={(subject, body) =>
                        setAndrat((f) => ({ ...f, [post.id]: { subject, brodtext: body } }))
                      }
                      efterText={post.svans ? <MejlSvans signatur={signatur} svans={post.svans} /> : null}
                    />
                  </div>
                ) : null}

                {kompakt && !öppen ? null : (
                <div className="mt-4 flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    disabled={pagar !== null}
                    onClick={() => void avgor(post.id, "approve")}
                    className={cn(btnPrimary, btnLiten)}
                  >
                    {pagar === post.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <Check className="h-4 w-4" aria-hidden />
                    )}
                    {text({ sv: "Godkänn och skicka", en: "Approve and send" })}
                  </button>
                  <button
                    type="button"
                    disabled={pagar !== null}
                    onClick={() => void avgor(post.id, "reject")}
                    className={cn(btnSecondary, btnLiten)}
                  >
                    <X className="h-4 w-4" aria-hidden />
                    {text({ sv: "Avvisa", en: "Reject" })}
                  </button>
                </div>
                )}
              </article>
            );
          })}
        </div>
      )}

      {kompakt && poster && poster.length > 1 ? (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          {poster.length > max ? (
            <button
              type="button"
              aria-expanded={allaVisas}
              onClick={() => {
                setAllaVisas((v) => !v);
                setValda(new Set());
              }}
              // 24 px klickyta (kritik 4: länken var 20 px).
              className="focus-ring inline-flex min-h-6 items-center text-[0.8125rem] font-medium text-ink-muted underline underline-offset-4 hover:text-ink"
            >
              {allaVisas
                ? text({ sv: "Visa färre", en: "Show fewer" })
                : text({ sv: `Visa alla ${poster.length} utkast`, en: `Show all ${poster.length} drafts` })}
            </button>
          ) : (
            <span />
          )}
          <button
            type="button"
            disabled={svep !== null || pagar !== null}
            onClick={() => setBekrafta({ typ: "skicka", ids: poster.map((p) => p.id) })}
            className={cn(btnSecondary, btnLiten)}
          >
            {svep === "approve" ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <Check className="h-4 w-4" aria-hidden />
            )}
            {text({ sv: `Godkänn och skicka alla ${poster.length}`, en: `Approve and send all ${poster.length}` })}
          </button>
        </div>
      ) : null}
      {bekrafta && poster && kompakt ? (
        <div className={kompakt ? "mt-3" : "mb-4"}>
          <BekraftaUtskick
            typ={bekrafta.typ}
            poster={poster
              .filter((p) => bekrafta.ids.includes(p.id))
              .map((p) => ({
                id: p.id,
                bolag: p.company_name ?? null,
                mottagare: p.prospect_email ?? null,
                amne: p.subject ?? null,
                utdrag: forstaMening(brodtextFor(p))
              }))}
            upptagen={svep !== null}
            onBekrafta={() => void avgorValda(bekrafta.typ === "skicka" ? "approve" : "reject", bekrafta.ids)}
            onAvbryt={() => setBekrafta(null)}
          />
        </div>
      ) : null}

      {demo && Object.keys(besked).length > 0 ? (
        <p role="status" className="mt-6 text-[13px] text-ink-subtle">
          {`${Object.entries(besked)
            .map(([id, val]) => `${EXEMPELBOLAG.find((b) => b.id === id)?.companyName ?? id}: ${val === "approve" ? text({ sv: "godkänt", en: "approved" }) : text({ sv: "avvisat", en: "rejected" })}`)
            .join(" · ")}.`}
        </p>
      ) : null}
    </div>
  );
}
