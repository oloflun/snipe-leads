"use client";

import { Check, Copy, Loader2, Plus, PlugZap } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, EmptyState, SkeletonRows, btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import { BAS } from "@/lib/api";
import { felmeddelande } from "@/lib/http/json";
import { cn } from "@/lib/utils";
import { Hemligheter, type Forslag } from "./Hemligheter";
import { faltklass, las, skicka, type Anslutning, type Hemlighetsandringar, type KanalSvar, type Kanalnamn } from "./typer";

/**
 * Kanalerna: agenten svarar kunder i WhatsApp, Messenger, Slack och Teams.
 * Varje anslutning får en egen webhookadress som klistras in hos kanalen, och
 * varje inkommande meddelande kontrolleras mot kanalens signatur innan det
 * släpps in. Medarbetarens svar i Chattar går ut i samma kanal.
 */

const KANALNAMN: Record<Kanalnamn, string> = {
  whatsapp: "WhatsApp",
  messenger: "Messenger",
  slack: "Slack",
  teams: "Microsoft Teams"
};

const HEMLIGHETSETIKETT: Record<string, { etikett: string; hjalp?: string }> = {
  access_token: { etikett: "Åtkomsttoken" },
  app_secret: { etikett: "Apphemlighet", hjalp: "Meta-appen → Appinställningar → Grundläggande → Apphemlighet." },
  verify_token: {
    etikett: "Verifieringstoken",
    hjalp: "En valfri sträng ni hittar på. Samma sträng klistras in hos Meta tillsammans med webhookadressen."
  },
  bot_token: { etikett: "Bot-token", hjalp: "Börjar med xoxb-. Finns under OAuth & Permissions." },
  signing_secret: { etikett: "Signing Secret", hjalp: "Finns under Basic Information → App Credentials." },
  app_password: {
    etikett: "Klienthemlighet",
    hjalp: "Skapas under appregistreringens Certifikat och hemligheter i Microsoft Entra."
  }
};

/** Hjälptext som skiljer sig per kanal trots samma nyckelnamn. */
const KANALHJALP: Partial<Record<Kanalnamn, Record<string, string>>> = {
  whatsapp: { access_token: "En systemanvändartoken med behörigheten whatsapp_business_messaging." },
  messenger: { access_token: "Sidans åtkomsttoken, med behörigheten pages_messaging." }
};

const STEG: Record<Kanalnamn, string[]> = {
  whatsapp: [
    "I Meta-appen: WhatsApp → Konfiguration → Webhook. Klistra in webhookadressen och er verifieringstoken.",
    "Prenumerera på fältet messages.",
    "Anslutningens id är numrets phone_number_id, under WhatsApp → API-inställningar."
  ],
  messenger: [
    "I Meta-appen: Messenger → Inställningar → Webhooks. Klistra in webhookadressen och er verifieringstoken.",
    "Prenumerera sidan på messages och messaging_postbacks.",
    "Anslutningens id är Facebook-sidans id."
  ],
  slack: [
    "På api.slack.com/apps: Event Subscriptions → Request URL = webhookadressen.",
    "Bot events: message.im och app_mention.",
    "OAuth-scopes: chat:write, im:history och app_mentions:read, gärna också users:read och users:read.email.",
    "Anslutningens id är arbetsytans team_id (börjar med T)."
  ],
  teams: [
    "I Azure Bot: Konfiguration → Messaging endpoint = webhookadressen.",
    "Under Kanaler: lägg till Microsoft Teams.",
    "Anslutningens id är botens Microsoft App ID. För en single-tenant-bot anger ni också Entra-tenantens id."
  ]
};

