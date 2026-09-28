import Link from "next/link";
import { Badge, Radlista, Rad, Sidhuvud, Tomt, etikett, meta, rubrikPanel } from "@/components/ui";
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
 * Systemprompt, användarmeddelande, råsvar och reasoning ligger i fällbara
 * sektioner. Fälten är kapade till 8 000 tecken vardera redan vid skrivningen
 * (step_runner.TRACE_FIELD_MAX_CHARS); utfällda direkt hade en enda körning
 * ändå varit femtio skärmar text, och det man letar efter är oftast ETT steg.
 *
 * Rubriken är "Körning" och inte agent_type: koden är en maskin-id och står i
 * mono i metaraden under. Ingen tillbakalänk överst; railens Körningar leder dit.
 */

function Field({ label, value }: Readonly<{ label: string; value?: string | null }>) {
  if (!value) return null;
  return (
    <details className="mt-3 border-t border-ink/15 pt-3">
      <summary className={cn(etikett, "focus-ring cursor-pointer rounded-input hover:text-ink")}>
        {label}
      </summary>
      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words font-mono text-[0.8125rem] leading-6 text-ink-muted">
        {value}
      </pre>
    </details>
  );
}

function Step({ step, index }: Readonly<{ step: StepLogEntry; index: number }>) {
  return (
    <Rad className="min-w-0">
      <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <h2 className={cn(rubrikPanel, "min-w-0 break-words")}>
          Steg {index + 1}
          <span className="ml-3 font-mono text-[0.8125rem] font-normal text-ink-muted">
            {step.skill}
          </span>
        </h2>
        {step.escalated ? <Badge tone="warn">Eskalerade</Badge> : null}
      </div>

      <dl className="mt-3 flex flex-wrap gap-x-8 gap-y-2 text-[0.8125rem]">
        {[
          ["Försök", String(step.attempts)],
          ["Tokens", `${step.tokens_in} / ${step.tokens_out}`],
          ["Reasoning", String(step.reasoning_tokens)],
          ["Latens", `${step.latency_ms} ms`],
          ["Thinking", step.thinking_mode],
          ["Overlay", step.overlay ?? "–"]
        ].map(([label, value]) => (
          <div key={label}>
            <dt className={cn(etikett, "inline")}>{label}</dt>{" "}
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
          <span className={etikett}>Grundat i</span> {step.sources_used.join(" · ")}
        </p>
      ) : null}

      <Field label="Systemprompt" value={step.system_prompt} />
      <Field label="Användarmeddelande" value={step.user_message} />
      <Field label="Råsvar" value={step.raw_output} />
      <Field label="Reasoning" value={step.reasoning_content} />
    </Rad>
  );
}

export default async function Page({ params }: Readonly<{ params: Promise<{ id: string }> }>) {
  const { id } = await params;
  const { data: run, error } = unwrap(await getRun(id));

  if (error || !run) {
    return (
      <div>
        <Sidhuvud title="Körning" />
        <p role="alert" className="mt-8 max-w-[70ch] break-words text-[15px] text-danger">
          {error ?? "Körningen finns inte."}
        </p>
        <Link
          href="/admin/korningar"
          className="focus-ring mt-6 inline-block underline underline-offset-4 hover:text-ochre"
        >
          Tillbaka till körningarna
        </Link>
      </div>
    );
  }

  const steps = run.step_log ?? [];

  return (
    <div>
      <Sidhuvud title="Körning" />
      <p className={cn(meta, "num mt-2 break-words")}>
        <span className="font-mono">{run.agent_type}</span> · {run.tenant_slug ?? "–"} ·{" "}
        {run.created_at.slice(0, 19).replace("T", " ")} ·{" "}
        <span className="font-mono">{run.pack_version}</span>
      </p>

      {/* Fas A (onboarding) kör Runner.run och skriver ingen step_log: en känd
          lucka i instrumenteringen, inte en körning utan steg. */}
      {steps.length === 0 ? (
        <div className="mt-8">
          <Tomt>Körningen har ingen spårning. Onboardingkörningar (fas A) loggar inga steg.</Tomt>
        </div>
      ) : (
        <Radlista ariaLabel="Steg" className="mt-8">
          {steps.map((step, index) => (
            <Step key={`${step.skill}-${index}`} step={step} index={index} />
          ))}
        </Radlista>
      )}
    </div>
  );
}
