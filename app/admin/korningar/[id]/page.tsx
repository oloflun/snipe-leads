import Link from "next/link";
import { AdminRadlista, AdminText } from "@/components/admin/AdminText";
import { Lagerstapel } from "@/components/admin/insyn/Lagerstapel";
import { Badge, Rad, Sidhuvud, Tomt, etikett, meta, rubrikPanel } from "@/components/ui";
import { getRun, unwrap, type StepLogEntry } from "@/lib/data/admin";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

// Backenden ligger på Renders gratisnivå och tar upp till ~35 s att vakna.
// Utan detta dödar Vercel renderingen mitt i uppvakningen. Se app/admin/page.tsx.
export const maxDuration = 60;

/**
 * Spårvyn. Den enda platsen i produkten med genuint hög täthet, och den enda
 * som svarar på "varför skrev den så här?".
 *
 * Sedan Fas 7 (2026-10-07) visar ett steg sin lagerstapel: systemlagren i
 * verklig ordning med texten ur prompt_lager, och hela användarmeddelandet,
 * klippt vid sina rubriker. Ingenting är kapat. Äldre körningar har fyra
 * fällbara råfält, kapade till 8 000 tecken vid skrivningen; de visas som
 * förut med en rad som säger det. Kodgrindarnas utslag och anropen utanför
 * stegmotorn (nyckeln "step") står som egna poster mellan stegen.
 *
 * Rubriken är "Körning" och inte agent_type: koden är en maskin-id och står i
 * mono i metaraden under. Ingen tillbakalänk överst; railens Körningar leder dit.
 */

function Field({ label, value }: Readonly<{ label: string; value?: string | null }>) {
  if (!value) return null;
  return (
    <details className="mt-3 border-t border-ink/15 pt-3">
      <summary className={cn(etikett, "focus-ring cursor-pointer rounded-input hover:text-ink")}>
        <AdminText n={label} />
      </summary>
      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words font-mono text-[0.8125rem] leading-6 text-ink-muted">
        {value}
      </pre>
    </details>
  );
}

function Step({
  step,
  index,
  lagertexter
}: Readonly<{ step: StepLogEntry; index: number; lagertexter: Record<string, string> }>) {
  return (
    <Rad className="min-w-0">
      <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <h2 className={cn(rubrikPanel, "min-w-0 break-words")}>
          <AdminText n="steg" /> {index + 1}
          <span className="ml-3 font-mono text-[0.8125rem] font-normal text-ink-muted">
            {step.skill}
          </span>
        </h2>
        {step.escalated ? (
          <Badge tone="warn">
            <AdminText n="eskalerade" />
          </Badge>
        ) : null}
      </div>

      <dl className="mt-3 flex flex-wrap gap-x-8 gap-y-2 text-[0.8125rem]">
        {[
          ["forsok", String(step.attempts)],
          ["kolTokens", `${step.tokens_in} / ${step.tokens_out}`],
          ["reasoning", String(step.reasoning_tokens)],
          ["kolLatens", `${step.latency_ms} ms`],
          ["thinking", step.thinking_mode],
          ["overlay", step.overlay ?? "–"]
        ].map(([label, value]) => (
          <div key={label}>
            <dt className={cn(etikett, "inline")}>
              <AdminText n={label} />
            </dt>{" "}
            <dd className="num inline text-ink">{value}</dd>
          </div>
        ))}
      </dl>

      {/* --warning, inte --ochre: ochre mäter 2.17:1 mot papper och får
          aldrig bära text i brödstorlek (DESIGN.md). */}
      {step.escalation_reason ? (
        <p className="mt-3 max-w-[70ch] text-[0.9375rem] leading-7 text-warning">
          {step.escalation_reason}
        </p>
      ) : null}

      {step.sources_used?.length ? (
        <p className="mt-3 max-w-[70ch] text-[0.9375rem] leading-7">
          <span className={etikett}>
            <AdminText n="grundatI" />
          </span>{" "}
          {step.sources_used.join(" · ")}
        </p>
      ) : null}

      {/* Spår av version 2 (Fas 7): prompten lager för lager, hela texten.
          Äldre spår har de fyra kapade fälten och visas som förut, med en
          rad som säger att de är kapade. */}
      {step.spar === 2 && step.lager?.length ? (
        <div className="mt-4">
          <Lagerstapel
            lager={step.lager}
            texter={lagertexter}
            anvandartext={step.user_message}
            skilldelar={step.skilldelar}
          />
        </div>
      ) : (
        <>
          {step.system_prompt || step.user_message ? (
            <p className={cn(meta, "mt-3 max-w-[70ch]")}>
              <AdminText n="sparKapat" />
            </p>
          ) : null}
          <Field label="systemprompt" value={step.system_prompt} />
          <Field label="anvandarmeddelande" value={step.user_message} />
        </>
      )}
      <Field label="rasvar" value={step.raw_output} />
      <Field label="reasoning" value={step.reasoning_content} />
    </Rad>
  );
}

