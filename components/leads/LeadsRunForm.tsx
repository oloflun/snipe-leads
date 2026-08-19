"use client";

import Link from "next/link";
import { useState } from "react";
import { btnPrimary } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Formuläret som startar en leads-körning. EN komponent, två ytor.
 *
 * ## Varför den bröts ut
 *
 * Adminytans "Testkörningar" hade sedan tidigare ett fullständigt formulär —
 * bransch, geografi, roller, signaler, diskvalificerare, storleksspann,
 * omfattning och antal. Kundens leads-flik hade i stället fyra hårdkodade
 * knappar ("Bygg i Malmö", "Gym i Stockholm" …) ur `lib/mock-data.ts` och en
 * länk till assistentvyn, som också är mock. Kunden kunde alltså inte starta
 * en körning alls från sin egen yta.
 *
 * Att kopiera formuläret hade gett två formulär som glider isär: adminens fick
 * roller och signaler i augusti, kundens hade fortfarande inte fått dem. Därför
 * en komponent med två flaggor (`isTest`, `demo`), inte två filer.
 *
 * ## Överskrivningarna är inte inställningar
 *
 * Fälten gäller ENBART den startade körningen och rör aldrig arbetsytans
 * sparade ICP (`/settings/leads`). Alternativet — ändra målgruppen, köra, ändra
 * tillbaka — går fel den gång man glömmer sista steget, och då bearbetas nästa
 * riktiga körning med fel målgrupp utan att någon ser det.
 *
 * ## Två vägar till prospekt
 *
 * `POST /leads/runs/batch` svarar 422 om tenanten saknar prospekt, och "Inga
 * prospekt att köra på" är ett dåligt svar på en knapp som heter "Starta
 * körning". Formuläret erbjuder därför båda vägarna in, i samma knapptryck:
 *
 *  1. **Egna bolag** — bolag kunden själv äger eller vill träffa, ett per rad.
 *  2. **Exempelbolag** — påhittade bolag som passar ICP:t, för att se hur
 *     agenten arbetar innan man har en lista. De märks `origin='example'` i
 *     databasen och kan aldrig mejlas (INV-SEND: send_guard fäller dem).
 */

type Jobb = { job_id: string; prospect_id?: string };

type LeadsSvar = {
  jobs?: Jobb[];
  count?: number;
  scope?: string;
  is_test?: boolean;
  overrides?: Record<string, unknown> | null;
  error?: string;
  detail?: string;
};

const fältklass =
  "w-full rounded-input border border-ink/15 bg-paper px-3 py-2 text-[15px] focus-ring";

