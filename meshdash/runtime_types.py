from typing import Any, Callable, Optional

from .revision import RevisionInfo

MeshTargetLabelFn = Callable[[Any], str]
OpenMeshInterfaceFn = Callable[[Any], Any]
SubscribeFn = Callable[[Any, str], None]
SeedTrackerFn = Callable[[Any, Any], None]
RevisionInfoFn = Callable[[], RevisionInfo]

BuildStateFn = Callable[..., dict]
BuildNodeHistoryLoaderFn = Callable[..., Callable[..., dict]]
BuildOnlineActivityLoaderFn = Callable[..., Callable[..., dict]]
BuildSendChatLoaderFn = Callable[..., Callable[..., dict]]
BuildStateSnapshotLoaderFn = Callable[..., Callable[[], dict]]

SendChatMessageFn = Callable[..., dict]
SendReactionPacketFn = Callable[..., Any]
GetLocalNodeIdFn = Callable[[Any], str]

NormalizeSingleEmojiFn = Callable[[Any], tuple[Optional[str], Optional[int]]]
ToIntFn = Callable[[Any], Optional[int]]
UtcNowFn = Callable[[], str]

RenderHtmlFn = Callable[..., str]
MakeHttpHandlerFn = Callable[..., Any]
GuessLanIpv4Fn = Callable[[], Optional[str]]

StateFn = Callable[[], dict]
NodeHistoryFn = Callable[..., dict]
OnlineActivityFn = Callable[..., dict]
SendChatFn = Callable[..., dict]
