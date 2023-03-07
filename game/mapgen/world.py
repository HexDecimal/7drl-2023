import attrs
from tcod.ec import ComponentDict

import game.map_tools
from game import map_attrs
from game.map import Map, MapKey
from game.tiles import TileDB


@attrs.define(frozen=True)
class WorldMap(MapKey):
    def generate(self, world: ComponentDict) -> ComponentDict:
        tiles_db = world[TileDB]

        map = game.map_tools.new_map(world, 120, 120)
        map[Map][map_attrs.a_tiles][:] = tiles_db["plains"]

        return map
