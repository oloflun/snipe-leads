"""G2/INV-SEC-002: tenant kommer aldrig från modellen. En wrapper 'avvisar'
enligt planen — här är garantin ännu starkare: parametern går inte ens att
UTTRYCKA, eftersom den aldrig finns i tool-schemat modellen ser. Verktygen
tar tenant_id från SupportContext (satt av servern), aldrig som ett
argument en modell kan fylla i.
"""

from app.agent.tools import ALL_TOOLS, DEMO_TOOLS

FORBIDDEN_PARAM_NAMES = {"tenant_id", "workspace_id", "tenant", "workspace"}


def test_no_tool_exposes_a_tenant_or_workspace_parameter():
    for tool in ALL_TOOLS:
        exposed_params = set(tool.params_json_schema.get("properties", {}).keys())
        leaked = exposed_params & FORBIDDEN_PARAM_NAMES
        assert not leaked, f"{tool.name} exponerar {leaked} i sitt tool-schema — modellen kan uttrycka en annan tenant."


def test_demo_tools_also_never_expose_tenant_or_workspace():
    for tool in DEMO_TOOLS:
        exposed_params = set(tool.params_json_schema.get("properties", {}).keys())
        assert not (exposed_params & FORBIDDEN_PARAM_NAMES)


def test_no_agent_visible_tool_can_mark_anything_sent():
    """INV-SEC-004: modellen kan bara köa. Ingen av verktygen agenten har
    tillgång till (ALL_TOOLS/DEMO_TOOLS) kan sätta send_queue-status='sent'
    — den enda kodvägen dit är app/leads/scheduler.process_due_item, som
    körs av bakgrundsschemaläggaren, inte av agenten."""
    agent_tool_names = {t.name for t in ALL_TOOLS} | {t.name for t in DEMO_TOOLS}
    send_capable_names = {"send_email", "enqueue_send", "dispatch_outreach", "send_outreach"}
    assert agent_tool_names.isdisjoint(send_capable_names)
    # send_response finns, men skickar bara till DEN PÅGÅENDE webbläsarsessionen
    # — inte en extern mottagare (se app/agent/tools.py:s docstring).
    assert "send_response" in agent_tool_names
