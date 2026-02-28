import pytest

from meshdash.api_input_radio import parse_radio_settings_request


def test_parse_radio_settings_request_defaults_missing_lora_to_empty_object():
    request = parse_radio_settings_request(b"{}")
    assert request.lora == {}


def test_parse_radio_settings_request_filters_to_supported_value_shapes():
    request = parse_radio_settings_request(
        b"""
        {
          "lora": {
            "region": "US",
            "tx_power": 17,
            "enabled": true,
            "channels": [1, "2", null],
            "none_field": null,
            "nested": {"bad": 1},
            "complex": [{"bad": 1}]
          }
        }
        """
    )

    assert request.lora == {
        "region": "US",
        "tx_power": 17,
        "enabled": True,
        "channels": [1, "2", None],
        "none_field": None,
    }


def test_parse_radio_settings_request_rejects_invalid_json():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_radio_settings_request(b"{not-json}")


def test_parse_radio_settings_request_rejects_non_object_payload():
    with pytest.raises(ValueError, match="Expected a JSON object"):
        parse_radio_settings_request(b'["not", "an", "object"]')


def test_parse_radio_settings_request_rejects_non_object_lora():
    with pytest.raises(ValueError, match="Expected 'lora' to be an object"):
        parse_radio_settings_request(b'{"lora": ["not", "an", "object"]}')
