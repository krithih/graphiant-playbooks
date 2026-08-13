# -*- coding: utf-8 -*-
# Copyright (c) Graphiant, Inc. | GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt)
"""Unit tests for graphiant_local_extranet_info module (mocked Ansible + connection)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ansible_collections.graphiant.naas.plugins.modules import graphiant_local_extranet_info


def _base_params() -> dict:
    return {
        "host": "https://api.example.com",
        "username": "u",
        "password": "p",
        "access_token": None,
        "query": "policies_summary",
        "policy_name": None,
        "is_provider": None,
        "detailed_logs": False,
    }


def test_execute_with_logging_wraps_plain_dict_as_result_data() -> None:
    """
    Regression: manager query methods (get_policies_summary, get_device_status, ...) return
    their payload directly (e.g. {"policies": [...]}), with no "result_msg" key of their own
    — the whole dict must be preserved as result_data, not dropped.
    """
    module = MagicMock()
    module.params = {"detailed_logs": False}

    out = graphiant_local_extranet_info.execute_with_logging(
        module, lambda: {"policies": [{"id": 1, "name": "local-extranet-policy-1"}]}, success_msg="ok"
    )

    assert out["result_msg"] == "ok"
    assert out["result_data"] == {"policies": [{"id": 1, "name": "local-extranet-policy-1"}]}


def test_execute_with_logging_non_dict_result_returns_empty_result_data() -> None:
    module = MagicMock()
    module.params = {"detailed_logs": False}

    out = graphiant_local_extranet_info.execute_with_logging(module, lambda: None, success_msg="ok")

    assert out["result_msg"] == "ok"
    assert out["result_data"] == {}


@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet_info.get_graphiant_connection")
@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet_info.AnsibleModule")
def test_main_policies_summary_calls_get_policies_summary(mock_ansible_module, mock_get_connection) -> None:
    mod = MagicMock()
    mod.check_mode = False
    mod.params = _base_params()
    mock_ansible_module.return_value = mod

    local_extranet = MagicMock()
    local_extranet.get_policies_summary.return_value = {
        "policies": [{"id": 1, "name": "local-extranet-policy-1", "sharedSegment": "lan-segment-3"}]
    }
    gc = MagicMock()
    gc.local_extranet = local_extranet
    mock_get_connection.return_value = MagicMock(graphiant_config=gc)

    graphiant_local_extranet_info.main()

    local_extranet.get_policies_summary.assert_called_once_with()
    mod.exit_json.assert_called_once()
    kwargs = mod.exit_json.call_args.kwargs
    assert kwargs["changed"] is False
    assert kwargs["query"] == "policies_summary"
    assert kwargs["result_data"]["policies"][0]["name"] == "local-extranet-policy-1"


@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet_info.get_graphiant_connection")
@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet_info.AnsibleModule")
def test_main_policy_device_status_passes_policy_name(mock_ansible_module, mock_get_connection) -> None:
    mod = MagicMock()
    mod.check_mode = False
    p = _base_params()
    p["query"] = "policy_device_status"
    p["policy_name"] = "local-extranet-policy-1"
    mod.params = p
    mock_ansible_module.return_value = mod

    local_extranet = MagicMock()
    local_extranet.get_device_status.return_value = {
        "policy_name": "local-extranet-policy-1",
        "devices": [{"deviceName": "edge-1-sdktest", "status": "SUCCESS"}],
    }
    gc = MagicMock()
    gc.local_extranet = local_extranet
    mock_get_connection.return_value = MagicMock(graphiant_config=gc)

    graphiant_local_extranet_info.main()

    local_extranet.get_device_status.assert_called_once_with("local-extranet-policy-1")
    kwargs = mod.exit_json.call_args.kwargs
    assert kwargs["result_data"]["devices"][0]["deviceName"] == "edge-1-sdktest"


@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet_info.get_graphiant_connection")
@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet_info.AnsibleModule")
def test_main_lan_segments_usage_passes_policy_name_and_is_provider(mock_ansible_module, mock_get_connection) -> None:
    mod = MagicMock()
    mod.check_mode = False
    p = _base_params()
    p["query"] = "lan_segments_usage"
    p["policy_name"] = "local-extranet-policy-1"
    p["is_provider"] = True
    mod.params = p
    mock_ansible_module.return_value = mod

    local_extranet = MagicMock()
    local_extranet.get_lan_segments_usage.return_value = {"vrfs": []}
    gc = MagicMock()
    gc.local_extranet = local_extranet
    mock_get_connection.return_value = MagicMock(graphiant_config=gc)

    graphiant_local_extranet_info.main()

    local_extranet.get_lan_segments_usage.assert_called_once_with("local-extranet-policy-1", True)


@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet_info.get_graphiant_connection")
@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet_info.AnsibleModule")
def test_main_nat_usage_passes_policy_name(mock_ansible_module, mock_get_connection) -> None:
    mod = MagicMock()
    mod.check_mode = False
    p = _base_params()
    p["query"] = "nat_usage"
    p["policy_name"] = "local-extranet-policy-1"
    mod.params = p
    mock_ansible_module.return_value = mod

    local_extranet = MagicMock()
    local_extranet.get_nat_usage.return_value = {"allocatedCount": 0, "usageCount": 0, "allocations": []}
    gc = MagicMock()
    gc.local_extranet = local_extranet
    mock_get_connection.return_value = MagicMock(graphiant_config=gc)

    graphiant_local_extranet_info.main()

    local_extranet.get_nat_usage.assert_called_once_with("local-extranet-policy-1")


@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet_info.get_graphiant_connection")
@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet_info.AnsibleModule")
def test_main_unsupported_query_fails_json(mock_ansible_module, mock_get_connection) -> None:
    mod = MagicMock()
    mod.check_mode = False
    p = _base_params()
    p["query"] = "not-a-real-query"
    mod.params = p
    mock_ansible_module.return_value = mod
    mock_get_connection.return_value = MagicMock(graphiant_config=MagicMock())

    graphiant_local_extranet_info.main()

    mod.fail_json.assert_called_once()
    assert "Unsupported query" in mod.fail_json.call_args.kwargs["msg"]


@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet_info.get_graphiant_connection")
@patch("ansible_collections.graphiant.naas.plugins.modules.graphiant_local_extranet_info.AnsibleModule")
def test_main_exception_calls_fail_json(mock_ansible_module, mock_get_connection) -> None:
    mod = MagicMock()
    mod.check_mode = False
    mod.params = _base_params()
    mock_ansible_module.return_value = mod

    local_extranet = MagicMock()
    local_extranet.get_policies_summary.side_effect = RuntimeError("boom")
    gc = MagicMock()
    gc.local_extranet = local_extranet
    mock_get_connection.return_value = MagicMock(graphiant_config=gc)

    graphiant_local_extranet_info.main()

    mod.fail_json.assert_called_once()
    assert "boom" in mod.fail_json.call_args.kwargs["msg"]
