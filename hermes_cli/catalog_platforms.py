"""Messaging platforms the curated plugin catalog offers that this home does not provide yet.

``hermes gateway setup``, ``hermes setup gateway``, the dashboard Channels page and the Desktop
Messaging page list the same rows and install a pick through the same path: the catalog install
``hermes plugins install <name>`` uses (pinned commit, kill list, security scan), then enable, so
the platform is configurable the moment the install returns. Only Nous-built entries are offered
here (``official`` / ``verified`` tiers and the Hermes Labs repo); community platforms stay in the
plugin browser, where their unreviewed status is the first thing shown. A Hermes Labs entry needs
an explicit confirmation: it is built by Nous Research but not supported.

Callers bind the owning profile (``_profile_scope`` / ``-p``) before calling; every read and the
install resolve ``get_hermes_home()``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Collection, Literal, Optional

LABS_REPO = "github.com/nousresearch/hermes-labs-plugins"
Badge = Literal["official", "verified", "labs"]
_TIER_BADGES: dict[str, Badge] = {"official": "official", "verified": "verified"}
# Why a row cannot install, keyed by the reason code the surfaces translate.
LAZY_OFF = "lazy_installs_off"
BLOCKED_SENTENCES = {
    LAZY_OFF: "security.allow_lazy_installs is off, so Hermes does not install plugins from setup.",
}


@dataclass(frozen=True)
class CatalogPlatform:
    """One not-installed catalog platform row. ``blocked`` is empty when a pick can install it, else
    a :data:`BLOCKED_SENTENCES` key; ``install_command`` is the one command that installs it into
    this home either way."""

    name: str
    title: str
    badge: Badge
    summary: str
    disclosure: str
    blocked: str
    install_command: str

    @property
    def needs_confirm(self) -> bool:
        return self.badge == "labs"

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "needs_confirm": self.needs_confirm,
                "blocked_reason": BLOCKED_SENTENCES.get(self.blocked, "")}


def badge_for(entry: Any) -> Optional[Badge]:
    """The row badge for a catalog entry, or None when this list does not offer it."""
    from hermes_cli.plugin_catalog import _normalize_repo
    if _normalize_repo(entry.repo) == LABS_REPO:
        return "labs"
    return _TIER_BADGES.get(entry.tier)


def provided_platforms() -> frozenset[str]:
    """Platform ids and owning plugin names the bound home already loads (built-in or plugin)."""
    from hermes_cli.plugins import discover_plugins
    from gateway.platform_registry import platform_registry
    discover_plugins()
    return frozenset(name for entry in platform_registry.all_entries()
                     for name in (entry.name, entry.plugin_name) if name)


def _runs_here(entry: Any) -> bool:
    from hermes_cli.plugins_cmd_catalog import catalog_hermes_error, normalized_platforms
    from hermes_platform.host.facts import os_family
    if entry.platforms and os_family() not in normalized_platforms(entry.platforms):
        return False
    return catalog_hermes_error(entry) is None


def available_catalog_platforms(provided: Optional[Collection[str]] = None) -> list[CatalogPlatform]:
    """Catalog ``category: platform`` entries this list offers that nothing loaded provides, sorted by
    title. A removed (kill-listed) entry, one for another OS or one this Hermes is too old for is left
    out: its install would be refused. Never raises; an unreadable catalog lists nothing."""
    from hermes_cli.default_plugins import fetch_allowed
    from hermes_cli.memory_provider_migration import _install_command
    from hermes_cli.plugin_catalog import load_catalog_live, match_removed, resolved_removed_entries
    from hermes_cli.plugin_catalog_presence import disclosure, first_sentence
    from hermes_constants import get_hermes_home

    home = get_hermes_home()
    have = provided_platforms() if provided is None else frozenset(provided)
    entries = [e for e in load_catalog_live() if e.category == "platform" and e.name not in have]
    offered: list[tuple[Any, Badge]] = []
    for entry in entries:
        badge = badge_for(entry)
        if badge is not None:
            offered.append((entry, badge))
    if not offered:
        return []
    removed = resolved_removed_entries()
    blocked = "" if fetch_allowed(home) else LAZY_OFF
    rows = [CatalogPlatform(name=e.name, title=e.title or e.name, badge=badge,
                            summary=first_sentence(e.description), disclosure=disclosure(e.description),
                            blocked=blocked, install_command=_install_command(e.name, home))
            for e, badge in offered
            if not (match_removed(e.name, removed) or match_removed(e.repo, removed)) and _runs_here(e)]
    return sorted(rows, key=lambda row: row.title.lower())


def platforms_of(plugin_name: str) -> list[str]:
    """Platform ids *plugin_name* registered in this process (after its install loaded it)."""
    from gateway.platform_registry import platform_registry
    return [entry.name for entry in platform_registry.all_entries() if entry.plugin_name == plugin_name]


def install_catalog_platform(name: str, *, confirmed: bool = False) -> dict[str, Any]:
    """Install and enable catalog platform *name* into the bound home. ``{"ok": True, "plugin_name",
    "platforms": [ids], "warnings"}`` on success; else ``{"ok": False, "error", "install_command"}``,
    plus ``"confirm_required": True`` when *name* is a Hermes Labs entry and *confirmed* is False.
    Only a row :func:`available_catalog_platforms` offers installs: a community or unknown name is
    refused here, never installed past the list's tier rule."""
    from hermes_cli.left_core_migration import _first_cause
    from hermes_cli.plugins_cmd_install import dashboard_install_plugin
    from hermes_cli.plugins import discover_plugins

    row = next((r for r in available_catalog_platforms() if r.name == name), None)
    if row is None:
        return {"ok": False, "error": f"'{name}' is not a catalog platform this home can add.", "install_command": ""}
    if row.blocked:
        return {"ok": False, "error": BLOCKED_SENTENCES[row.blocked], "install_command": row.install_command}
    if row.needs_confirm and not confirmed:
        return {"ok": False, "confirm_required": True, "error": "Hermes Labs plugins need an explicit confirmation.",
                "install_command": row.install_command}
    result = dashboard_install_plugin("", force=False, enable=True, catalog_name=name)
    if not result.get("ok"):
        return {"ok": False, "error": _first_cause(str(result.get("error") or "")),
                "install_command": row.install_command}
    plugin_name = str(result.get("plugin_name") or name)
    discover_plugins()
    return {"ok": True, "plugin_name": plugin_name, "platforms": platforms_of(plugin_name),
            "warnings": list(result.get("warnings") or [])}
