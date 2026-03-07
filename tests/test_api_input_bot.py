from meshdash.api_input_bot import BotSettingsRequest, parse_bot_settings_request


def test_parse_bot_settings_request_handles_valid_bool_values():
    parsed = parse_bot_settings_request(
        b'{"enabled":true,"log_enabled":"0","gameEnabled":"yes"}'
    )
    assert isinstance(parsed, BotSettingsRequest)
    assert parsed.enabled is True
    assert parsed.log_enabled is False
    assert parsed.game_enabled is True


def test_parse_bot_settings_request_handles_invalid_or_missing_values():
    parsed = parse_bot_settings_request(b'{"enabled":"maybe"}')
    assert parsed.enabled is None
    assert parsed.log_enabled is None
    assert parsed.game_enabled is None

    invalid = parse_bot_settings_request(b"{not-json}")
    assert invalid.enabled is None
    assert invalid.log_enabled is None
    assert invalid.game_enabled is None

