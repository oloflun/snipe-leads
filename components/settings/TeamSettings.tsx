"use client";

import { useEffect, useState, useTransition } from "react";
import { inviteMember, listTeam, revokeInvite, type TeamMember } from "@/lib/actions/team";

/**
 * Teamvyn. Ersätter fyra hårdkodade strängar med den faktiska arbetsytan.
 *
 * Ledger, inte kort: en rad per person, hairline mellan. Operate mode — det
 * här är en arbetsyta, och täthet slår uttryck (DESIGN.md).
 *
 * Inbjudna och medlemmar står i SAMMA lista med olika status i stället för i
 * två sektioner. Frågan användaren har är "vem har åtkomst", inte "vilka
 * tabeller finns" — och en skickad inbjudan som ligger i en egen sektion
 * längre ned är precis en inbjudan som skickas två gånger.
 */
export function TeamSettings() {
  const [members, setMembers] = useState<TeamMember[] | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  async function reload() {
    setMembers(await listTeam());
  }

  useEffect(() => {
    void reload();
  }, []);

  function handleInvite(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    startTransition(async () => {
      const result = await inviteMember(email, role);
      if (!result.success) {
        setError(result.error ?? "Inbjudan gick inte att skapa.");
        return;
      }
      setMessage(result.message ?? "Inbjudan skapad.");
      setEmail("");
      await reload();
    });
  }

  function handleRevoke(inviteId: string) {
    setError(null);
    setMessage(null);
    startTransition(async () => {
      const result = await revokeInvite(inviteId);
      if (!result.success) {
        setError(result.error ?? "Inbjudan gick inte att ta bort.");
        return;
      }
      await reload();
    });
  }

  return (
    <div className="grid gap-8">
      <div>
        <h3 className="kicker text-mineral">Teamet</h3>

        {members === null ? (
          // Skelettrader, inte en spinnare mitt i innehållet: raderna hoppar
          // inte när datan landar.
          <div className="mt-5 grid gap-px">
            {[0, 1, 2].map((row) => (
              <div key={row} className="h-12 animate-pulse border-t border-ink/15 bg-ink/[0.03]" />
            ))}
          </div>
        ) : members.length === 0 ? (
          <p className="mt-5 border-t border-ink/15 pt-5 text-[15px] text-mineral">
            Du är ensam i arbetsytan. Bjud in någon nedan.
          </p>
        ) : (
          <ul className="mt-5">
            {members.map((member) => (
              <li
                key={member.id}
                className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-6 gap-y-2 border-t border-ink/15 py-4"
              >
                <span className="min-w-0 break-words text-[15px]">{member.label}</span>
                <span className="kicker shrink-0 text-mineral">
                  {member.role === "owner" ? "Ägare" : "Medlem"}
                  {member.status === "invited" ? " · inbjuden" : null}
                </span>
                {member.status === "invited" ? (
                  <button
                    type="button"
                    disabled={isPending}
                    onClick={() => handleRevoke(member.id)}
                    className="shrink-0 text-[13px] text-mineral underline underline-offset-4 transition hover:text-danger disabled:opacity-60"
                  >
                    Ta bort
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>

      <form onSubmit={handleInvite} className="border-t border-ink/15 pt-6">
        <h3 className="kicker text-mineral">Bjud in</h3>

        <div className="mt-5 flex min-w-0 flex-wrap items-end gap-4">
          <label className="grid min-w-0 flex-1 gap-2 text-[15px]">
            <span className="kicker text-mineral">E-post</span>
            <input
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="kollega@bolag.se"
              className="h-12 w-full min-w-0 border border-ink/15 bg-paper2/70 px-4 outline-none focus:border-ochre"
            />
          </label>

          <label className="grid gap-2 text-[15px]">
            <span className="kicker text-mineral">Roll</span>
            <select
              value={role}
              onChange={(event) => setRole(event.target.value)}
              className="h-12 border border-ink/15 bg-paper2/70 px-4 outline-none focus:border-ochre"
            >
              <option value="member">Medlem</option>
              <option value="owner">Ägare</option>
            </select>
          </label>

          <button
            type="submit"
            disabled={isPending}
            className="h-12 bg-ink px-5 font-mono text-[13px] uppercase tracking-[0.18em] text-paper transition-colors duration-500 hover:bg-ochre hover:text-ink disabled:opacity-60"
          >
            {isPending ? "Sparar..." : "Bjud in"}
          </button>
        </div>

        {error ? (
          <p role="alert" className="mt-5 break-words text-[14px] text-danger">
            {error}
          </p>
        ) : null}
        {message ? (
          <p role="status" className="mt-5 break-words text-[14px] text-moss">
            {message}
          </p>
        ) : null}
      </form>
    </div>
  );
}
