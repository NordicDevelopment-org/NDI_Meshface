from .api_chat import (
    handle_chat_send_post as _handle_chat_send_post_helper,
)
from .api_theme import (
    handle_theme_settings_post as _handle_theme_settings_post_helper,
)
from .api_radio import (
    handle_radio_settings_post as _handle_radio_settings_post_helper,
)
from .api_channels import (
    handle_channel_settings_post as _handle_channel_settings_post_helper,
)
from .api_bot import (
    handle_bot_settings_post as _handle_bot_settings_post_helper,
)
from .api_zork import (
    handle_standalone_zork_post as _handle_standalone_zork_post_helper,
)
from .http_handler_contracts import DashboardHttpHandler
from .http_route_contracts import DashboardPostRouteDependencies


def handle_dashboard_post(
    handler: DashboardHttpHandler,
    *,
    path: str,
    deps: DashboardPostRouteDependencies,
) -> None:
    if path == "/api/chat/send":
        _handle_chat_send_post_helper(
            handler,
            send_chat_fn=deps.send_chat_fn,
            to_int_fn=deps.to_int_fn,
            validate_content_length_fn=deps.validate_content_length_fn,
            parse_chat_send_request_fn=deps.parse_chat_send_request_fn,
            write_json_response_fn=deps.write_json_response_fn,
        )
        return

    if path == "/api/games/zork":
        _handle_standalone_zork_post_helper(
            handler,
            play_standalone_zork_fn=deps.play_standalone_zork_fn,
            to_int_fn=deps.to_int_fn,
            validate_content_length_fn=deps.validate_content_length_fn,
            parse_standalone_zork_request_fn=deps.parse_standalone_zork_request_fn,
            write_json_response_fn=deps.write_json_response_fn,
        )
        return

    if path == "/api/settings/radio":
        parse_radio_settings_request_fn = deps.parse_radio_settings_request_fn
        if parse_radio_settings_request_fn is None:
            deps.write_json_response_fn(
                handler,
                status_code=503,
                payload_obj={
                    "ok": False,
                    "error": "Radio settings are not enabled on this dashboard instance",
                },
            )
            return
        _handle_radio_settings_post_helper(
            handler,
            apply_radio_settings_fn=deps.apply_radio_settings_fn,
            to_int_fn=deps.to_int_fn,
            validate_content_length_fn=deps.validate_content_length_fn,
            parse_radio_settings_request_fn=parse_radio_settings_request_fn,
            write_json_response_fn=deps.write_json_response_fn,
        )
        return

    if path == "/api/settings/channels":
        parse_channel_settings_request_fn = deps.parse_channel_settings_request_fn
        if parse_channel_settings_request_fn is None:
            deps.write_json_response_fn(
                handler,
                status_code=503,
                payload_obj={
                    "ok": False,
                    "error": "Channel settings are not enabled on this dashboard instance",
                },
            )
            return
        _handle_channel_settings_post_helper(
            handler,
            apply_channel_settings_fn=deps.apply_channel_settings_fn,
            to_int_fn=deps.to_int_fn,
            validate_content_length_fn=deps.validate_content_length_fn,
            parse_channel_settings_request_fn=parse_channel_settings_request_fn,
            write_json_response_fn=deps.write_json_response_fn,
        )
        return

    if path == "/api/settings/theme":
        parse_theme_settings_request_fn = deps.parse_theme_settings_request_fn
        if parse_theme_settings_request_fn is None:
            deps.write_json_response_fn(
                handler,
                status_code=503,
                payload_obj={"ok": False, "error": "Theme settings are not enabled on this dashboard instance"},
            )
            return
        _handle_theme_settings_post_helper(
            handler,
            set_theme_preset_fn=deps.set_theme_preset_fn,
            to_int_fn=deps.to_int_fn,
            validate_content_length_fn=deps.validate_content_length_fn,
            parse_theme_settings_request_fn=parse_theme_settings_request_fn,
            write_json_response_fn=deps.write_json_response_fn,
        )
        return

    if path == "/api/settings/bot":
        parse_bot_settings_request_fn = deps.parse_bot_settings_request_fn
        if parse_bot_settings_request_fn is None:
            deps.write_json_response_fn(
                handler,
                status_code=503,
                payload_obj={"ok": False, "error": "Bot settings are not enabled on this dashboard instance"},
            )
            return
        _handle_bot_settings_post_helper(
            handler,
            apply_bot_settings_fn=deps.apply_bot_settings_fn,
            to_int_fn=deps.to_int_fn,
            validate_content_length_fn=deps.validate_content_length_fn,
            parse_bot_settings_request_fn=parse_bot_settings_request_fn,
            write_json_response_fn=deps.write_json_response_fn,
        )
        return

    deps.write_json_response_fn(
        handler,
        status_code=404,
        payload_obj={"ok": False, "error": "Not Found"},
    )
