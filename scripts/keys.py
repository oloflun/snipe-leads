"""Nyckelhantering — ett verktyg, fungerar från vilken katalog som helst.

    python "C:\\Users\\Anton L\\snipe-leads\\scripts\\keys.py"          # sätt + verifiera
    python .../scripts/keys.py --check                                  # bara verifiera
    python .../scripts/keys.py --push-railway                           # skicka till Railway + verifiera
    python .../scripts/keys.py --new-unlock-key                         # generera skill-låsnyckeln

Render och appens Vercel-projekt är avvecklade. Skrivvägarna dit (Render-pushen
och Vercels push och pull) togs bort 2026-11-18, se docs/BESLUT.md.

Sökvägar löses ur __file__, aldrig ur cwd — skriptet kan köras varifrån som
helst. Värden läses med getpass (syns aldrig, hamnar aldrig i shell-historiken)
och skrivs bara till gitignorerade filer.

Nycklarna hamnar ALDRIG i databasen (INV-SEC-006 / plan G5). Se DEPLOY_KEYS.md.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_ENV = ROOT / "snajp-support" / ".env"
FRONTEND_ENV = ROOT / ".env.local"
UNLOCK_HASH = ROOT / "agent-core" / ".unlock-hash"
#: Drift- och speglingsvariabler. Egen fil, inte .env: de här läses av
#: skripten i scripts/, aldrig av appen, och ska inte följa med en env-pull.
DEPLOY_ENV = ROOT / ".env.deploy"


class Key:
    def __init__(self, name, files, blurb, *, required, where, generated=False):
        self.name, self.files, self.blurb = name, files, blurb
        self.required, self.where = required, where
        # generated=True => klistras aldrig in för hand, så cmd_set frågar inte
        # efter den. Den har ett eget kommando som skapar värdet lokalt.
        self.generated = generated


KEYS = [
    Key(
        "DEEPSEEK_API_KEY",
        [BACKEND_ENV],
        # Texten sa "driver ALLA agentkörningar" fram till 2026-08-28. Det var
        # sant före 24 augusti och direkt vilseledande efteråt: DeepSeek är
        # sedan dess spärrad mot allt som bär kunddata (CLAUDE.md), och Gemini
        # driver chatten. En prompt som påstår motsatsen får någon att sätta
        # fel provider och sedan undra varför tjänsten vägrar starta.
        "DeepSeek — BARA för lokala körningar mot syntetisk data. Spärrad i "
        "main och development (tredjelandsöverföring, se CLAUDE.md). Krävs "
        "för att jämföra providers lokalt i Fas 6; annars valfri.",
        required=True,
        where="https://platform.deepseek.com/api_keys",
    ),
    Key(
        "SCRAPEGRAPHAI_API_KEY",
        [BACKEND_ENV],
        "ScrapeGraphAI — bara för Fas B-research (prospektskrapning).",
        required=False,
        where="https://dashboard.scrapegraphai.com",
    ),
    Key(
        "GEMINI_API_KEY",
        # BÅDA filerna sedan 2026-08-28. Backenden har alltid läst den; webben
        # behöver den för Email-studion, vars modellväljare annars faller
        # tillbaka på mallgenererad text. Att skriva båda i samma inklistring
        # är skillnaden mot att bli ombedd att klistra in samma nyckel två
        # gånger med en veckas mellanrum.
        [BACKEND_ENV, FRONTEND_ENV],
        "Gemini — driver numera CHATTEN (agentkörningarna), plus "
        "bildbeskrivning i supportärenden och KB-embeddings. UTAN denna föll "
        "KB-sökningen tillbaka på svensk fulltext i skarpa tester 2026-08-07 "
        "och missade uppenbara träffar (se HANDOFF.md Steg 0). Nyckelns "
        "PROJEKT måste vara kopplat till ett faktureringskonto, annars gäller "
        "gratisnivåns 20 anrop/dygn oavsett hur nyckeln ser ut (snipe-zfn).",
        required=False,
        where="https://aistudio.google.com/apikey",
    ),
    Key(
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        [BACKEND_ENV],
        "Vertex AI service account JSON — ersätter GEMINI_API_KEY sedan Google "
        "tog bort Cloud-krediter från AI Studio. Klistra in HELA JSON-strängen "
        "(börjar med { och slutar med }). Innehåller project_id, private_key, "
        "client_email m.fl. — se DEPLOY_KEYS.md.",
        required=False,
        where="Google Cloud Console -> IAM -> Service Accounts -> Keys -> Add Key -> JSON",
    ),
    Key(
        "GOOGLE_CLOUD_REGION",
        [BACKEND_ENV],
        "Vertex AI-region — var modellerna körs. Default: europe-west1 (EU). "
        "Alternativ: us-central1, europe-west4. Sätts bara om du vill byta region.",
        required=False,
        where="https://cloud.google.com/vertex-ai/docs/general/locations",
        generated=True,  # ponytail: frågas inte i interaktiv loop
    ),
    Key(
        "SNAJP_SKILL_UNLOCK_KEY",
        [BACKEND_ENV],
        "Avsiktlighetsgrind för agent-core/skills/ — INTE en säkerhetsmekanism. "
        "Krävs för att regenerera manifestet eller publicera skills till DB:n. "
        "Bara på den här maskinen; aldrig i CI.",
        required=False,
        where="genereras lokalt: python scripts/keys.py --new-unlock-key",
        generated=True,
    ),
    Key(
        "TYPESAFE_API_KEY",
        [BACKEND_ENV],
        "Jev (TypeSafe jev-1.13.0) — Iris förbedömning och klassning av leads "
        "(app/leads/jev.py). Valfri: utan den körs Iris som vanligt, bara utan Jev. "
        "Jev ser bara prospektens publika bolagsdata, aldrig kundens egna data. "
        "Samma nyckel som i ~/.secrets/knowledge-graph.env (Jev-experimentet).",
        required=False,
        where="https://typesafe.ai (konto → API keys)",
    ),
]

# Startvärden för en TOM uppsättning — de skrivs bara när fältet saknas eller
# står på en platshållare. De ÖVERSKRIVER aldrig ett värde någon valt.
#
# Varför villkoret finns (2026-08-28): blocket tillämpades tidigare
# ovillkorligt i slutet av `cmd_set`, så den som klistrade in en Gemini-nyckel
# fick `LLM_PROVIDER=deepseek` på köpet och skriptet skrev ut att det gjort
# det. Med en fjärr-DATABASE_URL i samma fil vägrar backenden sedan starta
# (`Settings.llm_provider_fault`), och felet pekar på providern i stället för
# på skriptet som satte den. Samma klass som scripts/railway_provision.py:319
# (snipe-u70): ett verktyg man når efter för att LAGA en konfiguration ska
# inte ändra en annan del av den i tysthet.
FIXED = {BACKEND_ENV: {"LLM_PROVIDER": "deepseek", "MODEL": "deepseek-v4-flash"}}


def looks_placeholder(value: str) -> bool:
    """Samma heuristik som app/config.py:is_simulation()."""
    return len(value) < 20 or "..." in value or "din-" in value


def key_fault(value: str, name: str = "") -> str | None:
    """Varför nyckeln inte GÅR ATT SKICKA, eller None.

    Samma kontroll som Settings.llm_key_fault() i snajp-support/app/config.py,
    fast vid inklistring i stället för vid första agentanropet.

    Ett API-nyckelvärde går i huvudet `Authorization: Bearer <nyckel>`, och
    huvudvärden är per definition ASCII. En nyckel med ett tecken över 127
    kraschar därför inte hos leverantören utan INNE i http-klienten. Det hände
    skarpt: /health/ready svarade "riktig agent aktiv" och första körningen föll
    på `'ascii' codec can't encode character 'à' in position 7` — position 7
    är första tecknet efter "Bearer ".

    Positionen står med i beskedet med flit. Utan den söker den som läser efter
    ett osynligt tecken i en sträng som aldrig får skrivas ut.
    """
    # Service account JSON skickas aldrig i ett HTTP-huvud — den parsas lokalt
    # och OAuth2-tokens genereras vid runtime. ASCII-kontrollen gäller inte.
    if name == "GOOGLE_SERVICE_ACCOUNT_JSON":
        try:
            json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return "är inte giltig JSON"
        return None

    bad = next((i for i, ch in enumerate(value) if ord(ch) > 127), None)
    if bad is not None:
        return (f"innehåller ett tecken utanför ASCII på position {bad} — "
                f"kan inte skickas i ett Authorization-huvud")
    if value != value.strip():
        return "har inledande eller avslutande blanktecken"
    return None


def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, _, value = line.partition("=")
            out[key.strip()] = value.strip()
    return out


def upsert(path: Path, key: str, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def guard_gitignored() -> None:
    # .env.deploy står med sedan --set-railway-token och --set-preview-db
    # skriver hemligheter dit. Den ÄR ignorerad (.gitignore-raden `.env*`), men
    # guarden visste inte det, och en guard som inte täcker en fil den skyddar
    # är en guard man tror på i fel läge.
    for path in (BACKEND_ENV, FRONTEND_ENV, DEPLOY_ENV):
        relative = path.relative_to(ROOT).as_posix()
        result = subprocess.run(
            ["git", "check-ignore", relative], cwd=ROOT, capture_output=True, text=True
        )
        if result.returncode != 0:
            sys.exit(f"AVBRYTER: {relative} är inte gitignorerad — nycklar kunde committas.")


def cmd_check() -> bool:
    print(f"Repo: {ROOT}\n")
    ok = True
    for key in KEYS:
        value = read_env(key.files[0]).get(key.name, "")
        if not value:
            status = "SAKNAS" if key.required else "tom (valfri)"
            ok = ok and not key.required
        elif key_fault(value, key.name):
            # Egen rad, inte samma som PLATSHÅLLARE: den som läser "platshållare"
            # letar efter en saknad variabel, inte efter ett osynligt tecken i
            # den som redan finns.
            status = f"TRASIG — {key_fault(value, key.name)}"
            ok = False
        elif looks_placeholder(value):
            status = "PLATSHÅLLARE — tjänsten kör i SIMULERINGSLÄGE"
            ok = False
        elif key.generated:
            # Ingen svans för genererade nycklar — du bad om att aldrig se den.
            status = f"OK (len={len(value)})"
        else:
            status = f"OK (len={len(value)}, ...{value[-4:]})"
        flag = "KRÄVS" if key.required else "valfri"
        print(f"  {key.name:24} [{flag:6}] {status}")

    backend = read_env(BACKEND_ENV)
    print(f"\n  LLM_PROVIDER={backend.get('LLM_PROVIDER', '(saknas)')}  MODEL={backend.get('MODEL', '(saknas)')}")
    print(
        "\nKLART — riktiga agentkörningar möjliga."
        if ok
        else "\nBLOCKERAT — minst DEEPSEEK_API_KEY behövs."
    )
    return ok


def _read_service_account_json() -> str:
    """Läs service account JSON från en fil. getpass kan bara en rad —
    flerradig JSON spills som shell-kommandon."""
    path_str = input("  Sökväg till JSON-filen (den du laddade ner): ").strip().strip('"').strip("'")
    if not path_str:
        return ""
    p = Path(path_str).expanduser()
    if not p.exists():
        print(f"  -> filen finns inte: {p}")
        return ""
    raw = p.read_text(encoding="utf-8").strip()
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  -> inte giltig JSON: {e}")
        return ""
    # ponytail: compact single-line for .env storage
    return json.dumps(obj, separators=(",", ":"))


def cmd_set(bara: str | None = None) -> None:
    """Satter nycklarna interaktivt. `bara` begransar till en enda.

    Filtret finns for att den vanliga anledningen att kora skriptet ar att EN
    nyckel har roterat. Utan det maste man Enter-trycka sig forbi de andra, och
    ett skript man klickar igenom ar ett skript man till slut klickar fel i.
    """
    if bara is not None and bara not in {key.name for key in KEYS}:
        sys.exit(f"Okand nyckel: {bara}. Kanda: {', '.join(key.name for key in KEYS)}")

    guard_gitignored()
    print(f"Repo: {ROOT}")
    print("Lämna tomt för att hoppa över (befintligt värde behålls).")
    print("GEMINI_API_KEY är den som driver agenten i drift — börja där.\n")

    for key in KEYS:
        if bara is not None and key.name != bara:
            continue
        if key.generated and bara is None:
            continue  # eget kommando, klistras aldrig in för hand
        current = read_env(key.files[0]).get(key.name, "")
        marker = " [redan satt]" if current and not looks_placeholder(current) else ""
        print(f"{key.name}{marker}")
        print(f"  {key.blurb}")
        print(f"  Hämtas här: {key.where}")
        if key.name == "GOOGLE_SERVICE_ACCOUNT_JSON":
            value = _read_service_account_json()
        else:
            value = getpass.getpass("  Klistra in (syns inte): ").strip()
        if not value:
            print("  -> hoppar över\n")
            continue
        if looks_placeholder(value):
            print("  -> VARNING: ser ut som en platshållare, sparar ändå\n")
        for path in key.files:
            upsert(path, key.name, value)
        print(f"  -> sparad i {', '.join(p.name for p in key.files)}\n")

    satta = []
    for path, pairs in FIXED.items():
        befintliga = read_env(path)
        for name, value in pairs.items():
            # OBS: `looks_placeholder` duger INTE här. Den mäter nyckellängd
            # (<20 tecken = platshållare), och ett providernamn är kort per
            # definition — "gemini" är sex tecken. Ett första försök använde
            # den och skrev över `LLM_PROVIDER=gemini` ändå. För de här
            # fälten finns bara två lägen: satt eller osatt.
            if befintliga.get(name, "").strip():
                continue  # någon har valt ett värde — rör det inte
            upsert(path, name, value)
            satta.append(f"{name}={value}")
    if satta:
        print("Satte startvärden: " + ", ".join(satta) + "\n")
    else:
        print("Provider och modell var redan satta — lämnade dem orörda.\n")
    cmd_check()


def cmd_new_unlock_key() -> None:
    """Genererar SNAJP_SKILL_UNLOCK_KEY och committar bara dess sha256.

    Nyckeln skrivs ALDRIG till stdout. Den hamnar direkt i den gitignorerade
    snajp-support/.env och existerar därefter bara där. Det är hela poängen:
    en nyckel du har sett är en nyckel som ligger i ett terminaltranskript, och
    repot har redan bränt en Vercel-token på precis det sättet (STATUS.md
    2026-07-30).

    Roterar du nyckeln måste .unlock-hash committas, annars kan ingen annan
    maskin verifiera den.
    """
    guard_gitignored()
    existing = read_env(BACKEND_ENV).get("SNAJP_SKILL_UNLOCK_KEY", "")
    if existing:
        answer = input(
            "SNAJP_SKILL_UNLOCK_KEY finns redan. Rotera den? Den gamla slutar "
            "fungera direkt. [j/N]: "
        ).strip().lower()
        if answer not in ("j", "ja", "y", "yes"):
            print("Avbrutet — nyckeln är oförändrad.")
            return

    key = secrets.token_urlsafe(32)
    upsert(BACKEND_ENV, "SNAJP_SKILL_UNLOCK_KEY", key)

    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    UNLOCK_HASH.parent.mkdir(parents=True, exist_ok=True)
    UNLOCK_HASH.write_text(digest + "\n", encoding="utf-8")
    del key  # inget kvar i minnet efter den här punkten som skrivs ut

    print(f"Nyckeln skrevs till {BACKEND_ENV.relative_to(ROOT).as_posix()} (visas inte).")
    print(f"sha256 skrevs till {UNLOCK_HASH.relative_to(ROOT).as_posix()}: {digest}")
    print("\nCOMMITTA agent-core/.unlock-hash. Nyckeln själv committas aldrig.")


#: Nycklar som backend-tjänsten behöver, oavsett värd. Master- och demo-
#: nycklarna står INTE här: de är miljöspecifika med flit och sätts av
#: railway_provision.py, som slumpar en egen per miljö.
BACKEND_KEYS = (
    "DEEPSEEK_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "SCRAPEGRAPHAI_API_KEY",
    "SNAJP_SKILL_UNLOCK_KEY",
)

#: Bakåtkompatibelt namn från tiden då listan delades med en andra värd.
#: Railway är den enda värden sedan Render-vägen togs bort 2026-11-18.
RAILWAY_BACKEND_KEYS = BACKEND_KEYS


def cmd_push_railway() -> None:
    """Skicka backend-nycklarna till BÅDA Railway-miljöerna och verifiera.

    Verifieringen är poängen. En satt variabel bevisar bara att API:t tog emot
    den; att `/health/ready` går från `simulation` till `live` bevisar att
    nyckeln faktiskt går att använda. Skillnaden kostade en hel felsökning.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import json
    import time
    import urllib.request

    from railway_provision import (ENVIRONMENTS, env_read, envs_by_name,
                                   services_by_name, set_vars, state, deploy)

    backend = read_env(BACKEND_ENV)
    payload = {}
    for name in RAILWAY_BACKEND_KEYS:
        value = backend.get(name, "")
        if not value:
            print(f"  {name}: saknas lokalt — hoppar över")
            continue
        fault = key_fault(value, name)
        if fault:
            sys.exit(f"AVBRYTER: {name} {fault}. Sätt om den med `python scripts/keys.py` först.")
        payload[name] = value
    if not payload:
        sys.exit("Inga nycklar att skicka.")
    print(f"skickar: {', '.join(sorted(payload))}")   # namn, aldrig värden

    project = state()
    environments = envs_by_name(project)
    services = services_by_name(project)
    deploys = {}
    for env_name in ENVIRONMENTS:
        if env_name not in environments:
            print(f"  {env_name}: miljön finns inte — hoppar över")
            continue
        env_id = environments[env_name]
        set_vars(services["api"]["id"], env_id, payload)
        deploys[env_name] = deploy(services["api"]["id"], env_id)
        print(f"  {env_name}: satt, deploy {deploys[env_name]}")

    store = env_read()
    print("\nVerifierar mot /health/ready (kan ta en minut per miljö):")
    failed = False
    for env_name in deploys:
        url = store.get(f"RAILWAY_{env_name.upper()}_API_URL")
        if not url:
            print(f"  {env_name}: ingen API-URL i .env.deploy — kan inte verifiera")
            failed = True
            continue
        mode = None
        # time.sleep mellan försöken, inte trettio varv på tre sekunder: en
        # omdeploy tar en till tre minuter, och utan paus svarar loopen
        # "simulation" om en nyckel som är korrekt satt. Ett falskt nej här
        # leder till att någon sätter om en nyckel som aldrig var fel.
        for forsok in range(30):
            try:
                with urllib.request.urlopen(f"{url}/health/ready", timeout=20) as resp:
                    mode = json.load(resp).get("mode")
            except Exception:
                mode = None
            if mode == "live":
                break
            time.sleep(10)
        print(f"  {env_name}: mode={mode}")
        if mode != "live":
            failed = True
    if failed:
        sys.exit("Minst en miljö gick inte till live-läge. Se /health/ready för skälet.")
    print("\nBåda miljöerna kör med riktig modell.")


