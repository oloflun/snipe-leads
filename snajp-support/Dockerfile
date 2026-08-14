FROM python:3.12-slim

# Byggkontexten är REPO-ROTEN, inte snajp-support/ (render.yaml: rootDir: .).
#
# Skälet är tvingande: agent-core/ ligger utanför snajp-support/, och Docker
# kan inte COPY:a något utanför sin byggkontext. Med den gamla uppsättningen
# (rootDir: snajp-support) fanns agent-core/ inte ens som en möjlig källa.
#
# Layouten under /srv speglar repot exakt. Det är inte kosmetik: varje
# Path(__file__).parents[N] i kodbasen räknar katalognivåer, och de går sönder
# tyst om nivåerna inte stämmer.
#   registry.AGENT_CORE_ROOT  parents[3] -> /srv/agent-core
#   context_pack.VAR_ROOT     parents[2] -> /srv/snajp-support/var
#   config.model_config       parent.parent -> /srv/snajp-support/.env
WORKDIR /srv

COPY snajp-support/requirements.txt ./snajp-support/requirements.txt
RUN pip install --no-cache-dir -r snajp-support/requirements.txt

COPY snajp-support/app ./snajp-support/app

# UTAN den här raden startar containern GRÖNT och /health/live svarar OK —
# agentimporterna är uppskjutna in i request-handlers, så kraschen kommer
# först på det första riktiga agentanropet, som UnknownSkillError. Maskerat
# så länge DEEPSEEK_API_KEY saknas (simuleringsläge kortsluter före
# playbook-importen), vilket betyder att felet utlöses av att man sätter
# nyckeln för att gå live. Verifieras av docker-smoke-jobbet i verify.yml.
COPY agent-core ./agent-core

WORKDIR /srv/snajp-support

EXPOSE 8000
# Render (och liknande) injicerar $PORT; lokalt defaultar den till 8000.
ENV PORT=8000
HEALTHCHECK CMD python -c "import os,urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT','8000')}/health/live\")"
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
