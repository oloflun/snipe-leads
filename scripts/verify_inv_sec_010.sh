#!/usr/bin/env bash
# INV-SEC-010, levande verifiering: oautentiserade anrop mot en riktig deploy.
#
# Statiska testet (tests/invariants/test_inv_sec_010.py) är CI-spärren och
# fäller nya routes utan grind. Det här skriptet är beviset — det mäter den
# instans som faktiskt kör, inte källkoden.
#
#   bash scripts/verify_inv_sec_010.sh https://snajp.vercel.app
#
# Kör det efter varje deploy som rör app/api/. Det tar tio sekunder.
#
# Metodnot: skriptet är också själva falsifieringen av testet ovan. Innan du
# litar på ETT av dem — peka det här mot en medvetet trasig version (ta bort
# proxyAsTenant ur en route) och bekräfta att det blir RÖTT. Ett grönt test
# som aldrig varit rött har inte bevisat någonting.

set -uo pipefail

BASE="${1:-}"
if [ -z "$BASE" ]; then
  echo "Användning: bash scripts/verify_inv_sec_010.sh <bas-url>" >&2
  exit 2
fi
BASE="${BASE%/}"

fails=0

# Ska kräva session: 401 (eller 409/503 om tenanten inte är kopplad — båda
# betyder att grinden svarade, vilket är det vi mäter).
must_deny() {
  local method="$1" path="$2"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" \
    -H "Content-Type: application/json" -d '{}' "$BASE$path")
  case "$code" in
    401|403|409|503)
      echo "  ok    $method $path -> $code" ;;
    *)
      echo "  FEL   $method $path -> $code (förväntade 401)" >&2
      fails=$((fails + 1)) ;;
  esac
}

# Ska fungera utan session — den publika demon är produkten.
must_allow() {
  local method="$1" path="$2" body="$3"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" \
    -H "Content-Type: application/json" -d "$body" "$BASE$path")
  case "$code" in
    200|202|429)
      echo "  ok    $method $path -> $code" ;;
    *)
      echo "  FEL   $method $path -> $code (demon ska svara utan inloggning)" >&2
      fails=$((fails + 1)) ;;
  esac
}

echo "INV-SEC-010 mot $BASE"
echo "Kräver session:"
must_deny GET  /api/snajp-support/leads/soul
must_deny PUT  /api/snajp-support/leads/soul
must_deny GET  /api/snajp-support/kb
must_deny GET  /api/snajp-support/rules
must_deny GET  /api/snajp-support/inbox
must_deny POST /api/snajp-support/keys
must_deny POST /api/email-studio
must_deny GET  /api/email-studio

echo "Anonym med flit:"
must_allow POST /api/snajp-support/chat '{"message":"hej","tenant":"demo"}'

if [ "$fails" -gt 0 ]; then
  echo "INV-SEC-010: $fails avvikelser." >&2
  exit 1
fi
echo "INV-SEC-010: allt stängt."
