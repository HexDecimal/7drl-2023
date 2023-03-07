import itertools
from typing import Any

import numpy as np
import tcod.camera
import tcod.console
from numpy.typing import NDArray
from tcod.ec import ComponentDict

import game.actor_tools
from game.components import Context, Graphic, MapFeatures, MapInfo, Position
from game.map import Map
from game.map_attrs import a_tiles
from game.messages import MessageLog
from game.tiles import TileDB

SHROUD = np.array([(0x20, (0, 0, 0), (0, 0, 0))], dtype=tcod.console.rgb_graphic)


def render_all(world: ComponentDict, console: tcod.console.Console) -> None:
    LOG_HEIGHT = 5
    SIDEBAR_WIDTH = 20
    console.clear()
    # if __debug__:
    #    console.rgb[:] = 0x20, (0, 127, 0), (255, 0, 255)
    render_map(world, console.rgb[:-LOG_HEIGHT, :-SIDEBAR_WIDTH])
    log_console = tcod.console.Console(console.width - SIDEBAR_WIDTH, LOG_HEIGHT)
    side_console = tcod.console.Console(SIDEBAR_WIDTH, console.height)

    y = log_console.height
    for message in reversed(world[MessageLog].log):
        text = str(message)
        y -= tcod.console.get_height_rect(log_console.width, text)
        log_console.print_box(0, y, log_console.width, 0, text, (255, 255, 255))
        if y <= 0:
            break
    log_console.blit(console, dest_x=0, dest_y=console.height - log_console.height)

    side_console.print(0, 0, f"Turn: {world[Context].sched.time}", fg=(255, 255, 255))
    side_console.blit(console, dest_x=console.width - side_console.width, dest_y=0)


def render_map(world: ComponentDict, out: NDArray[Any]) -> None:
    """Render the active world map, showing visible and remembered tiles/objects."""
    map = world[Context].active_map[Map]
    map_info = world[Context].active_map[MapInfo]
    player = world[Context].player
    tiles_db = world[TileDB]
    player_memory = game.actor_tools.get_memory(world, player)
    player_fov = game.actor_tools.compute_fov(world, player)
    map_info.camera_vector = Position(*tcod.camera.get_camera(out.T.shape, map_info.camera_center.xy))
    camera_ij = map_info.camera_vector.yx

    screen_slice, world_slice = tcod.camera.get_slices(out.shape, (map.height, map.width), camera_ij)
    world_view = map[a_tiles][world_slice]

    visible_graphics = tiles_db.data["graphic"][world_view]

    for obj in itertools.chain(
        world[Context].active_map[MapFeatures].features,
        world[Context].actors,
    ):
        pos = obj[Position]
        screen_x = pos.x - camera_ij[1] - screen_slice[1].start
        screen_y = pos.y - camera_ij[0] - screen_slice[0].start
        if 0 <= screen_x < visible_graphics.shape[1] and 0 <= screen_y < visible_graphics.shape[0]:
            graphic = obj[Graphic]
            visible_graphics[["ch", "fg"]][screen_y, screen_x] = graphic.ch, graphic.fg

    memory_graphics = tiles_db.data["graphic"][player_memory.tiles[world_slice]]

    for pos, obj in player_memory.objs.items():
        screen_x = pos.x - camera_ij[1] - screen_slice[1].start
        screen_y = pos.y - camera_ij[0] - screen_slice[0].start
        if 0 <= screen_x < visible_graphics.shape[1] and 0 <= screen_y < visible_graphics.shape[0]:
            graphic = obj[Graphic]
            memory_graphics[["ch", "fg"]][screen_y, screen_x] = graphic.ch, graphic.fg

    memory_graphics["fg"] //= 2
    memory_graphics["bg"] //= 2

    full_bright = True  # If True show whole map as visible.

    out[screen_slice] = np.select(
        [full_bright or player_fov.visible[world_slice], player_memory.tiles[world_slice] != 0],
        [visible_graphics, memory_graphics],
        SHROUD,
    )
    if map_info.cursor:
        cursor_x = map_info.cursor.x - camera_ij[1]
        cursor_y = map_info.cursor.y - camera_ij[0]
        if 0 <= cursor_x < out.shape[1] and 0 <= cursor_y < out.shape[0]:
            out[["fg", "bg"]][cursor_y, cursor_x] = (0x0, 0x0, 0x0), (0xFF, 0xFF, 0xFF)
