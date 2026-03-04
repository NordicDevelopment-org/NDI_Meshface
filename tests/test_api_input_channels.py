import pytest

from meshdash.api_input_channels import (
    ChannelSettingsRequest,
    parse_channel_settings_request,
)


def test_parse_channel_settings_request_defaults():
    request = parse_channel_settings_request(b"{}")
    assert request == ChannelSettingsRequest()


def test_parse_channel_settings_request_parses_action_role_settings_and_include_all():
    request = parse_channel_settings_request(
        b"""
        {
          "op": "UPSERT",
          "channel_index": "2",
          "role": " secondary ",
          "include_all": "false",
          "settings": {
            "name": "Ops",
            "psk": "base64:AAAA",
            "uplink_enabled": "yes",
            "downlink_enabled": 0,
            "module_settings": {"is_muted": true, "position_precision": 2},
            "ignored": "value"
          }
        }
        """
    )
    assert request.action == "upsert"
    assert request.channel_index == 2
    assert request.role == "SECONDARY"
    assert request.include_all is False
    assert request.settings == {
        "name": "Ops",
        "psk": "base64:AAAA",
        "uplink_enabled": True,
        "downlink_enabled": False,
        "module_settings": {"is_muted": True, "position_precision": 2},
    }


def test_parse_channel_settings_request_supports_flat_payload_fields():
    request = parse_channel_settings_request(
        b'{"action":"upsert","name":"Test","psk":"<redacted>","uplink_enabled":"1","downlink_enabled":"off"}'
    )
    assert request.action == "upsert"
    assert request.settings == {
        "name": "Test",
        "psk": "<redacted>",
        "uplink_enabled": True,
        "downlink_enabled": False,
    }


def test_parse_channel_settings_request_rejects_invalid_payload_shapes():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_channel_settings_request(b"{bad-json}")
    with pytest.raises(ValueError, match="Expected a JSON object"):
        parse_channel_settings_request(b'["not","object"]')
    with pytest.raises(ValueError, match="Unsupported action"):
        parse_channel_settings_request(b'{"action":"delete"}')
    with pytest.raises(ValueError, match="Invalid channel_index"):
        parse_channel_settings_request(b'{"channel_index":"not-a-number"}')
    with pytest.raises(ValueError, match="Expected 'settings' to be an object"):
        parse_channel_settings_request(b'{"settings":["bad"]}')

