import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.api_input_network_tools import parse_network_tool_request
from meshdash.helpers import to_int


def test_parse_network_tool_request_normalizes_position_command() -> None:
    raw = (
        b'{"command":"--request-position","destination":"!abcd1234",'
        b'"channel_index":"1","timeout_ms":"8000"}'
    )

    request = parse_network_tool_request(raw, to_int_fn=to_int)

    assert request.command == "request_position"
    assert request.destination == "!abcd1234"
    assert request.channel_index == 1
    assert request.timeout_ms == 8000
    assert request.hop_limit is None


def test_parse_network_tool_request_normalizes_traceroute_command() -> None:
    raw = (
        b'{"command":"--traceroute","destination":"!abcd1234",'
        b'"channel_index":"1","hop_limit":"5","timeout":"12000"}'
    )

    request = parse_network_tool_request(raw, to_int_fn=to_int)

    assert request.command == "traceroute"
    assert request.destination == "!abcd1234"
    assert request.channel_index == 1
    assert request.hop_limit == 5
    assert request.timeout_ms == 12000


def test_parse_network_tool_request_normalizes_ping_command() -> None:
    raw = (
        b'{"command":"--ping","destination":"!abcd1234",'
        b'"channel_index":"1","hop_limit":"4","timeout":"8000"}'
    )

    request = parse_network_tool_request(raw, to_int_fn=to_int)

    assert request.command == "ping"
    assert request.destination == "!abcd1234"
    assert request.channel_index == 1
    assert request.hop_limit == 4
    assert request.timeout_ms == 8000


def test_parse_network_tool_request_normalizes_telemetry_type_alias() -> None:
    raw = b'{"command":"request-telemetry","destination":"!abcd1234","type":"power"}'

    request = parse_network_tool_request(raw, to_int_fn=to_int)

    assert request.command == "request_telemetry"
    assert request.telemetry_type == "power_metrics"


def test_parse_network_tool_request_allows_nodes_without_destination() -> None:
    request = parse_network_tool_request(b'{"command":"--nodes"}', to_int_fn=to_int)

    assert request.command == "nodes"
    assert request.destination is None


def test_parse_network_tool_request_allows_send_node_info_without_destination() -> None:
    request = parse_network_tool_request(
        b'{"command":"--send-node-info","channel_index":"2","hop_limit":"3"}',
        to_int_fn=to_int,
    )

    assert request.command == "send_node_info"
    assert request.destination is None
    assert request.channel_index == 2
    assert request.hop_limit == 3


def test_parse_network_tool_request_rejects_missing_destination_for_radio_commands() -> None:
    with pytest.raises(ValueError, match="Missing destination"):
        parse_network_tool_request(b'{"command":"traceroute"}', to_int_fn=to_int)
