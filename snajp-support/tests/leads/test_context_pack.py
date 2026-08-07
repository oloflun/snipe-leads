from app.leads.context_pack import (
    PRODUCT_MARKETING_RELATIVE_PATH,
    VAR_ROOT,
    materialize_product_marketing,
    render_context_pack,
)


def test_materialize_writes_file_at_the_path_skills_expect(tmp_path, monkeypatch):
    monkeypatch.setattr("app.leads.context_pack.VAR_ROOT", tmp_path)
    path = materialize_product_marketing("tenant-a", "# Livrustning\nSäljer kurser och hjärtstartare.")
    assert path == tmp_path / "tenant-a" / ".agents" / "product-marketing.md"
    assert path.read_text(encoding="utf-8") == "# Livrustning\nSäljer kurser och hjärtstartare."


def test_materialize_is_isolated_per_tenant(tmp_path, monkeypatch):
    monkeypatch.setattr("app.leads.context_pack.VAR_ROOT", tmp_path)
    materialize_product_marketing("tenant-a", "A:s data")
    materialize_product_marketing("tenant-b", "B:s data")
    path_a = tmp_path / "tenant-a" / ".agents" / "product-marketing.md"
    path_b = tmp_path / "tenant-b" / ".agents" / "product-marketing.md"
    assert path_a.read_text(encoding="utf-8") == "A:s data"
    assert path_b.read_text(encoding="utf-8") == "B:s data"


def test_render_context_pack_labels_with_the_exact_path_skills_check_for():
    rendered = render_context_pack(product_marketing="Vårt erbjudande...", customer_research=None)
    assert PRODUCT_MARKETING_RELATIVE_PATH in rendered
    assert "Vårt erbjudande..." in rendered


def test_render_context_pack_fallback_when_nothing_collected_yet():
    rendered = render_context_pack(product_marketing=None, customer_research=None)
    assert "Inget kontextdokument" in rendered
    assert "sektion för sektion" in rendered


def test_render_context_pack_includes_customer_research_when_present():
    rendered = render_context_pack(
        product_marketing="PM-innehåll", customer_research="Kundernas vanligaste problem: X"
    )
    assert "Kundernas vanligaste problem: X" in rendered
    assert "mk:customer-research" in rendered
