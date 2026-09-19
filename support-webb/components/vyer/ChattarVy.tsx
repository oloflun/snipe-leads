"use client";

import { CornerUpLeft, Loader2, Send } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, EmptyState, SkeletonRows, btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import { BAS, type Chatt, type Chattdetalj, type ChattRad } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Chattar: samtal agenten lämnat över till en människa (bd snipe-1fl).
 *
 * Hela samtalet visas — alla kundens meddelanden, inte bara det sista — och
 * svaret du skriver här hamnar i kundens EGET chattfönster. Kunden behöver
 * inte byta kanal eller börja om. "Lämna tillbaka" ger samtalet till agenten
 * igen. Listan och det valda samtalet uppdateras av sig själva medan vyn är
 * öppen, så ett nytt kundmeddelande syns utan att du laddar om.
 */

const UPPDATERA_MS = 10000;

/** Kanaler där kunden INTE sitter i webbchatten, så svaret måste skickas dit
 *  (bd snipe-36u). Webbchatten hämtar själv och får ingen etikett. */
const KANALNAMN: Record<string, string> = {
  whatsapp: "WhatsApp",
  messenger: "Messenger",
  slack: "Slack",
  teams: "Teams",
  email: "E-post"
};

/** Svaret från POST /api/chattar/{kund}/svar: levererat är null för
 *  webbchatten, sant när kanalen tog emot svaret, falskt när den inte gjorde det. */
type Svarsutfall = { levererat?: boolean | null; leveransfel?: string | null };

const AVSANDARE: Record<ChattRad["author"], string> = {
  customer: "Kunden",
  agent: "Agenten",
  human: "Medarbetare"
};

function tid(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleString("sv-SE", {
        timeZone: "Europe/Stockholm",
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit"
      });
}

