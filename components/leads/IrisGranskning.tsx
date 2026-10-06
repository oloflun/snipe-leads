"use client";

import { Check, ChevronDown, Loader2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { EmptyState, SkeletonRows, btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import type { EmailStudioData } from "@/lib/data/emails";
import { EXEMPELBOLAG } from "@/lib/demo/iris-exempel";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";
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
};

/** Tenantens mejlsignatur, normaliserad av backenden (app/leads/signatur.py).
 *  `text` är blocket som redan ligger sist i brödtexten; logotypen finns bara
 *  i mejlets HTML-del, så vyn renderar den här för att granskaren ska se det
 *  mottagaren ser. */
type Signatur = {
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

function SignaturBlock({ signatur }: Readonly<{ signatur: Signatur }>) {
  const { text } = useLocale();
  return (
    <aside className="mt-4 rounded-input border border-ink/15 bg-paper px-4 py-3">
      <p className="text-[0.8125rem] font-medium text-ink-subtle">
        {text({
          sv: "Signaturen så som mottagaren ser den",
          en: "The signature as the recipient sees it"
        })}
      </p>
      <div className="mt-3 text-[0.8125rem] leading-6 text-ink">
        <p className="font-semibold">{signatur.namn}</p>
        {signatur.titel ? <p>{signatur.titel}</p> : null}
        {signatur.telefon ? <p>{signatur.telefon}</p> : null}
        {signatur.epost ? <p>{signatur.epost}</p> : null}
        {signatur.logotyp_url ? (
          // eslint-disable-next-line @next/next/no-img-element -- extern absolut
          // URL (samma som i mejlets HTML-del); next/image kräver domänkonfig.
          <img
            src={signatur.logotyp_url}
            alt={signatur.bolag ?? signatur.namn}
            width={120}
            className="my-3 block h-auto w-[120px]"
          />
        ) : null}
        {signatur.ort ? <p>{signatur.ort}</p> : null}
        {signatur.webb ? <p>{signatur.webb}</p> : null}
        {signatur.bolag ? <p className="mt-3">{signatur.bolag}</p> : null}
      </div>
    </aside>
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

function tillStudioData(post: KöItem, utanAmne: string): EmailStudioData {
  return {
    source: "database",
    businessContext: null,
    email: {
      id: post.id,
      subject: post.subject || utanAmne,
      body: post.body ?? "",
      variantLength: "medium",
      variantType: "cold_outreach",
      status: "draft",
      companyId: null,
      contactId: null,
      companyName: post.company_name ?? null,
      signal: null,
      offer: null,
      cta: null,
      contactName: null
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
  const [fel, setFel] = useState<Localized | null>(null);
  const [pagar, setPagar] = useState<string | null>(null);
  const [oppen, setOppen] = useState<string | null>(null);
  const [besked, setBesked] = useState<Record<string, "approve" | "reject">>({});
  const [valda, setValda] = useState<Set<string>>(new Set());
  const [svep, setSvep] = useState<"approve" | "reject" | null>(null);
  // Granskarens redigering per utkast (editorn rapporterar varje ändring,
  // egen eller AI:ns). Sparas i utkastet före godkännandet, så att det är
  // den texten som skickas.
  const [andrat, setAndrat] = useState<Record<string, { subject: string; body: string }>>({});
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demo]);

  async function sparaAndring(post: KöItem): Promise<boolean> {
    const ny = andrat[post.id];
    if (!ny || (ny.subject === (post.subject ?? "") && ny.body === (post.body ?? ""))) return true;
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

  async function avgor(id: string, handling: "approve" | "reject") {
    setPagar(id);
    setFel(null);
    setUtfall(null);
    if (demo) {
      // Demon avgör bara lokalt state — inget skickas, se docstringen.
      await new Promise((r) => setTimeout(r, 250));
      setBesked((f) => ({ ...f, [id]: handling }));
      setPoster((f) => (f ? f.filter((p) => p.id !== id) : f));
      setPagar(null);
      return;
    }
    try {
      const post = poster?.find((p) => p.id === id);
      if (handling === "approve" && post && !(await sparaAndring(post))) return;
      const response = await fetch(`/api/snajp-support/leads/queue/${id}/${handling}`, {
        method: "POST"
      });
      if (!response.ok) {
        setFel({
          sv: `Åtgärden misslyckades (status ${response.status}).`,
          en: `The action failed (status ${response.status}).`
        });
        return;
      }
      if (handling === "approve") {
        const svar = await readJsonBody<{ utfall?: string; besked?: string }>(response);
        const mottagare = post?.prospect_email ?? post?.company_name ?? "";
        const skal = svar?.besked?.split(": ").slice(1).join(": ");
        if (svar?.utfall === "sent") {
          setUtfall({ sv: `Skickat till ${mottagare}.`, en: `Sent to ${mottagare}.` });
        } else if (svar?.utfall === "requeued") {
          setUtfall({
            sv: `Godkänt. Mejlet till ${mottagare} skickas när sändfönstret öppnar (vardagar 08–16).`,
            en: `Approved. The email to ${mottagare} goes out when the sending window opens (weekdays 08–16).`
          });
        } else {
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
    } catch (orsak) {
      const m = felmeddelande(orsak);
      setFel({ sv: m, en: m });
    } finally {
      setPagar(null);
    }
  }

  async function avgorValda(handling: "approve" | "reject") {
    if (valda.size === 0 || svep) return;
    if (
      handling === "reject" &&
      !window.confirm(text({ sv: `Avvisa ${valda.size} utkast?`, en: `Reject ${valda.size} drafts?` }))
    )
      return;
    setSvep(handling);
    try {
      // I tur och ordning, inte parallellt: varje beslut går genom samma
      // endpoint och grindar som ett enskilt klick.
      for (const id of [...valda]) {
        // eslint-disable-next-line no-await-in-loop
        await avgor(id, handling);
      }
      setValda(new Set());
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
                onClick={() => void avgorValda("approve")}
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
                onClick={() => void avgorValda("reject")}
                className={cn(btnSecondary, btnLiten)}
              >
                <X className="h-4 w-4" aria-hidden />
                {text({ sv: `Avvisa ${valda.size} valda`, en: `Reject ${valda.size} selected` })}
              </button>
            </>
          ) : null}
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

                {!öppen && !kompakt && post.body ? (
                  <p className="mt-3 max-w-[72ch] whitespace-pre-wrap text-[0.9375rem] leading-7 text-ink-muted">
                    {post.body.length > 220 ? `${klippVidOrdgrans(post.body)}…` : post.body}
                  </p>
                ) : null}

                {öppen ? (
                  <div className="mt-4">
                    <EmailStudioEditor
                      data={tillStudioData(post, text(UTAN_AMNE))}
                      compact
                      onAndring={(subject, body) => setAndrat((f) => ({ ...f, [post.id]: { subject, body } }))}
                    />
                    {signatur ? <SignaturBlock signatur={signatur} /> : null}
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

      {kompakt && poster && poster.length > max ? (
        <button
          type="button"
          aria-expanded={allaVisas}
          onClick={() => {
            setAllaVisas((v) => !v);
            setValda(new Set());
          }}
          className="focus-ring mt-3 text-[0.8125rem] font-medium text-ink-muted underline underline-offset-4 hover:text-ink"
        >
          {allaVisas
            ? text({ sv: "Visa färre", en: "Show fewer" })
            : text({ sv: `Visa alla ${poster.length} utkast`, en: `Show all ${poster.length} drafts` })}
        </button>
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
