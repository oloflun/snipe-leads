"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Badge, Sektion, Tomt, etikett, faltTatt, meta, radLank } from "@/components/ui";
import { Flodeskarta, type Utfall } from "@/components/admin/insyn/Flodeskarta";
import { KbProv } from "@/components/admin/insyn/KbProv";
import { Kallmatris } from "@/components/admin/insyn/Kallmatris";
import { Lagerstapel } from "@/components/admin/insyn/Lagerstapel";
import {
  hamtaKedja,
  hamtaKorning,
  type Kedja,
  type KedjeNod,
  type KorningSteg
} from "@/lib/actions/insyn";
import { ADMIN, a, antal, tidpunkt } from "@/lib/admin/sprak";
import type { Insyn, InsynGrind, InsynSteg, StepLogEntry } from "@/lib/data/admin";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Admin › Kund › Underlag och flöde (Fas 7). Fyra delar på samma yta:
 * flödeskartan, lagerstapeln för valt steg, källmatrisen och körningsväljaren
 * som färgar kartan. Allt kommer ur backendens insyn, som bygger ur samma
 * funktioner som bygger prompten — komponenten räknar ingenting själv utom
 * färgningen av en vald körning.
 */

export type KorningVal = {
  id: string;
  agent_type: string;
  created_at: string;
  prospect_id: string | null;
  etikett: string;
};

function skalText(skal: KedjeNod["skal"], locale: "sv" | "en"): string | null {
  if (!skal) return null;
  const delar: string[] = [];
  if (typeof skal.kod === "string") {
    // Ett skäl backenden lagt till efter den här texten visas med sin kod i
    // stället för att fälla vyn.
    const nyckel = `skal_${skal.kod}`;
    delar.push(
      ADMIN[nyckel] ? a(nyckel, locale).replace("{n}", antal(Number(skal.tecken ?? 0), locale)) : skal.kod
    );
  }
  if (typeof skal.text === "string" && skal.text) delar.push(skal.text);
  return delar.join(": ") || null;
}

function Json({ varde }: Readonly<{ varde: unknown }>) {
  return (
    <pre className="thin-scrollbar mt-2 max-h-[20rem] overflow-auto whitespace-pre-wrap break-words font-mono text-[0.8125rem] leading-6 text-ink-muted">
      {typeof varde === "string" ? varde : JSON.stringify(varde, null, 2)}
    </pre>
  );
}

function Falt({ n, children }: Readonly<{ n: string; children: React.ReactNode }>) {
  const { locale } = useLocale();
  return (
    <div className="min-w-0">
      <dt className={etikett}>{a(n, locale)}</dt>
      <dd className="mt-0.5 min-w-0 break-words text-[0.875rem] text-ink">{children}</dd>
    </div>
  );
}

function StegInfo({ steg }: Readonly<{ steg: InsynSteg }>) {
  const { locale } = useLocale();
  return (
    <dl className="grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
      <Falt n="insynSkill">
        <span className="font-mono">{steg.skill}</span>
        {" · "}
        {a(steg.laddning === "hel" ? "insynHel" : "insynSkopa", locale)}
        {steg.skopa.length ? (
          <span className="block text-ink-muted">{steg.skopa.join(" · ")}</span>
        ) : null}
      </Falt>
      <Falt n="insynModell">
        <span className="font-mono">{steg.modell}</span>
        {steg.modell_falt ? <span className="block font-mono text-ink-muted">{steg.modell_falt}</span> : null}
        <span className="block text-ink-muted">
          {a("insynTemperatur", locale)} {steg.temperatur} · thinking {steg.thinking}
        </span>
      </Falt>
      {steg.motivering ? (
        <div className="sm:col-span-2">
          <Falt n="insynMotivering">{steg.motivering}</Falt>
        </div>
      ) : null}
      {steg.extra_skills.length ? (
        <Falt n="insynExtra">
          {steg.extra_skills.map((x) => (
            <span key={x.skill} className="block">
              <span className="font-mono">{x.skill}</span>
              {x.skopa.length ? <span className="text-ink-muted"> · {x.skopa.join(" · ")}</span> : null}
            </span>
          ))}
        </Falt>
      ) : null}
      {steg.overlays.length ? (
        <Falt n="insynOverlays">
          <span className="font-mono">{steg.overlays.join(" + ")}</span>
        </Falt>
      ) : null}
      <Falt n="insynKraver">
        <span className="font-mono">{steg.kraver.join(", ")}</span>
      </Falt>
      {steg.villkor ? (
        <Falt n="insynVillkor">
          {steg.villkor_text ? steg.villkor_text[locale] : <span className="font-mono">{steg.villkor}</span>}
        </Falt>
      ) : null}
      {steg.radandringar.length ? (
        <div className="sm:col-span-2">
          <Falt n="insynRadandringar">
            <ul className="divide-y divide-ink/10">
              {steg.radandringar.map((r, i) => (
                <li key={i} className="py-2">
                  <span className="block whitespace-pre-wrap font-mono text-[0.8125rem] text-ink-muted line-through">
                    {r.gammal}
                  </span>
                  <span className="block text-[0.8125rem] text-ink">
                    {r.ny ? (
                      <>
                        {a("insynErsatts", locale)}: <span className="whitespace-pre-wrap font-mono">{r.ny}</span>
                      </>
                    ) : (
                      a("insynStryks", locale)
                    )}
                  </span>
                  <span className={cn(meta, "block")}>
                    {a("insynSkal", locale)}: {r.skal}
                  </span>
                </li>
              ))}
            </ul>
          </Falt>
        </div>
      ) : null}
    </dl>
  );
}

