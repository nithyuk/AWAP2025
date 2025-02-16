from src.player import Player
from src.map import Map
from src.robot_controller import RobotController
from src.game_constants import Team, Tile, GameConstants, Direction, BuildingType, UnitType

from src.units import Unit
from src.buildings import Building
from typing import Tuple
class BotPlayer(Player):
    def __init__(self, map: Map):
        self.map = map
        self.rc = None

    def get_nearest_buildable_tile(self, rc: RobotController, building_type: BuildingType, building_location: Tuple[int, int]) -> Tuple[int, int]:
        # get the nearest buildable tile in a 7x7 square around the given building location (castle)
        candidate_tiles = []
        for i in range(-3, 4):
            for j in range(-3, 4):
                # if its in bounds of the map
                if building_location[0] + i >= 0 and building_location[0] + i < self.map.width and building_location[1] + j >= 0 and building_location[1] + j < self.map.height:
                    candidate_tiles.append((building_location[0] + i, building_location[1] + j))

        buildable_tiles = [tile for tile in candidate_tiles if rc.can_build_building(building_type, tile[0], tile[1])]
        if len(buildable_tiles) == 0:
            return None
        nearest_tile = min(buildable_tiles, key=lambda tile: rc.get_chebyshev_distance(tile[0], tile[1], building_location[0], building_location[1]))
        return nearest_tile
    
    # build a farm in the farthest buildable tile to the enemy castle within a 10 radius square
    def build_farm_away_from_castle(self, rc: RobotController, building_type: BuildingType, building_location: Tuple[int, int]) -> bool:
        candidate_tiles = []
        radius = 4
        for i in range(-radius, radius + 1):
            for j in range(-radius, radius + 1):
                # if its in bounds of the map
                if building_location[0] + i >= 0 and building_location[0] + i < self.map.width and building_location[1] + j >= 0 and building_location[1] + j < self.map.height:
                    candidate_tiles.append((building_location[0] + i, building_location[1] + j))

        buildable_tiles = [tile for tile in candidate_tiles if rc.can_build_building(building_type, tile[0], tile[1])]
        if len(buildable_tiles) == 0:
            return None
        farthest_tile = max(buildable_tiles, key=lambda tile: rc.get_chebyshev_distance(tile[0], tile[1], building_location[0], building_location[1]))
        return farthest_tile
    
    def count_units(self, unit_type: UnitType, team: Team) -> int:
        return len([unit for unit in self.rc.get_units(team) if unit.type == unit_type])
    
    def count_buildings(self, building_type: BuildingType, team: Team) -> int:
        return len([building for building in self.rc.get_buildings(team) if building.type == building_type])
    
    def play_turn(self, rc: RobotController):
        self.rc = rc
        print("Playing turn")
        team = rc.get_ally_team()
        ally_castle_id = -1
        money = rc.get_balance(team)
        ally_buildings = rc.get_buildings(team)
        for building in ally_buildings:
            if building.type == BuildingType.MAIN_CASTLE:
                ally_castle_id = rc.get_id_from_building(building)[1]
                break

        castle = rc.get_building_from_id(ally_castle_id)
        if castle is None:
            return
        
        castle_location = castle.x, castle.y
        enemy = rc.get_enemy_team()
        enemy_castle_id = -1

        enemy_buildings = rc.get_buildings(enemy)
        for building in enemy_buildings:
            if building.type == BuildingType.MAIN_CASTLE:
                enemy_castle_id = rc.get_id_from_building(building)[1]
                break

        enemy_castle = rc.get_building_from_id(enemy_castle_id)
        if enemy_castle is None: 
            return
        
        # if we have a farm, build a catapult there
        if self.count_buildings(BuildingType.FARM_1, team) > 0:
            farm_locations = [building.id for building in ally_buildings if building.type == BuildingType.FARM_1]
            for farm_location in farm_locations:
                if rc.can_spawn_unit(UnitType.CATAPULT, farm_location) and self.count_units(UnitType.CATAPULT, team) < 2:
                    success = rc.spawn_unit(UnitType.CATAPULT, farm_location)
                    print(f"Spawned catapult: {success}")
                else:
                    print(f"Can't spawn catapult: {rc.can_spawn_unit(UnitType.CATAPULT, farm_location)} {self.count_units(UnitType.CATAPULT, team)}")


        # print("Trying to spawn catapult")
        # if we have less than 2 catapults, spawn catapult
        # if rc.can_spawn_unit(UnitType.CATAPULT, ally_castle_id) and self.count_units(UnitType.CATAPULT, team) < 2:
        #     success = rc.spawn_unit(UnitType.CATAPULT, ally_castle_id)
        #     print(f"Spawned catapult: {success}")
            # if success:
                # move the catapult to a cardinal direction from the castle
                # plus_shaped_tiles = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                # for dir in plus_shaped_tiles:
                #     if rc.can_move_unit_in_direction(success, dir):
                #         rc.move_unit_in_direction(success, dir)
                #         print(f"Moved catapult to {dir}")
                #         break


        # if we have less than 4 warrior, spawn warrior
        if rc.can_spawn_unit(UnitType.WARRIOR, ally_castle_id) and self.count_units(UnitType.WARRIOR, team) + self.count_units(UnitType.SWORDSMAN, team) < 2 + len(rc.get_units(enemy)):
            # if we have at least 1 farm, spawn swordsmen instead of warriors
            # if self.count_buildings(BuildingType.FARM_1, team) > 0 and rc.can_spawn_unit(UnitType.SWORDSMAN, ally_castle_id):
            #     success = rc.spawn_unit(UnitType.SWORDSMAN, ally_castle_id)
            #     print(f"Spawned swordman: {success}")
            # else:
            success = rc.spawn_unit(UnitType.WARRIOR, ally_castle_id)
            print(f"Spawned warrior: {success}")
        else:
            # print why we can't spawn warrior
            print(f"Can't spawn warrior: {rc.can_spawn_unit(UnitType.WARRIOR, ally_castle_id)} {self.count_units(UnitType.WARRIOR, team)}")

        # otherwise spam farms in the nearest buildable tile to our castle
        nearest_tile = self.build_farm_away_from_castle(rc, BuildingType.FARM_1, (enemy_castle.x, enemy_castle.y))
        print(f"Nearest tile: {nearest_tile}")
        if money < 30:
            print("Not enough money to spawn farm")
        elif nearest_tile is None:
            print("No buildable tiles found for farm")
        elif rc.can_build_building(BuildingType.FARM_1, nearest_tile[0], nearest_tile[1]) and self.count_buildings(BuildingType.FARM_1, team) < 2:
            success = rc.build_building(BuildingType.FARM_1, nearest_tile[0], nearest_tile[1])
            print(f"Spawned farm: {success}")
        else:
            # print why we can't spawn farm
            print(f"Can't spawn farm: {rc.can_build_building(BuildingType.FARM_1, nearest_tile[0], nearest_tile[1])} {self.count_buildings(BuildingType.FARM_1, team)}")

        # spawn 1 knight per turn for every 2 farms
        # if rc.can_spawn_unit(UnitType.KNIGHT, ally_castle_id) and self.count_units(UnitType.KNIGHT, team) < self.count_buildings(BuildingType.FARM_1, team) // 2:
        #     success = rc.spawn_unit(UnitType.KNIGHT, ally_castle_id)
        #     print(f"Spawned knight: {success}")
        # else:
        #     # print why we can't spawn knight
        #     print(f"Can't spawn knight: {rc.can_spawn_unit(UnitType.KNIGHT, ally_castle_id)} {self.count_units(UnitType.KNIGHT, team)}")


        # now if we have a farm, spawn a warrior for every troop they have
        # total_enemy_troops_cost = sum([enemy_unit.cost for enemy_unit in rc.get_units(enemy)])
        # if rc.can_spawn_unit(UnitType.WARRIOR, ally_castle_id) and rc.get_unit_count(UnitType.WARRIOR, team) < total_enemy_troops_cost:
        #     rc.spawn_unit(UnitType.WARRIOR, ally_castle_id)
        #     # run the unit towards enemy units
        #     enemy_units = rc.get_units(enemy)
        #     closest_enemy_unit = min(enemy_units, key=lambda unit: rc.get_chebyshev_distance(unit.x, unit.y, enemy_castle.x, enemy_castle.y))
        #     rc.move_unit_in_direction(rc.get_id_from_unit(UnitType.WARRIOR, team)[0], closest_enemy_unit.x, closest_enemy_unit.y)

        # loop through all the units
        for unit_id in rc.get_unit_ids(team):

            unit = rc.get_unit_from_id(unit_id)
            possible_move_dirs = rc.unit_possible_move_directions(unit_id)
            
            # if our unit is within one unit of our castle, move away from castle
            if unit.x == castle.x and unit.y == castle.y:
                # for now, let catapults only move cardinally and others move diagonally
                # if unit.type == UnitType.CATAPULT:
                    # possible_move_dirs = [dir for dir in possible_move_dirs if dir in [Direction.DOWN, Direction.UP, Direction.LEFT, Direction.RIGHT]]
                # else:
                    # possible_move_dirs = [dir for dir in possible_move_dirs if dir in [Direction.DOWN_LEFT, Direction.DOWN_RIGHT, Direction.UP_LEFT, Direction.UP_RIGHT]]
                possible_move_dirs.sort(key= lambda dir: rc.get_chebyshev_distance(*rc.new_location(unit.x, unit.y, dir), enemy_castle.x, enemy_castle.y))
                best_dir = possible_move_dirs[0] if len(possible_move_dirs) > 0 else Direction.STAY #least chebyshev dist direction
                rc.move_unit_in_direction(unit_id, best_dir)
                print(f"Moved unit {unit_id} of type {unit.type} to {best_dir}")

            # if our unit can attack enemy units, attack enemy units closest to our castle
            enemy_units = rc.get_units(enemy)
            if len(enemy_units) > 0 and unit.type in [UnitType.WARRIOR, UnitType.SWORDSMAN]:
                closest_enemy_unit = min(enemy_units, key=lambda unit: rc.get_chebyshev_distance(unit.x, unit.y, castle.x, castle.y))
                if rc.can_unit_attack_unit(unit_id, closest_enemy_unit.id):
                    rc.unit_attack_unit(unit_id, closest_enemy_unit.id)

            if unit.type == UnitType.CATAPULT:
                # if we have a catapult, attack the enemy castle
                if rc.can_unit_attack_building(unit_id, enemy_castle_id):
                    rc.unit_attack_building(unit_id, enemy_castle_id)

            # if castle still stands and can attack castle, attack castle
            # if enemy_castle_id in rc.get_building_ids(enemy) and rc.can_unit_attack_building(unit_id, enemy_castle_id):
            #     rc.unit_attack_building(unit_id, enemy_castle_id)

            # if can move towards castle, move towards castle
            # if unit is a knight, move towards castle
            # if unit.type == UnitType.KNIGHT:
            #     possible_move_dirs = rc.unit_possible_move_directions(unit_id)
            #     possible_move_dirs.sort(key= lambda dir: rc.get_chebyshev_distance(*rc.new_location(unit.x, unit.y, dir), enemy_castle.x, enemy_castle.y))

            #     best_dir = possible_move_dirs[0] if len(possible_move_dirs) > 0 else Direction.STAY #least chebyshev dist direction

            #     if rc.can_move_unit_in_direction(unit_id, best_dir):
            #         rc.move_unit_in_direction(unit_id, best_dir)

            # if unit.type == UnitType.WARRIOR:
            #     possible_move_dirs = rc.unit_possible_move_directions(unit_id)
            #     possible_move_dirs.sort(key= lambda dir: rc.get_chebyshev_distance(*rc.new_location(unit.x, unit.y, dir), enemy_castle.x, enemy_castle.y))

            #     best_dir = possible_move_dirs[0] if len(possible_move_dirs) > 0 else Direction.STAY #least chebyshev dist direction

            #     if rc.can_move_unit_in_direction(unit_id, best_dir):
            #         rc.move_unit_in_direction(unit_id, best_dir)
            
            # if unit is a warrior, move towards enemy units
            # if unit.type == UnitType.WARRIOR:
            #     enemy_units = rc.get_units(enemy)
            #     if len(enemy_units) > 0:
            #         closest_enemy_unit = min(enemy_units, key=lambda unit: rc.get_chebyshev_distance(unit.x, unit.y, enemy_castle.x, enemy_castle.y))
            #         # manually calculate the best direction
            #         best_dir = Direction.STAY
            #         best_dist = rc.get_chebyshev_distance(unit.x, unit.y, closest_enemy_unit.x, closest_enemy_unit.y)
            #         for dir in possible_move_dirs:
            #             if rc.can_move_unit_in_direction(unit_id, dir) and rc.get_chebyshev_distance(*rc.new_location(unit.x, unit.y, dir), closest_enemy_unit.x, closest_enemy_unit.y) < best_dist:
            #                 best_dir = dir
            #                 best_dist = rc.get_chebyshev_distance(*rc.new_location(unit.x, unit.y, dir), closest_enemy_unit.x, closest_enemy_unit.y)
                        
            #         rc.move_unit_in_direction(unit_id, best_dir)
            #     else:
            #         print("No enemy units to attack, moving towards castle")
            #         possible_move_dirs = rc.unit_possible_move_directions(unit_id)
            #         possible_move_dirs.sort(key= lambda dir: rc.get_chebyshev_distance(*rc.new_location(unit.x, unit.y, dir), enemy_castle.x, enemy_castle.y))

            #         best_dir = possible_move_dirs[0] if len(possible_move_dirs) > 0 else Direction.STAY #least chebyshev dist direction

            #         rc.move_unit_in_direction(unit_id, best_dir)