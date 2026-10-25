"use client";

/* design · Operate-yta i det låsta systemet (DESIGN.md, Tier 0): samma fält,
   knappar, hairline-lista och bekräftelse som IrisErbjudanden och
   KorningensUtkast, ingen ny riktning. */

import { Check, Loader2, Megaphone } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { BekraftaUtskick, forstaMening } from "@/components/leads/BekraftaUtskick";
import { btnLiten, btnPrimary, btnSecondary, etikett, meta, rubrikPanel } from "@/components/ui";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { leadsAnrop } from "@/lib/leads/suite";
import { cn } from "@/lib/utils";

/**
 * Leads › Erbjudanden › Kampanjer (Antons beställning 2026-10-25): massutskick
 * till en befintlig kund- eller leadslista med lite anpassning, "Hej Namn,"
 * och sedan kampanjtexten. Utkasten hamnar i granskningen och skickas med
 * "Godkänn och skicka alla" genom samma sändspärrar, fot och avregistrering
 * som allt annat. Förloppet och utfallet läses ur databasen och står kvar
 * efter en omladdning. Backend: snajp-support/app/api/leads_kampanjer.py.
 */

type Utfall = { koade: number; vantar: number; skickade: number; svar: number; stoppade: number };
type Kampanj = {
  id: string;
  namn: string;
  amne: string;
  text: string;
  kalla: { namn: string };
  skapad: string;
  status: "pagar" | "klar" | "fel" | "avbruten";
  totalt: number;
  hoppade?: Record<string, number>;
  fel?: string;
  utfall: Utfall | null;
};
type Svar = {
  kampanjer: Kampanj[];
  listor: { id: string; titel: string | null; kalla: string | null; antal: number }[];
  korningar: { job_id: string; datum: string; levererade: number | null }[];
};
type Post = { queue_item_id: string | null; status: string | null; company_name: string | null; email: string | null };

const POLL_MS = 4000;

const T = {
  rubrik: { sv: "Kampanjer", en: "Campaigns" },
  om: {
    sv: "Ett utskick till en lista ni redan har. Varje mottagare får \"Hej\" med sitt förnamn när det är känt, och sedan er text. Utkasten hamnar i granskningen, och inget skickas förrän ni godkänt dem.",
    en: "A send-out to a list you already have. Each recipient gets \"Hi\" with their first name when it is known, followed by your text. The drafts go to review, and nothing is sent until you approve them."
  },
  namn: { sv: "Kampanjens namn", en: "Campaign name" },
  amne: { sv: "Ämnesrad", en: "Subject line" },
  text: { sv: "Text efter hälsningen", en: "Text after the greeting" },
  textHint: {
    sv: "Signaturen och avregistreringsraden läggs på automatiskt.",
    en: "The signature and the unsubscribe line are added automatically."
  },
  kalla: { sv: "Mottagare", en: "Recipients" },
  valjKalla: { sv: "Välj en lista eller en körning", en: "Choose a list or a run" },
  listor: { sv: "Listor", en: "Lists" },
  korningar: { sv: "Körningars leads", en: "Leads from runs" },
  bolag: { sv: "bolag", en: "companies" },
  skapa: { sv: "Skapa kampanj", en: "Create campaign" },
  skapar: { sv: "Skapar…", en: "Creating…" },
  kravFalt: { sv: "Fyll i namn, ämnesrad, text och mottagare.", en: "Fill in name, subject line, text and recipients." },
  tomt: { sv: "Inga kampanjer än.", en: "No campaigns yet." },
  pagar: { sv: "Köar utkast", en: "Queuing drafts" },
  klar: { sv: "Klar", en: "Done" },
  fel: { sv: "Avbröts av ett fel", en: "Stopped by an error" },
  avbruten: { sv: "Avbröts innan alla köats", en: "Stopped before all were queued" },
  koade: { sv: "Köade", en: "Queued" },
  vantar: { sv: "Väntar på dig", en: "Waiting for you" },
  skickade: { sv: "Skickade", en: "Sent" },
  svar: { sv: "Svar", en: "Replies" },
  stoppade: { sv: "Stoppade", en: "Stopped" },
  hoppade: { sv: "Hoppades över", en: "Skipped" },
  skicka: (n: number): Localized => ({ sv: `Godkänn och skicka ${n}`, en: `Approve and send ${n}` }),
  skickat: (n: number, v: number): Localized => ({
    sv: `${n} skickade${v ? `, ${v} skickas när sändfönstret öppnar (vardagar 08–16)` : ""}.`,
    en: `${n} sent${v ? `, ${v} go out when the sending window opens (weekdays 08–16)` : ""}.`
  }),
  hamtaFel: { sv: "Kampanjerna kunde inte hämtas:", en: "The campaigns could not be loaded:" },
  forsokIgen: { sv: "Försök igen", en: "Try again" }
} as const;

