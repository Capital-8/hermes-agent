"""Catalog platforms a home does not have yet: listed by every setup surface, installed on pick.

Also: a platform plugin installed after this process imported config is labelled and masked from
its own manifest on the Channels card, not shown as raw env names in plain text.
"""

import pytest

from gateway.platform_registry import PlatformEntry, platform_registry
from hermes_constants import get_hermes_home


@pytest.fixture
def in_tree_catalog(monkeypatch):
    from hermes_cli import plugin_catalog
    monkeypatch.setattr(plugin_catalog, "fetch_live_catalog", lambda **_: None)  # in-tree only, no network
    monkeypatch.delenv("HERMES_DISABLE_LAZY_INSTALLS", raising=False)  # the suite's opt-out; config decides here


def test_nous_built_catalog_platforms_are_offered_community_ones_are_not(in_tree_catalog):
    from hermes_cli.catalog_platforms import available_catalog_platforms

    rows = {row.name: row for row in available_catalog_platforms(provided=())}
    assert rows["yuanbao"].badge == "labs" and rows["yuanbao"].needs_confirm
    assert rows["xchat"].badge == "official" and not rows["xchat"].needs_confirm
    assert rows["yuanbao"].install_command == "hermes plugins install yuanbao"
    assert rows["yuanbao"].summary.startswith("Tencent Yuanbao messaging platform") and rows["yuanbao"].blocked == ""
    assert "fluxer-platform" not in rows  # community: offered in the plugin browser, not as a setup pick
    assert "yuanbao" not in {row.name for row in available_catalog_platforms(provided={"yuanbao"})}


def test_setup_menu_lists_catalog_platforms_and_lazy_off_says_why(in_tree_catalog):
    from hermes_cli import gateway

    rows = gateway._all_platforms(catalog=True)
    pick = next(p for p in rows if p["key"] == "yuanbao" and p.get("_catalog_platform"))
    assert gateway._platform_status(pick) == "not installed · Hermes Labs"
    assert not any(p.get("_catalog_platform") for p in gateway._all_platforms())  # summaries: no progress

    (get_hermes_home() / "config.yaml").write_text("security:\n  allow_lazy_installs: false\n", encoding="utf-8")
    from hermes_cli.catalog_platforms import install_catalog_platform
    refused = install_catalog_platform("yuanbao", confirmed=True)
    assert refused["ok"] is False and "allow_lazy_installs is off" in refused["error"]
    assert refused["install_command"] == "hermes plugins install yuanbao"


def test_platform_plugin_installed_after_import_is_labelled_and_masked():
    from hermes_cli.web_routers.messaging import _messaging_env_info
    from hermes_cli.web_server_messaging import _messaging_platform_catalog

    plugin_dir = get_hermes_home() / "plugins" / "lateplat"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        "name: lateplat\nkind: platform\nlabel: Late Platform\n"
        "requires_env:\n  - name: LATEPLAT_APP_SECRET\n    prompt: App Secret\n"
        "optional_env:\n  - name: LATEPLAT_ALLOWED_USERS\n    prompt: Allowed users\n    password: false\n",
        encoding="utf-8")
    entry = PlatformEntry(name="lateplat", label="Late Platform", adapter_factory=lambda cfg: None,
                          check_fn=lambda: True, required_env=["LATEPLAT_APP_SECRET"], plugin_name="lateplat")
    scope = platform_registry.current_scope_key()
    platform_registry.register(entry, scope=scope)
    try:
        card = next(c for c in _messaging_platform_catalog() if c["id"] == "lateplat")
        assert card["env_vars"] == ("LATEPLAT_APP_SECRET", "LATEPLAT_ALLOWED_USERS")
        secret = _messaging_env_info("LATEPLAT_APP_SECRET", card["env_info"].get("LATEPLAT_APP_SECRET"))
        assert secret["is_password"] is True and secret["prompt"] == "App Secret"
        assert _messaging_env_info("LATEPLAT_ALLOWED_USERS", card["env_info"]["LATEPLAT_ALLOWED_USERS"])["is_list"]
    finally:
        platform_registry.unregister("lateplat", scope=scope)
