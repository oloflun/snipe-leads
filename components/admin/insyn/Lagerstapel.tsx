"use client";

import { useEffect, useRef, useState } from "react";

import { Badge, etikett, meta, radLank } from "@/components/ui";
import { hamtaSkillfil, type Skillfil } from "@/lib/actions/insyn";
import { a, antal } from "@/lib/admin/sprak";
import type { LagerPost, SkillDel } from "@/lib/data/admin";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Lagerstapeln (Fas 7): prompten exakt som den byggs, lager för lager i verklig
 * ordning. Systemlagren kommer ur step_runner.bygg_systemprompt (samma lista
 * som skickas till modellen), användarlagren ur användarmeddelandet som det
 * faktiskt skickades, klippt vid sina rubriker.
 *
 * Stapeln överst är proportionell mot tecken: det man ser först är var
 * prompten väger, och ett lager som borde vara tjockt men är en strimma är
 * ofta felet. Listan under bär källa, vem som får ändra, tecken och hash.
 *
 * Användarlagrens text slås inte upp per hash: lagren är sammanhängande bitar
 * av `anvandartext`, så de skärs ut med sina teckenantal. Saknas texten (spår
 * utan verbose) visas bara mätvärdena.
 */

/** Färg per systemlager. Tokens, inga opacitetssteg på text (DESIGN.md § Theme). */
const FARG: Record<string, string> = {
  gemensamt: "bg-ink",
  agent: "bg-seal",
  skill: "bg-mineral",
  overlay: "bg-ochre",
  kund: "bg-moss",
  kontrakt: "bg-danger"
};

function kortHash(hash: string) {
  return hash.slice(0, 12);
}

function Stapel({ lager, aria }: Readonly<{ lager: LagerPost[]; aria: string }>) {
  const summa = lager.reduce((s, l) => s + l.tecken, 0) || 1;
  return (
    <div role="img" aria-label={aria} className="flex h-3 w-full overflow-hidden rounded-[3px] border border-ink/15 bg-paper">
      {lager.map((l, i) => (
        <span
          key={`${l.hash}-${i}`}
          className={cn(
            "h-full min-w-[2px] border-r border-paper last:border-r-0",
            l.position === "system" ? FARG[l.etikett] ?? "bg-ink-subtle" : i % 2 ? "bg-paper2" : "bg-ink/10"
          )}
          style={{ width: `${(l.tecken / summa) * 100}%` }}
        />
      ))}
    </div>
  );
}

function SkillFiler({ delar }: Readonly<{ delar: SkillDel[] }>) {
  const { locale } = useLocale();
  const [oppen, setOppen] = useState<Skillfil | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [laddar, setLaddar] = useState<string | null>(null);

  async function las(skill: string, fil: string) {
    setLaddar(`${skill}/${fil}`);
    setFel(null);
    const svar = await hamtaSkillfil(skill, fil);
    setLaddar(null);
    if (svar.fil) setOppen(svar.fil);
    else setFel(svar.error ?? a("insynFel", locale));
  }

  return (
    <div className="mt-3 border-t border-ink/12 pt-3">
      <p className={etikett}>{a("insynFiler", locale)}</p>
      <ul className="mt-2 divide-y divide-ink/10">
        {delar.map((d, i) => (
          <li key={`${d.skill}-${d.del}-${i}`} className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 py-1.5 text-[0.8125rem]">
            <span className="min-w-0 break-all font-mono text-ink">{d.skill}</span>
            <span className="min-w-0 break-words text-ink-muted">{d.del ?? d.fil}</span>
            {d.fel ? (
              <Badge tone="danger">{d.fel}</Badge>
            ) : (
              <>
                <span className={cn(meta, "num")}>{antal(d.tecken ?? 0, locale)}</span>
                <span className={cn(meta, "font-mono")}>{(d.sha256 ?? "").slice(0, 12)}</span>
                <Badge tone={d.orord ? "good" : "danger"}>
                  {a(d.orord ? "insynOrord" : "insynAndrad", locale)}
                </Badge>
                {d.fil ? (
                  <button type="button" className={radLank} onClick={() => las(d.skill, d.fil as string)}>
                    {laddar === `${d.skill}/${d.fil}` ? a("insynLaddar", locale) : a("insynLasHela", locale)}
                  </button>
                ) : null}
              </>
            )}
          </li>
        ))}
      </ul>
      {fel ? (
        <p role="alert" className="mt-2 text-[0.8125rem] text-danger">
          {fel}
        </p>
      ) : null}
      {oppen ? (
        <div className="mt-3 rounded-input border border-ink/12 bg-paper2 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="min-w-0 break-all font-mono text-[0.8125rem] text-ink">
              {oppen.skill} / {oppen.fil}
            </p>
            <div className="flex items-center gap-2">
              <Badge tone={oppen.orord ? "good" : "danger"}>
                {a(oppen.orord ? "insynOrord" : "insynAndrad", locale)}
              </Badge>
              <button type="button" className={radLank} onClick={() => setOppen(null)}>
                {a("insynStang", locale)}
              </button>
            </div>
          </div>
          <pre className="thin-scrollbar mt-2 max-h-[28rem] overflow-auto whitespace-pre-wrap break-words font-mono text-[0.8125rem] leading-6 text-ink-muted">
            {oppen.text}
          </pre>
        </div>
      ) : null}
    </div>
  );
}

