"""
Smoke tests - verify the system can import and basic operations work.

Run with: python -m pytest tests/test_smoke.py -v
"""

import json
from pathlib import Path


# ── Import Tests ──────────────────────────────────────────────────────────


def test_import_schema():
    from recorder.schema.workflow import Workflow, Step, Locator, Target

    w = Workflow()
    assert w.version == "1.0"
    assert w.steps == []


def test_import_skills():
    from recorder.skills import create_default_registry, create_context

    registry = create_default_registry()
    assert len(registry.skill_names) >= 10


def test_import_skill_base():
    from recorder.skills.base import SkillBase, SkillResult, SkillContext, SkillMode

    assert SkillMode.LOCAL.value == "local"
    assert SkillMode.HYBRID.value == "hybrid"
    assert SkillMode.SERVER.value == "server"


def test_import_portal_client():
    from recorder.skills.portal_client import PortalClient

    client = PortalClient()
    assert not client.is_configured
    assert not client.is_connected


# ── Skills Execution Tests ────────────────────────────────────────────────


def test_assertions_skill_pass():
    from recorder.skills import create_default_registry, create_context

    registry = create_default_registry()
    ctx = create_context(skill_mode="local")

    result = registry.execute(
        "assertions", ctx,
        actual_value="Hello World",
        expected_value="World",
        match_mode="contains",
    )
    assert result.success is True
    assert result.data["passed"] is True


def test_assertions_skill_fail():
    from recorder.skills import create_default_registry, create_context

    registry = create_default_registry()
    ctx = create_context(skill_mode="local")

    result = registry.execute(
        "assertions", ctx,
        actual_value="Hello",
        expected_value="Goodbye",
        match_mode="equals",
    )
    assert result.success is False
    assert "Assertion failed" in result.error


def test_assertions_regex():
    from recorder.skills import create_default_registry, create_context

    registry = create_default_registry()
    ctx = create_context(skill_mode="local")

    result = registry.execute(
        "assertions", ctx,
        actual_value="Order #12345 confirmed",
        expected_value=r"Order #\d+ confirmed",
        match_mode="regex",
    )
    assert result.success is True


def test_assertions_negate():
    from recorder.skills import create_default_registry, create_context

    registry = create_default_registry()
    ctx = create_context(skill_mode="local")

    result = registry.execute(
        "assertions", ctx,
        actual_value="Hello",
        expected_value="Goodbye",
        match_mode="equals",
        negate=True,
    )
    assert result.success is True


def test_variables_store_and_get():
    from recorder.skills import create_default_registry, create_context

    registry = create_default_registry()
    ctx = create_context(skill_mode="local")

    variables = {}

    # Store
    result = registry.execute(
        "variables", ctx,
        action="store",
        variable_name="user",
        value="admin",
        variables=variables,
    )
    assert result.success is True
    variables = result.data["variables"]

    # Get
    result = registry.execute(
        "variables", ctx,
        action="get",
        variable_name="user",
        variables=variables,
    )
    assert result.success is True
    assert result.data["value"] == "admin"


def test_variables_get_missing():
    from recorder.skills import create_default_registry, create_context

    registry = create_default_registry()
    ctx = create_context(skill_mode="local")

    result = registry.execute(
        "variables", ctx,
        action="get",
        variable_name="nonexistent",
        variables={},
    )
    assert result.success is False


def test_unknown_skill():
    from recorder.skills import create_default_registry, create_context

    registry = create_default_registry()
    ctx = create_context(skill_mode="local")

    result = registry.execute("nonexistent_skill", ctx)
    assert result.success is False
    assert "Unknown skill" in result.error


def test_server_skill_fails_in_local_mode():
    from recorder.skills import create_default_registry, create_context

    registry = create_default_registry()
    ctx = create_context(skill_mode="local")

    result = registry.execute("analytics", ctx, action="dashboard")
    assert result.success is False


# ── Context and Registry Tests ────────────────────────────────────────────


def test_create_context_from_settings():
    from recorder.skills import create_context

    ctx = create_context(
        settings={
            "portalUrl": "http://localhost:8000",
            "portalAccessToken": "test-token",
            "skillMode": "hybrid",
        }
    )
    assert ctx.skill_mode.value == "hybrid"
    assert ctx.portal_client is not None
    assert ctx.portal_client.base_url == "http://localhost:8000"
    assert ctx.portal_client.access_token == "test-token"


def test_create_context_no_portal():
    from recorder.skills import create_context

    ctx = create_context(skill_mode="local")
    assert ctx.portal_client is None


def test_registry_get_all_status():
    from recorder.skills import create_default_registry

    registry = create_default_registry()
    statuses = registry.get_all_status()
    assert len(statuses) >= 10

    names = [s["name"] for s in statuses]
    assert "record" in names
    assert "replay" in names
    assert "healing" in names
    assert "analytics" in names


# ── Portal Client Tests ───────────────────────────────────────────────────


def test_portal_client_unconfigured():
    from recorder.skills.portal_client import PortalClient

    client = PortalClient()
    assert not client.is_configured
    assert not client.is_connected


def test_portal_client_configured_but_unreachable():
    from recorder.skills.portal_client import PortalClient

    client = PortalClient(base_url="http://localhost:99999")
    assert client.is_configured
    assert not client.is_connected


def test_portal_client_health_check_unreachable():
    from recorder.skills.portal_client import PortalClient

    client = PortalClient(base_url="http://localhost:99999")
    result = client.check_health()
    assert result["connected"] is False


# ── Settings Tests ────────────────────────────────────────────────────────


def test_settings_file_exists():
    settings_path = Path(__file__).parent.parent / "data" / "settings.json"
    assert settings_path.exists()

    with open(settings_path) as f:
        settings = json.load(f)

    assert "skillMode" in settings
    assert settings["skillMode"] in ("local", "hybrid", "server")
    assert "serverFallback" in settings
    assert "maxTier" in settings


# ── Workflow Schema Tests ─────────────────────────────────────────────────


def test_workflow_schema():
    from recorder.schema.workflow import Workflow, Step, Target, Locator

    loc = Locator(type="css", value="#login", score=0.9)
    target = Target(locators=[loc])
    step = Step(id="s1", name="click login", type="click", target=target)
    workflow = Workflow(steps=[step])

    assert len(workflow.steps) == 1
    assert workflow.steps[0].target.locators[0].value == "#login"


def test_workflow_roundtrip():
    from recorder.schema.workflow import Workflow, Step, Target, Locator

    step = Step(
        id="s1", name="type user", type="input",
        target=Target(locators=[Locator(type="id", value="#user", score=0.95)]),
        input={"value": "admin"},
    )
    workflow = Workflow(steps=[step], metadata={"name": "test"})

    # Serialize and deserialize
    data = json.loads(workflow.model_dump_json())
    restored = Workflow(**data)
    assert restored.steps[0].input["value"] == "admin"


# ── Demo Workflow Tests ───────────────────────────────────────────────────


def test_demo_workflows_exist():
    workflows_dir = Path(__file__).parent.parent / "data" / "workflows"
    demo_files = list(workflows_dir.glob("demo-*.json"))
    assert len(demo_files) >= 1, "At least one demo workflow should be bundled"


def test_demo_workflow_valid():
    from recorder.schema.workflow import Workflow

    workflows_dir = Path(__file__).parent.parent / "data" / "workflows"
    demo_files = list(workflows_dir.glob("demo-*.json"))

    for demo_file in demo_files:
        with open(demo_file) as f:
            data = json.load(f)
        workflow = Workflow(**data)
        assert len(workflow.steps) > 0, f"{demo_file.name} should have steps"
