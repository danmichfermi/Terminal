import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global FILTER, ENCRYPTOR, DESTRUCTOR, PING, EMP, SCRAMBLER
        FILTER = config["unitInformation"][0]["shorthand"]
        ENCRYPTOR = config["unitInformation"][1]["shorthand"]
        DESTRUCTOR = config["unitInformation"][2]["shorthand"]
        PING = config["unitInformation"][3]["shorthand"]
        EMP = config["unitInformation"][4]["shorthand"]
        SCRAMBLER = config["unitInformation"][5]["shorthand"]
        # This is a good place to do initial setup
        self.scored_on_locations = []
        self.dead_filter_locations = []
        self.dead_destructor_locations = []
        self.death_count = {}
        for i_map in range(0,28):
            for j_map in range(0,14):
                self.death_count[i_map,j_map] = 0
        # Define six "door" locations. 
        # [0] most (edge) left.
        # [1] side left.
        # [2] center left.
        # [3] center right.
        # [4] side right.
        # [5] most (edge) right.
        self.doors_locations = [[], [], [], [], [], []]
        self.doors_locations[0] = [[0, 13], [1, 13], [1, 12], [2, 12]]
        self.doors_locations[1] = [[5, 11], [6, 11], [5, 10], [6, 10]]
        self.doors_locations[2] = [[10, 11], [11, 11], [10, 10], [11, 10]]

        self.doors_locations[3] = [[17, 11], [18, 11], [17, 10], [18, 10]]
        self.doors_locations[4] = [[22, 11], [23, 11], [22, 10]]
        self.doors_locations[5] = [[26, 13], [27, 13], [25, 12], [26, 12]]
        
        # Define six "door" conditions.
        self.doors_open = [False, False, False, False, False, False]


    
        

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """


    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some Scramblers early on.
        We will place destructors near locations the opponent managed to score on.
        For offense we will use long range EMPs if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Pings to try and score quickly.
        """

        # For door testing!!!!
        if game_state.turn_number > 3:
            self.doors_open[0] = True

        if game_state.turn_number > 10:
            self.doors_open[0] = False
            self.doors_open[1] = True

        if game_state.turn_number > 20:
            self.doors_open[1] = False
            self.doors_open[2] = True

        if game_state.turn_number > 30:
            self.doors_open[2] = False
            self.doors_open[3] = True

        if game_state.turn_number > 40:
            self.doors_open[3] = False
            self.doors_open[4] = True


        # Build reactive defenses based on where the enemy scored
        self.build_reactive_defense(game_state)

        # Place basic defenses
        self.build_defences(game_state)

        # Then, place more defenses as resource allow.
        self.build_secondary_defenses(game_state)

        # Check time spend.

        self.deploy_attackers(game_state)


        gamelib.debug_write("My Time last turn: {}".format(game_state.my_time))
        gamelib.debug_write("Opponent Time last turn: {}".format(game_state.enemy_time))

        # If the turn is less than ?, do nothing and save up for a burst.

        if game_state.turn_number > 4:
            # Now let's analyze the enemy base to see where their defenses are concentrated.
            # If they have many units in the front we can build a line for our EMPs to attack them at long range.
            if self.detect_enemy_unit(game_state, unit_type=None, valid_x=None, valid_y=[14, 15]) > 10:
                self.emp_line_strategy(game_state)
            else:
                # They don't have many units in the front so lets figure out their least defended area and send Pings there.

                # Only spawn Ping's every ? turn
                # Sending more at once is better since attacks can only hit a single ping at a time
                if game_state.turn_number % 3 == 1:
                    # To simplify we will just check sending them from back left and right
                    ping_spawn_location_options = [[13, 0], [14, 0]]
                    best_location = self.least_damage_spawn_location(game_state, ping_spawn_location_options)
                    game_state.attempt_spawn(PING, best_location, 1000)

                # Lastly, if we have spare cores, let's build some Encryptors to boost our Pings' health.
                encryptor_locations = [[13, 2], [14, 2], [13, 3], [14, 3], [13, 4], [14, 4]]
                game_state.attempt_spawn(ENCRYPTOR, encryptor_locations)

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy EMPs can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Priority 0.-----------
        # Place minimum amount of filters in front of destructors to soak up damage for them.
        filter_locations_0 = [[8, 11], [14, 11], [20, 11]]
        game_state.attempt_spawn(FILTER, filter_locations_0)

        # Place destructors that attack enemy units.
        destructor_locations_0 = [[8, 10], [14, 10], [20, 10]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(DESTRUCTOR, destructor_locations_0)
        
      
        # Priority 1.-----------
        # Place minimum amount of filters in front of destructors to soak up damage for them.
        filter_locations_1 = [[2, 13], [3, 13], [24, 13], [25, 13], [4, 12], [23, 12]]
        game_state.attempt_spawn(FILTER, filter_locations_1)

        # Place destructors that attack enemy units.
        destructor_locations_1 = [[3, 12], [24, 12]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(DESTRUCTOR, destructor_locations_1)


        # Priority 2.-----------
        # Place more filters to form the wall.
        filter_locations_2 = [[4, 11], [7, 11], [9, 11], [12, 11], [13, 11], [15, 11], [16, 11], [19, 11], [21, 11]]
        game_state.attempt_spawn(FILTER, filter_locations_2)







        # Place more destructors as needed.
        #destructor_locations_5 = [[4, 11], [9, 11], [15, 11], [23, 11]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        #game_state.attempt_spawn(DESTRUCTOR, destructor_locations_5)


    def build_secondary_defenses(self, game_state):
        """
        Close up the wall as resource allows.
        Remember to defend corners and avoid placing units in the front where enemy EMPs can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download


        # Door control. Edge doors first.
        for i_door in [0, 5, 1, 4, 3, 2]:
            if self.doors_open[i_door]:
                game_state.attempt_remove(self.doors_locations[i_door])
            else:
                game_state.attempt_spawn(FILTER, self.doors_locations[i_door])


        # Priority 0.-----------
        # Place more filters to form the wall.
        filter_locations_0 = [[7, 10], [9, 10], [12, 10], [13, 10], [15, 10], [16, 10], [19, 10], [21, 10]]
        game_state.attempt_spawn(FILTER, filter_locations_0)




    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        # Build two destructors if one is killed.
        #gamelib.debug_write("Reactive-defense: {}".format(len(self.dead_destructor_locations)))
        while self.dead_destructor_locations:
            location = self.dead_destructor_locations[-1]
            locs_around = [[], [], [], []]
            locs_around[0] = [location[0]-1, location[1]]   # Left.
            locs_around[1] = [location[0]+1, location[1]]   # Right.
            locs_around[2] = [location[0], location[1]-1]   # Down.
            locs_around[3] = [location[0], location[1]+1]   # Up.
            # First try build the second one around the dead one.
            for i_locs in range(0, 4):
                if game_state.can_spawn(DESTRUCTOR, locs_around[i_locs]):
                    game_state.attempt_spawn(DESTRUCTOR, locs_around[i_locs])
                    break
            # Then build the dead one back.
            if game_state.can_spawn(DESTRUCTOR, location):
                game_state.attempt_spawn(DESTRUCTOR, location)
                # Delete this location.
                self.dead_destructor_locations.pop()
            else:
                # No resource left, break the loop.
                break

        # Build destructor behind if filter is killed multiple times.
        while self.dead_filter_locations:
            location = self.dead_filter_locations[-1]
            locs_down = [[], [], []]
            locs_down[0] = [location[0]-1, location[1]-1] # Down Left.
            locs_down[1] = [location[0], location[1]-1]   # Down Mid.
            locs_down[2] = [location[0]+1, location[1]-1] # Down Right.
            # If the filter has dead above ? times, try build a destructor below the dead filter.
            if self.death_count[location[0], location[1]] > 3:
                for i_locs in range(0, 3):
                    if game_state.can_spawn(DESTRUCTOR, locs_down[i_locs]):
                        game_state.attempt_spawn(DESTRUCTOR, locs_down[i_locs])
                        break
            # Then build the dead filter back.
            if game_state.can_spawn(FILTER, location):
                game_state.attempt_spawn(FILTER, location)
                # Delete this location.
                self.dead_filter_locations.pop()
            else:
                # No resource left, break the loop.
                break        





    def stall_with_scramblers(self, game_state):
        """
        Send out Scramblers at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) +\
                         game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own firewalls 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        

        # While we have remaining bits to spend lets send out scramblers randomly.
        while game_state.get_resource(game_state.BITS) >= game_state.type_cost(SCRAMBLER) and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(SCRAMBLER, deploy_location)
            """
            We don't have to remove the location since multiple information 
            units can occupy the same space.
            """

    def emp_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our EMP's can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [FILTER, DESTRUCTOR, ENCRYPTOR]
        cheapest_unit = FILTER
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost < gamelib.GameUnit(cheapest_unit, game_state.config).cost:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our EMPs from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        #for x in range(27, 5, -1):
        #    game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn EMPs next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        # Two locations to release EMP
        # Send out ? number of EMP at once.
        #if game_state.get_resource(game_state.BITS)/gamelib.GameUnit(DESTRUCTOR, game_state.config) > 4:
        if game_state.number_affordable(EMP)>4:
            if random.randint(0,1):
                game_state.attempt_spawn(EMP, [13, 0], 1000)
            else:
                game_state.attempt_spawn(EMP, [14, 0], 1000)

#Attempts to count how many EMPs are needed to attack through units
    def EMP_needed(game_state, start_loc, going_left)
        cur_loc = start_loc
        killed = 0
        total = 0
        # This may need to be updated
        Min_to_kill = 4
        while gamelib.game_map.in_arena_bounds(cur_loc)
            if (game_state.get_attackers(k,.5))&& total<Min_to_kill
                total= Min_to_kill
            total+=(len(game_state.get_attackers(k,.5)))-killed
            killed++
            cur_loc[1]+=1
            if going_left
                cur_loc[0]+=-1
            else
                cur_loc[0]+=1
        return total
#THIS FUNCTION MIGHT BE INCORRECT- selects spawn location to attack with
    def find_release_location(self, game_state, door_loc, left_min):
        if left_min:
            game_state.find_map_to_edge(door_loc, BOTTOM_RIGHT )
        else:
            game_state.find_map_to_edge(door_loc, BOTTOM_LEFT )

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(DESTRUCTOR, game_state.config).damage
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
        
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered


    def deploy_attackers(self, game_state):
        """
        First lets check if we have enough bits
        otherwise wait
        """
        # self.update_num_attackers(game_state)
        """
        this gives the number of EMPs needed to kill defenders
        variables requiring connecting
        door_locations[i], target_edge, attack_doors, door_state, open_doors etc.
        """
        attack_door_indexes = [0,0]
        EMP_attack_index = -1
        #number of EMPs being used
        EMP_attack_load = 100
        # 1 is left
        #this loop determines where attack locations are
        bestlocation = [0,0]
        doorstate=False
        self.top_wall_y=10
        for i in self.doors_open:
            if (self.doors_open[i]):
                doorstate=True
        if not door_state:
            EMP_Min = [-1,-1]
            for i in self.door_locations:
                for j in self.door_locations[i]:
                    if(self.door_locations[i][j][1]<top_wall):
                        pass
                    EMP_Num_left = EMP_needed(game_state, self.door_locations[i][j], True)
                    EMP_Num_right = EMP_needed(game_state, self.door_locations[i][j], False)
                    if EMP_Min[0]<0:
                        EMP_Min[0] = EMP_Num_left
                        EMP_Min[1] = EMP_Num_right   
                    if EMP_Num_left < EMP_Min[1]:
                        if EMP_Num_left < EMP_Min[0]:
                            EMP_Min[1]=EMP_Min[0]
                            attack_door_indexes[1]=attack_door_indexes[0]
                            EMP_Min[0]=EMP_Num_left
                            attack_door_indexes[0]=i
                        else:
                            EMP_Min[1]=EMP_Num_left
                            attack_door_indexes[1]=i
                    if EMP_Num_right < EMP_Min[1]:
                        if EMP_Num_right < EMP_Min[0]:
                            EMP_Min[1]=EMP_Min[0]
                            attack_door_indexes[1]=attack_door_indexes[0]
                            EMP_Min[0]=EMP_Num_right
                            attack_door_indexes[0]=i
                        else:
                            EMP_Min[1]=EMP_Num_right
                            attack_door_indexes[1]=i
        #open the doors if prepared
        #should we consider max value?
                        if ((game_state.get_resource(game_state.BITS)*0.75+5) > (EMP_Min[0])* game_state.type_cost(EMP) ):
                            self.doors_open[i]=True
                            self.doors_open[i]=True
        #decide where to fire after doors open
        else:
            EMP_Min=-1
            left_min=False
            #Find Minimal open door
            for i in self.door_locations:
                if notself.doors_open[i]:
                    pass
                for j in self.door_locations[i]:
                    if(self.door_locations[i][j][1]<top_wall):
                        pass

                    EMP_Num_left = EMP_needed(game_state, self.door_locations[i][j], True)
                    EMP_Num_right = EMP_needed(game_state, self.door_locations[i][j], False)
                    if((EMP_Min<0) || (EMP_Min<EMP_Num_left)):
                        EMP_Min = EMP_Num_left
                        EMP_attack_index = i
                        left_min=True
                    if((EMP_Min<0) || (EMP_Min<EMP_Num_right)):
                        EMP_Min = EMP_Num_right
                        EMP_attack_index = i
                        left_min=False
            bestlocation=find_release_location(self, game_state, self.door_locations[i][j], left_min)
            EMP_attack_load = EMP_min
        #Need to add max conditions; do we wat
        if (game_state.get_resource(game_state.BITS) < (EMP_attack_load)* game_state.type_cost(EMP) ):
            self.perform_attack = False
            return

        #EMP attack
        self.perform_attack = True
        game_state.attempt_spawn(EMP, bestlocation, EMP_attack_load)

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at: https://docs.c1games.com/json-docs.html
        """
        # # Let's record at what position we get scored on
        # state = json.loads(turn_string)
        # events = state["events"]
        # breaches = events["breach"]
        # for breach in breaches:
        #     location = breach[0]
        #     unit_owner_self = True if breach[4] == 1 else False
        #     # When parsing the frame data directly, 
        #     # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
        #     if not unit_owner_self:
        #         gamelib.debug_write("Got scored on at: {}".format(location))
        #         self.scored_on_locations.append(location)
        #         gamelib.debug_write("All locations: {}".format(self.scored_on_locations))

        
        # Find the positions of dead defense units.
        state = json.loads(turn_string)
        events = state["events"]
        deaths = events["death"]

        for death in deaths:
            location = death[0]
            unit_type = death[1]
            unit_owner_self = True if death[3] == 1 else False
            removed_by_us = death[4]
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if unit_owner_self and not removed_by_us:
                #gamelib.debug_write("On-action-frame unit_type: {}".format(unit_type))
                #gamelib.debug_write("On-action-frame FILTER: {}".format(FILTER))
                if unit_type == 2: # DESTRUCTOR
                    self.dead_destructor_locations.append(location)
                    self.death_count[location[0], location[1]] = self.death_count[location[0], location[1]] + 1
                if unit_type == 0: # FILTER
                    self.dead_filter_locations.append(location)
                    self.death_count[location[0], location[1]] = self.death_count[location[0], location[1]] + 1
                




if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
