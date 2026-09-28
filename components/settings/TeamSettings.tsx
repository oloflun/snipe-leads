"use client";

import { useEffect, useState, useTransition } from "react";
import { Badge, Rad, Radlista, Sektion, Tomt, btnPrimary, btnSecondary, etikett, meta } from "@/components/ui";
import { cn } from "@/lib/utils";
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
    // listTeam kan kasta (nätverk, session). Utan fångsten förblev members
    // null och sidan stod i skelettet för alltid, utan ett ord om varför.
    try {
      setMembers(await listTeam());
    } catch (orsak) {
      setMembers([]);
      setError(orsak instanceof Error ? orsak.message : "Kunde inte hämta teamet.");
    }
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
    <div>
      <Sektion title="Personer med åtkomst">
        {members === null ? (
          // Skelettrader, inte en spinnare mitt i innehållet: raderna hoppar
          // inte när datan landar.
          <div className="grid gap-px">
            {[0, 1, 2].map((row) => (
              <div key={row} className="h-12 animate-pulse border-t border-ink/15 bg-ink/[0.03]" />
            ))}
          </div>
        ) : members.length === 0 ? (
          <Tomt>Du är ensam i arbetsytan. Bjud in någon nedan.</Tomt>
        ) : (
          <Radlista ariaLabel="Personer med åtkomst">
            {/* Fast schema: namn/e-post | roll och status | åtgärd. Åtgärdsspalten
                har fast bredd så att "Ta bort" står på samma plats på varje rad,
                och lämnar ett tomt fält på rader utan åtgärd i stället för att
                rollen glider ut i kanten. */}
            {members.map((member) => (
              <Rad
                key={member.id}
                className="grid grid-cols-[minmax(0,1fr)_auto_7rem] items-center gap-x-4"
              >
                <span className="min-w-0 break-words text-[0.9375rem]">{member.label}</span>
                <span className="flex flex-wrap items-center justify-end gap-2">
                  <span className={meta}>{member.role === "owner" ? "Ägare" : "Medlem"}</span>
                  {member.status === "invited" ? <Badge tone="warn">Inbjuden</Badge> : null}
                </span>
                {member.status === "invited" ? (
                  <button
                    type="button"
                    disabled={isPending}
                    onClick={() => handleRevoke(member.id)}
                    className={cn(btnSecondary, "justify-self-end")}
                  >
                    Ta bort
                  </button>
                ) : (
                  <span aria-hidden />
                )}
              </Rad>
            ))}
          </Radlista>
        )}
      </Sektion>

      <Sektion title="Bjud in">
        <form onSubmit={handleInvite}>
          <div className="flex min-w-0 flex-wrap items-end gap-4">
            {/* basis-full under sm: `flex-1 min-w-0` kan krympa till noll i stället
                för att tvinga fram en radbrytning, och vid 320px lämnade Roll +
                knappen ~30px åt adressfältet. Etiketten bröts till "E-/POST" och
                fältet gick inte att skriva i. Uppmätt i pixlar, inte antaget. */}
            <label className="grid min-w-0 basis-full gap-2 sm:flex-1 sm:basis-0">
              <span className={etikett}>E-post</span>
              <input
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="kollega@bolag.se"
                className="focus-ring min-h-11 w-full min-w-0 rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
              />
            </label>

            <label className="grid gap-2">
              <span className={etikett}>Roll</span>
              <select
                value={role}
                onChange={(event) => setRole(event.target.value)}
                className="focus-ring min-h-11 rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
              >
                <option value="member">Medlem</option>
                <option value="owner">Ägare</option>
              </select>
            </label>

            <button type="submit" disabled={isPending} className={btnPrimary}>
              {isPending ? "Bjuder in…" : "Bjud in"}
            </button>
          </div>

          {error ? (
            <p role="alert" className="mt-4 break-words text-[0.9375rem] text-danger">
              {error}
            </p>
          ) : null}
          {message ? (
            <p role="status" className="mt-4 break-words text-[0.9375rem] text-moss">
              {message}
            </p>
          ) : null}
        </form>
      </Sektion>
    </div>
  );
}
