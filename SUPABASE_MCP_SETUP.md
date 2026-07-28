# Supabase MCP Setup (Snipra project)

One-time setup so Claude Code can read and modify the Snipra Supabase database
directly — apply migrations, inspect tables, run queries — without anyone
sharing the database password.

**Time:** ~5 minutes. **You only do this once per machine.**

---

## Why this exists

Claude Code's built-in Supabase connector authorizes against **one organization
at a time** via OAuth. If your account belongs to more than one org (e.g. a
personal one and Snipra's), connecting to one loses access to the other.

The workaround: add a **second, separate MCP server** scoped to the Snipra
project only, authenticated with a Personal Access Token instead of OAuth. Both
connections then coexist — your existing connector keeps working untouched.

| | Value |
|---|---|
| Supabase project ref | `spsmblyvasagpekjmgmf` |
| Supabase organization | `fgaquwmqajjaboyqliij` |
| Config file | `.mcp.json` in the repo root (gitignored) |
| Server name | `supabase-snipra` |

---

## Step 1 — Create a Personal Access Token

1. Go to https://supabase.com/dashboard/account/tokens
   (or: Supabase dashboard → click your avatar → **Account Preferences** → **Access Tokens**)
2. Make sure you are logged in with the account that has access to the **Snipra**
   organization. If you belong to several orgs, this matters — the token
   inherits your account's access.
3. Click **Generate new token**.
4. Name it something you'll recognize later, e.g. `Claude Code — Snipra`.
5. **Copy the token now.** Supabase shows it exactly once.

> The token starts with `sbp_`. Treat it like a password — it can read and write
> every project your account can reach.

---

## Step 2 — Store the token as an environment variable

Do **not** paste the token into any file in the repo. The config references an
environment variable instead, so the secret never touches git.

### Windows (PowerShell)

```powershell
setx SUPABASE_PAT_SNIPRA "sbp_paste-your-token-here"
```

### macOS / Linux

Add it to your shell profile so it persists across restarts:

```bash
echo 'export SUPABASE_PAT_SNIPRA="sbp_paste-your-token-here"' >> ~/.zshrc
```

(Use `~/.bashrc` instead if you're on bash.)

> **This is the step people get wrong.** See Step 4 — the variable must exist in
> the environment *before* the terminal window that launches Claude Code is
> opened. Setting it does not affect terminals that are already running.

---

## Step 3 — Create `.mcp.json`

In the **repo root** (`snipe-leads/`), create a file named `.mcp.json`:

```json
{
  "mcpServers": {
    "supabase-snipra": {
      "type": "http",
      "url": "https://mcp.supabase.com/mcp?project_ref=spsmblyvasagpekjmgmf",
      "headers": {
        "Authorization": "Bearer ${SUPABASE_PAT_SNIPRA}"
      }
    }
  }
}
```

Notes:

- `.mcp.json` is already in `.gitignore` — never commit it. Each developer has
  their own token.
- `project_ref` scopes the connection to Snipra only. The token technically has
  broader access, but this MCP server can't reach anything else.
- Add `&read_only=true` to the URL if you want a connection that cannot write.

---

## Step 4 — Start Claude Code correctly

Two conditions must both hold. Getting either wrong is the usual cause of
"it doesn't show up".

**a) Open a brand-new terminal window.**

Environment variables are read when a process starts. A terminal window that was
already open when you ran Step 2 still has the old environment — and starting
`claude` inside it inherits that stale environment. Opening a *new* `claude`
session in the *same* window is not enough. Close the window and open a new one.

Verify the variable is actually visible before continuing:

```powershell
# Windows
echo $env:SUPABASE_PAT_SNIPRA
```

```bash
# macOS / Linux
echo $SUPABASE_PAT_SNIPRA
```

If that prints nothing, stop and fix Step 2 — nothing downstream will work.

**b) Launch Claude Code from the project directory.**

Project-scoped `.mcp.json` is only loaded when Claude Code runs inside that
project. Starting it from your home directory silently ignores the file.

```bash
cd path/to/snipe-leads
claude
```

---

## Step 5 — Approve the server

Project MCP servers require explicit approval the first time, for security —
a repo can't silently connect you to an external service.

On first launch you'll see a prompt asking whether to trust the project's MCP
servers. Approve it.

If you missed the prompt, `claude mcp list` will show:

```
supabase-snipra: https://mcp.supabase.com/mcp?project_ref=... (HTTP) - ⏸ Pending approval (run `claude` to approve)
```

Run `claude` again from the project directory and approve.

---

## Step 6 — Verify

Inside Claude Code:

```
/mcp
```

You should see `supabase-snipra` listed with:

```
Status:  ✔ connected
Auth:    ✔ authenticated
Tools:   20 tools
```

Then confirm it reaches the right database by asking Claude:

> List the tables in the Snipra Supabase project `spsmblyvasagpekjmgmf`.

You should get back the `ss_`-prefixed Snajp-Support tables (`ss_tenants`,
`ss_emails`, `ss_drafts`, `ss_knowledge_base`, …) plus the core Snipra tables.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `supabase-snipra` missing from `claude mcp list` | Ran the command outside the project directory | `cd` into `snipe-leads` and rerun |
| `⏸ Pending approval` | Project MCP not yet trusted | Run `claude` from the project dir, approve the prompt |
| `✘ failed` | Env var not visible to the process — almost always this | Close the terminal **window** entirely, open a new one, verify with `echo` (Step 4a) |
| `permission denied` on project calls | Token belongs to an account without Snipra org access | Regenerate the PAT while logged into the account that has access to org `fgaquwmqajjaboyqliij` |
| Connected, but only shows unrelated projects | You're looking at the old OAuth connector, not this one | Both appear separately in `/mcp`; make sure you're using the `supabase-snipra` tools |

---

## Security notes

- The PAT grants read **and write** access to every Supabase project your
  account can reach. Scope the risk by keeping `project_ref` in the URL.
- `.mcp.json` is gitignored. If you ever see it in `git status` as staged or
  untracked-but-about-to-be-added, stop and check `.gitignore` before committing.
- Revoke a token any time at https://supabase.com/dashboard/account/tokens —
  revoking breaks only your own local MCP connection, nothing shared.
- Migrations applied through this connection hit the **live** database directly.
  There is no staging copy. Read `supabase/migrations/` before applying anything.
