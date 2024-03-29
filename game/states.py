from typing import Callable, Iterable

import attrs
import tcod.camera
import tcod.console
import tcod.event
from tcod.ec import ComponentDict

import g
import game.action
import game.actions
import game.actor_tools
import game.commands
import game.rendering
from game.components import Context, Direction, Graphic, MapFeatures, MapInfo, Position
from game.messages import MessageLog
from game.sched import Ticket
from game.state import Pop, Push, Reset, State, StateResult


class InGame(State):
    def on_event(self, event: tcod.event.Event) -> StateResult:
        match event:
            case tcod.event.KeyDown():
                command = game.commands.keybindings.parse(event=event, enum=game.commands.InGame)
                if command:
                    return self.on_command(command)
            case tcod.event.Quit():
                raise SystemExit()
        return None

    def on_command(self, command: game.commands.InGame) -> StateResult:
        match command.value:
            case game.commands.MoveDir(x=dx, y=dy):
                self.do_action(game.actions.Bump([Direction(dx, dy)]))
            case ">":
                self.do_action(game.actions.UseStairs(["down"]))
            case "<":
                self.do_action(game.actions.UseStairs(["up"]))
        return None

    def do_action(self, action: game.action.Action) -> StateResult:
        world = g.world
        player = world[Context].player
        match action.perform(world, player):
            case game.action.Success(time_passed=time_passed):
                assert world[Context].sched.peek() is player[Ticket]
                world[Context].sched.pop()
                player[Ticket] = world[Context].sched.schedule(time_passed, player)
            case game.action.Impossible(reason=reason):
                world[MessageLog].append(reason)
            case _:
                raise NotImplementedError()
        return None

    def on_draw(self, console: tcod.console.Console) -> None:
        game.rendering.render_all(g.world, console)


class Overworld:
    def on_event(self, event: tcod.event.Event) -> StateResult:
        match event:
            case tcod.event.KeyDown():
                command = game.commands.keybindings.parse(
                    event=event, enum=game.commands.System
                ) or game.commands.keybindings.parse(event=event, enum=game.commands.InGame)
                if command:
                    return self.on_command(command)
            case tcod.event.MouseButtonUp(button=tcod.event.BUTTON_LEFT):
                return Push(DebugQuery())
            case tcod.event.MouseMotion(motion=motion, position=position, state=state):
                map_info = g.world[Context].active_map[MapInfo]
                map_info.cursor = map_info.camera_vector + Position(position.x, position.y)
                if state & tcod.event.BUTTON_RMASK:
                    map_info.camera_center -= motion
                    map_info.cursor -= motion
            case tcod.event.WindowEvent(type="WindowLeave"):
                g.world[Context].active_map[MapInfo].cursor = None
            case tcod.event.Quit():
                raise SystemExit()
        return None

    def on_command(self, command: game.commands.System | game.commands.InGame) -> StateResult:
        match command.value:
            case game.commands.MoveDir(x=dx, y=dy):
                map_info = g.world[Context].active_map[MapInfo]
                if map_info.cursor is None:
                    map_info.cursor = map_info.camera_center
                map_info.cursor += (dx, dy)
                map_info.camera_center = map_info.cursor
            case "CONFIRM":
                return Push(DebugQuery())
        return None

    def on_draw(self, console: tcod.console.Console) -> None:
        game.rendering.render_all(g.world, console)


@attrs.define
class MenuItem:
    label: str
    callback: Callable[[], StateResult]


class Menu(State):
    def __init__(self, items: Iterable[MenuItem], *, selected: int = 0, x: int = 5, y: int = 5) -> None:
        self.items = list(items)
        self.selected: int | None = selected
        """Index of the focused menu item or None if no item is focused."""
        self.x = x
        self.y = y

    def get_position(self, event: tcod.event.MouseButtonEvent | tcod.event.MouseMotion) -> int | None:
        """Return the menu position of a mouse event."""
        cursor_y = event.position.y - self.y
        if 0 <= cursor_y < len(self.items):
            return cursor_y
        return None

    def on_event(self, event: tcod.event.Event) -> StateResult:
        match event:
            case tcod.event.KeyDown():
                command = game.commands.keybindings.parse(
                    event=event, enum=game.commands.System
                ) or game.commands.keybindings.parse(event=event, enum=game.commands.InGame)
                if command:
                    return self.on_command(command)
            case tcod.event.MouseMotion(motion=motion):
                if motion.x == 0 and motion.y == 0:
                    return None
                self.selected = self.get_position(event)
            case tcod.event.MouseButtonUp(button=tcod.event.BUTTON_LEFT):
                self.selected = self.get_position(event)
                if self.selected is not None:
                    return self.items[self.selected].callback()
                else:
                    return self.on_cancel()
            case tcod.event.MouseButtonUp(button=tcod.event.BUTTON_RIGHT):
                return self.on_cancel()
            case tcod.event.WindowEvent(type="WindowLeave"):
                self.selected = None
            case tcod.event.Quit():
                raise SystemExit()
        return None

    def on_command(self, command: game.commands.System | game.commands.InGame) -> StateResult:
        match command.value:
            case game.commands.MoveDir(y=dy):
                if self.selected is None:
                    self.selected = 0 if dy > 0 else -1
                else:
                    self.selected += dy
                self.selected %= len(self.items)
            case "CONFIRM":
                if self.selected is not None:
                    return self.items[self.selected].callback()
            case "ESCAPE":
                return self.on_cancel()
        return None

    def on_draw(self, console: tcod.console.Console) -> None:
        this_index = g.state.index(self)
        if this_index > 0:
            g.state[this_index - 1].on_draw(console)
        for i, item in enumerate(self.items):
            bg = (0x40, 0x40, 0x40) if i == self.selected else (0, 0, 0)
            console.print_box(self.x, self.y + i, 0, 0, item.label, fg=(255, 255, 255), bg=bg)

    def on_cancel(self) -> StateResult:
        return None


class MainMenu(Menu):
    def __init__(self) -> None:
        super().__init__(
            [
                MenuItem("New game", self.new_game),
                MenuItem("Quit", self.quit),
            ]
        )

    def new_game(self) -> StateResult:
        return Reset(Overworld())

    def quit(self) -> StateResult:
        raise SystemExit()


class DebugQuery(Menu):
    def __init__(self) -> None:
        map_info = g.world[Context].active_map[MapInfo]
        assert map_info.cursor
        self.cursor = map_info.cursor
        screen_pos = Position(5, 5)
        if map_info.cursor is not None:
            screen_pos = map_info.cursor - map_info.camera_vector
        options = [
            MenuItem("Build: Town", self.b_town),
            MenuItem("Debug: Cave", self.d_cave),
            MenuItem("Debug: Node", self.d_node),
        ]
        super().__init__(
            options,
            x=screen_pos.x,
            y=screen_pos.y,
        )

    def b_town(self) -> StateResult:
        g.world[Context].active_map[MapFeatures].sites[self.cursor] = ComponentDict([Graphic(ord("#"))])
        return Pop()

    def d_cave(self) -> StateResult:
        g.world[Context].active_map[MapFeatures].sites[self.cursor] = ComponentDict([Graphic(ord(">"))])
        return Pop()

    def d_node(self) -> StateResult:
        g.world[Context].active_map[MapFeatures].sites[self.cursor] = ComponentDict([Graphic(ord("*"))])
        return Pop()

    def on_cancel(self) -> StateResult:
        return Pop()
