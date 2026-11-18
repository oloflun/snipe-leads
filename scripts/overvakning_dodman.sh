#!/usr/bin/env bash
# Dödmanskontrollen för övervakningen (.github/workflows/overvakning.yml) och,
# sedan 2026-11-18, för säkerhetsbevakningen (.github/workflows/sakerhetsbevakning.yml).
#
# Övervakningen larmar när produktionen avviker, men ingenting larmade när
# övervakningen själv slutade gå: GitHub körde bara EN av de schemalagda
# körningarna mellan 2026-11-17 23:32 och 2026-11-18 15:48 UTC (se kommentaren
# i overvakning.yml). Det här skriptet frågar GitHub när flödet senast
# gick klart och öppnar ett ärende med etiketten `overvakning-tyst` om det är
# längre sedan än GRANS_SEKUNDER (3 timmar). Ärendet kommenteras högst var
# sjätte timme och stängs när övervakningen gått igen.
#
# Körs av verify.yml (varje push och PR, alltså oberoende av GitHubs schema)
# och av flödet självt (som stänger ärendet när det går).
#
#   GH_TOKEN, GH_REPO   krävs (GITHUB_TOKEN med actions: read, issues: write)
#   LAGE                "kontrollera" (default), "stang" eller "alder"
#                       ("alder" skriver bara sekunderna sedan senaste lyckade
#                       körning på stdout; sakerhetsbevakning.yml använder det
#                       för att begränsa sin reserv)
#   FLODE               "overvakning.yml" (default) eller "sakerhetsbevakning.yml";
#                       väljer etikett, gräns, texter och vad som räknas som
#                       lyckad körning (se profilerna nedan)
#   GRANS_SEKUNDER      default enligt profilen (övervakningen 10800)
#   NU_EPOCH            för test; default `date +%s`
#
# Utan FLODE är beteendet exakt det som gällde före generaliseringen.
# Läser bara körningarnas tider; inga hemligheter, inga svarskroppar.
set -euo pipefail

LAGE="${LAGE:-kontrollera}"
FLODE="${FLODE:-overvakning.yml}"
NU="${NU_EPOCH:-$(date +%s)}"

# JOBB tomt: varje lyckad körning av flödet räknas. JOBB satt: bara körningar
# där jobbet med det namnet lyckades (inte hoppades över), så att en körning
# som avbrutits tidigt av reservgrinden inte räknas som att flödet gått.
case "$FLODE" in
  overvakning.yml)
    ETIKETT="overvakning-tyst"
    STANDARDGRANS=10800
    JOBB=""
    SUBJEKT="Övervakningen"
    SUBJEKT_LITEN="övervakningen"
    RUBRIK="Övervakningen av produktionen"
    ETIKETTBESKRIVNING="Dödmanskontrollen: övervakningen av produktionen har inte gått"
    KONSEKVENS="Under tiden har ingen kontrollerat att produktionen svarar. Starta övervakningen för hand:"
    ATGARD="och kontrollera produktionen."
    ;;
  sakerhetsbevakning.yml)
    ETIKETT="sakerhetsbevakning-tyst"
    STANDARDGRANS=172800
    JOBB="Bevaka säkerhetsflödena"
    SUBJEKT="Säkerhetsbevakningen"
    SUBJEKT_LITEN="säkerhetsbevakningen"
    RUBRIK="Säkerhetsbevakningen (CERT-SE och GitHub-advisories)"
    ETIKETTBESKRIVNING="Dödmanskontrollen: säkerhetsbevakningen har inte gått"
    KONSEKVENS="Under tiden har ingen läst CERT-SE:s flöde eller GitHubs advisories mot vår stack. Starta bevakningen för hand:"
    ATGARD="så tar den igen det som publicerats de senaste sju dagarna."
    ;;
  *)
    echo "Okänt flöde: $FLODE" >&2
    exit 1
    ;;
esac
GRANS="${GRANS_SEKUNDER:-$STANDARDGRANS}"

oppet_arende() {
  gh issue list --label "$ETIKETT" --state open --limit 1 --json number --jq '.[0].number // empty'
}

