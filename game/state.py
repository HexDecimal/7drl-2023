from __future__ import annotations

from typing import Protocol

import attrs
import tcod.console
import tcod.event


class State(Protocol):
    def on_event(self, event: tcod.event.Event) -> StateResult:
        pass

    def on_draw(self, console: tcod.console.Console) -> None:
        pass


@attrs.define(frozen=True)
class Push:
    state: State


@attrs.define(frozen=True)
class Pop:
    pass


@attrs.define(frozen=True)
class Reset:
    state: State


StateResult = Push | Pop | Reset | None