#: Lägena app/leads/jev.py förstår. "pa" fäller kandidater före research.
JEV_LAGEN = ("off", "skugga", "pa")


def _jev_levande(nyckel: str) -> str | None:
    """Ett riktigt Jev-anrop. None = nyckeln fungerar, annars felet.

    En satt variabel bevisar inte att nyckeln duger (skillens fallgrop 7);
    ett svar med en sannolikhet gör det."""
    import json
    import urllib.request

    kropp = json.dumps(
        {
            "state": {"company": "Exempel AB", "excerpt": "Vi säljer hemsidor till småföretag."},
            "model": "jev-1.13.0",
            "questions": {"test": {"type": "noul", "instructions": "Does this company sell websites?"}},
        }
    ).encode("utf-8")
    anrop = urllib.request.Request(
        "https://api.typesafe.ai/v1/systemone",
        data=kropp,
        headers={"Authorization": f"Bearer {nyckel}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(anrop, timeout=30) as svar:
            p = json.load(svar).get("answers", {}).get("test", {}).get("noul")
    except Exception as fel:  # noqa: BLE001 — felet rapporteras, värdet aldrig
        return f"{type(fel).__name__}"
    return None if isinstance(p, (int, float)) else "svaret saknade en sannolikhet"


def cmd_push_jev(env_name: str, lage: str) -> None:
    """TYPESAFE_API_KEY + IRIS_JEV till api-tjänsten i EN Railway-miljö.

    Medvetet inte en del av --push-railway: den skickar till BÅDA miljöerna,
    och Jev ska inte nå produktion förrän Iris-profilen är släppt dit
    (produktionsrelease kräver Antons ord). Nyckeln provas skarpt mot TypeSafe
    INNAN den skickas, så en felklistrad nyckel aldrig deployas.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from railway_provision import deploy, envs_by_name, services_by_name, set_vars, state

    nyckel = read_env(BACKEND_ENV).get("TYPESAFE_API_KEY", "")
    if not nyckel:
        sys.exit("TYPESAFE_API_KEY saknas lokalt. Kör först: python scripts/keys.py --key TYPESAFE_API_KEY")
    fault = key_fault(nyckel, "TYPESAFE_API_KEY")
    if fault:
        sys.exit(f"AVBRYTER: TYPESAFE_API_KEY {fault}.")
    print(f"TYPESAFE_API_KEY: {len(nyckel)} tecken, slutar på …{nyckel[-4:]}")
    fel = _jev_levande(nyckel)
    if fel:
        sys.exit(f"AVBRYTER: Jev svarade inte med nyckeln ({fel}). Inget skickat.")
    print("Jev svarade med en sannolikhet — nyckeln fungerar.")

    project = state()
    environments = envs_by_name(project)
    if env_name not in environments:
        sys.exit(f"Miljön {env_name} finns inte i Railway-projektet.")
    service_id = services_by_name(project)["api"]["id"]
    set_vars(service_id, environments[env_name], {"TYPESAFE_API_KEY": nyckel, "IRIS_JEV": lage})
    print(f"{env_name}: TYPESAFE_API_KEY och IRIS_JEV={lage} satta, deploy {deploy(service_id, environments[env_name])}")
    print("Verifiera efter deployen: Iris › Inställningar visar Jev-raden, och "
          "GET /api/leads/jev/statistik svarar med lage=" + lage + ".")


def cmd_set_railway_token() -> None:
    """Railway-tokenen. Samma delegering och samma skal som ovriga."""
    skript = Path(__file__).resolve().parent / "set_railway_token.py"
    if not skript.exists():
        sys.exit(f"Hittar inte {skript.name}.")
    raise SystemExit(subprocess.call([sys.executable, str(skript)]))


def cmd_set_railway_db() -> None:
    """Delegerar till set_railway_postgres_url.py — ingen kopierad logik.

    Skillen (api-key-setup) vill ha EN ingång per projekt, och det är den här
    filen. Verifieringen mot databasen bor i det dedikerade skriptet; två kopior
    av den logiken hade glidit isär. Samma tolk används med flit — annars kan
    psycopg2 saknas i den som startar.
    """
    skript = Path(__file__).resolve().parent / "set_railway_postgres_url.py"
    if not skript.exists():
        sys.exit(f"Hittar inte {skript.name}.")
    raise SystemExit(subprocess.call([sys.executable, str(skript), "--env", "development"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Nyckelhantering för snipra/snajp.")
    parser.add_argument("--check", action="store_true", help="verifiera utan att ändra")
    parser.add_argument("--push-railway", action="store_true",
                        help="skicka backend-nycklarna till BÅDA Railway-miljöerna och verifiera")
    parser.add_argument(
        "--key",
        metavar="NAMN",
        help="sätt EN nyckel i stället för att gå igenom alla (t.ex. DEEPSEEK_API_KEY)",
    )
    parser.add_argument(
        "--set-railway-db",
        action="store_true",
        help="sätt RAILWAY_DEVELOPMENT_PG_* (lösenord via getpass, verifieras mot databasen)",
    )
    parser.add_argument(
        "--set-railway-token",
        action="store_true",
        help="satt RAILWAY_TOKEN (via getpass, verifieras mot Railways API)",
    )
    parser.add_argument(
        "--push-jev",
        metavar="MILJO",
        choices=("development", "main"),
        help="skicka TYPESAFE_API_KEY + IRIS_JEV till api i EN Railway-miljö (provas skarpt först)",
    )
    parser.add_argument(
        "--jev-lage",
        default="skugga",
        choices=JEV_LAGEN,
        help="Jevs läge vid --push-jev: off, skugga (standard) eller pa",
    )
    parser.add_argument(
        "--new-unlock-key",
        action="store_true",
        help="generera SNAJP_SKILL_UNLOCK_KEY (värdet skrivs aldrig ut)",
    )
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if cmd_check() else 1)
    if args.set_railway_db:
        cmd_set_railway_db()
    elif args.set_railway_token:
        cmd_set_railway_token()
    elif args.new_unlock_key:
        cmd_new_unlock_key()
    elif args.push_railway:
        cmd_push_railway()
    elif args.push_jev:
        cmd_push_jev(args.push_jev, args.jev_lage)
    else:
        cmd_set(args.key)


if __name__ == "__main__":
    main()
