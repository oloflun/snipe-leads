#!/usr/bin/env python3
"""Skriver Railways ägarskaps-TXT till Loopia.

    python scripts/railway_verifiera_doman.py            # torrkörning
    python scripts/railway_verifiera_doman.py --apply

## Varför den behövs, och varför den var svår att hitta

Railway kräver TVÅ poster för en egen domän: CNAME:n som dirigerar trafiken,
och en TXT som bevisar att domänen är din. Certifikatet utfärdas först när
BÅDA finns — `certificateStatus` står på `VALIDATING_OWNERSHIP` till dess.

Fällan: TXT-posten syns INTE i `status.dnsRecords`. Den listan innehöll bara
CNAME:n, med `status: DNS_RECORD_STATUS_PROPAGATED`, alltså allt grönt — medan
`verified` stod på false i ett fält ingen tittade på. Domänen såg ut att bara
behöva mer tid, och gjorde det i flera dagar.

Kravet läses ur Railways API vid varje körning i stället för att hårdkodas.
Token roteras när en domän tas bort och läggs till igen, och en hårdkodad
sträng hade då verifierat fel domän — eller ingen alls.

Leakage-spärr: Loopia-nycklarna läses ur .env.deploy och skrivs aldrig ut.
Verifieringstoken är inte en hemlighet — den är avsedd att ligga publikt i DNS.
"""
import sys, xmlrpc.client
sys.path.insert(0, "scripts")
from railway import gql
from railway_provision import env_read

TORR = "--apply" not in sys.argv
DOMAN = "snajp.se"

d = gql("""query { projects { edges { node { id name
  environments { edges { node { id name } } }
  services { edges { node { id name } } } } } } }""")
p = next(k["node"] for k in d["projects"]["edges"] if k["node"]["name"] == "brave-passion")
m = {e["node"]["name"]: e["node"]["id"] for e in p["environments"]["edges"]}
t = {e["node"]["name"]: e["node"]["id"] for e in p["services"]["edges"]}

r = gql("""query($p:String!,$e:String!,$s:String!){ domains(projectId:$p,environmentId:$e,serviceId:$s){
  customDomains { domain status { verified verificationDnsHost verificationToken } } } }""",
  {"p": p["id"], "e": m["main"], "s": t["web"]})
cd = r["domains"]["customDomains"][0]
st = cd["status"]
if st["verified"]:
    print("redan verifierad — inget att gora"); raise SystemExit
vard, token = st["verificationDnsHost"], st["verificationToken"]
print(f"kraver TXT  {vard}.{DOMAN}  ->  {token[:24]}...")

E = env_read()
api = xmlrpc.client.ServerProxy(uri="https://api.loopia.se/RPCSERV", encoding="utf-8", allow_none=True)
anv, los = E["LOOPIA_API_USER"], E["LOOPIA_API_PASSWORD"]

befintliga = api.getZoneRecords(anv, los, DOMAN, vard)
if any(str(x.get("rdata", "")).strip('"') == token for x in befintliga):
    print("posten finns redan"); raise SystemExit

if TORR:
    print(f"SKULLE skapa underdoman {vard} och satta TXT")
    raise SystemExit

if vard not in api.getSubdomains(anv, los, DOMAN):
    api.addSubdomain(anv, los, DOMAN, vard)
    print("skapade underdoman", vard)

svar = api.addZoneRecord(anv, los, DOMAN, vard,
                         {"type": "TXT", "ttl": 3600, "priority": 0, "rdata": token})
print("satte TXT:", svar)
for x in api.getZoneRecords(anv, los, DOMAN, vard):
    print(f"  {vard}.{DOMAN}  {x.get('type')}  {str(x.get('rdata'))[:40]}...")
