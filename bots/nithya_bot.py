from src.player import Player
from src.map import Map
from src.robot_controller import RobotController
from src.game_constants import Team, Tile, GameConstants, Direction, BuildingType, UnitType

from src.units import Unit
from src.buildings import Building

NUM_FARMS_FOR_RUSH = 3

class BotPlayer(Player):
    def __init__(self, map: Map):
        self.map = map
        self.mode = "init"

    def safe2DListAccess(self, i, j, l):
        if i < 0 or i >= self.map.height:
            return False
        if j < 0 or j>= self.map.width:
            return False 
        return l[i][j]

    def checkRing(self, i, j, r):
        # Flags tiles that should be occupied
        for k in range(-r, r + 1):
            if self.safe2DListAccess(i + k, j + r, self.occupied):
                return True
            if self.safe2DListAccess(i + k, j - r, self.occupied):
                return True
            if self.safe2DListAccess(i + r, j + k, self.occupied):
                return True
            if self.safe2DListAccess(i - r, j + k, self.occupied):
                return True
        return False

    def enemyOnTile(self, rc:RobotController, x, y):
        for unit_id in rc.get_unit_ids(rc.get_enemy_team()):
            unit = rc.get_unit_from_id(unit_id)
            if unit.x == x and unit.y == y:
                return True
        return False
    
    def updateOccupied(self, rc: RobotController):
        self.occupied = [[0 for _ in range(self.map.width)] for _ in range(self.map.height)]

        # Flag tiles that are be occupied by a building
        team = rc.get_ally_team()
        for building in rc.get_buildings(team):
            self.occupied[building.y][building.x] = 1

        # Find tiles that should be occupied by a troop
        self.shouldOccupy = set()
        for i in range(self.map.width):
            for j in range(self.map.height):
                # Flags tiles that can't be occupied
                if self.map.is_tile_type(i, j, Tile.ERROR) or self.map.is_tile_type(i, j, Tile.MOUNTAIN) or self.map.is_tile_type(i, j, Tile.WATER):
                    self.occupied[j][i] = -1
                else:
                    if not self.occupied[j][i] and self.checkRing(i, j, 1):
                        self.shouldOccupy.add((i, j))
        
        self.totalOccupied = len(self.shouldOccupy)
        for building in rc.get_buildings(team):
            if (building.y, building.x) in self.shouldOccupy:
                self.occupied[building.y][building.x] = 1
                self.shouldOccupy.remove((building.y, building.x))

        for (i, j) in self.shouldOccupy:
            self.occupied[i][j] = 2

        for unit_id in rc.get_unit_ids(team):
            unit = rc.get_unit_from_id(unit_id)
            if (unit.x, unit.y) in self.shouldOccupy:
                self.shouldOccupy.remove((unit.x, unit.y))

    def updateTypeCounts(self, rc: RobotController):
        self.typeCounts = {}

        team = rc.get_ally_team()

        ally_buildings = rc.get_buildings(team)
        for building in ally_buildings:
            if building.type in self.typeCounts:
                self.typeCounts[building.type] += 1
            else:
                self.typeCounts[building.type] = 1

    def countFarms(self):
        tot = 0
        if BuildingType.FARM_1 in self.typeCounts:
            tot += self.typeCounts[BuildingType.FARM_1]

        if BuildingType.FARM_2 in self.typeCounts:
            tot += self.typeCounts[BuildingType.FARM_2]

        if BuildingType.FARM_3 in self.typeCounts:
            tot += self.typeCounts[BuildingType.FARM_3]
            
        return tot
    
    def getMode(self, rc):
        self.updateTypeCounts(rc)
        self.updateOccupied(rc)
        if self.countFarms() < NUM_FARMS_FOR_RUSH:
            self.mode = "FARM"
        else:
            self.mode = "RUSH"


    def getMainBuilding(self, rc):
        team = rc.get_ally_team()
        buildings = rc.get_buildings(team)
        for building in buildings:
            if building.type == BuildingType.MAIN_CASTLE:
                return building

    
    def farmTurn(self, rc: RobotController):
        # check if ring is closed and castle is surrounded--if it isnt then surround it
        # if the castle is surrounded, check how much space is inside the ring
        # if its enought for a farm, add a farm. if its not, expand the ringprint(self.shouldOccupy)
        team = rc.get_ally_team()
        ally_buildings = rc.get_buildings(team)
        main_building = self.getMainBuilding(rc)

        if main_building is None:
            return

        if len(self.shouldOccupy) > 0:
            excess =  self.totalOccupied - len(rc.get_unit_ids(team))
            if excess > 0:                
                for building in ally_buildings:
                    building_id = rc.get_id_from_building(building)[1]
                    if rc.can_spawn_unit(UnitType.WARRIOR, building_id) and excess > 0:
                        rc.spawn_unit(UnitType.WARRIOR, building_id)
                        excess -= 1
            
            for unit_id in rc.get_unit_ids(team):
                unit = rc.get_unit_from_id(unit_id)
                if self.occupied[unit.y][unit.x] != 2:
                    if len(self.shouldOccupy) > 0:
                        (x, y) = self.shouldOccupy.pop()

                        possible_move_dirs = rc.unit_possible_move_directions(unit_id)
                        possible_move_dirs.sort(key= lambda dir: rc.get_chebyshev_distance(*rc.new_location(unit.x, unit.y, dir), x, y))
                        best_dir = possible_move_dirs[0] if len(possible_move_dirs) > 0 else Direction.STAY #least chebyshev dist direction
                        if rc.can_move_unit_in_direction(unit_id, best_dir) and best_dir != Direction.STAY:
                            rc.move_unit_in_direction(unit_id, best_dir)
                        else:
                            best_dir = possible_move_dirs[1] if len(possible_move_dirs) > 1 else Direction.STAY #least chebyshev dist direction
                            rc.move_unit_in_direction(unit_id, best_dir)


            for unit_id in rc.get_unit_ids(team):
                for enemy_id in rc.get_unit_ids(rc.get_enemy_team()):
                    if rc.can_unit_attack_unit(unit_id, enemy_id):
                        rc.unit_attack_unit(unit_id, enemy_id)
            
            
            if rc.get_balance(team) > BuildingType.FARM_1.cost:
                built = False
                i = 0
                while not built:
                    i += 1
                    for j in range(i):
                        x = main_building.x + j
                        y = main_building.y + (i - j)
                        if self.safe2DListAccess(y, x, self.occupied) != 1 and (self.safe2DListAccess(y, x, self.occupied)!= False):
                            if rc.can_build_building(BuildingType.FARM_1, x, y):
                                rc.build_building(BuildingType.FARM_1, x, y)
                            built = True
                            
                        x = main_building.x + j
                        y =  main_building.y - (i - j)
                        if self.safe2DListAccess(x, y, self.occupied) != 1 and (self.safe2DListAccess(x, y, self.occupied) != False):
                            if rc.can_build_building(BuildingType.FARM_1, x, y):
                                rc.build_building(BuildingType.FARM_1, x, y)
                            built = True
                            
                        x = main_building.x - j
                        y = main_building.y + (i - j)
                        if self.safe2DListAccess(x, y, self.occupied) != 1 and (self.safe2DListAccess(x, y, self.occupied)!= False):
                            if rc.can_build_building(BuildingType.FARM_1, x, y):
                                rc.build_building(BuildingType.FARM_1, x, y)
                            built = True
                            
                        x = main_building.x - j
                        y =  main_building.y - (i - j)
                        if self.safe2DListAccess(x, y, self.occupied) != 1 and (self.safe2DListAccess(x, y, self.occupied)!= False):
                            if rc.can_build_building(BuildingType.FARM_1, x, y):
                                rc.build_building(BuildingType.FARM_1, x, y)
                            built = True
        return

    # Rush the enemy, clone of attack_bot_v1 with multiple spawners
    # This should be iterated upon to incorporate different troops
    def rushTurn(self, rc: RobotController):

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

        team = rc.get_ally_team()

        # Bulk spawn units
        ally_buildings = rc.get_buildings(team)
        for building in ally_buildings:
            building_id = rc.get_id_from_building(building)[1]
            if rc.can_spawn_unit(UnitType.KNIGHT, building_id):
                rc.spawn_unit(UnitType.KNIGHT, building_id)

        # loop through all the units
        for unit_id in rc.get_unit_ids(team):

            # if castle still stands and can attack castle, attack castle
            if enemy_castle_id in rc.get_building_ids(enemy) and rc.can_unit_attack_building(unit_id, enemy_castle_id):
                rc.unit_attack_building(unit_id, enemy_castle_id)

            # if can move towards castle, move towards castle
            unit = rc.get_unit_from_id(unit_id)
            if unit is None:
                return
            
            possible_move_dirs = rc.unit_possible_move_directions(unit_id)
            possible_move_dirs.sort(key= lambda dir: rc.get_chebyshev_distance(*rc.new_location(unit.x, unit.y, dir), enemy_castle.x, enemy_castle.y))

            best_dir = possible_move_dirs[0] if len(possible_move_dirs) > 0 else Direction.STAY #least chebyshev dist direction

            if rc.can_move_unit_in_direction(unit_id, best_dir):
                rc.move_unit_in_direction(unit_id, best_dir)
    
    def play_turn(self, rc: RobotController):
        self.getMode(rc)

        if self.mode == "FARM":
            self.farmTurn(rc)
            
        elif self.mode == "RUSH":
            self.rushTurn(rc)
            
        else:
            print("Unexpected Mode Encountered")
            raise ValueError

        
        return