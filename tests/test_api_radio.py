import io

from meshdash.api_input_radio import RadioSettingsRequest
from meshdash.api_radio import handle_radio_settings_post


def _fake_handler(payload: bytes = b"{}"):
    class _H:
        headers = {"Content-Length": str(len(payload))}
        rfile = io.BytesIO(payload)

    return _H()


def _to_int(value):
    if value in (None, ""):
        return None
    return int(value)


def test_handle_radio_settings_post_disabled_returns_503():
    calls = []
    handle_radio_settings_post(
        _fake_handler(),
        apply_radio_settings_fn=None,
        to_int_fn=_to_int,
        validate_content_length_fn=lambda *_args, **_kwargs: 2,
        parse_radio_settings_request_fn=None,
        write_json_response_fn=lambda *_args, **kwargs: calls.append(kwargs),
    )

    assert calls[0]["status_code"] == 503
    assert calls[0]["payload_obj"]["ok"] is False


def test_handle_radio_settings_post_handles_invalid_size():
    calls = []

    def _raise_size(*_args, **_kwargs):
        raise ValueError("bad size")

    handle_radio_settings_post(
        _fake_handler(),
        apply_radio_settings_fn=lambda _request: {"ok": True},
        to_int_fn=_to_int,
        validate_content_length_fn=_raise_size,
        parse_radio_settings_request_fn=lambda _raw: RadioSettingsRequest(lora={}),
        write_json_response_fn=lambda *_args, **kwargs: calls.append(kwargs),
    )

    assert calls[0]["status_code"] == 400
    assert calls[0]["payload_obj"] == {"ok": False, "error": "Invalid request size"}


def test_handle_radio_settings_post_handles_parse_error():
    calls = []

    handle_radio_settings_post(
        _fake_handler(b'{"lora":{"tx_power":17}}'),
        apply_radio_settings_fn=lambda _request: {"ok": True},
        to_int_fn=_to_int,
        validate_content_length_fn=lambda *_args, **_kwargs: len(b'{"lora":{"tx_power":17}}'),
        parse_radio_settings_request_fn=lambda _raw: (_ for _ in ()).throw(ValueError("invalid payload")),
        write_json_response_fn=lambda *_args, **kwargs: calls.append(kwargs),
    )

    assert calls[0]["status_code"] == 400
    assert calls[0]["payload_obj"]["error"] == "invalid payload"


def test_handle_radio_settings_post_handles_apply_exception():
    calls = []

    def _raise_apply(_request):
        raise RuntimeError("boom")

    handle_radio_settings_post(
        _fake_handler(b'{"lora":{"tx_power":17}}'),
        apply_radio_settings_fn=_raise_apply,
        to_int_fn=_to_int,
        validate_content_length_fn=lambda *_args, **_kwargs: len(b'{"lora":{"tx_power":17}}'),
        parse_radio_settings_request_fn=lambda _raw: RadioSettingsRequest(lora={"tx_power": 17}),
        write_json_response_fn=lambda *_args, **kwargs: calls.append(kwargs),
    )

    assert calls[0]["status_code"] == 500
    assert "Radio settings update failed: boom" in calls[0]["payload_obj"]["error"]


def test_handle_radio_settings_post_maps_service_error_to_400():
    calls = []

    handle_radio_settings_post(
        _fake_handler(b'{"lora":{"tx_power":17}}'),
        apply_radio_settings_fn=lambda _request: {"ok": False, "error": "No valid fields"},
        to_int_fn=_to_int,
        validate_content_length_fn=lambda *_args, **_kwargs: len(b'{"lora":{"tx_power":17}}'),
        parse_radio_settings_request_fn=lambda _raw: RadioSettingsRequest(lora={"tx_power": 17}),
        write_json_response_fn=lambda *_args, **kwargs: calls.append(kwargs),
    )

    assert calls[0]["status_code"] == 400
    assert calls[0]["payload_obj"]["ok"] is False
    assert calls[0]["no_store"] is True


def test_handle_radio_settings_post_maps_service_success_to_200():
    calls = []

    handle_radio_settings_post(
        _fake_handler(b'{"lora":{"tx_power":17}}'),
        apply_radio_settings_fn=lambda _request: {"ok": True, "applied_fields": ["tx_power"]},
        to_int_fn=_to_int,
        validate_content_length_fn=lambda *_args, **_kwargs: len(b'{"lora":{"tx_power":17}}'),
        parse_radio_settings_request_fn=lambda _raw: RadioSettingsRequest(lora={"tx_power": 17}),
        write_json_response_fn=lambda *_args, **kwargs: calls.append(kwargs),
    )

    assert calls[0]["status_code"] == 200
    assert calls[0]["payload_obj"]["ok"] is True
    assert calls[0]["no_store"] is True