stang() {
  local nummer
  nummer="$(oppet_arende)"
  if [[ -n "$nummer" ]]; then
    gh issue close "$nummer" --reason completed \
      --comment "$SUBJEKT har gått igen ($(date -u '+%Y-%m-%d %H:%M UTC')). Stängt av dödmanskontrollen."
  fi
}

# Tidpunkten (ISO 8601) då flödet senast gick klart, tom om aldrig.
senast_lyckad() {
  if [[ -z "$JOBB" ]]; then
    gh api "repos/${GH_REPO}/actions/workflows/${FLODE}/runs?status=success&per_page=1" \
      --jq '.workflow_runs[0].updated_at // empty'
    return
  fi
  local id tid
  for id in $(gh api "repos/${GH_REPO}/actions/workflows/${FLODE}/runs?status=success&per_page=20" \
      --jq '.workflow_runs[].id'); do
    # JOBB är en fast sträng ur profilen ovan (inga citattecken), så den kan
    # stå direkt i jq-uttrycket; gh api --jq tar inga --arg.
    tid="$(gh api "repos/${GH_REPO}/actions/runs/${id}/jobs" \
      --jq "[.jobs[] | select(.name == \"$JOBB\" and .conclusion == \"success\") | .completed_at] | first // empty")"
    if [[ -n "$tid" ]]; then
      printf '%s' "$tid"
      return
    fi
  done
}

if [[ "$LAGE" == "stang" ]]; then
  stang
  exit 0
fi

senast="$(senast_lyckad)"
if [[ -z "$senast" ]]; then
  alder=$((GRANS + 1))
  senast_text="aldrig"
else
  alder=$(( NU - $(date -d "$senast" +%s) ))
  senast_text="$senast"
fi

if [[ "$LAGE" == "alder" ]]; then
  # Aldrig gått: ett stort tal, så att anroparen alltid kör.
  if [[ -z "$senast" ]]; then echo 999999999; else echo "$alder"; fi
  exit 0
fi

echo "$SUBJEKT gick senast klart: $senast_text (för $((alder / 60)) minuter sedan, gräns $((GRANS / 60)))."

if (( alder <= GRANS )); then
  stang
  exit 0
fi

echo "::warning::$SUBJEKT har inte gått på $((alder / 60)) minuter (gräns $((GRANS / 60)))."

if ! gh label list --limit 200 --json name --jq '.[].name' | grep -qx "$ETIKETT"; then
  gh label create "$ETIKETT" --color D93F0B \
    --description "$ETIKETTBESKRIVNING"
fi

text="$(mktemp)"
{
  echo "**$RUBRIK har inte gått på $((alder / 60)) minuter.**"
  echo
  echo "- Senast lyckade körning: $senast_text"
  echo "- Gräns: $((GRANS / 3600)) timmar"
  echo "- Upptäckt av: ${GITHUB_WORKFLOW:-dödmanskontrollen}, $GITHUB_SERVER_URL/$GH_REPO/actions/runs/${GITHUB_RUN_ID:-}"
  echo
  echo "$KONSEKVENS"
  echo "\`gh workflow run $FLODE -R $GH_REPO\` $ATGARD Orsaken är oftast att GitHub hoppat över schemalagda körningar (se kommentaren i \`.github/workflows/$FLODE\`). Ärendet stängs när $SUBJEKT_LITEN gått igen."
} > "$text"

nummer="$(oppet_arende)"
if [[ -z "$nummer" ]]; then
  gh issue create --title "$SUBJEKT har inte gått: dödmanskontrollen larmar" \
    --label "$ETIKETT" --body-file "$text"
  exit 0
fi

forra="$(gh issue view "$nummer" --json createdAt,comments --jq '[.createdAt] + [.comments[].createdAt] | last')"
if (( NU - $(date -d "$forra" +%s) >= 21600 )); then
  gh issue comment "$nummer" --body-file "$text"
else
  echo "Ärende #$nummer är redan öppet och kommenterat för mindre än sex timmar sedan."
fi
