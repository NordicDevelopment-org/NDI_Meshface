from __future__ import annotations

import random
import re
from typing import Iterable

from ...bot_apps.base import BotAppResult
from ...bot_commands import BotCommandSpec
from .world import AdventureWorld, TravelOption, load_adventure_world


GAME_SESSION_TTL_SECONDS = 45 * 60
START_TRIGGERS = frozenset({"adventure", "adv", "!adventure", "#adventure"})
START_HELP_HINT = "Type 'help' for the command set."
START_ROOM = 1

KEYS = 1
LAMP = 2
GRATE = 3
CAGE = 4
ROD = 5
BIRD = 7
NUGGET = 10
SNAKE = 11
FISSURE = 12
FOOD = 19
WATER = 20
AXE = 21

INITIAL_LOCATIONS = {
    1: 3,
    2: 3,
    3: 8,
    4: 10,
    5: 11,
    6: 14,
    7: 13,
    8: 9,
    9: 15,
    10: 18,
    11: 19,
    12: 17,
    13: 27,
    14: 28,
    15: 29,
    16: 30,
    17: 0,
    18: 0,
    19: 3,
    20: 3,
    21: 0,
    23: 0,
}

FIXED_OBJECTS = {3, 6, 8, 9, 11, 12}
TREASURE_IDS = frozenset({10, 13, 14, 15, 16})
OBJECT_NAMES = {
    1: "keys",
    2: "lamp",
    3: "grate",
    4: "cage",
    5: "rod",
    6: "steps",
    7: "bird",
    8: "grate",
    9: "steps",
    10: "gold nugget",
    11: "snake",
    12: "fissure",
    13: "diamonds",
    14: "silver bars",
    15: "jewelry",
    16: "coins",
    17: "dwarf",
    18: "knife",
    19: "food",
    20: "water bottle",
    21: "axe",
    23: "treasure chest",
}
LIT_ROOMS = set(range(1, 11))
NO_QUESTION_ROOMS = {16, 20, 21, 22, 23, 24, 25, 26, 31, 32, 79}
INVENTORY_LOCATION = -1
GONE_LOCATION = 300


def _compact(text: object) -> str:
    return " ".join(str(text or "").strip().split())


def _clean_words(text: object) -> list[str]:
    return [
        part[:5].upper()
        for part in re.findall(r"[A-Za-z?]+", str(text or ""))
        if part.strip()
    ]


def _canonical_peer(value: object) -> str:
    return str(value or "").strip().lower()


