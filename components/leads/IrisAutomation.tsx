"use client";

import { useEffect, useRef, useState } from "react";
import { Vaxel } from "@/components/leads/IrisEskalering";
import { etikett, meta, rubrikPanel } from "@/components/ui";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { leadsAnrop } from "@/lib/leads/suite";
import { LEAD_TYP_ETIKETT, type LeadTyp } from "@/lib/prospekt";
import { cn } from "@/lib/utils";

/**
 * Iris › Inställningar › Automation (Fas 10, Leads Suite F): per typ av lead
 * (Iris, Listor, Import, Inkorg) om utkast skrivs automatiskt och efter hur
 * många dagar första uppföljningen går, om Jev får välja bort kandidater, och
 * envägssynk ut till kundens CRM. Lagras under `agent_configs.settings`
 * (`automation`, `crm_synk`) via `PUT /leads/config`, fältvis. Samma mönster
 * som IrisEskalering: sparas direkt, återställs om sparningen faller.
 */

type PerTyp = { utkast_auto: boolean; uppfoljning_dagar: number };
type Autopilot = { pa: boolean; leads_per_dag: number };
type Automation = { per_typ: Record<LeadTyp, PerTyp>; jev_bortval: boolean; autopilot?: Autopilot };
type CrmSynk = { leverantor: "hubspot" | "pipedrive" | null; integration_id: string | null };
type Config = { automation?: Automation; crm_synk?: CrmSynk | null };
/** `GET /api/integrationer`: `hemligheter` är namn → maskerat värde, aldrig riktiga värden (lagring.offentlig). */
type Integration = { id: string; namn: string; typ: string; aktiv: boolean; hemligheter?: Record<string, string> };

type Lage =
  | { fas: "laddar" }
  | { fas: "fel"; text: string }
  | { fas: "klar"; automation: Automation; crm: CrmSynk };

const TYPER: LeadTyp[] = ["iris", "lista", "import", "inkorg"];

const TYP_NAMN: Record<LeadTyp, Localized> = { ...LEAD_TYP_ETIKETT, lista: { sv: "Listor", en: "Lists" } };

const T = {
  rubrik: { sv: "Automation", en: "Automation" },
  hamtaFel: { sv: "Inställningarna kunde inte hämtas:", en: "The settings could not be loaded:" },
  utanAutomation: { sv: "Backenden svarade utan automation.", en: "The backend replied without automation." },
  utkastAuto: { sv: "Skriv utkast automatiskt", en: "Write drafts automatically" },
  utkastAutoHjalp: {
    sv: "Iris skriver ett utkast så fort researchen är klar. Utkastet väntar i Granskning.",
    en: "Iris writes a draft as soon as the research is done. The draft waits in Review."
  },
  uppfoljning: { sv: "Uppföljning efter dagar", en: "Follow up after days" },
  uppfoljningHjalp: { sv: "0 betyder ingen uppföljning.", en: "0 means no follow-up." },
  jev: { sv: "Låt Jev välja bort automatiskt", en: "Let Jev rule out automatically" },
  jevHjalp: {
    sv: "Jev får fälla kandidater som inte passar innan Iris researchar dem.",
    en: "Jev may drop candidates that do not fit before Iris researches them."
  },
  crm: { sv: "Synk till CRM", en: "Sync to CRM" },
  crmHjalp: {
    sv: "Statusbyten och anteckningar skickas till ert CRM. Integrationen behöver hemligheten api_key.",
    en: "Status changes and notes are sent to your CRM. The integration needs the secret api_key."
  },
  leverantor: { sv: "Leverantör", en: "Provider" },
  ingen: { sv: "Ingen", en: "None" },
  integration: { sv: "Integration", en: "Integration" },
  valjIntegration: { sv: "Välj integration", en: "Choose integration" },
  saknarNyckel: { sv: "saknar api_key", en: "missing api_key" },
  ingaIntegrationer: {
    sv: "Inga integrationer ännu. Lägg till en under Inställningar › Integrationer.",
    en: "No integrations yet. Add one under Settings › Integrations."
  },
  autopilot: { sv: "Autopilot: en körning varje vardag", en: "Autopilot: one run every weekday" },
  autopilotHjalp: {
    sv: "Iris startar en körning med research och utkast varje vardag från 06:00. Vad som skickas utan ert ja styrs av inställningen Hur långt agenterna får gå.",
    en: "Iris starts a run with research and drafts every weekday from 06:00. What is sent without your approval is set by How far the agents may go."
  },
  leadsPerDag: { sv: "Leads per vardag", en: "Leads per weekday" },
  leadsPerDagHjalp: { sv: "1–50. Körningen syns i Körningar.", en: "1–50. The run appears in Runs." },
  sparat: { sv: "Sparat.", en: "Saved." }
} satisfies Record<string, Localized>;