function Lagerrad({
  post,
  text,
  delar,
  markerad
}: Readonly<{ post: LagerPost; text: string | undefined; delar?: SkillDel[]; markerad: boolean }>) {
  const { locale } = useLocale();
  const ref = useRef<HTMLLIElement>(null);
  useEffect(() => {
    if (markerad) ref.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [markerad]);
  const namn = post.position === "system" ? a(`lager_${post.etikett}`, locale) : post.etikett;
  return (
    <li ref={ref} className={cn("min-w-0 py-3", markerad && "rounded-input bg-ochre/10 px-2 ring-2 ring-ochre")}>
      <div className="flex min-w-0 flex-wrap items-baseline gap-x-4 gap-y-1">
        {post.position === "system" ? (
          <span aria-hidden className={cn("inline-block h-2.5 w-2.5 shrink-0 rounded-[2px]", FARG[post.etikett])} />
        ) : null}
        <span className="min-w-0 break-words text-[0.9375rem] font-medium text-ink">{namn}</span>
        <span className={cn(meta, "min-w-0 break-all font-mono")}>{post.kalla}</span>
      </div>
      <dl className="mt-1.5 flex flex-wrap gap-x-6 gap-y-1 text-[0.8125rem]">
        {post.vem ? (
          <div>
            <dt className={cn(etikett, "inline")}>{a("insynVem", locale)}</dt>{" "}
            <dd className="inline text-ink">{post.vem}</dd>
          </div>
        ) : null}
        <div>
          <dt className={cn(etikett, "inline")}>{a("insynTecken", locale)}</dt>{" "}
          <dd className="num inline text-ink">{antal(post.tecken, locale)}</dd>
        </div>
        <div>
          <dt className={cn(etikett, "inline")}>{a("insynHash", locale)}</dt>{" "}
          <dd className="inline font-mono text-ink">{kortHash(post.hash)}</dd>
        </div>
        {post.redigera ? (
          <a href={post.redigera} className={radLank}>
            {a("insynRedigera", locale)}
          </a>
        ) : null}
      </dl>
      {text !== undefined ? (
        <details className="mt-2" open={markerad || undefined}>
          <summary className={cn(etikett, "focus-ring cursor-pointer rounded-input hover:text-ink")}>
            {a("insynVisaText", locale)}
          </summary>
          <pre className="thin-scrollbar mt-2 max-h-[28rem] overflow-auto whitespace-pre-wrap break-words font-mono text-[0.8125rem] leading-6 text-ink-muted">
            {text}
          </pre>
        </details>
      ) : null}
      {delar?.length ? <SkillFiler delar={delar} /> : null}
    </li>
  );
}

export function Lagerstapel({
  lager,
  texter,
  anvandartext,
  skilldelar,
  markerad
}: Readonly<{
  lager: LagerPost[];
  texter: Record<string, string>;
  anvandartext?: string | null;
  skilldelar?: SkillDel[];
  markerad?: string | null;
}>) {
  const { locale } = useLocale();
  const system = lager.filter((l) => l.position === "system");
  const anvandare = lager.filter((l) => l.position === "user");

  // Användarlagren är sammanhängande bitar av meddelandet, i ordning.
  const anvandarTexter: (string | undefined)[] = [];
  let start = 0;
  for (const l of anvandare) {
    anvandarTexter.push(l.text ?? (anvandartext ? anvandartext.slice(start, start + l.tecken) : undefined));
    start += l.tecken;
  }

  return (
    <div className="min-w-0">
      <section aria-label={a("insynSystem", locale)}>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className={etikett}>{a("insynSystem", locale)}</h3>
          <span className={cn(meta, "num")}>
            {antal(system.reduce((s, l) => s + l.tecken, 0), locale)}
          </span>
        </div>
        <div className="mt-2">
          <Stapel lager={system} aria={a("insynSystem", locale)} />
        </div>
        <ul className="mt-2 divide-y divide-ink/12 border-b border-ink/15">
          {system.map((post, i) => (
            <Lagerrad
              key={`${post.hash}-${i}`}
              post={post}
              text={texter[post.hash]}
              delar={post.etikett === "skill" ? skilldelar : undefined}
              markerad={markerad === post.hash}
            />
          ))}
        </ul>
      </section>
      {anvandare.length ? (
        <section aria-label={a("insynAnvandare", locale)} className="mt-6">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className={etikett}>{a("insynAnvandare", locale)}</h3>
            <span className={cn(meta, "num")}>
              {antal(anvandare.reduce((s, l) => s + l.tecken, 0), locale)}
            </span>
          </div>
          <div className="mt-2">
            <Stapel lager={anvandare} aria={a("insynAnvandare", locale)} />
          </div>
          <ul className="mt-2 divide-y divide-ink/12 border-b border-ink/15">
            {anvandare.map((post, i) => (
              <Lagerrad
                key={`${post.hash}-${i}`}
                post={post}
                text={anvandarTexter[i]}
                markerad={markerad === post.hash}
              />
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