const falt = "focus-ring w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[16px] leading-6";

export function Kampanjer() {
  const { text } = useLocale();
  const [data, setData] = useState<Svar | null>(null);
  const [laddfel, setLaddfel] = useState<string | null>(null);
  const [form, setForm] = useState({ namn: "", amne: "", text: "", kalla: "" });
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const [besked, setBesked] = useState("");
  const [bekrafta, setBekrafta] = useState<{ id: string; poster: Post[] } | null>(null);
  const [skickar, setSkickar] = useState(false);
  const poll = useRef<ReturnType<typeof setTimeout> | null>(null);

  const hamta = useCallback(async () => {
    try {
      const svar = await leadsAnrop<Svar>("/leads/kampanjer");
      setData(svar);
      setLaddfel(null);
      if (poll.current) clearTimeout(poll.current);
      if (svar.kampanjer.some((k) => k.status === "pagar")) poll.current = setTimeout(() => void hamta(), POLL_MS);
    } catch (orsak) {
      setLaddfel(felmeddelande(orsak));
    }
  }, []);

  useEffect(() => {
    void hamta();
    return () => {
      if (poll.current) clearTimeout(poll.current);
    };
  }, [hamta]);

  async function skapa() {
    if (busy) return;
    if (!form.namn.trim() || !form.amne.trim() || !form.text.trim() || !form.kalla) {
      setFel(text(T.kravFalt));
      return;
    }
    const [typ, id] = form.kalla.split(":");
    setBusy(true);
    setFel(null);
    setBesked("");
    try {
      await leadsAnrop("/leads/kampanjer", {
        method: "POST",
        body: JSON.stringify({
          namn: form.namn.trim(),
          amne: form.amne.trim(),
          text: form.text.trim(),
          ...(typ === "lista" ? { list_id: id } : { job_id: id })
        })
      });
      setForm({ namn: "", amne: "", text: "", kalla: "" });
      await hamta();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setBusy(false);
    }
  }

  async function oppnaSkicka(id: string) {
    setFel(null);
    setBesked("");
    try {
      const svar = await leadsAnrop<{ poster: Post[] }>(`/leads/kampanjer/${encodeURIComponent(id)}`);
      setBekrafta({ id, poster: svar.poster.filter((p) => p.status === "awaiting_review") });
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    }
  }

  async function skicka() {
    if (!bekrafta) return;
    setSkickar(true);
    try {
      const svar = await leadsAnrop<{
        skickade: number;
        vantar_pa_fonstret: number;
        stoppade: { company_name: string | null; skal: string | null }[];
      }>(`/leads/kampanjer/${encodeURIComponent(bekrafta.id)}/skicka`, { method: "POST" });
      setBesked(text(T.skickat(svar.skickade, svar.vantar_pa_fonstret)));
      if (svar.stoppade.length) {
        setFel(svar.stoppade.map((s) => `${s.company_name ?? "?"}${s.skal ? `: ${s.skal}` : ""}`).join("; "));
      }
      setBekrafta(null);
      await hamta();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setSkickar(false);
    }
  }

  if (laddfel) {
    return (
      <div role="alert" className="grid gap-3">
        <p className="max-w-[62ch] text-[0.9375rem] leading-6 text-danger">
          {text(T.hamtaFel)} {laddfel}
        </p>
        <button type="button" onClick={() => void hamta()} className={cn(btnSecondary, "justify-self-start")}>
          {text(T.forsokIgen)}
        </button>
      </div>
    );
  }
  if (data === null) {
    return <div className="h-48 animate-pulse rounded-card bg-ink/[0.055]" aria-busy="true" />;
  }

  return (
    <section aria-labelledby="kampanjer-rubrik" className="grid gap-6">
      <div>
        <h2 id="kampanjer-rubrik" className={rubrikPanel}>
          {text(T.rubrik)}
        </h2>
        <p className="mt-1 max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">{text(T.om)}</p>
      </div>

      <form
        className="grid gap-3 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          void skapa();
        }}
      >
        <label className="grid gap-1">
          <span className={etikett}>{text(T.namn)}</span>
          <input value={form.namn} maxLength={80} onChange={(e) => setForm({ ...form, namn: e.target.value })} className={falt} />
        </label>
        <label className="grid gap-1">
          <span className={etikett}>{text(T.kalla)}</span>
          <select value={form.kalla} onChange={(e) => setForm({ ...form, kalla: e.target.value })} className={falt}>
            <option value="">{text(T.valjKalla)}</option>
            {data.listor.length ? (
              <optgroup label={text(T.listor)}>
                {data.listor.map((l) => (
                  <option key={l.id} value={`lista:${l.id}`}>
                    {l.titel ?? l.id} ({l.antal} {text(T.bolag)})
                  </option>
                ))}
              </optgroup>
            ) : null}
            {data.korningar.length ? (
              <optgroup label={text(T.korningar)}>
                {data.korningar.map((k) => (
                  <option key={k.job_id} value={`korning:${k.job_id}`}>
                    {k.datum}
                    {k.levererade != null ? ` (${k.levererade})` : ""}
                  </option>
                ))}
              </optgroup>
            ) : null}
          </select>
        </label>
        <label className="grid gap-1 sm:col-span-2">
          <span className={etikett}>{text(T.amne)}</span>
          <input value={form.amne} maxLength={120} onChange={(e) => setForm({ ...form, amne: e.target.value })} className={falt} />
        </label>
        <label className="grid gap-1 sm:col-span-2">
          <span className={etikett}>{text(T.text)}</span>
          <textarea
            value={form.text}
            rows={6}
            maxLength={3000}
            onChange={(e) => setForm({ ...form, text: e.target.value })}
            className={cn(falt, "resize-y")}
          />
          <span className={meta}>{text(T.textHint)}</span>
        </label>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-3 sm:col-span-2">
          <button type="submit" aria-disabled={busy || undefined} className={cn(btnPrimary, "aria-disabled:opacity-60")}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Megaphone className="h-4 w-4" aria-hidden />}
            {busy ? text(T.skapar) : text(T.skapa)}
          </button>
          <span aria-live="polite" className="text-[0.9375rem] text-ink-muted">
            {besked}
          </span>
          {fel ? (
            <p role="alert" className="max-w-[62ch] break-words text-[0.9375rem] text-danger">
              {fel}
            </p>
          ) : null}
        </div>
      </form>

      {bekrafta ? (
        <BekraftaUtskick
          poster={bekrafta.poster.map((p) => ({
            id: p.queue_item_id ?? p.email ?? "",
            bolag: p.company_name,
            mottagare: p.email,
            amne: data.kampanjer.find((k) => k.id === bekrafta.id)?.amne ?? null,
            utdrag: forstaMening(data.kampanjer.find((k) => k.id === bekrafta.id)?.text)
          }))}
          upptagen={skickar}
          onBekrafta={() => void skicka()}
          onAvbryt={() => setBekrafta(null)}
        />
      ) : null}

      {data.kampanjer.length === 0 ? (
        <p className={meta}>{text(T.tomt)}</p>
      ) : (
        <ol className="divide-y divide-ink/12 border-y border-ink/15">
          {data.kampanjer.map((k) => {
            const u = k.utfall;
            const hoppade = Object.entries(k.hoppade ?? {});
            return (
              <li key={k.id} className="grid gap-2 py-4">
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <p className="font-semibold">{k.namn}</p>
                  <p className={cn(meta, k.status === "fel" ? "text-danger" : undefined)}>
                    {k.status === "pagar" ? (
                      <span className="inline-flex items-center gap-1.5">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                        {text(T.pagar)} {u ? `${u.koade} / ${k.totalt}` : ""}
                      </span>
                    ) : k.status === "klar" ? (
                      <span className="inline-flex items-center gap-1.5">
                        <Check className="h-3.5 w-3.5" aria-hidden />
                        {text(T.klar)}
                      </span>
                    ) : (
                      text(T[k.status])
                    )}
                  </p>
                </div>
                <p className={meta}>
                  {k.kalla.namn} · {k.amne}
                </p>
                {u ? (
                  <p className={cn(meta, "flex flex-wrap gap-x-4 gap-y-1")}>
                    <span>
                      {text(T.koade)} {u.koade}
                    </span>
                    <span>
                      {text(T.vantar)} {u.vantar}
                    </span>
                    <span>
                      {text(T.skickade)} {u.skickade}
                    </span>
                    <span>
                      {text(T.svar)} {u.svar}
                    </span>
                    {u.stoppade ? (
                      <span>
                        {text(T.stoppade)} {u.stoppade}
                      </span>
                    ) : null}
                  </p>
                ) : null}
                {hoppade.length ? (
                  <p className={meta}>
                    {text(T.hoppade)}: {hoppade.map(([skal, n]) => `${n} ${skal}`).join(", ")}
                  </p>
                ) : null}
                {k.fel ? <p className="text-[0.9375rem] text-danger">{k.fel}</p> : null}
                {u && u.vantar > 0 ? (
                  <button
                    type="button"
                    onClick={() => void oppnaSkicka(k.id)}
                    disabled={skickar}
                    className={cn(btnPrimary, btnLiten, "justify-self-start")}
                  >
                    <Check className="h-4 w-4" aria-hidden />
                    {text(T.skicka(u.vantar))}
                  </button>
                ) : null}
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