const faltKlass = "focus-ring min-h-11 rounded-input border border-ink/15 bg-paper px-3 text-[16px] text-ink disabled:opacity-60";

export function IrisAutomation() {
  const { text } = useLocale();
  const [lage, setLage] = useState<Lage>({ fas: "laddar" });
  const [dagarText, setDagarText] = useState<Partial<Record<LeadTyp, string>>>({});
  const [antalText, setAntalText] = useState("");
  const [integrationer, setIntegrationer] = useState<Integration[]>([]);
  const [sparar, setSparar] = useState(false);
  const [sparfel, setSparfel] = useState<string | null>(null);
  const [sparad, setSparad] = useState(false);
  const sparadTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function visa(config: Config): boolean {
    const automation = config.automation;
    if (!automation) return false;
    setLage({
      fas: "klar",
      automation,
      crm: config.crm_synk ?? { leverantor: null, integration_id: null }
    });
    setDagarText(Object.fromEntries(TYPER.map((t) => [t, String(automation.per_typ[t]?.uppfoljning_dagar ?? 0)])));
    setAntalText(String(automation.autopilot?.leads_per_dag ?? 10));
    return true;
  }

  useEffect(() => {
    (async () => {
      try {
        const config = await leadsAnrop<Config>("/leads/config");
        if (!visa(config)) setLage({ fas: "fel", text: text(T.utanAutomation) });
      } catch (orsak) {
        setLage({ fas: "fel", text: felmeddelande(orsak) });
      }
      // Integrationslistan är en bekvämlighet: faller den visas bara tomläget.
      leadsAnrop<{ integrationer?: Integration[] }>("/integrationer")
        .then((svar) => setIntegrationer(svar.integrationer ?? []))
        .catch(() => setIntegrationer([]));
    })();
    return () => {
      if (sparadTimer.current) clearTimeout(sparadTimer.current);
    };
    // Bara vid montering; text() byter inte vad som hämtas.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function spara(kropp: { automation?: unknown; crm_synk?: CrmSynk }, optimistiskt: Lage) {
    if (lage.fas !== "klar") return;
    const forra = lage;
    setLage(optimistiskt);
    setSparar(true);
    setSparfel(null);
    try {
      const svar = await leadsAnrop<Config>("/leads/config", { method: "PUT", body: JSON.stringify(kropp) });
      if (!visa(svar)) throw new Error(text(T.utanAutomation));
      setSparad(true);
      if (sparadTimer.current) clearTimeout(sparadTimer.current);
      sparadTimer.current = setTimeout(() => setSparad(false), 2500);
    } catch (orsak) {
      visa({ automation: forra.automation, crm_synk: forra.crm });
      setSparfel(
        text({
          sv: `Ändringen sparades inte: ${felmeddelande(orsak)}`,
          en: `The change was not saved: ${felmeddelande(orsak)}`
        })
      );
    } finally {
      setSparar(false);
    }
  }

  function sparaTyp(typ: LeadTyp, andring: Partial<PerTyp>) {
    if (lage.fas !== "klar") return;
    const per_typ = { ...lage.automation.per_typ, [typ]: { ...lage.automation.per_typ[typ], ...andring } };
    void spara({ automation: { per_typ: { [typ]: andring } } }, { ...lage, automation: { ...lage.automation, per_typ } });
  }

  function sparaDagar(typ: LeadTyp) {
    if (lage.fas !== "klar") return;
    const nu = lage.automation.per_typ[typ]?.uppfoljning_dagar ?? 0;
    const raw = (dagarText[typ] ?? "").trim();
    const varde = Math.min(60, Math.max(0, Math.round(Number(raw))));
    if (raw === "" || Number.isNaN(varde) || varde === nu) {
      setDagarText((d) => ({ ...d, [typ]: String(nu) }));
      return;
    }
    sparaTyp(typ, { uppfoljning_dagar: varde });
  }

  function sparaAutopilot(andring: Partial<Autopilot>) {
    if (lage.fas !== "klar") return;
    const autopilot = { pa: false, leads_per_dag: 10, ...lage.automation.autopilot, ...andring };
    void spara({ automation: { autopilot: andring } }, { ...lage, automation: { ...lage.automation, autopilot } });
  }

  function sparaAntal() {
    if (lage.fas !== "klar") return;
    const nu = lage.automation.autopilot?.leads_per_dag ?? 10;
    const varde = Math.min(50, Math.max(1, Math.round(Number(antalText.trim()))));
    if (antalText.trim() === "" || Number.isNaN(varde) || varde === nu) {
      setAntalText(String(nu));
      return;
    }
    sparaAutopilot({ leads_per_dag: varde });
  }

  function sparaCrm(andring: Partial<CrmSynk>) {
    if (lage.fas !== "klar") return;
    const crm = { ...lage.crm, ...andring };
    if (crm.leverantor === null) crm.integration_id = null;
    void spara({ crm_synk: crm }, { ...lage, crm });
  }

  return (
    <section aria-labelledby="iris-automation">
      <h3 id="iris-automation" className={rubrikPanel}>
        {text(T.rubrik)}
      </h3>

      {lage.fas === "laddar" ? (
        <div className="mt-5 grid gap-px">
          {[0, 1, 2, 3].map((row) => (
            <div key={row} className="h-16 animate-pulse border-t border-ink/15 bg-ink/[0.03]" />
          ))}
        </div>
      ) : lage.fas === "fel" ? (
        <p role="alert" className="mt-5 border-y border-ink/15 py-4 text-[15px] text-danger">
          {text(T.hamtaFel)} {lage.text}
        </p>
      ) : (
        <div className="mt-5 divide-y divide-ink/12 border-y border-ink/15">
          <div className="py-4">
            <Vaxel
              paslagen={Boolean(lage.automation.autopilot?.pa)}
              etikett={text(T.autopilot)}
              beskrivning={text(T.autopilotHjalp)}
              upptagen={sparar}
              onByt={(v) => sparaAutopilot({ pa: v })}
            />
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              <label htmlFor="iris-autopilot-antal" className="text-[0.9375rem] font-medium text-ink">
                {text(T.leadsPerDag)}
              </label>
              <input
                id="iris-autopilot-antal"
                type="number"
                inputMode="numeric"
                min={1}
                max={50}
                value={antalText}
                disabled={sparar}
                aria-describedby="iris-autopilot-antal-hjalp"
                onChange={(e) => setAntalText(e.target.value)}
                onBlur={sparaAntal}
                onKeyDown={(e) => {
                  if (e.key === "Enter") e.currentTarget.blur();
                }}
                className={cn(faltKlass, "w-24")}
              />
              <span id="iris-autopilot-antal-hjalp" className={meta}>
                {text(T.leadsPerDagHjalp)}
              </span>
            </div>
          </div>
          {TYPER.map((typ) => {
            const regel = lage.automation.per_typ[typ] ?? { utkast_auto: false, uppfoljning_dagar: 0 };
            const namn = text(TYP_NAMN[typ]);
            const faltId = `iris-uppfoljning-${typ}`;
            return (
              <div key={typ} className="py-4">
                <p className={rubrikPanel}>{namn}</p>
                <Vaxel
                  paslagen={regel.utkast_auto}
                  etikett={text(T.utkastAuto)}
                  ariaLabel={`${namn}: ${text(T.utkastAuto)}`}
                  beskrivning={text(T.utkastAutoHjalp)}
                  upptagen={sparar}
                  onByt={(v) => sparaTyp(typ, { utkast_auto: v })}
                />
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                  <label htmlFor={faltId} className="text-[0.9375rem] font-medium text-ink">
                    {text(T.uppfoljning)}
                  </label>
                  <input
                    id={faltId}
                    type="number"
                    inputMode="numeric"
                    min={0}
                    max={60}
                    value={dagarText[typ] ?? ""}
                    disabled={sparar}
                    aria-describedby={`${faltId}-hjalp`}
                    onChange={(e) => setDagarText((d) => ({ ...d, [typ]: e.target.value }))}
                    onBlur={() => sparaDagar(typ)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") e.currentTarget.blur();
                    }}
                    className={cn(faltKlass, "w-24")}
                  />
                  <span id={`${faltId}-hjalp`} className={meta}>
                    {text(T.uppfoljningHjalp)}
                  </span>
                </div>
              </div>
            );
          })}

          <Vaxel
            paslagen={lage.automation.jev_bortval}
            etikett={text(T.jev)}
            beskrivning={text(T.jevHjalp)}
            upptagen={sparar}
            onByt={(v) =>
              void spara(
                { automation: { jev_bortval: v } },
                { ...lage, automation: { ...lage.automation, jev_bortval: v } }
              )
            }
          />

          <div className="py-4">
            <p className={rubrikPanel}>{text(T.crm)}</p>
            <p className="mt-0.5 max-w-[60ch] text-[0.875rem] leading-6 text-ink-muted">{text(T.crmHjalp)}</p>
            <div className="mt-3 flex flex-wrap items-end gap-3">
              <label className={cn(etikett, "flex flex-col gap-1")}>
                {text(T.leverantor)}
                <select
                  value={lage.crm.leverantor ?? ""}
                  disabled={sparar}
                  onChange={(e) =>
                    sparaCrm({ leverantor: (e.target.value || null) as CrmSynk["leverantor"] })
                  }
                  className={faltKlass}
                >
                  <option value="">{text(T.ingen)}</option>
                  <option value="hubspot">HubSpot</option>
                  <option value="pipedrive">Pipedrive</option>
                </select>
              </label>
              {lage.crm.leverantor ? (
                integrationer.length ? (
                  <label className={cn(etikett, "flex min-w-[220px] flex-col gap-1")}>
                    {text(T.integration)}
                    <select
                      value={lage.crm.integration_id ?? ""}
                      disabled={sparar}
                      onChange={(e) => sparaCrm({ integration_id: e.target.value || null })}
                      className={faltKlass}
                    >
                      <option value="">{text(T.valjIntegration)}</option>
                      {integrationer.map((i) => (
                        <option key={i.id} value={i.id}>
                          {"api_key" in (i.hemligheter ?? {}) ? i.namn : `${i.namn} (${text(T.saknarNyckel)})`}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <p className={cn(meta, "pb-3")}>{text(T.ingaIntegrationer)}</p>
                )
              ) : null}
            </div>
          </div>
        </div>
      )}

      <p
        role={sparfel ? "alert" : "status"}
        className={cn("mt-2 min-h-5 text-[0.8125rem] leading-5", sparfel ? "text-danger" : "text-ink-subtle")}
      >
        {sparfel ?? (sparad ? text(T.sparat) : null)}
      </p>
    </section>
  );
}
