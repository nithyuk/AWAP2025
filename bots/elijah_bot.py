from typing import List
from src.player import Player
from src.map import Map
from src.robot_controller import RobotController
from src.game_constants import (
    Team,
    Tile,
    GameConstants,
    Direction,
    BuildingType,
    UnitType,
)

from src.units import Unit
from src.buildings import Building


class StaticInfo:
    def __init__(self, own_team: Team, opponent_team: Team, board_map: Map):
        self.team = own_team
        self.opponent_team = opponent_team
        self.board_map = board_map


class TurnInfo:
    def __init__(self, rc: RobotController, our_team: Team):
        self.turn_num = rc.get_turn()
        self.our_balance = rc.get_balance(our_team)


class WrappedPlayer(Player):
    def __init__(self, map: Map):
        self.map = map
        self.static_info: StaticInfo | None = None
        self.turn_info: TurnInfo | None = None

    def init_static_info(self, rc: RobotController):
        if self.static_info is not None:
            return

        self.static_info = StaticInfo(
            rc.get_ally_team(), rc.get_enemy_team(), self.map
        )

    def init_turn_info(self, rc: RobotController):
        self.turn_info = TurnInfo(rc, self.static_info.team)

    def start_turn(self, rc: RobotController):
        self.init_static_info(rc)
        self.init_turn_info(rc)

    def end_turn(self, _rc: RobotController):
        self.turn_info = None

    def play_turn(self, rc: RobotController):
        raise NotImplementedError


class BotPlayer(WrappedPlayer):

    def __init__(self, map):
        super().__init__(map)
        self.farm_coords: list[tuple[int, int]] = []

    def play_turn(self, rc):

        target_cost = BuildingType.FARM_1.cost + (UnitType.WARRIOR.cost * 4)

        self.start_turn(rc)

        team = self.static_info.team
        ally_castle_id = -1

        ally_buildings = rc.get_buildings(team)
        for building in ally_buildings:
            if building.type == BuildingType.MAIN_CASTLE:
                ally_castle_id = rc.get_id_from_building(building)[1]
                break

        enemy = self.static_info.opponent_team
        enemy_castle_id = -1

        enemy_buildings = rc.get_buildings(enemy)
        for building in enemy_buildings:
            if building.type == BuildingType.MAIN_CASTLE:
                enemy_castle_id = rc.get_id_from_building(building)[1]
                break

        enemy_castle = rc.get_building_from_id(enemy_castle_id)
        if enemy_castle is None:
            return

        warrior_spawn_id = ally_castle_id


        enemy_unit_map = {}
        enemy_units = rc.get_units(self.static_info.opponent_team)
        for enemy_unit in enemy_units:
            enemy_unit_map[(enemy_unit.x, enemy_unit.y)] = True

        if (
            # len(self.farm_coords) == 0 and
            self.turn_info.our_balance >= target_cost
        ):

            potential_farm_coords = []
            for x in range(self.map.width):
                for y in range(self.map.height):
                    if rc.can_build_building(BuildingType.FARM_1, x, y) and (x, y) not in enemy_unit_map:
                        potential_farm_coords.append((x, y))
            potential_farm_coords.sort(
                key=lambda coords: rc.get_chebyshev_distance(
                    enemy_castle.x, enemy_castle.y, coords[0], coords[1]
                )
            )

            if len(potential_farm_coords) > 0:
                (best_x, best_y) = potential_farm_coords[0]

                old_len = len(rc.get_buildings(self.static_info.team))
                assert (
                    rc.build_building(BuildingType.FARM_1, best_x, best_y)
                    is True
                )
                self.farm_coords.append((x, y))

                farm_id = -1
                if len(self.farm_coords) > 0:
                    our_buildings: List[Building] = rc.get_buildings(
                        self.static_info.team
                    )
                    for building in our_buildings:
                        if (building.x, building.y) == (best_x, best_y):
                            warrior_spawn_id = building.id
                            farm_id = building.id
                            break

                for i in range(4):
                    # build warrior
                    built_warrior = rc.spawn_unit(
                        UnitType.WARRIOR, warrior_spawn_id
                    )
                    assert built_warrior is True  

                    return
        if len(self.farm_coords) > 0:
            our_buildings = rc.get_buildings(self.static_info.team)
            for building in our_buildings:
                if (building.x, building.y) == self.farm_coords[0]:
                    warrior_spawn_id = building.id
                    break

        if self.turn_info.turn_num % 3 == 0:
            # if can spawn warrior, spawn warrior
            if rc.can_spawn_unit(UnitType.WARRIOR, warrior_spawn_id):
                rc.spawn_unit(UnitType.WARRIOR, warrior_spawn_id)

            # if can spawn knight, spawn knight
            if rc.can_spawn_unit(UnitType.KNIGHT, warrior_spawn_id):
                rc.spawn_unit(UnitType.KNIGHT, warrior_spawn_id)

            for building in ally_buildings:
                if rc.can_spawn_unit(UnitType.KNIGHT, building_id=building.id):
                    rc.spawn_unit(UnitType.KNIGHT, building_id=building.id)

        castle = rc.get_building_from_id(ally_castle_id)

        # loop through all the units
        for unit_id in rc.get_unit_ids(team):
            # attack the unit closest to our castle, if possible
            closest_enemy_unit = min(enemy_units, key=lambda unit: rc.get_chebyshev_distance(unit.x, unit.y, castle.x, castle.y))
            if rc.can_unit_attack_unit(unit_id, closest_enemy_unit.id):
                rc.unit_attack_unit(unit_id, closest_enemy_unit.id)

            # if castle still stands and can attack castle, attack castle
            if enemy_castle_id in rc.get_building_ids(
                enemy
            ) and rc.can_unit_attack_building(unit_id, enemy_castle_id):
                rc.unit_attack_building(unit_id, enemy_castle_id)

            # if can move towards castle, move towards castle
            unit = rc.get_unit_from_id(unit_id)
            if unit is None:
                return

            # if can attack any other troops, do so now
            for enemy_unit in enemy_units:
                if rc.can_unit_attack_unit(unit_id, enemy_unit.id):
                    rc.unit_attack_unit(unit_id, enemy_unit.id)
                    break

            possible_move_dirs = rc.unit_possible_move_directions(unit_id)
            possible_move_dirs.sort(
                key=lambda dir: rc.get_chebyshev_distance(
                    *rc.new_location(unit.x, unit.y, dir),
                    enemy_castle.x,
                    enemy_castle.y,
                )
            )

            best_dir = (
                possible_move_dirs[0]
                if len(possible_move_dirs) > 0
                else Direction.STAY
            )  # least chebyshev dist direction

            if rc.can_move_unit_in_direction(unit_id, best_dir):
                rc.move_unit_in_direction(unit_id, best_dir)

        self.end_turn(rc)
        return
