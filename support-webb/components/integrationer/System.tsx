"use client";

import { ChevronDown, Loader2, Play, Plus, Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, EmptyState, SkeletonRows, btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import { BAS } from "@/lib/api";
import { felmeddelande } from "@/lib/http/json";
import { cn } from "@/lib/utils";
import { Hemligheter, type Forslag } from "./Hemligheter";
import {
  faltklass,
  las,
  skicka,
  textfaltklass,
  type Hemlighetsandringar,
  type Integration,
  type IntegrationsSvar,
  type Integrationstyp,
  type Provresultat,
  type Verktyg
} from "./typer";

/**
 * Kundens egna system: HTTP-anrop (Ebbots http_request-format) och
 * MCP-servrar. Agenten väljer verktyg ur dem när ett ärende behöver uppgifter
 * som inte står i kunskapsbasen, till exempel orderstatus eller kontot.
 */

const MALL_HTTP = {
  requests: [
    {
      name: "Orderstatus",
      description: "Hämtar status och leveransdatum för en order.",
      method: "GET",
      url: "https://api.er-butik.se/v1/orders/{{ordernummer}}?email={{kund.email}}",
      headers: { Authorization: "Bearer {{hemlighet.token}}" },
      placeholders: [{ key: "ordernummer", type: "string", description: "Kundens ordernummer" }],
      responsePath: "order"
    }
  ]
};

const EXEMPEL_HANDELSE = `{
  "requests": [
    {
      "name": "Skapa ärende",
      "method": "POST",
      "url": "https://{{hemlighet.instans}}.zendesk.com/api/v2/tickets.json",
      "headers": { "Authorization": "Basic {{hemlighet.token}}" },
      "body": {
        "ticket": {
          "subject": "Från Snajp: {{handelse.orsak}}",
          "comment": { "body": "{{handelse.samtal}}" },
          "requester": { "email": "{{kund.email}}", "name": "{{kund.namn}}" }
        }
      }
    }
  ],
  "handelser": { "arende_eskalerat": "Skapa ärende" }
}`;

const MCP_FORSLAG: Forslag[] = [
  {
    namn: "auth",
    etikett: "Auth-hemlighet",
    hjalp: "Hela rubrikvärdet, till exempel ”Bearer …”. Lämna tomt om servern är öppen."
  }
];

function lista(text: string): string[] {
  return text
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function Formular({
  befintlig,
  kontextvarden,
  onKlar,
  onAvbryt
}: Readonly<{
  befintlig: Integration | null;
  kontextvarden: string[];
  onKlar: () => Promise<void>;
  onAvbryt: () => void;
}>) {
  const [typ, setTyp] = useState<Integrationstyp>(befintlig?.typ ?? "http");
  const [namn, setNamn] = useState(befintlig?.namn ?? "");
  const [beskrivning, setBeskrivning] = useState(befintlig?.beskrivning ?? "");
  const [httpJson, setHttpJson] = useState(() =>
    JSON.stringify(befintlig?.typ === "http" ? befintlig.konfig : MALL_HTTP, null, 2)
  );
  const mcp = (befintlig?.typ === "mcp" ? befintlig.konfig : {}) as Record<string, unknown>;
  const [mcpUrl, setMcpUrl] = useState(String(mcp.url ?? ""));
  const [transport, setTransport] = useState(String(mcp.transport ?? "streamable_http"));
  const [authRubrik, setAuthRubrik] = useState(String(mcp.auth_header_name ?? "Authorization"));
  const [tillatna, setTillatna] = useState(((mcp.tillatna_verktyg as string[]) ?? []).join(", "));
  const [skrivande, setSkrivande] = useState(((mcp.skrivande_verktyg as string[]) ?? []).join(", "));
  const [andringar, setAndringar] = useState<Hemlighetsandringar>(() => {
    const start: Hemlighetsandringar = {};
    // Mallen refererar {{hemlighet.token}}, så raden finns redan på plats.
    if (!befintlig) start.token = "";
    return start;
  });
  const [sparar, setSparar] = useState(false);
  const [fel, setFel] = useState<string | null>(null);

  const sparade = Object.keys(befintlig?.hemligheter ?? {});

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    setFel(null);
    let konfig: Record<string, unknown>;
    if (typ === "http") {
      try {
        konfig = JSON.parse(httpJson);
      } catch (orsak) {
        setFel(`Konfigurationen är inte giltig JSON: ${(orsak as Error).message}`);
        return;
      }
    } else {
      konfig = {
        url: mcpUrl.trim(),
        transport,
        auth_header_name: authRubrik.trim() || "Authorization",
        tillatna_verktyg: lista(tillatna),
        skrivande_verktyg: lista(skrivande)
      };
    }
    // Tomma rader betyder "inget ändrat", inte "ta bort": ta bort är null.
    const hemligheter = Object.fromEntries(
      Object.entries(andringar).filter(([, v]) => v === null || (typeof v === "string" && v !== ""))
    );
    setSparar(true);
    try {
      if (befintlig) {
        await las(
          await skicka("PATCH", `${BAS}/integrationer/${befintlig.id}`, {
            namn: namn.trim(),
            beskrivning: beskrivning.trim(),
            konfig,
            hemligheter
          })
        );
      } else {
        await las(
          await skicka("POST", `${BAS}/integrationer`, {
            typ,
            namn: namn.trim(),
            beskrivning: beskrivning.trim(),
            konfig,
            hemligheter: Object.fromEntries(
              Object.entries(hemligheter).filter(([, v]) => typeof v === "string")
            )
          })
        );
      }
      await onKlar();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setSparar(false);
    }
  }

  return (
    <form onSubmit={spara} className="space-y-5 border-y border-ink/15 py-5" aria-label="Integration">
      {!befintlig ? (
        <fieldset>
          <legend className="text-[0.875rem] font-medium text-ink">Typ</legend>
          <div className="mt-1.5 inline-flex rounded-input border border-ink/15 p-0.5" role="radiogroup">
            {(
              [
                ["http", "HTTP-anrop"],
                ["mcp", "MCP-server"]
              ] as const
            ).map(([varde, etikett]) => (
              <button
                key={varde}
                type="button"
                role="radio"
                aria-checked={typ === varde}
                onClick={() => {
                  setTyp(varde);
                  setAndringar(varde === "http" ? { token: "" } : {});
                }}
                className={cn(
                  "focus-ring h-10 rounded-[6px] px-4 text-[0.9375rem] transition-colors",
                  typ === varde ? "bg-ink text-paper" : "text-ink/70 hover:bg-paper2"
                )}
              >
                {etikett}
              </button>
            ))}
          </div>
        </fieldset>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-[0.875rem] font-medium text-ink">Namn</span>
          <input
            value={namn}
            onChange={(e) => setNamn(e.target.value)}
            required
            maxLength={80}
            placeholder={typ === "http" ? "Webbutiken" : "CRM"}
            className={faltklass}
          />
        </label>
        <label className="block">
          <span className="text-[0.875rem] font-medium text-ink">Beskrivning</span>
          <input
            value={beskrivning}
            onChange={(e) => setBeskrivning(e.target.value)}
            maxLength={500}
            placeholder="Ordrar och leveranser"
            className={faltklass}
          />
        </label>
      </div>

      {typ === "http" ? (
        <div>
          <label className="block">
            <span className="text-[0.875rem] font-medium text-ink">Konfiguration (JSON)</span>
            <textarea
              value={httpJson}
              onChange={(e) => setHttpJson(e.target.value)}
              rows={16}
              spellCheck={false}
              className={cn(textfaltklass, "font-mono text-[0.8125rem] leading-5")}
            />
          </label>
          <div className="mt-2 max-w-[72ch] space-y-1.5 text-[0.8125rem] leading-5 text-ink-muted">
            <p>
              Ebbots <code className="font-mono">http_request</code>-format: varje post i{" "}
              <code className="font-mono">requests</code> blir ett verktyg. Bara https.
            </p>
            <p>
              <code className="font-mono">{"{{namn}}"}</code> fylls i av agenten.{" "}
              <code className="font-mono">{"{{hemlighet.namn}}"}</code> hämtas ur nycklarna nedan.{" "}
              Fylls i av Snajp, låsta för agenten:{" "}
              {kontextvarden.map((k, i) => (
                <span key={k}>
                  <code className="font-mono">{`{{${k}}}`}</code>
                  {i < kontextvarden.length - 1 ? ", " : "."}
                </span>
              ))}
            </p>
            <p>
              Annan metod än GET räknas som ändrande: högst ett per ärende, aldrig i testchatten. Markera
              ett sökanrop med POST med <code className="font-mono">{'"skrivande": false'}</code>.
            </p>
            <details className="group">
              <summary className="focus-ring inline-flex cursor-pointer list-none items-center gap-1 rounded-[4px] font-medium text-ink/75">
                <ChevronDown className="h-3.5 w-3.5 transition-transform group-open:rotate-180" aria-hidden />
                Exempel: skapa ärendet i Zendesk när agenten lämnar över
              </summary>
              <pre className="mt-2 overflow-x-auto rounded-input bg-paper2/70 p-3 font-mono text-[0.75rem] leading-5 text-ink/80">
                {EXEMPEL_HANDELSE}
              </pre>
              <p className="mt-1.5">
                En förfrågan i <code className="font-mono">handelser</code> anropas av Snajp vid
                överlämning, med hela samtalet i <code className="font-mono">{"{{handelse.samtal}}"}</code>.
                Den visas inte för agenten.
              </p>
            </details>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <label className="block">
            <span className="text-[0.875rem] font-medium text-ink">Serverns adress</span>
            <input
              value={mcpUrl}
              onChange={(e) => setMcpUrl(e.target.value)}
              required
              type="url"
              placeholder="https://mcp.er-crm.se/mcp"
              className={faltklass}
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-[0.875rem] font-medium text-ink">Transport</span>
              <select value={transport} onChange={(e) => setTransport(e.target.value)} className={faltklass}>
                <option value="streamable_http">Streamable HTTP (standard)</option>
                <option value="sse">SSE (äldre servrar)</option>
              </select>
            </label>
            <label className="block">
              <span className="text-[0.875rem] font-medium text-ink">Rubrik för nyckeln</span>
              <input value={authRubrik} onChange={(e) => setAuthRubrik(e.target.value)} className={faltklass} />
            </label>
          </div>
          <label className="block">
            <span className="text-[0.875rem] font-medium text-ink">Tillåtna verktyg</span>
            <input
              value={tillatna}
              onChange={(e) => setTillatna(e.target.value)}
              placeholder="Tomt = alla som servern inte märker som destruktiva"
              className={faltklass}
            />
          </label>
          <label className="block">
            <span className="text-[0.875rem] font-medium text-ink">Verktyg som ändrar data</span>
            <input
              value={skrivande}
              onChange={(e) => setSkrivande(e.target.value)}
              placeholder="t.ex. avboka_order, uppdatera_adress"
              className={faltklass}
            />
            <span className="mt-1.5 block text-[0.8125rem] leading-5 text-ink-muted">
              Högst ett anrop per ärende, aldrig i testchatten. Verktyg som servern märker som ändrande
              räknas in automatiskt.
            </span>
          </label>
        </div>
      )}

      <div>
        <h3 className="text-[0.875rem] font-medium text-ink">Nycklar</h3>
        <div className="mt-2">
          <Hemligheter
            sparade={sparade}
            forslag={typ === "mcp" ? MCP_FORSLAG : []}
            andringar={andringar}
            onAndra={setAndringar}
            friaNamn={typ === "http"}
          />
        </div>
      </div>

      {fel ? (
        <p role="alert" className="max-w-[70ch] whitespace-pre-wrap text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" disabled={sparar || !namn.trim()} className={btnPrimary}>
          {sparar ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
          {befintlig ? "Spara ändringar" : "Lägg till"}
        </button>
        <button type="button" onClick={onAvbryt} className={btnSecondary}>
          Avbryt
        </button>
      </div>
    </form>
  );
}

function exempelArgument(v: Verktyg): string {
  const ut: Record<string, unknown> = {};
  for (const [nyckel, schema] of Object.entries(v.argument.properties ?? {})) {
    ut[nyckel] = schema.default ?? (schema.type === "number" || schema.type === "integer" ? 0 : "");
  }
  return JSON.stringify(ut, null, 2);
}

function VerktygPanel({ integration }: Readonly<{ integration: Integration }>) {
  const [verktyg, setVerktyg] = useState<Verktyg[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [valt, setValt] = useState<string>("");
  const [argument, setArgument] = useState("{}");
  const [kundEmail, setKundEmail] = useState("");
  const [tillatSkrivning, setTillatSkrivning] = useState(false);
  const [kor, setKor] = useState(false);
  const [resultat, setResultat] = useState<Provresultat | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await las<{ verktyg: Verktyg[] }>(await fetch(`${BAS}/integrationer/${integration.id}/verktyg`, { cache: "no-store" }));
        setVerktyg(data.verktyg);
        const forsta = data.verktyg[0];
        if (forsta) {
          setValt(forsta.namn);
          setArgument(exempelArgument(forsta));
        }
      } catch (orsak) {
        setFel(felmeddelande(orsak));
        setVerktyg([]);
      }
    })();
  }, [integration.id, integration.updated_at]);

  const aktuellt = verktyg?.find((v) => v.namn === valt) ?? null;

  async function prova() {
    if (!aktuellt) return;
    let arg: Record<string, unknown>;
    try {
      arg = JSON.parse(argument || "{}");
    } catch {
      setFel("Argumenten är inte giltig JSON.");
      return;
    }
    setFel(null);
    setResultat(null);
    setKor(true);
    try {
      const data = await las<{ resultat: Provresultat }>(
        await skicka("POST", `${BAS}/integrationer/${integration.id}/prova`, {
          verktyg: integration.typ === "http" ? aktuellt.forfragan ?? aktuellt.namn : aktuellt.namn,
          argument: arg,
          kontext: kundEmail.trim() ? { "kund.email": kundEmail.trim() } : {},
          tillat_skrivning: tillatSkrivning
        })
      );
      setResultat(data.resultat);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setKor(false);
    }
  }

  if (verktyg === null) {
    return (
      <div className="mt-3">
        <SkeletonRows />
      </div>
    );
  }

  return (
    <div className="mt-3 space-y-5 rounded-input bg-paper2/45 p-4">
      <div>
        <h4 className="text-[0.875rem] font-medium">Det agenten ser</h4>
        {verktyg.length === 0 ? (
          <p className="mt-1 text-[0.875rem] text-ink/60">{fel ?? "Inga verktyg."}</p>
        ) : (
          <ul className="mt-1.5 divide-y divide-ink/10">
            {verktyg.map((v) => (
              <li key={v.namn} className="py-2">
                <div className="flex flex-wrap items-baseline gap-2">
                  <code className="font-mono text-[0.8125rem]">{v.namn}</code>
                  {v.skrivande ? <Badge tone="warn">Ändrar data</Badge> : null}
                  {v.handelse ? <Badge>Vid {v.handelse.replace("_", " ")}</Badge> : null}
                  {!v.synligt_for_agenten && !v.handelse ? <Badge>Dolt för agenten</Badge> : null}
                </div>
                <p className="mt-0.5 text-[0.8125rem] leading-5 text-ink/65">{v.beskrivning}</p>
                {Object.keys(v.argument.properties ?? {}).length ? (
                  <p className="mt-0.5 text-[0.75rem] text-ink/50">
                    Argument:{" "}
                    {Object.keys(v.argument.properties ?? {})
                      .map((a) => ((v.argument.required ?? []).includes(a) ? a : `${a} (valfri)`))
                      .join(", ")}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      {verktyg.length ? (
        <div className="space-y-3">
          <h4 className="text-[0.875rem] font-medium">Prova på riktigt</h4>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="text-[0.8125rem] font-medium text-ink">Verktyg</span>
              <select
                value={valt}
                onChange={(e) => {
                  setValt(e.target.value);
                  const v = verktyg.find((x) => x.namn === e.target.value);
                  if (v) setArgument(exempelArgument(v));
                  setTillatSkrivning(false);
                  setResultat(null);
                }}
                className={faltklass}
              >
                {verktyg.map((v) => (
                  <option key={v.namn} value={v.namn}>
                    {v.namn}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-[0.8125rem] font-medium text-ink">Kundens e-post (för {"{{kund.email}}"})</span>
              <input
                value={kundEmail}
                onChange={(e) => setKundEmail(e.target.value)}
                type="email"
                placeholder="kund@exempel.se"
                className={faltklass}
              />
            </label>
          </div>
          <label className="block">
            <span className="text-[0.8125rem] font-medium text-ink">Argument (JSON)</span>
            <textarea
              value={argument}
              onChange={(e) => setArgument(e.target.value)}
              rows={4}
              spellCheck={false}
              className={cn(textfaltklass, "font-mono text-[0.8125rem] leading-5")}
            />
          </label>
          {aktuellt?.skrivande ? (
            <label className="flex items-start gap-2 text-[0.875rem]">
              <input
                type="checkbox"
                checked={tillatSkrivning}
                onChange={(e) => setTillatSkrivning(e.target.checked)}
                className="mt-1 h-4 w-4 accent-[oklch(var(--ink))]"
              />
              <span>Jag förstår att provet ändrar data i vårt system på riktigt.</span>
            </label>
          ) : null}
          <button
            type="button"
            onClick={prova}
            disabled={kor || (aktuellt?.skrivande && !tillatSkrivning)}
            className={cn(btnSecondary)}
          >
            {kor ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Play className="h-4 w-4" aria-hidden />}
            Kör provet
          </button>
          {fel && verktyg.length ? (
            <p role="alert" className="text-[0.875rem] text-danger">
              {fel}
            </p>
          ) : null}
          {resultat ? (
            <div role="status" className="space-y-1.5">
              <p className="text-[0.875rem]">
                {resultat.fel ? (
                  <span className="text-danger">{resultat.fel}</span>
                ) : (
                  <span className="text-moss">
                    Svar{resultat.status ? ` ${resultat.status}` : ""}: så här ser agenten uppgifterna.
                  </span>
                )}
              </p>
              {resultat.data ? (
                <pre className="max-h-72 overflow-auto rounded-input border border-ink/10 bg-paper p-3 font-mono text-[0.75rem] leading-5 text-ink/80">
                  {resultat.data}
                </pre>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function SystemSektion() {
  const [data, setData] = useState<IntegrationsSvar | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [redigerar, setRedigerar] = useState<string | "ny" | null>(null);
  const [oppen, setOppen] = useState<string | null>(null);
  const [pagar, setPagar] = useState<string | null>(null);

  async function ladda() {
    try {
      setData(await las<IntegrationsSvar>(await fetch(`${BAS}/integrationer`, { cache: "no-store" })));
      setFel(null);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
      setData((nu) => nu ?? { integrationer: [], kontextvarden: [], handelser: {} });
    }
  }

  useEffect(() => {
    void ladda();
  }, []);

  async function vaxlaAktiv(i: Integration) {
    setPagar(i.id);
    try {
      await las(await skicka("PATCH", `${BAS}/integrationer/${i.id}`, { aktiv: !i.aktiv }));
      await ladda();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setPagar(null);
    }
  }

  async function taBort(i: Integration) {
    if (!window.confirm(`Ta bort ${i.namn}? Nycklarna raderas också och går inte att få tillbaka.`)) return;
    setPagar(i.id);
    try {
      await las(await skicka("DELETE", `${BAS}/integrationer/${i.id}`));
      if (oppen === i.id) setOppen(null);
      await ladda();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setPagar(null);
    }
  }

  const redigerad = data?.integrationer.find((i) => i.id === redigerar) ?? null;

  return (
    <section aria-labelledby="rubrik-system">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 id="rubrik-system" className="font-display text-[1.25rem]">
          Era system
        </h2>
        {redigerar === null ? (
          <button type="button" onClick={() => setRedigerar("ny")} className={btnSecondary}>
            <Plus className="h-4 w-4" aria-hidden />
            Lägg till system
          </button>
        ) : null}
      </div>

      {fel ? (
        <p role="alert" className="mt-3 max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      {redigerar !== null && data ? (
        <div className="mt-4">
          <Formular
            key={redigerar}
            befintlig={redigerad}
            kontextvarden={data.kontextvarden}
            onKlar={async () => {
              setRedigerar(null);
              await ladda();
            }}
            onAvbryt={() => setRedigerar(null)}
          />
        </div>
      ) : null}

      <div className="mt-4">
        {data === null ? (
          <SkeletonRows />
        ) : data.integrationer.length === 0 ? (
          redigerar === null ? (
            <EmptyState title="Inga system kopplade" />
          ) : null
        ) : (
          <ul className="divide-y divide-ink/12 border-y border-ink/15">
            {data.integrationer.map((i) => (
              <li key={i.id} className="py-3">
                <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
                  <div className="min-w-0">
                    <p className="flex flex-wrap items-baseline gap-2">
                      <span className="text-[0.9375rem] font-medium">{i.namn}</span>
                      <Badge>{i.typ === "http" ? "HTTP" : "MCP"}</Badge>
                      <Badge tone={i.aktiv ? "good" : "neutral"}>{i.aktiv ? "Aktiv" : "Avstängd"}</Badge>
                    </p>
                    {i.beskrivning ? (
                      <p className="mt-0.5 truncate text-[0.875rem] text-ink/55">{i.beskrivning}</p>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      aria-expanded={oppen === i.id}
                      onClick={() => setOppen(oppen === i.id ? null : i.id)}
                      className={cn(btnSecondary, btnLiten)}
                    >
                      <Wrench className="h-3.5 w-3.5" aria-hidden />
                      Verktyg och prov
                    </button>
                    <button type="button" onClick={() => setRedigerar(i.id)} className={cn(btnSecondary, btnLiten)}>
                      Redigera
                    </button>
                    <button
                      type="button"
                      disabled={pagar === i.id}
                      onClick={() => void vaxlaAktiv(i)}
                      className={cn(btnSecondary, btnLiten)}
                    >
                      {i.aktiv ? "Stäng av" : "Aktivera"}
                    </button>
                    <button
                      type="button"
                      disabled={pagar === i.id}
                      onClick={() => void taBort(i)}
                      className={cn(btnSecondary, btnLiten, "!text-danger")}
                    >
                      Ta bort
                    </button>
                  </div>
                </div>
                {oppen === i.id ? <VerktygPanel integration={i} /> : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