export function Insynsvy({
  tenantId,
  insyn,
  korningar
}: Readonly<{ tenantId: string; insyn: Insyn; korningar: KorningVal[] }>) {
  const { locale } = useLocale();
  const allaNoder = useMemo(() => insyn.banor.flatMap((b) => b.noder), [insyn]);
  const forstaSteg = allaNoder.find((n) => n.typ === "steg")?.id ?? null;
  const [vald, setVald] = useState<string | null>(forstaSteg);
  const [markerad, setMarkerad] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [valdKorning, setValdKorning] = useState("");
  const [kedja, setKedja] = useState<Kedja | null>(null);
  const [korning, setKorning] = useState<(KorningSteg & { agent_type: string }) | null>(null);
  const [laddar, setLaddar] = useState(false);
  const [fel, setFel] = useState<string | null>(null);

  const synliga = korningar.filter((k) => !filter.trim() || k.etikett.toLowerCase().includes(filter.trim().toLowerCase()));

  async function valjKorning(id: string) {
    setValdKorning(id);
    setKedja(null);
    setKorning(null);
    setFel(null);
    const k = korningar.find((x) => x.id === id);
    if (!k) return;
    setLaddar(true);
    // Ett bolags körning ritas som hela kedjan (grindar och steg); övriga
    // körningar färgar stegen i sin bana efter vad spåret innehåller.
    if (k.prospect_id && insyn.agent === "leads" && ["leads_research", "leads_outreach"].includes(k.agent_type)) {
      const svar = await hamtaKedja(tenantId, k.prospect_id);
      if (svar.kedja) setKedja(svar.kedja);
      else setFel(svar.error ?? a("insynFel", locale));
    } else {
      const svar = await hamtaKorning(id);
      if (svar.korning) setKorning({ ...svar.korning, agent_type: k.agent_type });
      else setFel(svar.error ?? a("insynFel", locale));
    }
    setLaddar(false);
  }

  const kedjeNoder = useMemo(() => new Map((kedja?.noder ?? []).map((n) => [n.id, n])), [kedja]);

  const utfall = useMemo(() => {
    const ut: Record<string, Utfall> = {};
    for (const n of kedja?.noder ?? []) ut[n.id] = n.utfall;
    if (korning) {
      const korda = new Set(korning.step_log.filter((p) => p.skill).map((p) => p.skill));
      for (const n of allaNoder) {
        if (n.typ === "steg" && n.agent_type === korning.agent_type) {
          ut[n.id] = korda.has(n.skill) ? "kord" : "hoppad";
        }
      }
    }
    return ut;
  }, [kedja, korning, allaNoder]);

  const valdNod = allaNoder.find((n) => n.id === vald) ?? null;
  const kedjeNod = vald ? kedjeNoder.get(vald) : undefined;
  // Stegets post i den valda körningen: ur kedjan, eller ur körningens spår.
  const korningsPost: StepLogEntry | null =
    (kedjeNod?.post as StepLogEntry | undefined) ??
    (korning && valdNod?.typ === "steg" && valdNod.agent_type === korning.agent_type
      ? korning.step_log.find((p) => p.skill === valdNod.skill) ?? null
      : null);
  const korningsTexter = kedja?.texter ?? korning?.lagertexter ?? {};

  function valjFranMatris(steg: string, hash: string | null) {
    setVald(steg);
    setMarkerad(hash);
  }

  return (
    <div>
      <Sektion title={a("insynKarta", locale)}>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex min-w-0 flex-col gap-1">
            <span className={etikett}>{a("insynValjKorning", locale)}</span>
            <select
              value={valdKorning}
              onChange={(e) => (e.target.value ? valjKorning(e.target.value) : (setValdKorning(""), setKedja(null), setKorning(null)))}
              className={cn(faltTatt, "max-w-full sm:w-[26rem]")}
            >
              <option value="">{a("insynIngenVald", locale)}</option>
              {synliga.map((k) => (
                <option key={k.id} value={k.id}>
                  {tidpunkt(k.created_at, locale)} · {k.agent_type} · {k.etikett.slice(0, 60)}
                </option>
              ))}
            </select>
          </label>
          <label className="flex min-w-0 flex-col gap-1">
            <span className={etikett}>{a("insynFiltrera", locale)}</span>
            <input value={filter} onChange={(e) => setFilter(e.target.value)} className={cn(faltTatt, "w-56 max-w-full")} />
          </label>
          {laddar ? <span className={meta}>{a("insynLaddar", locale)}</span> : null}
        </div>
        {fel ? (
          <p role="alert" className="mt-3 text-[0.875rem] text-danger">
            {fel}
          </p>
        ) : null}
        {kedja?.stannade ? (
          <p className="mt-3 max-w-[70ch] text-[0.9375rem] text-ink">
            <span className="font-medium">{a("insynStannade", locale)}</span>{" "}
            <span className="font-mono">{kedja.stannade.nod}</span>
            {skalText(kedja.stannade.skal, locale) ? `: ${skalText(kedja.stannade.skal, locale)}` : ""}
          </p>
        ) : null}
        <div className="mt-4">
          <Flodeskarta banor={insyn.banor} vald={vald} utfall={utfall} onValj={(id) => (setVald(id), setMarkerad(null))} />
        </div>
      </Sektion>

      <Sektion title={a("insynStapel", locale)}>
        {!valdNod ? (
          <Tomt>{a("insynValjSteg", locale)}</Tomt>
        ) : valdNod.typ === "grind" ? (
          <GrindDetalj nod={valdNod} kedjeNod={kedjeNod} />
        ) : (
          <div className="min-w-0">
            <p className="font-mono text-[0.8125rem] text-ink-muted">
              {valdNod.playbook} · {valdNod.id}
            </p>
            <div className="mt-3">
              <StegInfo steg={valdNod} />
            </div>
            {kedjeNod || korningsPost ? (
              <div className="mt-6 rounded-input border border-ink/12 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className={etikett}>
                    {a("insynKorning", locale)}
                    {kedjeNod ? (
                      <span className="ml-2">
                        <Badge tone={kedjeNod.utfall === "kord" ? "good" : kedjeNod.utfall === "stoppad" ? "danger" : "neutral"}>
                          {a(`utfall_${kedjeNod.utfall}`, locale)}
                        </Badge>
                      </span>
                    ) : null}
                  </p>
                  {kedjeNod?.run_id || valdKorning ? (
                    <Link href={`/admin/korningar/${kedjeNod?.run_id ?? valdKorning}`} className={radLank}>
                      {a("insynOppnaSpar", locale)}
                    </Link>
                  ) : null}
                </div>
                {skalText(kedjeNod?.skal ?? null, locale) ? (
                  <p
                    className={cn(
                      "mt-2 text-[0.9375rem]",
                      kedjeNod?.utfall === "stoppad" || kedjeNod?.utfall === "falld" ? "text-danger" : "text-ink-muted"
                    )}
                  >
                    {skalText(kedjeNod?.skal ?? null, locale)}
                  </p>
                ) : null}
                {kedjeNod?.sidoanrop?.length ? (
                  <div className="mt-4">
                    <p className={etikett}>{a("insynSidoanrop", locale)}</p>
                    <ul className="mt-1 divide-y divide-ink/10">
                      {kedjeNod.sidoanrop.map((p, i) => (
                        <li key={i} className="py-2 text-[0.8125rem]">
                          <span className="font-mono text-ink">{String(p.anrop ?? p.step)}</span>
                          {p.model ? <span className={cn(meta, "ml-2 font-mono")}>{p.model}</span> : null}
                          <details className="mt-1">
                            <summary className={cn(etikett, "focus-ring cursor-pointer rounded-input hover:text-ink")}>
                              {a("insynIndata", locale)} / {a("insynUtdata", locale)}
                            </summary>
                            <Json varde={p.user_message ?? ""} />
                            <Json varde={p.raw_output ?? ""} />
                          </details>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {korningsPost?.lager?.length ? (
                  <div className="mt-4">
                    <Lagerstapel
                      lager={korningsPost.lager}
                      texter={korningsTexter}
                      anvandartext={korningsPost.user_message}
                      skilldelar={korningsPost.skilldelar}
                      markerad={markerad}
                    />
                  </div>
                ) : null}
                {korningsPost?.raw_output ? (
                  <details className="mt-4">
                    <summary className={cn(etikett, "focus-ring cursor-pointer rounded-input hover:text-ink")}>
                      {a("insynUtdata", locale)}
                    </summary>
                    <Json varde={korningsPost.raw_output} />
                  </details>
                ) : null}
              </div>
            ) : (
              <div className="mt-6">
                {valdNod.anvandare ? (
                  <p className={cn(meta, "mb-2")}>
                    {a("insynFranKorning", locale)}: {tidpunkt(valdNod.anvandare.created_at, locale)}
                    {valdNod.anvandare.kapat ? ` · ${a("insynKapatSpar", locale)}` : ""}
                  </p>
                ) : null}
                <Lagerstapel
                  lager={[...valdNod.lager, ...(valdNod.anvandare?.lager ?? [])]}
                  texter={insyn.texter}
                  skilldelar={valdNod.skilldelar}
                  markerad={markerad}
                />
                {!valdNod.anvandare ? <p className={cn(meta, "mt-3")}>{a("insynIngenKorning", locale)}</p> : null}
              </div>
            )}
          </div>
        )}
      </Sektion>

      <Sektion title={a("insynMatris", locale)}>
        <Kallmatris matris={insyn.matris} onValj={valjFranMatris} />
      </Sektion>

      {kedja?.skills.length ? (
        <Sektion title={a("insynSkillsIKorningen", locale)}>
          <ul className="divide-y divide-ink/12 border-y border-ink/15">
            {kedja.skills.map((s) => (
              <li key={`${s.steg}-${s.skill}`} className="py-3">
                <p className="text-[0.9375rem] font-medium text-ink">
                  <span className="font-mono">{s.steg}</span> · <span className="font-mono">{s.skill}</span>
                </p>
                <ul className="mt-1.5 space-y-1">
                  {s.delar.map((d, i) => (
                    <li key={i} className="flex min-w-0 flex-wrap items-center gap-x-3 text-[0.8125rem]">
                      <span className="font-mono text-ink">{d.skill}</span>
                      <span className="text-ink-muted">{d.del ?? d.fil}</span>
                      <span className={cn(meta, "num")}>{antal(d.tecken ?? 0, locale)}</span>
                      <span className={cn(meta, "font-mono")}>{(d.sha256 ?? "").slice(0, 12)}</span>
                      <Badge tone={d.orord ? "good" : "danger"}>{a(d.orord ? "insynOrord" : "insynAndrad", locale)}</Badge>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </Sektion>
      ) : null}

      {insyn.agent === "support" ? (
        <Sektion title={a("insynKbRubrik", locale)}>
          <KbProv tenantId={tenantId} />
        </Sektion>
      ) : null}
    </div>
  );
}

function GrindDetalj({ nod, kedjeNod }: Readonly<{ nod: InsynGrind; kedjeNod?: KedjeNod }>) {
  const { locale } = useLocale();
  return (
    <div className="min-w-0">
      <p className="text-[0.9375rem] font-medium text-ink">
        {a("kodgrind", locale)}: {a(`grind_${nod.grind}`, locale)}
      </p>
      <p className="mt-1 break-all font-mono text-[0.8125rem] text-ink-muted">{nod.kod}</p>
      {kedjeNod ? (
        <div className="mt-4 rounded-input border border-ink/12 p-4">
          <p className={etikett}>
            {a("insynKorning", locale)}{" "}
            <Badge tone={kedjeNod.utfall === "slappt" ? "good" : kedjeNod.utfall === "falld" ? "danger" : "neutral"}>
              {a(`utfall_${kedjeNod.utfall}`, locale)}
            </Badge>
          </p>
          {skalText(kedjeNod.skal, locale) ? (
            <p className="mt-2 text-[0.9375rem] text-danger">{skalText(kedjeNod.skal, locale)}</p>
          ) : null}
          {kedjeNod.kallor?.length ? (
            <div className="mt-3">
              <p className={etikett}>{a("insynKallor", locale)}</p>
              <ul className="mt-1 space-y-0.5">
                {kedjeNod.kallor.map((k) => (
                  <li key={k} className="break-all font-mono text-[0.8125rem] text-ink-muted">
                    {k}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {kedjeNod.utdata ? (
            <details className="mt-3">
              <summary className={cn(etikett, "focus-ring cursor-pointer rounded-input hover:text-ink")}>
                {a("insynUtdata", locale)}
              </summary>
              <Json varde={kedjeNod.utdata} />
            </details>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
