#!/usr/bin/env bash
# SessionStart-hook (Antons regel 2026-10-07, CLAUDE.md › Projektregler — drift):
# hämtar origin och säger till om arbetsgrenen ligger efter. Ändrar aldrig
# arbetsträdet; sammanslagningen är sessionens första steg, inte hookens.
cd "$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
gren=$(git branch --show-current 2>/dev/null)
[ -n "$gren" ] || exit 0
if ! timeout 20 git fetch -q origin "$gren" 2>/dev/null; then
  echo "Kunde inte hämta origin/$gren. Kör git fetch origin själv innan arbetet börjar."
  exit 0
fi
efter=$(git rev-list --count "HEAD..origin/$gren" 2>/dev/null || echo 0)
fore=$(git rev-list --count "origin/$gren..HEAD" 2>/dev/null || echo 0)
if [ "$efter" -gt 0 ]; then
  echo "GRENEN LIGGER $efter COMMITS EFTER origin/$gren ($fore lokala före). Kör git merge --ff-only origin/$gren (git merge origin/$gren om de divergerat) innan arbetet börjar."
fi
exit 0
