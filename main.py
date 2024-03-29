#!/usr/bin/env python
import logging
import sys
import warnings

from tcod import tcod

import g
import game.state
import game.states
import game.world_logic
import game.world_tools


def handle_state(result: game.state.StateResult) -> None:
    match result:
        case game.state.Push(state):
            g.state.append(state)
        case game.state.Pop():
            g.state.pop()
        case game.state.Reset(state):
            g.state = [state]
        case None:
            pass
        case _:
            assert False
    if hasattr(g, "world"):
        game.world_logic.until_player_turn(g.world)


def main() -> None:
    tileset = tcod.tileset.load_tilesheet("data/dejavu16x16_gs_tc.png", 32, 8, tcod.tileset.CHARMAP_TCOD)

    with tcod.context.new(
        tileset=tileset,
        width=1280,
        height=720,
        title="7drl-2023",
        vsync=True,
    ) as g.context:
        g.world = game.world_tools.new_world()
        g.state = [game.states.MainMenu()]
        while True:
            console = g.context.new_console(30, 20)
            g.state[-1].on_draw(console)
            g.context.present(console, keep_aspect=True, integer_scaling=True)
            for event in tcod.event.wait():
                event = g.context.convert_event(event)
                handle_state(g.state[-1].on_event(event))
                match event:
                    case tcod.event.MouseButtonDown():
                        tcod.lib.SDL_CaptureMouse(True)
                    case tcod.event.MouseButtonUp():
                        if tcod.event.get_mouse_state().state == 0:
                            tcod.lib.SDL_CaptureMouse(False)


if __name__ == "__main__":
    if __debug__:
        logging.basicConfig(level=logging.DEBUG)
        if not sys.warnoptions:
            warnings.simplefilter("default")
    main()