function Rad({
  etikett,
  hint,
  children
}: Readonly<{ etikett: string; hint?: string; children: React.ReactNode }>) {
  return (
    <label className="block">
      <span className="text-[13px] font-medium text-ink/70">{etikett}</span>
      {hint ? <span className="ml-2 text-[12px] text-ink/45">{hint}</span> : null}
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

/** "Bygg, Tillverkning" → ["Bygg","Tillverkning"]. Tom sträng → undefined. */
function lista(värde: string): string[] | undefined {
  const delar = värde
    .split(",")
    .map((d) => d.trim())
    .filter(Boolean);
  return delar.length ? delar : undefined;
}

function rader(värde: string): string[] {
  return värde
    .split(/[\n;]/)
    .map((d) => d.trim())
    .filter(Boolean);
}

function tal(värde: string): number | undefined {
  const n = Number(värde.trim());
  return värde.trim() && Number.isFinite(n) ? n : undefined;
}

export function LeadsRunForm({
  isTest = true,
  demo = false,
  rubrik = null
}: Readonly<{ isTest?: boolean; demo?: boolean; rubrik?: React.ReactNode }>) {
  const [limit, setLimit] = useState("3");
  const [scope, setScope] = useState<"research" | "research_and_draft">("research");
  const [branscher, setBranscher] = useState("");
  const [undvik, setUndvik] = useState("");
  const [geografi, setGeografi] = useState("");
  // Roller, krävs och diskvalificerar ÄR nischen — bransch och geografi säger
  // bara var man letar. Utan dem gick en körning mot en särskild nisch inte att
  // styra: de tre kom alltid från arbetsytans sparade ICP.
  const [roller, setRoller] = useState("");
  const [kravs, setKravs] = useState("");
  const [diskvalificerar, setDiskvalificerar] = useState("");
  const [minAnst, setMinAnst] = useState("");
  const [maxAnst, setMaxAnst] = useState("");
  const [egnaBolag, setEgnaBolag] = useState("");
  const [exempelbolag, setExempelbolag] = useState(true);
  const [svar, setSvar] = useState<LeadsSvar | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function byggÖverskrivningar() {
    // Tomma fält skickas INTE. null betyder "använd arbetsytans sparade ICP",
    // vilket inte är samma sak som "inga branscher alls".
    const overrides = {
      industries: lista(branscher),
      exclude_industries: lista(undvik),
      geography: lista(geografi),
      roles: lista(roller),
      must_have: lista(kravs),
      deal_breakers: lista(diskvalificerar),
      anstallda_min: tal(minAnst),
      anstallda_max: tal(maxAnst)
    };
    return Object.values(overrides).some((v) => v !== undefined) ? overrides : null;
  }

  async function anropa<T>(path: string, init: RequestInit): Promise<T> {
    const response = await fetch(`/api/snajp-support${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init
    });
    const kropp = (await readJsonBody<T & { error?: string; detail?: string }>(response)) ?? ({} as T);
    if (!response.ok) {
      const k = kropp as { error?: string; detail?: string };
      throw new Error(k.detail ?? k.error ?? `Anropet avvisades (${response.status}).`);
    }
    return kropp;
  }

  async function kör() {
    setBusy(true);
    setFel(null);
    setSvar(null);
    setStatus(null);
    try {
      const overrides = byggÖverskrivningar();
      const antal = Number(limit) || 1;

      // 1. Egna bolag blir prospekt först — de är det kunden helst vill se.
      const egna = rader(egnaBolag);
      for (const namn of egna) {
        setStatus(`Lägger till ${namn}…`);
        await anropa("/leads/prospects", {
          method: "POST",
          body: JSON.stringify({ company_name: namn })
        });
      }

      // 2. Exempelbolag, om kunden bad om det ELLER om det inte finns något
      //    att köra på. Att svara "Inga prospekt att köra på" på en knapp som
      //    heter Starta körning är att lämna tillbaka arbetet.
      if (exempelbolag || egna.length === 0) {
        const befintliga = await anropa<{ prospects?: unknown[] }>("/leads/prospects", {
          method: "GET"
        });
        const saknas = (befintliga.prospects?.length ?? 0) === 0;
        if (exempelbolag || saknas) {
          setStatus("Tar fram exempelbolag som passar er produkt…");
          await anropa("/leads/prospects/exempel", {
            method: "POST",
            body: JSON.stringify({
              // Taket i ExempelbolagRequest är 10: exempelbolag är en väg IN i
              // produkten, inte en lista att arbeta ur. Klamras här så att ett
              // stort `antal` ger en körning på tio exempel i stället för 422.
              limit: Math.min(Math.max(antal - egna.length, 1), 10),
              ...(overrides ? { overrides } : {})
            })
          });
        }
      }

      // 3. Själva körningen.
      setStatus("Startar körningen…");
      const resultat = await anropa<LeadsSvar>("/leads/runs/batch", {
        method: "POST",
        body: JSON.stringify({
          limit: antal,
          scope,
          is_test: isTest,
          ...(overrides ? { overrides } : {})
        })
      });
      setSvar(resultat);
      setStatus(null);
    } catch (cause) {
      setFel(felmeddelande(cause));
      setStatus(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      {rubrik}

      <div className="mt-6 grid max-w-[760px] gap-5 sm:grid-cols-2">
        <Rad etikett="Antal bolag" hint="1–50">
          <input
            type="number"
            min={1}
            max={50}
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
            className={fältklass}
          />
        </Rad>
        <Rad etikett="Omfattning">
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value as typeof scope)}
            className={fältklass}
          >
            <option value="research">Bara research</option>
            <option value="research_and_draft">Research och utkast</option>
          </select>
        </Rad>
        <Rad etikett="Branscher" hint="komma emellan">
          <input value={branscher} onChange={(e) => setBranscher(e.target.value)} placeholder="Bygg, Tillverkning" className={fältklass} />
        </Rad>
        <Rad etikett="Undvik branscher">
          <input value={undvik} onChange={(e) => setUndvik(e.target.value)} placeholder="Bemanning" className={fältklass} />
        </Rad>
        <Rad etikett="Geografi">
          <input value={geografi} onChange={(e) => setGeografi(e.target.value)} placeholder="Västra Götaland" className={fältklass} />
        </Rad>
        <Rad etikett="Beslutsfattarroller" hint="vem agenten ska leta efter">
          <input value={roller} onChange={(e) => setRoller(e.target.value)} placeholder="VD, inköpschef" className={fältklass} />
        </Rad>
        <Rad etikett="Signaler som krävs" hint="nischen">
          <input value={kravs} onChange={(e) => setKravs(e.target.value)} placeholder="Egen produktion, växer" className={fältklass} />
        </Rad>
        <Rad etikett="Diskvalificerar">
          <input value={diskvalificerar} onChange={(e) => setDiskvalificerar(e.target.value)} placeholder="Under 10 anställda" className={fältklass} />
        </Rad>
        <div className="grid grid-cols-2 gap-3">
          <Rad etikett="Anställda, min">
            <input type="number" min={0} value={minAnst} onChange={(e) => setMinAnst(e.target.value)} className={fältklass} />
          </Rad>
          <Rad etikett="max">
            <input type="number" min={0} value={maxAnst} onChange={(e) => setMaxAnst(e.target.value)} className={fältklass} />
          </Rad>
        </div>
        <Rad etikett="Egna bolag" hint="ett per rad — bolag ni själva vill träffa">
          <textarea
            value={egnaBolag}
            onChange={(e) => setEgnaBolag(e.target.value)}
            rows={3}
            placeholder={"Byggkompaniet Syd AB\nNordvik Fastigheter"}
            className={cn(fältklass, "resize-y")}
          />
        </Rad>
      </div>

      <label className="mt-5 flex max-w-[70ch] items-start gap-3">
        <input
          type="checkbox"
          checked={exempelbolag}
          onChange={(e) => setExempelbolag(e.target.checked)}
          className="mt-1 h-4 w-4 accent-ochre"
        />
        <span className="text-[14px] leading-6 text-ink/70">
          Fyll på med <strong>exempelbolag</strong> som passar er produkt. Påhittade bolag som
          visar hur agenten arbetar innan ni har en egen lista — de kan aldrig mejlas.
        </span>
      </label>

      {/* På demoytan finns ingen session, och /api/snajp-support/* svarar 401
          med flit (requireSnajpTenant härleder kunden ur sessionen). Att visa
          en knapp som alltid svarar "Du måste vara inloggad" är sämre än att
          säga det innan den trycks — och att fejka ett körresultat vore värst
          av allt: hela poängen med vyn är att den visar vad agenten FAKTISKT
          gjorde. */}
      {demo ? (
        <div className="mt-6 rounded-card bg-paper2/60 p-5">
          <p className="max-w-[65ch] text-[15px] leading-7 text-ink/70">
            Formuläret är det riktiga. En körning kostar LLM-anrop mot er egen
            målgrupp och kräver därför ett konto — här visar vi vilka reglagen är,
            inte ett påhittat resultat.
          </p>
          <Link href="/login" className={cn(btnPrimary, "mt-4")}>
            Logga in för att köra
          </Link>
        </div>
      ) : (
        <button type="button" onClick={() => void kör()} disabled={busy} className={cn(btnPrimary, "mt-6")}>
          {busy ? "Startar…" : isTest ? "Starta testkörning" : "Starta körning"}
        </button>
      )}

      {status ? <p className="mt-3 text-[13px] text-ink/55">{status}</p> : null}

      {fel ? (
        <p role="alert" className="mt-5 max-w-[70ch] break-words text-[15px] text-danger">
          {fel}
        </p>
      ) : null}

      {svar ? (
        <div className="mt-5 rounded-card bg-paper2/60 p-5">
          <p className="text-[15px]">
            {svar.count} jobb startade · omfattning{" "}
            <span className="font-mono text-[13px]">{svar.scope}</span>
            {svar.is_test ? " · märkt som testkörning" : null}
          </p>
          {svar.overrides ? (
            // Ekar tillbaka vad körningen FAKTISKT kördes med, inte vad
            // formuläret råkade innehålla när knappen trycktes.
            <pre className="thin-scrollbar mt-3 overflow-x-auto rounded-input bg-paper p-3 font-mono text-[12px] text-ink/70">
              {JSON.stringify(svar.overrides, null, 2)}
            </pre>
          ) : (
            <p className="mt-2 text-[13px] text-ink/55">
              Inga överskrivningar — arbetsytans sparade målgrupp användes.
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}
