# Session Log — 2026-05-24-4

## Session Summary
Debugged and fixed two broken global MCP servers: `agentmemory` (failing with JSON-RPC -32000) and `carl-mcp` (not appearing at all). Both root causes were in Claude Code's MCP config files. Changes are global — affect all projects, not just snipe-leads.

## What Changed

### Files Modified
- `~/.claude.json` — Changed agentmemory command from `npx -y @agentmemory/mcp` → `node .../cli.mjs mcp`; added `carl-mcp` entry to global `mcpServers`
- `~/.claude/settings.json` — Added `"enabledMcpjsonServers": ["carl-mcp"]` (belt-and-suspenders for .mcp.json opt-in)

### Files Created
- None

## Decisions Made
- **agentmemory fix — direct node over npx:** `npx -y @agentmemory/mcp` is unreliable in non-interactive Windows process spawns (downloads shim on every start, can fail/timeout). Changed to `node <full path>/dist/cli.mjs mcp` using the globally installed package. Confirmed working: proper JSON-RPC `{"result":{"serverInfo":{"name":"agentmemory","version":"0.9.21"}}}` response.
- **carl-mcp in ~/.claude.json mcpServers (not just .mcp.json):** `.mcp.json` requires `enabledMcpjsonServers` per project; project entries in `~/.claude.json` had empty arrays that would override user-level settings. Adding carl-mcp directly to the top-level `mcpServers` in `~/.claude.json` (same mechanism as agentmemory) guarantees global availability.

## Context & Discussion
- `agentmemory` is installed globally via npm (`@agentmemory/agentmemory@0.9.21`). The `agentmemory connect claude-code` command had written the npx config to `~/.claude.json`. The daemon was running fine at port 3111; the failure was entirely in how the MCP shim was spawned.
- `carl-mcp` lives at `~/.carl/carl-mcp/index.js` (30 tools: domains, decisions, staging, carl-json). It was registered in `~/.mcp.json` but `.mcp.json` servers need per-project opt-in. Only `super-intelligence` had it enabled.
- Claude Code stores global MCP servers in `~/.claude.json` under top-level `mcpServers` key. Per-project overrides live in `~/.claude.json` → `projects["<cwd>"]`. The `settings.json` does NOT support `mcpServers` (schema validation error).
- `enabledMcpjsonServers` in `settings.json` enables `.mcp.json` servers but may be overridden by project-level empty arrays in `~/.claude.json`.

## Open Threads
- Session restart required — both MCP servers need a session restart to appear. Verify both show up in `/mcp` after restarting.

## Cross-Project Handoffs
- Both fixes are global — will affect carl-os, super-intelligence, warehouse-handy-next, all other projects. No specific action required in those projects; the MCP servers will just appear on next session start.

## Current State After This Session
Both MCP servers are configured correctly. `agentmemory` daemon is running at port 3111 with 0 memories (fresh). `carl-mcp` has 30 tools wired to the CARL workspace. A session restart will activate both. The snipe-leads project itself was not modified; this was a global infra fix session.

<!-- session-state
date: 2026-05-24
type: infrastructure/debugging
files_created: []
files_modified:
  - ~/.claude.json
  - ~/.claude/settings.json
decisions_made: 2
open_threads: 1
handoffs_pending: []
priority_changes: false
status_updated: false
next_session_focus: "Restart session and verify agentmemory + carl-mcp appear in /mcp"
session-state -->
