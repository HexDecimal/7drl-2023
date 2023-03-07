import itertools
import random

import attrs
from tcod.ec import ComponentDict

import game.mapgen.caves
from game import map_attrs
from game.components import Context, Graphic, MapDict, MapFeatures, MapInfo, Position, Stairway
from game.map import Map, MapKey
from game.tiles import TileDB


@attrs.define(frozen=True)
class TestMap(MapKey):
    level: int = 0

    def generate(self, world: ComponentDict) -> ComponentDict:
        map = new_map(world, 50, 50)
        free_spaces = list(itertools.product(range(1, 9), range(1, 9)))
        random.shuffle(free_spaces)
        map[MapFeatures] = MapFeatures(
            [
                ComponentDict(
                    [
                        Position(*free_spaces.pop()),
                        Graphic(ord(">")),
                        Stairway(down=game.mapgen.caves.CaveMap(self.level + 1)),
                    ]
                ),
            ]
        )
        if self.level > 0:
            map[MapFeatures].features.append(
                ComponentDict([Position(*free_spaces.pop()), Graphic(ord("<")), Stairway(up=TestMap(self.level - 1))])
            )
        print(map[MapFeatures])
        return map


def new_map(world: ComponentDict, width: int, height: int) -> ComponentDict:
    tile_db = world[TileDB]
    map = Map(width, height)
    map[map_attrs.a_tiles][:] = tile_db["wall"]
    map[map_attrs.a_tiles][1:-1, 1:-1] = tile_db["floor"]
    map_entity = ComponentDict([map])
    map_entity[MapFeatures] = MapFeatures()
    map_entity[MapInfo] = MapInfo()
    return map_entity


def get_map(world: ComponentDict, key: MapKey) -> ComponentDict:
    map_dict = world[MapDict]
    if key not in map_dict:
        map_dict[key] = key.generate(world)
    return map_dict[key]


def activate_map(world: ComponentDict, key: MapKey) -> None:
    world[Context].active_map = get_map(world, key)
