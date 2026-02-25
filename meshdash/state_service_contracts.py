from typing import Any, Callable, Optional

from .revision import RevisionInfo
from .state_node_contracts import CollectedNodes

CollectNodesFn = Callable[[Any], CollectedNodes | dict[str, Any]]
CollectLocalStateFn = Callable[[Any], dict[str, Any]]
CollectLocalStateSafeFn = Callable[..., tuple[dict[str, Any], Optional[str]]]
ModemPresetFromLocalStateFn = Callable[[dict[str, Any]], Optional[str]]
ApplyNodeSavedCountsFn = Callable[[list[dict[str, Any]], dict[str, dict[str, Any]]], None]
BuildSummaryPayloadFn = Callable[..., dict[str, Any]]
RedactSecretsFn = Callable[[Any, set[str]], Any]

RevisionPayload = RevisionInfo | dict[str, str]
