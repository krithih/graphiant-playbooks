# -*- coding: utf-8 -*-
# Copyright (c) Graphiant, Inc. | GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt)
"""Unit tests for graphiant_local_extranet module (mocked Ansible + connection)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ansible_collections.graphiant.naas.plugins.modules import graphiant_local_extranet


def _base_params() -> dict:
    return {
        "host": "https://api.example.com",
        "username": "u",
        "password": "p",
        "access_token": None,
        "operation": "create_policies",
        "state": "present",
        "config_file": "sample_local_extranet_policies.yaml",
        "detailed_logs": False,
    }


def test_execute_with_logging_wraps_dict_result_with_changed_key() -> None:
    module = MagicMock()
    module.params = {"detailed_logs": False}

    out = graphiant_local_extranet.execute_with_logging(
        module,
        lambda: {"changed": True, "created": ["p1"], "skipped": []},
        success_msg="ok",
    )

    assert out["changed"] is True
    assert out["result_msg"] == "ok"
    assert out["details"] == {"changed": True, "created": ["p1"], "skipped": []}


def test_execute_with_logging_non_dict_result_uses_default_success() -> None:
    module = MagicMock()
    module.params = {"detailed_logs": False}

    out = graphiant_local_extranet.execute_with_logging(module, lambda: None, success_msg="ok")

    assert out["changed"] is True
    assert out["result_msg"] == "ok"


@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet.get_graphiant_connection")
@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet.AnsibleModule")
def test_main_create_policies_calls_create_policies(mock_ansible_module, mock_get_connection) -> None:
    mod = MagicMock()
    mod.check_mode = False
    mod._diff = False
    mod.params = _base_params()
    mock_ansible_module.return_value = mod

    local_extranet = MagicMock()
    local_extranet.create_policies.return_value = {
        "changed": True,
        "created": ["local-extranet-policy-1"],
        "skipped": [],
    }
    gc = MagicMock()
    gc.local_extranet = local_extranet
    mock_get_connection.return_value = MagicMock(graphiant_config=gc)

    graphiant_local_extranet.main()

    local_extranet.create_policies.assert_called_once()
    args, kwargs = local_extranet.create_policies.call_args
    assert args[0] == "sample_local_extranet_policies.yaml"
    assert kwargs["diff_mode"] is False
    mod.exit_json.assert_called_once()
    exit_kwargs = mod.exit_json.call_args.kwargs
    assert exit_kwargs["changed"] is True
    assert exit_kwargs["operation"] == "create_policies"


@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet.get_graphiant_connection")
@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet.AnsibleModule")
def test_main_update_policies_calls_update_policies(mock_ansible_module, mock_get_connection) -> None:
    mod = MagicMock()
    mod.check_mode = False
    p = _base_params()
    p["operation"] = "update_policies"
    p["config_file"] = "sample_local_extranet_policies_update.yaml"
    mod.params = p
    mock_ansible_module.return_value = mod

    local_extranet = MagicMock()
    local_extranet.update_policies.return_value = {
        "changed": True,
        "updated": ["local-extranet-policy-1"],
        "skipped": [],
    }
    gc = MagicMock()
    gc.local_extranet = local_extranet
    mock_get_connection.return_value = MagicMock(graphiant_config=gc)

    graphiant_local_extranet.main()

    local_extranet.update_policies.assert_called_once_with("sample_local_extranet_policies_update.yaml")
    mod.exit_json.assert_called_once()
    assert mod.exit_json.call_args.kwargs["changed"] is True


@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet.get_graphiant_connection")
@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet.AnsibleModule")
def test_main_update_policies_check_mode_uses_check_mode_success_message(
    mock_ansible_module, mock_get_connection
) -> None:
    mod = MagicMock()
    mod.check_mode = True
    p = _base_params()
    p["operation"] = "update_policies"
    mod.params = p
    mock_ansible_module.return_value = mod

    local_extranet = MagicMock()
    local_extranet.update_policies.return_value = {
        "changed": False,
        "updated": [],
        "skipped": ["local-extranet-policy-1"],
    }
    gc = MagicMock()
    gc.local_extranet = local_extranet
    mock_get_connection.return_value = MagicMock(graphiant_config=gc)

    graphiant_local_extranet.main()

    # success_msg is consumed by execute_with_logging (popped from kwargs before calling the
    # manager method) and surfaces in the exit payload's "msg", not in update_policies' own args.
    local_extranet.update_policies.assert_called_once_with("sample_local_extranet_policies.yaml")
    assert "Check mode" in mod.exit_json.call_args.kwargs["msg"]


@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet.get_graphiant_connection")
@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet.AnsibleModule")
def test_main_delete_policies_calls_delete_policies(mock_ansible_module, mock_get_connection) -> None:
    mod = MagicMock()
    mod.check_mode = False
    p = _base_params()
    p["operation"] = None
    p["state"] = "absent"
    mod.params = p
    mock_ansible_module.return_value = mod

    local_extranet = MagicMock()
    local_extranet.delete_policies.return_value = {
        "changed": True,
        "deleted": ["local-extranet-policy-1"],
        "skipped": [],
    }
    gc = MagicMock()
    gc.local_extranet = local_extranet
    mock_get_connection.return_value = MagicMock(graphiant_config=gc)

    graphiant_local_extranet.main()

    local_extranet.delete_policies.assert_called_once_with("sample_local_extranet_policies.yaml")
    mod.exit_json.assert_called_once()
    assert mod.exit_json.call_args.kwargs["operation"] == "delete_policies"


@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet.get_graphiant_connection")
@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet.AnsibleModule")
def test_main_missing_config_file_fails_json(mock_ansible_module, mock_get_connection) -> None:
    mod = MagicMock()
    mod.check_mode = False
    p = _base_params()
    p["config_file"] = None
    mod.params = p
    mock_ansible_module.return_value = mod
    mock_get_connection.return_value = MagicMock(graphiant_config=MagicMock())

    graphiant_local_extranet.main()

    mod.fail_json.assert_called_once()
    assert "config_file parameter is required" in mod.fail_json.call_args.kwargs["msg"]


@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet.get_graphiant_connection")
@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet.AnsibleModule")
def test_main_diff_mode_sets_diff_key(mock_ansible_module, mock_get_connection) -> None:
    mod = MagicMock()
    mod.check_mode = False
    mod._diff = True
    mod.params = _base_params()
    mock_ansible_module.return_value = mod

    local_extranet = MagicMock()
    local_extranet.create_policies.return_value = {
        "changed": True,
        "created": ["local-extranet-policy-1"],
        "skipped": [],
        "diff_plan": [
            {
                "device": "local-extranet-policy-1",
                "branch": "create",
                "before": {},
                "after": {"sharedSegment": 1},
            }
        ],
    }
    gc = MagicMock()
    gc.local_extranet = local_extranet
    mock_get_connection.return_value = MagicMock(graphiant_config=gc)

    graphiant_local_extranet.main()

    kwargs = mod.exit_json.call_args.kwargs
    assert "diff" in kwargs
    assert "local-extranet-policy-1" in kwargs["diff"]["before"]
    assert "local-extranet-policy-1" in kwargs["diff"]["after"]


@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet.get_graphiant_connection")
@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet.AnsibleModule")
def test_main_exception_calls_fail_json(mock_ansible_module, mock_get_connection) -> None:
    mod = MagicMock()
    mod.check_mode = False
    mod.params = _base_params()
    mock_ansible_module.return_value = mod

    local_extranet = MagicMock()
    local_extranet.create_policies.side_effect = RuntimeError("LAN segment 'lan-x' not found")
    gc = MagicMock()
    gc.local_extranet = local_extranet
    mock_get_connection.return_value = MagicMock(graphiant_config=gc)

    graphiant_local_extranet.main()

    mod.fail_json.assert_called_once()
    assert mod.fail_json.call_args.kwargs["operation"] == "create_policies"
