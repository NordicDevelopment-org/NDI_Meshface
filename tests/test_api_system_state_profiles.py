from meshdash.api_system import handle_state_get


class _Headers:
    def get(self, _key: str):
        return None

    def items(self):
        return []


class _Handler:
    def __init__(self) -> None:
        self.headers = _Headers()


def test_handle_state_get_uses_lite_chat_profile_when_requested() -> None:
    calls: list[str] = []

    def state_fn():
        calls.append("full")
        return {"generated_at": "now", "summary": {}, "traffic": {}}

    def state_lite():
        calls.append("lite")
        return {"generated_at": "now", "summary": {}, "traffic": {}}

    def state_lite_chat():
        calls.append("lite_chat")
        return {"generated_at": "now", "summary": {}, "traffic": {}}

    setattr(state_fn, "lite", state_lite)
    setattr(state_fn, "lite_chat", state_lite_chat)
    setattr(state_fn, "fault_history_fn", lambda: [])

    written: list[object] = []

    def write_json_response_fn(_handler, *, status_code, payload_obj, no_store=False, extra_headers=None):
        written.append((status_code, payload_obj, no_store, extra_headers))

    handle_state_get(
        _Handler(),
        state_fn=state_fn,
        write_json_response_fn=write_json_response_fn,
        query="lite=1&profile=chat",
        private_mode=False,
    )

    assert calls == ["lite_chat"]
    assert written
    assert written[0][0] == 200


def test_handle_state_get_falls_back_to_lite_when_chat_profile_missing() -> None:
    calls: list[str] = []

    def state_fn():
        calls.append("full")
        return {"generated_at": "now", "summary": {}, "traffic": {}}

    def state_lite():
        calls.append("lite")
        return {"generated_at": "now", "summary": {}, "traffic": {}}

    setattr(state_fn, "lite", state_lite)
    setattr(state_fn, "fault_history_fn", lambda: [])

    def write_json_response_fn(_handler, *, status_code, payload_obj, no_store=False, extra_headers=None):
        return None

    handle_state_get(
        _Handler(),
        state_fn=state_fn,
        write_json_response_fn=write_json_response_fn,
        query="lite=1&profile=chat",
        private_mode=False,
    )

    assert calls == ["lite"]


def test_handle_state_get_uses_lite_network_profile_when_requested() -> None:
    calls: list[str] = []

    def state_fn():
        calls.append("full")
        return {"generated_at": "now", "summary": {}, "traffic": {}}

    def state_lite():
        calls.append("lite")
        return {"generated_at": "now", "summary": {}, "traffic": {}}

    def state_lite_network():
        calls.append("lite_network")
        return {"generated_at": "now", "summary": {}, "traffic": {}}

    setattr(state_fn, "lite", state_lite)
    setattr(state_fn, "lite_network", state_lite_network)
    setattr(state_fn, "fault_history_fn", lambda: [])

    def write_json_response_fn(_handler, *, status_code, payload_obj, no_store=False, extra_headers=None):
        return None

    handle_state_get(
        _Handler(),
        state_fn=state_fn,
        write_json_response_fn=write_json_response_fn,
        query="lite=1&profile=network",
        private_mode=False,
    )

    assert calls == ["lite_network"]


def test_handle_state_get_uses_lite_status_profile_when_requested() -> None:
    calls: list[str] = []

    def state_fn():
        calls.append("full")
        return {"generated_at": "now", "summary": {}, "traffic": {}}

    def state_lite():
        calls.append("lite")
        return {"generated_at": "now", "summary": {}, "traffic": {}}

    def state_lite_status():
        calls.append("lite_status")
        return {"generated_at": "now", "summary": {}, "traffic": {}}

    setattr(state_fn, "lite", state_lite)
    setattr(state_fn, "lite_status", state_lite_status)
    setattr(state_fn, "fault_history_fn", lambda: [])

    def write_json_response_fn(_handler, *, status_code, payload_obj, no_store=False, extra_headers=None):
        return None

    handle_state_get(
        _Handler(),
        state_fn=state_fn,
        write_json_response_fn=write_json_response_fn,
        query="lite=1&profile=status",
        private_mode=False,
    )

    assert calls == ["lite_status"]


def test_handle_state_get_uses_lite_console_profile_when_requested() -> None:
    calls: list[str] = []

    def state_fn():
        calls.append("full")
        return {"generated_at": "now", "summary": {}, "traffic": {}}

    def state_lite():
        calls.append("lite")
        return {"generated_at": "now", "summary": {}, "traffic": {}}

    def state_lite_console():
        calls.append("lite_console")
        return {"generated_at": "now", "summary": {}, "traffic": {}}

    setattr(state_fn, "lite", state_lite)
    setattr(state_fn, "lite_console", state_lite_console)
    setattr(state_fn, "fault_history_fn", lambda: [])

    def write_json_response_fn(_handler, *, status_code, payload_obj, no_store=False, extra_headers=None):
        return None

    handle_state_get(
        _Handler(),
        state_fn=state_fn,
        write_json_response_fn=write_json_response_fn,
        query="lite=1&profile=console",
        private_mode=False,
    )

    assert calls == ["lite_console"]
