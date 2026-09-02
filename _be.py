import json, urllib.request, urllib.error, sys
sys.path.insert(0, "scripts")
from railway_provision import env_read
E = env_read()
API = E["RAILWAY_DEVELOPMENT_API_URL"].rstrip("/")
NYCKEL = E["RAILWAY_DEVELOPMENT_DEMO_API_KEY"]

def anrop(vag, metod="GET", kropp=None, nyckel=None, timeout=120):
    data = json.dumps(kropp).encode() if kropp is not None else None
    r = urllib.request.Request(API + vag, data=data, method=metod, headers={
        "X-API-Key": nyckel or NYCKEL, "Content-Type": "application/json",
        "User-Agent": "snajp-qa/1.0"})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as sv:
            return sv.status, json.loads(sv.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        ra = e.read().decode()[:400]
        try: return e.code, json.loads(ra)
        except Exception: return e.code, {"ra": ra}
    except Exception as e:
        return 0, {"fel": str(e)[:200]}
