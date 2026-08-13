# -*- coding: utf-8 -*-
# Copyright (c) Graphiant, Inc. | GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt)
"""Unit tests for local_extranet_manager helpers (no live API)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ansible_collections.graphiant.naas.plugins.module_utils.libs.local_extranet_manager import (
    LocalExtranetManager,
)
from ansible_collections.graphiant.naas.plugins.module_utils.libs.exceptions import (
    ConfigurationError,
    DeviceNotFoundError,
    SiteNotFoundError,
)


def _make_manager() -> LocalExtranetManager:
    config_utils = MagicMock()
    config_utils.gsdk = MagicMock()
    config_utils.template = MagicMock()
    return LocalExtranetManager(config_utils)


def test_validate_cidr_prefixes_accepts_network_address() -> None:
    mgr = _make_manager()
    mgr._validate_cidr_prefixes(["10.1.1.0/24"], "policy1", "manual.prefixes")  # pylint: disable=protected-access


def test_validate_cidr_prefixes_rejects_non_network_address() -> None:
    mgr = _make_manager()
    with pytest.raises(ConfigurationError, match="invalid manual.prefixes prefix"):
        mgr._validate_cidr_prefixes(["10.1.1.5/24"], "policy1", "manual.prefixes")  # pylint: disable=protected-access


def test_validate_policy_prefixes_checks_all_prefix_sources() -> None:
    mgr = _make_manager()
    with pytest.raises(ConfigurationError, match="manual.prefixes"):
        mgr._validate_policy_prefixes(  # pylint: disable=protected-access
            {"manual": {"prefixes": ["10.1.1.5/24"]}}, "policy1"
        )


def test_resolve_policy_ids_raises_when_shared_segment_missing() -> None:
    mgr = _make_manager()
    mgr.gsdk.get_lan_segment_id.return_value = None
    with pytest.raises(ConfigurationError, match="LAN segment 'lan-1' not found"):
        mgr._resolve_policy_ids({"sharedSegment": "lan-1"}, "policy1")  # pylint: disable=protected-access


def test_resolve_policy_ids_resolves_names_to_ids() -> None:
    mgr = _make_manager()
    mgr.gsdk.get_lan_segment_id.side_effect = {"lan-1": 100, "lan-2": 200}.get
    mgr.gsdk.get_site_id.side_effect = {"site-a": 11}.get
    mgr.gsdk.get_device_id.side_effect = {"dev-a": 21}.get

    api_policy = {
        "sharedSegment": "lan-1",
        "targetSegments": ["lan-2"],
        "source": {"sites": ["site-a"], "excludedDevices": ["dev-a"]},
    }
    mgr._resolve_policy_ids(api_policy, "policy1")  # pylint: disable=protected-access

    assert api_policy["type"] == "enterprise"
    assert api_policy["sharedSegment"] == 100
    assert api_policy["targetSegments"] == [200]
    assert api_policy["source"]["sites"] == [11]
    assert api_policy["source"]["excludedDevices"] == [21]


def test_resolve_policy_ids_sends_int_type_for_update() -> None:
    # A live PUT confirmed the backend's update path only accepts "type" as a genuine JSON
    # int (2) -- the string "enterprise" (which works for create) and omitting it entirely
    # both failed with a backend foreign-key constraint violation on update.
    mgr = _make_manager()
    mgr.gsdk.get_lan_segment_id.return_value = 100

    api_policy = {"sharedSegment": "lan-1", "type": "enterprise"}
    mgr._resolve_policy_ids(api_policy, "policy1", for_update=True)  # pylint: disable=protected-access

    assert api_policy["type"] == 2
    assert isinstance(api_policy["type"], int)


def test_resolve_policy_target_ids_defaults_excluded_devices_to_empty_list() -> None:
    mgr = _make_manager()
    mgr.gsdk.get_site_id.return_value = 11

    target_config = {"sites": ["site-a"]}
    mgr._resolve_policy_target_ids(target_config, "policy1", "source")  # pylint: disable=protected-access

    assert target_config["excludedDevices"] == []


def test_resolve_policy_target_ids_raises_site_not_found() -> None:
    mgr = _make_manager()
    mgr.gsdk.get_site_id.return_value = None
    with pytest.raises(SiteNotFoundError):
        mgr._resolve_policy_target_ids(  # pylint: disable=protected-access
            {"sites": ["missing-site"]}, "policy1", "source"
        )


def test_resolve_policy_target_ids_raises_device_not_found() -> None:
    mgr = _make_manager()
    mgr.gsdk.get_device_id.return_value = None
    with pytest.raises(DeviceNotFoundError):
        mgr._resolve_policy_target_ids(  # pylint: disable=protected-access
            {"excludedDevices": ["missing-device"]}, "policy1", "source"
        )


def test_create_policies_skips_existing_policy() -> None:
    mgr = _make_manager()
    mgr.config_utils.render_config_file.return_value = {
        "local_extranet_policies": [{"name": "policy1", "sharedSegment": "lan-1"}]
    }
    mgr.gsdk.get_local_extranet_policy_by_name.return_value = SimpleNamespace(id=1, name="policy1")

    result = mgr.create_policies("dummy.yaml")

    assert result["changed"] is False
    assert result["skipped"] == ["policy1"]
    assert result["created"] == []
    mgr.gsdk.create_local_extranet_policy.assert_not_called()
    mgr.gsdk.apply_local_extranet_policy.assert_not_called()


def test_create_policies_creates_and_applies_new_policy() -> None:
    mgr = _make_manager()
    mgr.config_utils.render_config_file.return_value = {
        "local_extranet_policies": [
            {"name": "policy1", "sharedSegment": "lan-1", "targetSegments": ["lan-2"]}
        ]
    }
    mgr.gsdk.get_local_extranet_policy_by_name.return_value = None
    mgr.gsdk.get_lan_segment_id.side_effect = {"lan-1": 100, "lan-2": 200}.get
    mgr.gsdk.create_local_extranet_policy.return_value = {"id": 42}

    result = mgr.create_policies("dummy.yaml")

    assert result["changed"] is True
    assert result["created"] == ["policy1"]
    sent_policy = mgr.gsdk.create_local_extranet_policy.call_args[0][0]
    assert sent_policy["type"] == "enterprise"
    assert sent_policy["targetSegments"] == [200]
    mgr.gsdk.apply_local_extranet_policy.assert_called_once_with(42, None)


def test_create_policies_raises_when_created_policy_has_no_id() -> None:
    mgr = _make_manager()
    mgr.config_utils.render_config_file.return_value = {
        "local_extranet_policies": [{"name": "policy1", "sharedSegment": "lan-1"}]
    }
    mgr.gsdk.get_local_extranet_policy_by_name.return_value = None
    mgr.gsdk.get_lan_segment_id.return_value = 100
    mgr.gsdk.create_local_extranet_policy.return_value = {"id": None}

    with pytest.raises(ConfigurationError, match="no ID was returned"):
        mgr.create_policies("dummy.yaml")

    mgr.gsdk.apply_local_extranet_policy.assert_not_called()


def test_carry_over_prefix_set_id_fills_in_missing_id() -> None:
    mgr = _make_manager()
    desired = {"prefixSet": {"name": "list", "mode": "ipv4", "entries": {}}}
    current = {"prefixSet": {"name": "list", "id": 8621, "mode": "ipv4", "entries": []}}

    mgr._carry_over_prefix_set_id(desired, current)  # pylint: disable=protected-access

    assert desired["prefixSet"]["id"] == 8621


def test_carry_over_prefix_set_id_does_not_override_explicit_id() -> None:
    mgr = _make_manager()
    desired = {"prefixSet": {"name": "list", "id": 999, "mode": "ipv4", "entries": {}}}
    current = {"prefixSet": {"name": "list", "id": 8621, "mode": "ipv4", "entries": []}}

    mgr._carry_over_prefix_set_id(desired, current)  # pylint: disable=protected-access

    assert desired["prefixSet"]["id"] == 999


def test_build_prefix_set_entries_applies_defaults_and_seq() -> None:
    mgr = _make_manager()
    entries = mgr._build_prefix_set_entries(  # pylint: disable=protected-access
        [
            {"ipPrefix": "10.1.1.0/24"},  # neither given ("Exact"): both default to own length
            {"ipPrefix": "100.100.0.0/22", "maskUpper": 30},  # "Less & Equal": maskLower defaults to own length
            {"ipPrefix": "2.2.100.0/23", "maskLower": 27},  # "Greater & Equal": maskUpper defaults to 32
            {"ipPrefix": "70.0.0.0/23", "maskLower": 25, "maskUpper": 28},  # "Range": both explicit
        ],
        "policy1",
        "source.prefixSet",
    )

    assert entries == {
        "1": {"seq": 1, "ipPrefix": "10.1.1.0/24", "maskLower": 24, "maskUpper": 24},
        "2": {"seq": 2, "ipPrefix": "100.100.0.0/22", "maskLower": 22, "maskUpper": 30},
        "3": {"seq": 3, "ipPrefix": "2.2.100.0/23", "maskLower": 27, "maskUpper": 32},
        "4": {"seq": 4, "ipPrefix": "70.0.0.0/23", "maskLower": 25, "maskUpper": 28},
    }


def test_build_prefix_set_entries_rejects_invalid_cidr() -> None:
    mgr = _make_manager()
    with pytest.raises(ConfigurationError, match="invalid source.prefixSet prefix"):
        mgr._build_prefix_set_entries(  # pylint: disable=protected-access
            [{"ipPrefix": "10.1.1.5/24"}], "policy1", "source.prefixSet"
        )


def test_normalize_policy_target_detects_prefix_set_mask_change() -> None:
    mgr = _make_manager()
    current = {"prefixSet": {"name": "list", "mode": "ipv4", "entries": [{"seq": 1, "ipPrefix": "10.1.1.0/24"}]}}
    desired = {
        "prefixSet": {
            "name": "list",
            "mode": "ipv4",
            "entries": {"1": {"seq": 1, "ipPrefix": "10.1.1.0/24", "maskLower": 25, "maskUpper": 28}},
        }
    }

    # pylint: disable=protected-access
    assert mgr._normalize_policy_target(current) != mgr._normalize_policy_target(desired)
    assert mgr._normalize_policy_target(current) == mgr._normalize_policy_target(current)


def test_update_policies_raises_when_policy_missing() -> None:
    mgr = _make_manager()
    mgr.config_utils.render_config_file.return_value = {"local_extranet_policies": [{"name": "policy1"}]}
    mgr.gsdk.get_local_extranet_policy_by_name.return_value = None

    with pytest.raises(ConfigurationError, match="not found"):
        mgr.update_policies("dummy.yaml")


def test_delete_policies_skips_when_not_found() -> None:
    mgr = _make_manager()
    mgr.config_utils.render_config_file.return_value = {"local_extranet_policies": [{"name": "policy1"}]}
    mgr.gsdk.get_local_extranet_policy_by_name.return_value = None

    result = mgr.delete_policies("dummy.yaml")

    assert result["changed"] is False
    assert result["skipped"] == ["policy1"]
    assert result["deleted"] == []
    mgr.gsdk.delete_local_extranet_policy.assert_not_called()


def test_delete_policies_deletes_existing_policy() -> None:
    mgr = _make_manager()
    mgr.config_utils.render_config_file.return_value = {"local_extranet_policies": [{"name": "policy1"}]}
    mgr.gsdk.get_local_extranet_policy_by_name.return_value = SimpleNamespace(id=7, name="policy1")

    result = mgr.delete_policies("dummy.yaml")

    assert result["changed"] is True
    assert result["deleted"] == ["policy1"]
    mgr.gsdk.delete_local_extranet_policy.assert_called_once_with(7)
