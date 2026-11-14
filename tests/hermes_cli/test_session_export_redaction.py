"""Fail-closed redaction tests for sessions export --redact (#90361).

``redact_session_data`` used to walk only the ``messages``/``segments``
keys, so session-level string fields — most importantly the auto-generated
title, which quotes the first user message — escaped redaction and rendered
into the export header in plaintext despite an explicit ``--redact``. The
walk now covers every string in the export dict.
"""


def _fake_botfather_token() -> str:
    # BotFather shape: <10-digit id>:<35-char base64url-ish>, assembled to
    # avoid a credential-shaped literal in source.
    digits = "8" * 10
    tail = ("A" * 34) + "h"
    return digits + ":" + tail


def _fake_api_key() -> str:
    return "-".join(("sk", "probe" * 3, "key9")) + "XYZabcd"


def _session_fixture() -> dict:
    token = _fake_botfather_token()
    return {
        "id": "s1",
        "title": f"telegram setup with {token}",
        "cwd": "/tmp/x",
        "message_count": 3,
        "started_at": 1710000000,
        "messages": [
            {"role": "user", "content": f"use {token} please"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "tc1",
                        "function": {
                            "name": "send_message",
                            "arguments": f'{{"token": "{token}"}}',
                        },
                    }
                ],
            },
            {"role": "tool", "content": f"sent via {token}"},
        ],
    }


def test_markdown_export_header_and_body_contain_no_token():
    """--redact output must not contain the token anywhere, title header included (#90361)."""
    from hermes_cli.session_export_md import redact_session_data, render_session_markdown

    session = _session_fixture()
    md = render_session_markdown(redact_session_data(session), fmt="md")
    assert _fake_botfather_token() not in md
    assert _fake_botfather_token() in session["title"], "redaction must return a copy"


def test_credential_shaped_dict_key_redacted():
    from hermes_cli.session_export_md import redact_session_data

    session = _session_fixture()
    session["tool_result"] = {_fake_api_key(): "payload"}
    out = redact_session_data(session)
    assert _fake_api_key() not in str(out["tool_result"])
    assert "payload" in str(out["tool_result"])
