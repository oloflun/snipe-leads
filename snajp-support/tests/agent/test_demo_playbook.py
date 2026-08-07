from app.agent.demo_playbook import DEMO_V1, render_demo_instructions
from app.agent.tools import ALL_TOOLS, DEMO_TOOLS


def test_demo_playbook_has_no_ticket_creating_steps():
    skills = [s.skill for s in DEMO_V1.steps]
    assert skills == ["cs:draft-response", "snajp:humanizer-svenska"]
    assert "cs:ticket-triage" not in skills
    assert "cs:customer-escalation" not in skills


def test_render_executes_both_steps_and_states_no_real_ticket_created():
    instructions, ledger = render_demo_instructions()
    assert ledger.executed_order == ["cs:draft-response", "snajp:humanizer-svenska"]
    assert "Ingen kund skapas, inget ärende öppnas" in instructions


def test_demo_tools_is_a_strict_subset_excluding_all_data_writing_tools():
    demo_tool_names = {t.name for t in DEMO_TOOLS}
    all_tool_names = {t.name for t in ALL_TOOLS}
    assert demo_tool_names < all_tool_names  # äkta delmängd, inte lika
    assert "find_or_create_customer" not in demo_tool_names
    assert "create_ticket" not in demo_tool_names
    assert "save_inbound_message" not in demo_tool_names
    assert "log_metric" not in demo_tool_names
    assert "escalate_to_human" not in demo_tool_names
    assert "search_knowledge_base" in demo_tool_names
    assert "send_response" in demo_tool_names