class AdventureGame:
    """Native Python port of the 1977 Crowther Adventure data/command model."""

    SPEC = BotCommandSpec(
        name="adventure",
        usage="adventure",
        description="start Colossal Cave Adventure",
        kind="game",
    )

    def __init__(
        self,
        *,
        world: AdventureWorld | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._world = world or load_adventure_world()
        self._rng = rng or random.Random()
        self._sessions: dict[str, dict[str, object]] = {}

    def active_session_count(self) -> int:
        return len(self._sessions)

    def clear_sessions(self) -> None:
        self._sessions.clear()

    def end_session(self, from_id: str) -> bool:
        peer_id = _canonical_peer(from_id)
        if not peer_id:
            return False
        return self._sessions.pop(peer_id, None) is not None

    def has_active_session(self, from_id: str) -> bool:
        return _canonical_peer(from_id) in self._sessions

    def prune_expired_sessions(self, now_unix: int) -> None:
        cutoff = int(now_unix) - GAME_SESSION_TTL_SECONDS
        expired = [
            peer_id
            for peer_id, session in self._sessions.items()
            if int(session.get("updated_unix") or 0) < cutoff
        ]
        for peer_id in expired:
            self._sessions.pop(peer_id, None)

    def session_summaries(self, now_unix: int | None = None) -> list[dict[str, object]]:
        if now_unix is not None:
            self.prune_expired_sessions(int(now_unix))
        out: list[dict[str, object]] = []
        for peer_id, session in sorted(
            self._sessions.items(),
            key=lambda item: int(item[1].get("updated_unix") or 0),
            reverse=True,
        ):
            loc = int(session.get("loc") or START_ROOM)
            carried, secured, recovered = self._treasure_progress(session)
            out.append(
                {
                    "peer_id": peer_id,
                    "room": loc,
                    "room_name": self._room_name(loc),
                    "updated_unix": int(session.get("updated_unix") or 0),
                    "expires_unix": int(session.get("updated_unix") or 0) + GAME_SESSION_TTL_SECONDS,
                    "inventory_count": len(self._inventory(session)),
                    "treasures": {
                        "total": len(TREASURE_IDS),
                        "carried": carried,
                        "secured": secured,
                        "recovered": recovered,
                    },
                }
            )
        return out

    def _start_session(self, peer_id: str, now_unix: int) -> dict[str, object]:
        session = {
            "loc": START_ROOM,
            "prev_loc": START_ROOM,
            "inventory": [],
            "object_locations": dict(INITIAL_LOCATIONS),
            "props": {},
            "seen_rooms": set(),
            "abbr": {},
            "updated_unix": int(now_unix),
            "detail_count": 0,
            "west_count": 0,
        }
        self._sessions[peer_id] = session
        return session

    def _write_session(self, session: dict[str, object], *, now_unix: int) -> None:
        session["updated_unix"] = int(now_unix)

    def _is_direct_to_local(self, to_id: object, local_node_id: object) -> bool:
        clean_to = str(to_id or "").strip().lower()
        clean_local = str(local_node_id or "").strip().lower()
        return bool(clean_to and clean_local and clean_to == clean_local)

    def _room_name(self, loc: int) -> str:
        short = self._world.short_descriptions.get(loc)
        if short:
            return short.rstrip(".")
        long_desc = self._world.long_descriptions.get(loc, "")
        if not long_desc:
            return f"Room {loc}"
        return long_desc.split(".")[0].strip() or f"Room {loc}"

    def _message(self, msg_id: int, fallback: str = "") -> str:
        return self._world.messages.get(int(msg_id), fallback)

    def _prop(self, session: dict[str, object], obj_id: int) -> int:
        props = session.get("props")
        return int(props.get(obj_id, 0) if isinstance(props, dict) else 0)

    def _set_prop(self, session: dict[str, object], obj_id: int, value: int) -> None:
        props = session.setdefault("props", {})
        if isinstance(props, dict):
            props[int(obj_id)] = int(value)

    def _locations(self, session: dict[str, object]) -> dict[int, int]:
        locations = session.setdefault("object_locations", dict(INITIAL_LOCATIONS))
        return locations if isinstance(locations, dict) else dict(INITIAL_LOCATIONS)

    def _inventory(self, session: dict[str, object]) -> list[int]:
        inventory = session.setdefault("inventory", [])
        return [int(value) for value in inventory] if isinstance(inventory, list) else []

    def _set_inventory(self, session: dict[str, object], inventory: Iterable[int]) -> None:
        session["inventory"] = sorted({int(value) for value in inventory})

    def _is_lit(self, session: dict[str, object], loc: int) -> bool:
        if loc in LIT_ROOMS:
            return True
        locations = self._locations(session)
        return self._prop(session, LAMP) == 1 and locations.get(LAMP) in {loc, INVENTORY_LOCATION}

    def _visible_object_ids(self, session: dict[str, object], loc: int) -> list[int]:
        locations = self._locations(session)
        visible: list[int] = []
        for obj_id, obj_loc in sorted(locations.items()):
            if int(obj_loc) != int(loc):
                continue
            if obj_id in {6, 9} and locations.get(NUGGET) == INVENTORY_LOCATION:
                continue
            visible.append(int(obj_id))
        return visible

    def _object_message_id(self, session: dict[str, object], obj_id: int) -> int:
        prop = self._prop(session, obj_id)
        if prop and (obj_id + 100) in self._world.object_texts:
            return obj_id + 100
        if (obj_id + 200) in self._world.object_texts:
            return obj_id + 200
        return obj_id

    def _object_text(self, session: dict[str, object], obj_id: int) -> str:
        msg_id = self._object_message_id(session, obj_id)
        return self._world.object_texts.get(msg_id, OBJECT_NAMES.get(obj_id, f"object {obj_id}"))

    def _describe_location(
        self,
        session: dict[str, object],
        *,
        explicit_look: bool = False,
    ) -> str:
        loc = int(session.get("loc") or START_ROOM)
        if not self._is_lit(session, loc):
            return self._message(16, "It is now pitch black. If you proceed you will likely fall into a pit.")

        seen_rooms = session.setdefault("seen_rooms", set())
        if not isinstance(seen_rooms, set):
            seen_rooms = set(seen_rooms) if isinstance(seen_rooms, list) else set()
            session["seen_rooms"] = seen_rooms
        first_visit = loc not in seen_rooms
        seen_rooms.add(loc)
        text = ""
        if explicit_look or first_visit or loc not in self._world.short_descriptions:
            text = self._world.long_descriptions.get(loc, self._room_name(loc))
        else:
            text = self._world.short_descriptions.get(loc, self._room_name(loc))
        parts = [_compact(text)]
        for obj_id in self._visible_object_ids(session, loc):
            obj_text = _compact(self._object_text(session, obj_id))
            if obj_text:
                parts.append(obj_text)
        return _compact(" ".join(parts))

    def _classify_word(self, word: str) -> tuple[str, int] | None:
        code = self._world.vocabulary.get(str(word or "").upper()[:5])
        if code is None:
            return None
        category = int(code) // 1000
        value = int(code) % 1000
        if category == 0:
            return ("motion", value)
        if category == 1:
            return ("object", value)
        if category == 2:
            return ("verb", value)
        return ("special", value)

    def _resolve_object(self, session: dict[str, object], word: str) -> int | None:
        classified = self._classify_word(word)
        if classified is None or classified[0] != "object":
            return None
        obj_id = int(classified[1])
        loc = int(session.get("loc") or START_ROOM)
        if obj_id == GRATE:
            if loc in {1, 4, 7, 8}:
                return 3
            if 9 <= loc < 15:
                return 8
        return obj_id

    def _is_accessible(self, session: dict[str, object], obj_id: int) -> bool:
        loc = int(session.get("loc") or START_ROOM)
        locations = self._locations(session)
        return locations.get(obj_id) in {loc, INVENTORY_LOCATION}

    def _movement_response(self, session: dict[str, object], motion: int, *, now_unix: int) -> BotAppResult:
        loc = int(session.get("loc") or START_ROOM)
        if not self._is_lit(session, loc) and self._rng.random() < 0.25:
            peer_id = str(session.get("peer_id") or "")
            if peer_id:
                self._sessions.pop(peer_id, None)
            return BotAppResult(
                handled=True,
                reply_text=self._message(23, "You fell into a pit and broke every bone in your body!"),
                command_name=self.SPEC.name,
            )

        if motion == 57:
            session["detail_count"] = int(session.get("detail_count") or 0) + 1
            detail_prefix = ""
            if int(session.get("detail_count") or 0) <= 3:
                detail_prefix = self._message(15)
            self._write_session(session, now_unix=now_unix)
            return BotAppResult(
                handled=True,
                reply_text=_compact(f"{detail_prefix} {self._describe_location(session, explicit_look=True)}"),
                command_name=self.SPEC.name,
            )

        if motion == 67:
            msg = self._message(57 if loc < 8 else 58)
            self._write_session(session, now_unix=now_unix)
            return BotAppResult(handled=True, reply_text=msg, command_name=self.SPEC.name)

        if motion == 8:
            target = int(session.get("prev_loc") or loc)
        else:
            target = self._travel_destination(session, loc, motion)
        if target is None:
            self._write_session(session, now_unix=now_unix)
            return BotAppResult(handled=True, reply_text=self._travel_error(motion), command_name=self.SPEC.name)

        if target == GONE_LOCATION:
            target = 5 if self._rng.random() > 0.5 else 6
        elif target >= 300:
            target = self._special_destination(session, target)

        if target in {20, 21, 22, 23, 24, 25, 31, 32}:
            session["prev_loc"] = loc
            session["loc"] = target
            self._write_session(session, now_unix=now_unix)
            return BotAppResult(
                handled=True,
                reply_text=self._world.long_descriptions.get(target, self._room_name(target)),
                command_name=self.SPEC.name,
            )

        session["prev_loc"] = loc
        session["loc"] = int(target)
        self._write_session(session, now_unix=now_unix)
        return BotAppResult(
            handled=True,
            reply_text=self._describe_location(session),
            command_name=self.SPEC.name,
        )

    def _travel_destination(self, session: dict[str, object], loc: int, motion: int) -> int | None:
        del session
        options = self._world.travel.get(loc, ())
        for option in options:
            if 1 in option.words or int(motion) in option.words:
                return int(option.destination)
        return None

    def _special_destination(self, session: dict[str, object], target: int) -> int:
        special = int(target) - 300
        if special == 1:
            return 23 if self._prop(session, GRATE) == 0 else 9
        if special == 2:
            return 9 if self._prop(session, GRATE) != 0 else 8
        if special == 3:
            return 20 if self._locations(session).get(NUGGET) != INVENTORY_LOCATION else 15
        if special == 4:
            return 22 if self._locations(session).get(NUGGET) != INVENTORY_LOCATION else 14
        if special == 5:
            return 27 if self._prop(session, FISSURE) != 0 else 31
        if special in {6, 7, 8}:
            blocked_targets = {6: 28, 7: 29, 8: 30}
            return blocked_targets[special] if self._prop(session, SNAKE) != 0 else 32
        if special == 9:
            return START_ROOM
        if special == 11:
            return 8 if self._prop(session, GRATE) != 0 else 9
        if special in {12, 14}:
            return 68 if self._rng.random() <= 0.2 else 65
        if special == 13:
            if self._rng.random() <= 0.2:
                return 39 if self._rng.random() <= 0.5 else 70
            return 65
        return int(session.get("loc") or START_ROOM)

    def _travel_error(self, motion: int) -> str:
        if motion in {29, 30, 43, 44, 45, 46}:
            return self._message(9, "There is no way to go that direction.")
        if motion in {7, 8, 36, 37, 68}:
            return self._message(10, "I am unsure how you are facing.")
        if motion in {11, 19}:
            return self._message(11, "I don't know in from out here.")
        if motion == 48:
            return self._message(42, "Nothing happens.")
        if motion == 17:
            return self._message(80, "Which way?")
        return self._message(12, "I don't know how to apply that word here.")

    def _take_response(self, session: dict[str, object], obj_id: int) -> str:
        loc = int(session.get("loc") or START_ROOM)
        locations = self._locations(session)
        inventory = self._inventory(session)
        if obj_id == 18:
            return self._message(54, "OK")
        if locations.get(obj_id) == INVENTORY_LOCATION:
            return self._message(24, "You are already carrying it!")
        if locations.get(obj_id) != loc:
            return f"I see no {OBJECT_NAMES.get(obj_id, 'such thing')} here."
        if obj_id in FIXED_OBJECTS:
            return self._message(25, "You can't be serious!")
        if obj_id == BIRD:
            if locations.get(ROD) == INVENTORY_LOCATION:
                return self._message(26)
            if locations.get(CAGE) not in {INVENTORY_LOCATION, loc}:
                return self._message(27)
        inventory.append(obj_id)
        self._set_inventory(session, inventory)
        locations[obj_id] = INVENTORY_LOCATION
        return self._message(54, "OK")

    def _drop_response(self, session: dict[str, object], obj_id: int) -> str:
        loc = int(session.get("loc") or START_ROOM)
        locations = self._locations(session)
        inventory = self._inventory(session)
        if obj_id == 18:
            return self._message(54, "OK")
        if obj_id not in inventory:
            return self._message(29, "You aren't carrying it!")
        if obj_id == BIRD and loc == 19 and self._prop(session, SNAKE) == 0:
            self._set_prop(session, SNAKE, 1)
            inventory.remove(obj_id)
            self._set_inventory(session, inventory)
            locations[obj_id] = loc
            return self._message(30)
        inventory.remove(obj_id)
        self._set_inventory(session, inventory)
        locations[obj_id] = loc
        return self._message(54, "OK")

    def _open_lock_response(self, session: dict[str, object], *, opening: bool) -> str:
        loc = int(session.get("loc") or START_ROOM)
        if loc not in {8, 9}:
            return self._message(28, "There is nothing here with a lock!")
        locations = self._locations(session)
        if locations.get(KEYS) not in {loc, INVENTORY_LOCATION}:
            return self._message(31, "You have no keys!")
        if opening:
            if self._prop(session, GRATE) != 0:
                return self._message(36, "The grate was already unlocked.")
            self._set_prop(session, GRATE, 1)
            self._set_prop(session, 8, 1)
            return self._message(37, "The grate is now unlocked.")
        if self._prop(session, GRATE) == 0:
            return self._message(34, "The grate was already locked.")
        self._set_prop(session, GRATE, 0)
        self._set_prop(session, 8, 0)
        return self._message(35, "The grate is now locked.")

    def _verb_response(
        self,
        session: dict[str, object],
        verb: int,
        obj_id: int | None,
        *,
        now_unix: int,
    ) -> BotAppResult:
        loc = int(session.get("loc") or START_ROOM)
        reply = ""
        if verb == 1:
            if obj_id is None:
                visible = [obj for obj in self._visible_object_ids(session, loc) if obj not in FIXED_OBJECTS]
                if len(visible) == 1:
                    obj_id = visible[0]
                else:
                    return BotAppResult(handled=True, reply_text="Take what?", command_name=self.SPEC.name)
            reply = self._take_response(session, obj_id)
        elif verb == 2:
            if obj_id is None:
                return BotAppResult(handled=True, reply_text="Drop what?", command_name=self.SPEC.name)
            reply = self._drop_response(session, obj_id)
        elif verb == 4:
            reply = self._open_lock_response(session, opening=True)
        elif verb == 6:
            reply = self._open_lock_response(session, opening=False)
        elif verb == 7:
            if not self._is_accessible(session, LAMP):
                reply = self._message(38, "You have no source of light.")
            else:
                self._set_prop(session, LAMP, 1)
                reply = self._message(39, "Your lamp is now on.")
        elif verb == 8:
            if not self._is_accessible(session, LAMP):
                reply = self._message(38, "You have no source of light.")
            else:
                self._set_prop(session, LAMP, 0)
                reply = self._message(40, "Your lamp is now off.")
        elif verb == 9:
            if obj_id == FISSURE:
                self._set_prop(session, FISSURE, 1)
                reply = self._object_text(session, FISSURE)
            else:
                reply = self._message(42, "Nothing happens.")
        elif verb == 10:
            reply = self._message(42, "Nothing happens.")
        elif verb == 12:
            if obj_id == SNAKE:
                reply = self._message(46)
            elif obj_id == BIRD:
                self._locations(session)[BIRD] = GONE_LOCATION
                inventory = [obj for obj in self._inventory(session) if obj != BIRD]
                self._set_inventory(session, inventory)
                reply = self._message(45)
            else:
                reply = self._message(44, "There is nothing here to attack.")
        elif verb == 13:
            if obj_id not in {WATER, None}:
                reply = self._message(78, "You can't pour that.")
            else:
                self._set_prop(session, WATER, 1)
                reply = self._message(77, "Your bottle is empty and the ground is wet.")
        elif verb == 14:
            if obj_id == FOOD and self._is_accessible(session, FOOD) and self._prop(session, FOOD) == 0:
                self._set_prop(session, FOOD, 1)
                reply = self._message(72, "Eaten!")
            else:
                reply = self._message(71, "There is nothing here to eat.")
        elif verb == 15:
            if obj_id == WATER and self._is_accessible(session, WATER) and self._prop(session, WATER) == 0:
                self._set_prop(session, WATER, 1)
                reply = self._message(74, "The bottle of water is now empty.")
            else:
                reply = self._message(73, "There is no drinkable water here.")
        elif verb == 16:
            reply = self._message(75 if obj_id == LAMP else 76, "Peculiar. Nothing unexpected happens.")
        else:
            reply = self._message(12, "I don't know how to apply that word here.")
        self._write_session(session, now_unix=now_unix)
        return BotAppResult(handled=True, reply_text=_compact(reply), command_name=self.SPEC.name)

    def _treasure_progress(self, session: dict[str, object]) -> tuple[int, int, int]:
        locations = self._locations(session)
        carried = sum(1 for obj in TREASURE_IDS if locations.get(obj) == INVENTORY_LOCATION)
        secured = sum(1 for obj in TREASURE_IDS if locations.get(obj) == 3)
        recovered = sum(1 for obj in TREASURE_IDS if locations.get(obj) in {INVENTORY_LOCATION, 3})
        return carried, secured, recovered

    def _score_text(self, session: dict[str, object]) -> str:
        carried, secured, recovered = self._treasure_progress(session)
        return (
            f"score/progress: treasures secured {secured}/{len(TREASURE_IDS)}. "
            f"treasures carried {carried}. treasures recovered {recovered}/{len(TREASURE_IDS)}."
        )

    def _inventory_text(self, session: dict[str, object]) -> str:
        inventory = self._inventory(session)
        if not inventory:
            return "You are empty-handed."
        return "You are carrying: " + ", ".join(OBJECT_NAMES.get(obj, f"object {obj}") for obj in inventory) + "."

    def _help_text(self) -> str:
        return (
            "adventure: move with n/s/e/w/u/d or words like road, building, stream, cave, xyzzy, plugh. "
            "Use take/drop/open/close/light/extinguish/strike/attack/eat/drink/pour/rub, plus look, inventory, score, quit."
        )

    def _parse_command(self, text: str) -> tuple[str, int | None, int | None]:
        words = _clean_words(text)
        if not words:
            return ("", None, None)
        first = words[0]
        second = words[1] if len(words) > 1 else ""
        first_kind = self._classify_word(first)
        second_kind = self._classify_word(second) if second else None
        if first_kind is None:
            return ("unknown", None, None)
        if first_kind[0] == "motion":
            return ("motion", int(first_kind[1]), None)
        if first_kind[0] == "verb":
            obj = int(second_kind[1]) if second_kind and second_kind[0] == "object" else None
            if int(first_kind[1]) == 11 and second_kind and second_kind[0] == "motion":
                return ("motion", int(second_kind[1]), None)
            return ("verb", int(first_kind[1]), obj)
        if first_kind[0] == "object":
            if second_kind and second_kind[0] == "verb":
                return ("verb", int(second_kind[1]), int(first_kind[1]))
            return ("object", None, int(first_kind[1]))
        if first_kind[0] == "special":
            return ("special", int(first_kind[1]), None)
        return ("unknown", None, None)

    def try_handle_message(
        self,
        *,
        text: str,
        from_id: str,
        to_id: str,
        local_node_id: str,
        now_unix: int,
        enabled: bool,
    ) -> BotAppResult:
        raw = str(text or "").strip()
        if not raw:
            return BotAppResult(handled=False)
        if not self._is_direct_to_local(to_id, local_node_id):
            return BotAppResult(handled=False)
        peer_id = _canonical_peer(from_id)
        if not peer_id.startswith("!"):
            return BotAppResult(handled=False)

        self.prune_expired_sessions(now_unix)
        clean_start = raw.lower()
        if clean_start in START_TRIGGERS or clean_start == "restart":
            if not enabled:
                return BotAppResult(handled=True, command_name=self.SPEC.name)
            session = self._start_session(peer_id, now_unix)
            session["peer_id"] = peer_id
            intro = self._message(1)
            summary = self._describe_location(session, explicit_look=True)
            return BotAppResult(
                handled=True,
                reply_text=_compact(f"adventure: session started. {intro} {summary} {START_HELP_HINT}"),
                command_name=self.SPEC.name,
            )

        session = self._sessions.get(peer_id)
        if session is None:
            return BotAppResult(handled=False)
        session["peer_id"] = peer_id
        if not enabled:
            return BotAppResult(handled=True, command_name=self.SPEC.name)

        lowered = raw.lower()
        if lowered in {"help", "?"}:
            self._write_session(session, now_unix=now_unix)
            return BotAppResult(handled=True, reply_text=self._help_text(), command_name=self.SPEC.name)
        if lowered in {"look", "l"}:
            self._write_session(session, now_unix=now_unix)
            return BotAppResult(
                handled=True,
                reply_text=self._describe_location(session, explicit_look=True),
                command_name=self.SPEC.name,
            )
        if lowered in {"inventory", "inv", "i"}:
            self._write_session(session, now_unix=now_unix)
            return BotAppResult(handled=True, reply_text=self._inventory_text(session), command_name=self.SPEC.name)
        if lowered == "score":
            self._write_session(session, now_unix=now_unix)
            return BotAppResult(handled=True, reply_text=self._score_text(session), command_name=self.SPEC.name)
        if lowered in {"quit", "exitgame"}:
            score = self._score_text(session)
            self._sessions.pop(peer_id, None)
            return BotAppResult(
                handled=True,
                reply_text=_compact(f"{score} adventure: session ended. Send 'adventure' to start again."),
                command_name=self.SPEC.name,
            )

        kind, value, obj_id = self._parse_command(raw)
        if kind == "motion" and value is not None:
            if value == 44:
                session["west_count"] = int(session.get("west_count") or 0) + 1
                if int(session.get("west_count") or 0) == 10:
                    return BotAppResult(handled=True, reply_text=self._message(17), command_name=self.SPEC.name)
            return self._movement_response(session, value, now_unix=now_unix)
        if kind == "verb" and value is not None:
            resolved_obj = obj_id
            if resolved_obj is not None:
                obj_word = _clean_words(raw)[1 if self._classify_word(_clean_words(raw)[0])[0] == "verb" and len(_clean_words(raw)) > 1 else 0]
                resolved_obj = self._resolve_object(session, obj_word) or resolved_obj
            return self._verb_response(session, value, resolved_obj, now_unix=now_unix)
        if kind == "object" and obj_id is not None:
            self._write_session(session, now_unix=now_unix)
            name = OBJECT_NAMES.get(obj_id, "that")
            return BotAppResult(handled=True, reply_text=f"What do you want to do with the {name}?", command_name=self.SPEC.name)
        if kind == "unknown":
            self._write_session(session, now_unix=now_unix)
            return BotAppResult(handled=True, reply_text=self._message(60, "I don't know that word."), command_name=self.SPEC.name)
        self._write_session(session, now_unix=now_unix)
        return BotAppResult(handled=True, reply_text=self._message(13, "I don't understand that!"), command_name=self.SPEC.name)


__all__ = ["AdventureGame"]
