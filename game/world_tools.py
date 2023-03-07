from tcod.ec import ComponentDict

import game.map_tools
import game.mapgen.world
import game.tiles
from game.actor_tools import new_actor
from game.components import Context, Graphic, MapDict, Player, Position
from game.messages import MessageLog


def new_world() -> ComponentDict:
    world = ComponentDict([Context(), MapDict(), MessageLog()])
    game.tiles.init(world)
    ctx = world[Context]
    game.map_tools.activate_map(world, game.mapgen.world.WorldMap())
    ctx.player = new_actor(world, (Position(1, 1), Graphic(ord("@")), Player()))
    return world