/** Kodgrind eller anrop utanför stegmotorn (nyckeln "step"): namnet och datan. */
function Post({ post }: Readonly<{ post: StepLogEntry }>) {
  const { step: namn, ...data } = post;
  const grind = String(namn ?? "").startsWith("grind:");
  return (
    <Rad className="min-w-0">
      <h2 className={cn(rubrikPanel, "min-w-0 break-words")}>
        <AdminText n={grind ? "stegGrind" : "stegAnrop"} />
        <span className="ml-3 font-mono text-[0.8125rem] font-normal text-ink-muted">{String(namn)}</span>
      </h2>
      <pre className="mt-2 max-h-[24rem] overflow-auto whitespace-pre-wrap break-words font-mono text-[0.8125rem] leading-6 text-ink-muted">
        {JSON.stringify(data, null, 2)}
      </pre>
    </Rad>
  );
}

export default async function Page({ params }: Readonly<{ params: Promise<{ id: string }> }>) {
  const { id } = await params;
  const { data: run, error } = unwrap(await getRun(id));

  if (error || !run) {
    return (
      <div>
        <Sidhuvud title={<AdminText n="korningRubrik" />} />
        <p role="alert" className="mt-8 max-w-[70ch] break-words text-[15px] text-danger">
          {error ?? <AdminText n="korningSaknas" />}
        </p>
        <Link
          href="/admin/korningar"
          className="focus-ring mt-6 inline-block underline underline-offset-4 hover:text-ochre"
        >
          <AdminText n="tillbakaKorningar" />
        </Link>
      </div>
    );
  }

  const steps = run.step_log ?? [];

  return (
    <div>
      <Sidhuvud title={<AdminText n="korningRubrik" />} />
      <p className={cn(meta, "num mt-2 break-words")}>
        <span className="font-mono">{run.agent_type}</span> · {run.tenant_slug ?? "–"} ·{" "}
        {run.created_at.slice(0, 19).replace("T", " ")} ·{" "}
        <span className="font-mono">{run.pack_version}</span>
      </p>

      {/* Fas A (onboarding) kör Runner.run och skriver ingen step_log: en känd
          lucka i instrumenteringen, inte en körning utan steg. */}
      {steps.length === 0 ? (
        <div className="mt-8">
          <Tomt>
            <AdminText n="ingenSparning" />
          </Tomt>
        </div>
      ) : (
        <AdminRadlista aria="stegLista" className="mt-8">
          {steps.map((step, index) => (
            step.skill ? (
              <Step key={`${step.skill}-${index}`} step={step} index={index} lagertexter={run.lagertexter ?? {}} />
            ) : (
              <Post key={`${String(step.step)}-${index}`} post={step} />
            )
          ))}
        </AdminRadlista>
      )}
    </div>
  );
}