function Chattar() {
  const valtFranUrl = useSearchParams().get("kund");
  const [chattar, setChattar] = useState<Chatt[] | null>(null);
  const [valtId, setValtId] = useState<string | null>(valtFranUrl);
  const [detalj, setDetalj] = useState<Chattdetalj | null>(null);
  const [svar, setSvar] = useState("");
  const [fel, setFel] = useState<string | null>(null);
  const [pagar, setPagar] = useState<"svar" | "aterlamna" | null>(null);
  const [detaljFel, setDetaljFel] = useState<string | null>(null);
  // Utfallet av senaste svaret i en extern kanal. Ett svar kan vara sparat
  // men ändå inte ha nått kunden (WhatsApps 24-timmarsfönster, en borttagen
  // kanal), och det ska medarbetaren få veta, inte tro att det gick fram.
  const [leverans, setLeverans] = useState<{ ok: boolean; text: string } | null>(null);
  const utskriftRef = useRef<HTMLDivElement>(null);
  // Det samtal som är valt JUST NU. Ett svar som kommer tillbaka för ett
  // samtal man redan klickat vidare från ska inte skriva över det nya.
  const valtRef = useRef<string | null>(valtFranUrl);

  const hamtaLista = useCallback(async () => {
    try {
      const data = await fetch(`${BAS}/chattar`).then((s) => readJson<{ chattar?: Chatt[] }>(s));
      setChattar(data?.chattar ?? []);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
      setChattar((nu) => nu ?? []);
    }
  }, []);

  const hamtaDetalj = useCallback(async (kund: string) => {
    try {
      const data = await fetch(`${BAS}/chattar/${kund}`).then((s) => readJson<Chattdetalj>(s));
      if (valtRef.current !== kund) return;
      setDetalj(data);
      setDetaljFel(null);
    } catch (orsak) {
      if (valtRef.current !== kund) return;
      setDetaljFel(felmeddelande(orsak));
    }
  }, []);

  useEffect(() => {
    void hamtaLista();
    const timer = setInterval(() => void hamtaLista(), UPPDATERA_MS);
    return () => clearInterval(timer);
  }, [hamtaLista]);

  useEffect(() => {
    if (!valtId) return;
    void hamtaDetalj(valtId);
    const timer = setInterval(() => void hamtaDetalj(valtId), UPPDATERA_MS);
    return () => clearInterval(timer);
  }, [valtId, hamtaDetalj]);

  const antalRader = detalj?.meddelanden.length ?? 0;
  useEffect(() => {
    utskriftRef.current?.scrollTo({ top: utskriftRef.current.scrollHeight });
  }, [antalRader]);

  function valj(kund: string) {
    valtRef.current = kund;
    setFel(null);
    setDetaljFel(null);
    setSvar("");
    setDetalj(null);
    setLeverans(null);
    setValtId(kund);
  }

  async function skicka() {
    if (!valtId || !svar.trim()) return;
    setPagar("svar");
    setFel(null);
    setLeverans(null);
    try {
      const utfall = await readJson<Svarsutfall>(
        await fetch(`${BAS}/chattar/${valtId}/svar`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: svar.trim() })
        })
      );
      const kanal = KANALNAMN[valt?.channel ?? ""] ?? "kundens kanal";
      if (utfall?.levererat === true) {
        setLeverans({ ok: true, text: `Skickat till kunden i ${kanal}.` });
      } else if (utfall?.levererat === false) {
        setLeverans({
          ok: false,
          text: `Svaret är sparat men nådde inte kunden i ${kanal}. ${utfall.leveransfel ?? ""}`.trim()
        });
      }
      setSvar("");
      await Promise.all([hamtaDetalj(valtId), hamtaLista()]);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setPagar(null);
    }
  }

  async function aterlamna() {
    if (!valtId) return;
    setPagar("aterlamna");
    setFel(null);
    try {
      await readJson(await fetch(`${BAS}/chattar/${valtId}/aterlamna`, { method: "POST" }));
      valtRef.current = null;
      setValtId(null);
      setDetalj(null);
      await hamtaLista();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setPagar(null);
    }
  }

  const valt = chattar?.find((c) => c.customer_id === valtId) ?? detalj?.samtal ?? null;

  return (
    <div className="space-y-8">
      <PageHeader
        rubrik="Chattar"
        beskrivning="Samtal agenten har lämnat över till en människa. Du ser hela samtalet, och ditt svar hamnar i kundens eget chattfönster — kunden behöver inte börja om."
      />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      {chattar === null ? (
        <SkeletonRows />
      ) : chattar.length === 0 && !valtId ? (
        <EmptyState
          title="Inga överlämnade chattar"
          body="När agenten lämnar över ett samtal — kunden ber om en människa, frågan ligger utanför det agenten vet, eller ärendet är känsligt — hamnar det här."
        />
      ) : (
        <div className="grid gap-10 lg:grid-cols-12">
          <section className="lg:col-span-5" aria-label="Överlämnade chattar">
            <div className="divide-y divide-ink/12 border-y border-ink/15">
              {chattar.map((rad) => (
                <button
                  key={rad.customer_id}
                  type="button"
                  onClick={() => valj(rad.customer_id)}
                  aria-current={valtId === rad.customer_id ? "true" : undefined}
                  className={cn(
                    "focus-ring block w-full rounded-[4px] py-3 text-left transition-colors hover:bg-paper2/50",
                    valtId === rad.customer_id && "bg-paper2/60"
                  )}
                >
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="min-w-0 truncate text-[0.9375rem] font-medium">
                      {rad.subject || "Utan ämne"}
                    </span>
                    <span className="flex shrink-0 gap-1.5">
                      {rad.is_test ? <Badge>Test</Badge> : null}
                      {KANALNAMN[rad.channel ?? ""] ? <Badge>{KANALNAMN[rad.channel ?? ""]}</Badge> : null}
                      <Badge tone={rad.aktiv ? "warn" : "neutral"}>
                        {rad.aktiv ? "Väntar" : "Vilande"}
                      </Badge>
                    </span>
                  </span>
                  <span className="mt-0.5 block truncate text-[0.875rem] text-ink/55">
                    {rad.customer_name || "Webbesökare"}
                    {rad.orsak_text ? ` · ${rad.orsak_text}` : ""}
                  </span>
                  <span className="mt-0.5 block text-[0.8125rem] num text-ink/45">
                    {tid(rad.updated_at)}
                  </span>
                </button>
              ))}
            </div>
          </section>

          <section className="lg:col-span-7" aria-label="Valt samtal">
            {!valtId ? (
              <p className="border-y border-ink/15 py-8 text-[0.9375rem] text-ink/55">
                Välj ett samtal i listan så visas hela samtalet här.
              </p>
            ) : !detalj && detaljFel ? (
              <div className="border-y border-ink/15 py-6">
                <p role="alert" className="max-w-[62ch] text-[0.9375rem] text-danger">
                  Samtalet gick inte att hämta. {detaljFel}
                </p>
                <button
                  type="button"
                  onClick={() => void hamtaDetalj(valtId)}
                  className={cn(btnSecondary, btnLiten, "mt-3")}
                >
                  Försök igen
                </button>
              </div>
            ) : !detalj ? (
              <SkeletonRows />
            ) : (
              <article className="border-y border-ink/15 py-5">
                <h2 className="text-[1.0625rem] font-semibold text-ink">
                  {valt?.subject || "Utan ämne"}
                </h2>
                {detalj.samtal.orsak_text ? (
                  <p className="mt-0.5 text-[0.875rem] text-ink/55">
                    Överlämnat: {detalj.samtal.orsak_text}
                  </p>
                ) : null}
                {KANALNAMN[valt?.channel ?? ""] ? (
                  <p className="mt-0.5 text-[0.875rem] text-ink/55">
                    Kunden skriver i {KANALNAMN[valt?.channel ?? ""]}. Ditt svar skickas dit.
                  </p>
                ) : null}
                {detalj.samtal.aktiv === false && detalj.samtal.lage === "overlamnad" ? (
                  <p className="mt-2 max-w-[62ch] text-[0.8125rem] text-ink/50">
                    Samtalet har legat stilla ett dygn, så agenten svarar kunden igen. Ditt
                    svar tar tillbaka det.
                  </p>
                ) : null}

                <div
                  ref={utskriftRef}
                  aria-live="polite"
                  aria-label="Samtalet"
                  className="mt-4 max-h-[420px] space-y-3 overflow-y-auto border-l-[1px] border-ink/15 pl-4"
                >
                  {detalj.meddelanden.map((rad) => (
                    <div key={rad.id}>
                      <p className="text-[0.75rem] font-semibold text-ink/55">
                        {AVSANDARE[rad.author]}
                        <span className="ml-2 font-normal num text-ink/40">{tid(rad.created_at)}</span>
                      </p>
                      <p
                        dir="auto"
                        className={cn(
                          "mt-0.5 max-w-[72ch] whitespace-pre-wrap break-words text-[0.9375rem] leading-7",
                          rad.author === "customer" ? "text-ink" : "text-ink/70"
                        )}
                      >
                        {rad.content}
                      </p>
                    </div>
                  ))}
                </div>

                <label htmlFor="medarbetarsvar" className="mt-6 block font-display text-[1.125rem]">
                  Ditt svar
                </label>
                <textarea
                  id="medarbetarsvar"
                  value={svar}
                  onChange={(e) => setSvar(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                      e.preventDefault();
                      void skicka();
                    }
                  }}
                  aria-describedby="medarbetarsvar-tips"
                  rows={4}
                  maxLength={4000}
                  placeholder={
                    KANALNAMN[valt?.channel ?? ""]
                      ? `Svaret skickas till kunden i ${KANALNAMN[valt?.channel ?? ""]}.`
                      : "Svaret visas i kundens chattfönster."
                  }
                  className="focus-ring mt-2 w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[16px] leading-6"
                />
                <p id="medarbetarsvar-tips" className="mt-1 text-[0.8125rem] text-ink/45">
                  Ctrl+Enter skickar.
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    disabled={!svar.trim() || pagar !== null}
                    onClick={() => void skicka()}
                    className={cn(btnPrimary, btnLiten)}
                  >
                    {pagar === "svar" ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <Send className="h-4 w-4" aria-hidden />
                    )}
                    Skicka svar
                  </button>
                  <button
                    type="button"
                    disabled={pagar !== null}
                    onClick={() => void aterlamna()}
                    title="Agenten svarar kunden igen från nästa meddelande."
                    className={cn(btnSecondary, btnLiten)}
                  >
                    {pagar === "aterlamna" ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <CornerUpLeft className="h-4 w-4" aria-hidden />
                    )}
                    Lämna tillbaka till agenten
                  </button>
                </div>
                {leverans ? (
                  <p
                    role={leverans.ok ? "status" : "alert"}
                    className={cn("mt-3 max-w-[62ch] text-[0.875rem]", leverans.ok ? "text-moss" : "text-danger")}
                  >
                    {leverans.text}
                  </p>
                ) : null}
              </article>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

export function ChattarVy() {
  // useSearchParams kräver en Suspense-gräns vid statisk rendering.
  return (
    <Suspense fallback={<SkeletonRows />}>
      <Chattar />
    </Suspense>
  );
}