function Kopiera({ text }: Readonly<{ text: string }>) {
  const [kopierad, setKopierad] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setKopierad(true);
          setTimeout(() => setKopierad(false), 1800);
        } catch {
          setKopierad(false);
        }
      }}
      className={cn(btnSecondary, btnLiten)}
      aria-label="Kopiera webhookadressen"
    >
      {kopierad ? <Check className="h-3.5 w-3.5 text-moss" aria-hidden /> : <Copy className="h-3.5 w-3.5" aria-hidden />}
      {kopierad ? "Kopierad" : "Kopiera"}
    </button>
  );
}

function Webhook({ url }: Readonly<{ url: string | null }>) {
  if (!url) {
    return (
      <p className="text-[0.8125rem] text-ink/55">
        Webhookadressen visas när tjänstens publika adress är känd.
      </p>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <code className="min-w-0 flex-1 truncate rounded-input bg-paper2/70 px-2.5 py-1.5 font-mono text-[0.75rem] text-ink/80" title={url}>
        {url}
      </code>
      <Kopiera text={url} />
    </div>
  );
}

function NyAnslutning({
  kanaler,
  onKlar,
  onAvbryt
}: Readonly<{
  kanaler: KanalSvar["kanaler"];
  onKlar: (ny: Anslutning) => Promise<void>;
  onAvbryt: () => void;
}>) {
  const [kanal, setKanal] = useState<Kanalnamn>("whatsapp");
  const [namn, setNamn] = useState("");
  const [externId, setExternId] = useState("");
  const [entraTenant, setEntraTenant] = useState("");
  const [andringar, setAndringar] = useState<Hemlighetsandringar>({});
  const [sparar, setSparar] = useState(false);
  const [fel, setFel] = useState<string | null>(null);

  const kravs = kanaler[kanal]?.hemligheter ?? [];
  const forslag: Forslag[] = kravs.map((n) => {
    const bas = HEMLIGHETSETIKETT[n] ?? { etikett: n };
    return { namn: n, ...bas, hjalp: KANALHJALP[kanal]?.[n] ?? bas.hjalp };
  });
  const saknas = kravs.filter((n) => !(typeof andringar[n] === "string" && andringar[n]));

  async function spara(e: React.FormEvent) {
    e.preventDefault();
    setFel(null);
    setSparar(true);
    try {
      const ny = await las<Anslutning>(
        await skicka("POST", `${BAS}/kanaler`, {
          kanal,
          namn: namn.trim(),
          extern_id: externId.trim(),
          konfig: kanal === "teams" && entraTenant.trim() ? { app_tenant_id: entraTenant.trim() } : {},
          hemligheter: Object.fromEntries(
            Object.entries(andringar).filter(([, v]) => typeof v === "string" && v !== "")
          )
        })
      );
      await onKlar(ny);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setSparar(false);
    }
  }

  return (
    <form onSubmit={spara} className="space-y-5 border-y border-ink/15 py-5" aria-label="Ny kanal">
      <fieldset>
        <legend className="text-[0.875rem] font-medium text-ink">Kanal</legend>
        <div
          className="mt-1.5 grid grid-cols-2 gap-0.5 rounded-input border border-ink/15 p-0.5 sm:inline-flex"
          role="radiogroup"
        >
          {(Object.keys(KANALNAMN) as Kanalnamn[]).map((k) => (
            <button
              key={k}
              type="button"
              role="radio"
              aria-checked={kanal === k}
              onClick={() => {
                setKanal(k);
                setAndringar({});
              }}
              className={cn(
                "focus-ring h-10 whitespace-nowrap rounded-[6px] px-4 text-[0.9375rem] transition-colors",
                kanal === k ? "bg-ink text-paper" : "text-ink/70 hover:bg-paper2"
              )}
            >
              {k === "teams" ? "Teams" : KANALNAMN[k]}
            </button>
          ))}
        </div>
      </fieldset>

      <ol className="max-w-[72ch] list-decimal space-y-1 pl-5 text-[0.8125rem] leading-5 text-ink/65">
        {STEG[kanal].map((s) => (
          <li key={s}>{s}</li>
        ))}
        <li>Spara här först. Webhookadressen visas direkt efteråt.</li>
      </ol>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-[0.875rem] font-medium text-ink">Anslutningens id</span>
          <input
            value={externId}
            onChange={(e) => setExternId(e.target.value)}
            required
            spellCheck={false}
            className={faltklass}
          />
          <span className="mt-1.5 block text-[0.8125rem] leading-5 text-ink/55">{kanaler[kanal]?.extern_id}</span>
        </label>
        <label className="block">
          <span className="text-[0.875rem] font-medium text-ink">Namn (valfritt)</span>
          <input
            value={namn}
            onChange={(e) => setNamn(e.target.value)}
            maxLength={80}
            placeholder="Kundtjänst"
            className={faltklass}
          />
        </label>
        {kanal === "teams" ? (
          <label className="block sm:col-span-2">
            <span className="text-[0.875rem] font-medium text-ink">Entra-tenantens id (single-tenant-bot)</span>
            <input
              value={entraTenant}
              onChange={(e) => setEntraTenant(e.target.value)}
              spellCheck={false}
              placeholder="Tomt för en äldre multi-tenant-bot"
              className={faltklass}
            />
          </label>
        ) : null}
      </div>

      <div>
        <h3 className="text-[0.875rem] font-medium text-ink">Nycklar</h3>
        <div className="mt-2">
          <Hemligheter sparade={[]} forslag={forslag} andringar={andringar} onAndra={setAndringar} friaNamn={false} />
        </div>
      </div>

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" disabled={sparar || !externId.trim() || saknas.length > 0} className={btnPrimary}>
          {sparar ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
          Anslut {KANALNAMN[kanal]}
        </button>
        <button type="button" onClick={onAvbryt} className={btnSecondary}>
          Avbryt
        </button>
        {saknas.length ? (
          <span className="text-[0.8125rem] text-ink/55">
            Fyll i {saknas.map((n) => HEMLIGHETSETIKETT[n]?.etikett ?? n).join(", ").toLowerCase()}.
          </span>
        ) : null}
      </div>
    </form>
  );
}

export function KanalSektion() {
  const [data, setData] = useState<KanalSvar | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [ny, setNy] = useState(false);
  const [pagar, setPagar] = useState<string | null>(null);
  const [besked, setBesked] = useState<Record<string, { ok: boolean; text: string }>>({});
  const [nyss, setNyss] = useState<string | null>(null);

  async function ladda() {
    try {
      setData(await las<KanalSvar>(await fetch(`${BAS}/kanaler`, { cache: "no-store" })));
      setFel(null);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
      setData((nu) => nu ?? { anslutningar: [], kanaler: {} as KanalSvar["kanaler"], webhook_bas: null });
    }
  }

  useEffect(() => {
    void ladda();
  }, []);

  async function prova(a: Anslutning) {
    setPagar(a.id);
    // "Ansluten, klistra in adressen" är inaktuellt så fort ett prov körts:
    // provets besked är det som gäller nu.
    if (nyss === a.id) setNyss(null);
    try {
      const svar = await las<{ ok: boolean; besked: string }>(await skicka("POST", `${BAS}/kanaler/${a.id}/prova`));
      setBesked((b) => ({ ...b, [a.id]: { ok: svar.ok, text: svar.besked } }));
    } catch (orsak) {
      setBesked((b) => ({ ...b, [a.id]: { ok: false, text: felmeddelande(orsak) } }));
    } finally {
      setPagar(null);
    }
  }

  async function vaxlaAktiv(a: Anslutning) {
    setPagar(a.id);
    try {
      await las(await skicka("PATCH", `${BAS}/kanaler/${a.id}`, { aktiv: !a.aktiv }));
      await ladda();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setPagar(null);
    }
  }

  async function taBort(a: Anslutning) {
    if (!window.confirm(`Koppla bort ${KANALNAMN[a.kanal]} (${a.extern_id})? Agenten slutar svara i kanalen direkt.`)) return;
    setPagar(a.id);
    try {
      await las(await skicka("DELETE", `${BAS}/kanaler/${a.id}`));
      await ladda();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setPagar(null);
    }
  }

  return (
    <section aria-labelledby="rubrik-kanaler">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="rubrik-kanaler" className="font-display text-[1.25rem]">
            Kanaler
          </h2>
          <p className="mt-1 max-w-[62ch] text-[0.9375rem] leading-6 text-ink/60">
            Agenten svarar i WhatsApp, Messenger, Slack och Teams, med samma kunskapsbas och samma
            regler som i webbchatten. När den lämnar över svarar ni från Chattar, och svaret går ut i
            samma kanal.
          </p>
        </div>
        {!ny ? (
          <button type="button" onClick={() => setNy(true)} className={btnSecondary} disabled={!data}>
            <Plus className="h-4 w-4" aria-hidden />
            Anslut kanal
          </button>
        ) : null}
      </div>

      {fel ? (
        <p role="alert" className="mt-3 max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      {ny && data ? (
        <div className="mt-4">
          <NyAnslutning
            kanaler={data.kanaler}
            onKlar={async (anslutning) => {
              setNy(false);
              setNyss(anslutning.id);
              await ladda();
            }}
            onAvbryt={() => setNy(false)}
          />
        </div>
      ) : null}

      <div className="mt-4">
        {data === null ? (
          <SkeletonRows />
        ) : data.anslutningar.length === 0 ? (
          ny ? null : (
            <EmptyState
              title="Ingen kanal ansluten"
              body="Agenten svarar i dag i webbchatten och i mejl. Anslut en kanal för att möta kunderna där de redan skriver."
            />
          )
        ) : (
          <ul className="divide-y divide-ink/12 border-y border-ink/15">
            {data.anslutningar.map((a) => (
              <li key={a.id} className="space-y-2 py-3">
                <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
                  <p className="flex min-w-0 flex-wrap items-baseline gap-2">
                    <span className="text-[0.9375rem] font-medium">{KANALNAMN[a.kanal]}</span>
                    {a.namn ? <span className="text-[0.875rem] text-ink/60">{a.namn}</span> : null}
                    <code className="font-mono text-[0.75rem] text-ink/45">{a.extern_id}</code>
                    <Badge tone={a.aktiv ? "good" : "neutral"}>{a.aktiv ? "Aktiv" : "Avstängd"}</Badge>
                    {a.saknade_hemligheter.length ? <Badge tone="warn">Saknar nycklar</Badge> : null}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={pagar === a.id}
                      onClick={() => void prova(a)}
                      className={cn(btnSecondary, btnLiten)}
                    >
                      {pagar === a.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                      ) : (
                        <PlugZap className="h-3.5 w-3.5" aria-hidden />
                      )}
                      Prova anslutningen
                    </button>
                    <button
                      type="button"
                      disabled={pagar === a.id}
                      onClick={() => void vaxlaAktiv(a)}
                      className={cn(btnSecondary, btnLiten)}
                    >
                      {a.aktiv ? "Stäng av" : "Aktivera"}
                    </button>
                    <button
                      type="button"
                      disabled={pagar === a.id}
                      onClick={() => void taBort(a)}
                      className={cn(btnSecondary, btnLiten, "!text-danger")}
                    >
                      Koppla bort
                    </button>
                  </div>
                </div>
                <Webhook url={a.webhook_url} />
                {nyss === a.id ? (
                  <p role="status" className="text-[0.8125rem] leading-5 text-moss">
                    Ansluten. Klistra in webhookadressen hos {KANALNAMN[a.kanal]} och prova sedan
                    anslutningen.
                  </p>
                ) : null}
                {besked[a.id] ? (
                  <p
                    role="status"
                    className={cn("text-[0.8125rem] leading-5", besked[a.id].ok ? "text-moss" : "text-danger")}
                  >
                    {besked[a.id].text}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
