#!/usr/bin/env bash
# Dödmanskontrollen för övervakningen (.github/workflows/overvakning.yml).
#
# Övervakningen larmar när produktionen avviker, men ingenting larmade när
# övervakningen själv slutade gå: GitHub körde bara EN av de schemalagda
# körningarna mellan 2026-11-17 23:32 och 2026-11-18 15:48 UTC (se kommentaren
# i overvakning.yml). Det här skriptet frågar GitHub när övervakningen senast
# gick klart och öppnar ett ärende med etiketten `overvakning-tyst` om det är
# längre sedan än GRANS_SEKUNDER (3 timmar). Ärendet kommenteras högst var
# sjätte timme och stängs när övervakningen gått igen.
#
# Körs av verify.yml (varje push och PR, alltså oberoende av GitHubs schema)
# och av overvakning.yml självt (som stänger ärendet när den går).
#
#   GH_TOKEN, GH_REPO   krävs (GITHUB_TOKEN med actions: read, issues: write)
#   LAGE                "kontrollera" (default) eller "stang"
#   GRANS_SEKUNDER      default 10800
#   NU_EPOCH            för test; default `date +%s`
#
# Läser bara körningarnas tider; inga hemligheter, inga svarskroppar.
set -euo pipefail

ETIKETT="overvakning-tyst"
LAGE="${LAGE:-kontrollera}"
GRANS="${GRANS_SEKUNDER:-10800}"
NU="${NU_EPOCH:-$(date +%s)}"

oppet_arende() {
  gh issue list --label "$ETIKETT" --state open --limit 1 --json number --jq '.[0].number // empty'
}

stang() {
  local nummer
  nummer="$(oppet_arende)"
  if [[ -n "$nummer" ]]; then
    gh issue close "$nummer" --reason completed \
      --comment "Övervakningen har gått igen ($(date -u '+%Y-%m-%d %H:%M UTC')). Stängt av dödmanskontrollen."
  fi
}

if [[ "$LAGE" == "stang" ]]; then
  stang
  exit 0
fi

senast="$(gh api "repos/${GH_REPO}/actions/workflows/overvakning.yml/runs?status=success&per_page=1" \
  --jq '.workflow_runs[0].updated_at // empty')"
if [[ -z "$senast" ]]; then
  alder=$((GRANS + 1))
  senast_text="aldrig"
else
  alder=$(( NU - $(date -d "$senast" +%s) ))
  senast_text="$senast"
fi
echo "Övervakningen gick senast klart: $senast_text (för $((alder / 60)) minuter sedan, gräns $((GRANS / 60)))."

if (( alder <= GRANS )); then
  stang
  exit 0
fi

echo "::warning::Övervakningen har inte gått på $((alder / 60)) minuter (gräns $((GRANS / 60)))."

if ! gh label list --limit 200 --json name --jq '.[].name' | grep -qx "$ETIKETT"; then
  gh label create "$ETIKETT" --color D93F0B \
    --description "Dödmanskontrollen: övervakningen av produktionen har inte gått"
fi

text="$(mktemp)"
{
  echo "**Övervakningen av produktionen har inte gått på $((alder / 60)) minuter.**"
  echo
  echo "- Senast lyckade körning: $senast_text"
  echo "- Gräns: $((GRANS / 3600)) timmar"
  echo "- Upptäckt av: ${GITHUB_WORKFLOW:-dödmanskontrollen}, $GITHUB_SERVER_URL/$GH_REPO/actions/runs/${GITHUB_RUN_ID:-}"
  echo
  echo "Under tiden har ingen kontrollerat att produktionen svarar. Starta övervakningen för hand:"
  echo "\`gh workflow run overvakning.yml -R $GH_REPO\` och kontrollera produktionen. Orsaken är oftast att GitHub hoppat över schemalagda körningar (se kommentaren i \`.github/workflows/overvakning.yml\`). Ärendet stängs när övervakningen gått igen."
} > "$text"

nummer="$(oppet_arende)"
if [[ -z "$nummer" ]]; then
  gh issue create --title "Övervakningen har inte gått: dödmanskontrollen larmar" \
    --label "$ETIKETT" --body-file "$text"
  exit 0
fi

forra="$(gh issue view "$nummer" --json createdAt,comments --jq '[.createdAt] + [.comments[].createdAt] | last')"
if (( NU - $(date -d "$forra" +%s) >= 21600 )); then
  gh issue comment "$nummer" --body-file "$text"
else
  echo "Ärende #$nummer är redan öppet och kommenterat för mindre än sex timmar sedan."
fi
