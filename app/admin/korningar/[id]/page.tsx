import Link from "next/link";
import { getRun, unwrap, type StepLogEntry } from "@/lib/data/admin";

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
 */

function Field({ label, value }: Readonly<{ label: string; value?: string | null }>) {
  if (!value) return null;
  return (
    <details className="mt-3 border-t border-ink/15 pt-3">
      <summary className="kicker cursor-pointer text-mineral hover:text-ochre">{label}</summary>
      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words text-[13px] leading-6 text-ink/75">
        {value}
      </pre>
    </details>
  );
}

function Step({ step, index }: Readonly<{ step: StepLogEntry; index: number }>) {
  return (
    <li className="min-w-0 border-t border-ink/15 py-6">
      <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <h2 className="min-w-0 break-words text-[17px]">
          <span className="kicker mr-3 text-mineral">{index + 1}</span>
          {step.skill}
        </h2>
        {/* --warning, inte --ochre: ochre mäter 2.17:1 mot papper och får
            aldrig bära text i brödstorlek (DESIGN.md). */}
        {step.escalated ? <span className="kicker shrink-0 text-warning">eskalerade</span> : null}
      </div>

      <dl className="mt-3 flex flex-wrap gap-x-8 gap-y-2 text-[14px] text-mineral">
        {[
          ["Försök", String(step.attempts)],
          ["Tokens", `${step.tokens_in} / ${step.tokens_out}`],
          ["Reasoning", String(step.reasoning_tokens)],
          ["Latens", `${step.latency_ms} ms`],
          ["Thinking", step.thinking_mode],
          ["Overlay", step.overlay ?? "—"]
        ].map(([label, value]) => (
          <div key={label}>
            <dt className="kicker inline">{label}</dt>{" "}
            <dd className="inline tabular-nums text-ink">{value}</dd>
          </div>
        ))}
      </dl>

      {step.escalation_reason ? (
        <p className="mt-3 max-w-[70ch] text-[14px] leading-6 text-warning">
          {step.escalation_reason}
        </p>
      ) : null}

      {step.sources_used?.length ? (
        <p className="mt-3 max-w-[70ch] text-[14px] leading-6">
          <span className="kicker text-mineral">Grundat i</span> {step.sources_used.join(" · ")}
        </p>
      ) : null}

      <Field label="Systemprompt" value={step.system_prompt} />
      <Field label="Användarmeddelande" value={step.user_message} />
      <Field label="Råsvar" value={step.raw_output} />
      <Field label="Reasoning" value={step.reasoning_content} />
    </li>
  );
}

export default async function Page({ params }: Readonly<{ params: Promise<{ id: string }> }>) {
  const { id } = await params;
  const { data: run, error } = unwrap(await getRun(id));

  if (error || !run) {
    return (
      <div>
        <h1 className="font-display text-4xl italic-disp tighten">Körningen</h1>
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[15px] text-danger">
          {error ?? "Körningen finns inte."}
        </p>
        <Link
          href="/admin/korningar"
          className="mt-6 inline-block underline underline-offset-4 hover:text-ochre"
        >
          Tillbaka till körningarna
        </Link>
      </div>
    );
  }

  const steps = run.step_log ?? [];

  return (
    <div>
      <Link href="/admin/korningar" className="kicker text-mineral hover:text-ochre">
        ← Körningar
      </Link>

      <h1 className="mt-4 font-display text-4xl italic-disp tighten">{run.agent_type}</h1>
      <p className="mt-3 text-[15px] tabular-nums text-mineral">
        {run.tenant_slug ?? "—"} · {run.created_at.slice(0, 19).replace("T", " ")} ·{" "}
        {run.pack_version}
      </p>

      {steps.length === 0 ? (
        <p className="mt-8 max-w-[70ch] border-t border-ink/15 pt-5 text-[15px] leading-7 text-mineral">
          Ingen spårning för den här körningen. Fas A (onboarding) kör Runner.run och skriver
          ingen step_log — det är en känd lucka i instrumenteringen, inte en körning utan steg.
        </p>
      ) : (
        <ol className="mt-8">
          {steps.map((step, index) => (
            <Step key={`${step.skill}-${index}`} step={step} index={index} />
          ))}
        </ol>
      )}
    </div>
  );
}
