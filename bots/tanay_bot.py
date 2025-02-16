from src.player import Player
from src.map import Map
from src.robot_controller import RobotController
from src.game_constants import Team, Tile, GameConstants, Direction, BuildingType, UnitType

from src.units import Unit
from src.buildings import Building

NUM_FARMS_FOR_ACCUM = 3
NUM_FARMS_FOR_RUSH = 2


class BotPlayer(Player):
    def __init__(self, map: Map):
        self.map = map
        self.mode = "init"
        self.rushStart = False
        self.rushFarms = set()

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
    
    def updateFarms(self, rc: RobotController):
        team = rc.get_ally_team()
        removal = []

        for (x, y) in self.rushFarms:
            found = False
            for building in rc.get_buildings(team):
                if building.x == x and building.y == y:
                    found = True
            if not found:
                removal.append((x, y))

        for (x, y) in removal:
            self.rushFarms.remove((x, y))

        if len(self.rushFarms) != NUM_FARMS_FOR_RUSH:
            self.rushStart = False

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
                    if not self.occupied[j][i] and self.checkRing(j, i, 1):
                        self.shouldOccupy.add((i, j))

        self.totalOccupied = len(self.shouldOccupy)
        for building in rc.get_buildings(team):
            if (building.x, building.y) in self.shouldOccupy:
                self.occupied[building.y][building.x] = 1
                self.shouldOccupy.remove((building.x, building.y))

        for (i, j) in self.shouldOccupy:
            self.occupied[j][i] = 2

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
        self.updateFarms(rc)

        if self.countFarms() < NUM_FARMS_FOR_ACCUM:
            self.mode = "FARM"
        elif self.rushStart:
            self.mode = "RUSH"
        else:
            self.mode = "ACCUM"


    def getMainBuilding(self, rc):
        team = rc.get_ally_team()
        buildings = rc.get_buildings(team)
        for building in buildings:
            if building.type == BuildingType.MAIN_CASTLE:
                return building
            
    def enemyOnLocation(self, x, y, rc: RobotController):
        enemy = rc.get_enemy_team()

        for enemy_id in rc.get_unit_ids(rc.get_enemy_team()):
            enemy = rc.get_unit_from_id(enemy_id)
            if enemy.x == x and enemy.y == y:
                return True
        
        return False

    def accumTurn(self, rc: RobotController):
        team = rc.get_ally_team()

        if rc.get_balance(team) >= NUM_FARMS_FOR_RUSH * BuildingType.FARM_1.cost:
            # Buy shit
            enemy_buildings = rc.get_buildings(rc.get_enemy_team())
            for building in enemy_buildings:
                if building.type == BuildingType.MAIN_CASTLE:
                    enemy_castle_id = rc.get_id_from_building(building)[1]
                    break

            enemy_castle = rc.get_building_from_id(enemy_castle_id)

            built = len(self.rushFarms)
            i = 0
            while built < NUM_FARMS_FOR_RUSH:
                
                i += 1
                for j in range(i + 1):
                    if built >= NUM_FARMS_FOR_RUSH:
                        break

                    x = enemy_castle.x + j
                    y = enemy_castle.y + (i - j)

                    if self.safe2DListAccess(y, x, self.occupied) != 1 and (type(self.safe2DListAccess(y, x, self.occupied)) != bool):
                        if rc.can_build_building(BuildingType.FARM_1, x, y) and not self.enemyOnLocation(x, y, rc):
                            rc.build_building(BuildingType.FARM_1, x, y)
                            self.rushFarms.add((x, y))
                            built += 1
                            
                    x = enemy_castle.x + j
                    y =  enemy_castle.y - (i - j)

                    if self.safe2DListAccess(y, x, self.occupied) != 1 and (type(self.safe2DListAccess(y, x, self.occupied)) != bool):
                        if rc.can_build_building(BuildingType.FARM_1, x, y) and not self.enemyOnLocation(x, y, rc):
                            rc.build_building(BuildingType.FARM_1, x, y)
                            self.rushFarms.add((x, y))
                            built += 1
                        
                        
                    x = enemy_castle.x - j
                    y = enemy_castle.y + (i - j)
                    if self.safe2DListAccess(y, x, self.occupied) != 1 and (type(self.safe2DListAccess(y, x, self.occupied)) != bool):
                        if rc.can_build_building(BuildingType.FARM_1, x, y) and not self.enemyOnLocation(x, y, rc):
                            rc.build_building(BuildingType.FARM_1, x, y)
                            self.rushFarms.add((x, y))
                            built += 1
                        
                    x = enemy_castle.x - j
                    y =  enemy_castle.y - (i - j)
                    if self.safe2DListAccess(y, x, self.occupied) != 1 and (type(self.safe2DListAccess(y, x, self.occupied)) != bool):
                        if rc.can_build_building(BuildingType.FARM_1, x, y) and not self.enemyOnLocation(x, y, rc):
                            rc.build_building(BuildingType.FARM_1, x, y)
                            self.rushFarms.add((x, y))
                            built += 1
            self.rushStart = True
        
        self.farmTurn(rc, True)


    def farmTurn(self, rc: RobotController, accum: bool):
        # check if ring is closed and castle is surrounded--if it isnt then surround it
        # if the castle is surrounded, check how much space is inside the ring
        # if its enought for a farm, add a farm. if its not, expand the ringprint(self.shouldOccupy)
        team = rc.get_ally_team()
        ally_buildings = rc.get_buildings(team)
        main_building = self.getMainBuilding(rc)

        if main_building is None:
            return

        if len(self.shouldOccupy) > 0:
            excess =  (self.totalOccupied + 1) - len(rc.get_unit_ids(team))
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
                        moved = False
                        if rc.can_move_unit_in_direction(unit_id, best_dir) and best_dir != Direction.STAY:
                            rc.move_unit_in_direction(unit_id, best_dir)
                            moved = True
                        
                        if not moved:
                            best_dir = possible_move_dirs[1] if len(possible_move_dirs) > 1 else Direction.STAY #least chebyshev dist direction
                            if rc.can_move_unit_in_direction(unit_id, best_dir) and best_dir != Direction.STAY:
                                rc.move_unit_in_direction(unit_id, best_dir)
                                moved = True

                        if not moved:
                            best_dir = possible_move_dirs[2] if len(possible_move_dirs) > 2 else Direction.STAY #least chebyshev dist direction
                            if rc.can_move_unit_in_direction(unit_id, best_dir) and best_dir != Direction.STAY:
                                rc.move_unit_in_direction(unit_id, best_dir)
                                moved = True


            for unit_id in rc.get_unit_ids(team):
                for enemy_id in rc.get_unit_ids(rc.get_enemy_team()):
                    if rc.can_unit_attack_unit(unit_id, enemy_id):
                        rc.unit_attack_unit(unit_id, enemy_id)
            
        if not accum and rc.get_balance(team) > BuildingType.FARM_1.cost:
            built = False
            i = 0
            while not built:
                i += 1
                for j in range(i + 1):
                    if built:
                        break

                    x = main_building.x + j
                    y = main_building.y + (i - j)
                    if self.safe2DListAccess(y, x, self.occupied) != 1 and (type(self.safe2DListAccess(y, x, self.occupied)) != bool):
                        if rc.can_build_building(BuildingType.FARM_1, x, y):
                            rc.build_building(BuildingType.FARM_1, x, y)

                            built = True
                        
                    x = main_building.x + j
                    y =  main_building.y - (i - j)
                    if self.safe2DListAccess(y, x, self.occupied) != 1 and (type(self.safe2DListAccess(y, x, self.occupied)) != bool):
                        if rc.can_build_building(BuildingType.FARM_1, x, y):
                            rc.build_building(BuildingType.FARM_1, x, y)
                            built = True
                        
                    x = main_building.x - j
                    y = main_building.y + (i - j)
                    if self.safe2DListAccess(y, x, self.occupied) != 1 and (type(self.safe2DListAccess(y, x, self.occupied)) != bool):
                        if rc.can_build_building(BuildingType.FARM_1, x, y):
                            rc.build_building(BuildingType.FARM_1, x, y)
                            built = True
                        
                    x = main_building.x - j
                    y =  main_building.y - (i - j)
                    if self.safe2DListAccess(y, x, self.occupied) != 1 and (type(self.safe2DListAccess(y, x, self.occupied)) != bool):
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
            if (building.x, building.y) in self.rushFarms and rc.can_spawn_unit(UnitType.SWORDSMAN, building_id):
                rc.spawn_unit(UnitType.SWORDSMAN, building_id)

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
            self.farmTurn(rc, False)
            
        elif self.mode == "RUSH":
            self.rushTurn(rc)
        
        elif self.mode == "ACCUM":
            self.accumTurn(rc)

        else:
            print("Unexpected Mode Encountered")
            raise ValueError

        
        return