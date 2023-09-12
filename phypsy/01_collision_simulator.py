from simulation_handler import SimulationHandler
from tdw.add_ons.third_person_camera import ThirdPersonCamera
from utils import *
from copy import deepcopy
from tdw.tdw_utils import TDWUtils
from random import uniform
from tdw.add_ons.collision_manager import CollisionManager
import numpy as np


class CollisionSimulator(SimulationHandler):

    def __init__(self):
        """
        Initializes a new instance of the CollisionSimulator.
        """
        self.ctrl_id = 'collision'
        self.add_ons = []
        self.num_objects = 0
        self.o_ids = []
        self.entities = []
        self.target_rec = None

    def _initialize_psychological(self) -> Tuple[float, float, float, bool, List[dict]]:
        """
        Initializes the parameters for a psychological trial type.
        """
        velocity = .05
        agent_bounds = np.max(
            TDWUtils.get_bounds_extents(get_entity_by_name(self.entities[self.num_objects - 2]).bounds)) / 2
        target_bounds = np.max(TDWUtils.get_bounds_extents(self.target_rec.bounds)) * .2 / 2
        total_bounds = agent_bounds + target_bounds

        scaled_force = scale_force(get_entity_by_name(self.entities[1]))

        agent_success = False

        obstacle_data = [
            {
                "bounds": np.max(TDWUtils.get_bounds_extents(get_entity_by_name(self.entities[i]).bounds)) / 2,
                "height": TDWUtils.get_bounds_extents(get_entity_by_name(self.entities[i]).bounds)[1],
                "jump": False,
                "dist_hor": np.nan,
                "last_dist_hor": np.nan
            } for i in range(self.num_objects - 2)
        ]

        return velocity, total_bounds, scaled_force, agent_success, obstacle_data

    def _initialize_transitional(self) -> float:
        """
        Initializes the parameters for a transitional trial type.
        """
        tot_bounds = sum([
            np.max(TDWUtils.get_bounds_extents(get_entity_by_name(entity).bounds)) / 2
            for entity in [self.entities[0], self.entities[1]]
        ])
        return tot_bounds

    def _run_transitional(self, velocity: List[float], tot_bounds: float, transitions: List[int], i: int) -> List[int]:
        """
        Executes a frame in a transitional trial type.
        """
        transition_completed = False
        response = self.communicate([])
        if (calculate_dist(response, self.o_ids[0], self.o_ids[1]) - tot_bounds) < random.uniform(.5, .6):
            transition_completed = True
        if transition_completed:
            response = self.communicate([
                {
                    "$type": "teleport_object_by",
                    "position": {"x": velocity[0], "y": 0.0, "z": velocity[1]},
                    "id": self.o_ids[0],
                    "absolute": True
                }
            ])
            transitions.append(i)
        return transitions

    def _run_psychological(self, velocity: float, total_bounds: float, scaled_force: float, agent_success: bool,
                           obstacle_data: List[dict], transitions: List[int], i: int) -> Tuple[
        List[dict], List[int], bool]:
        """
        Executes a frame in a psychological trial type.
        """
        cmds = []
        response = self.communicate([])
        if i == 0:
            # Initial setup commands for the first frame.
            cmds.extend(
                [{"$type": "object_look_at", "other_object_id": self.o_ids[-1], "id": self.o_ids[-2]},
                 {"$type": "teleport_object_by", "position": {"x": 0, "y": 0, "z": velocity}, "id": self.o_ids[-2],
                  "absolute": False}])
        elif (calculate_dist(response, self.o_ids[-2], self.o_ids[-1]) - total_bounds) < .4 or agent_success:
            if not agent_success:
                cmds.extend(
                    [{"$type": "object_look_at", "other_object_id": self.o_ids[-1], "id": self.o_ids[-2]},
                     {"$type": "apply_force_magnitude_to_object",
                      "magnitude": scaled_force,
                      "id": self.o_ids[-2]}])
                agent_success = True
        else:
            # Commands for normal operation in subsequent frames.
            cmds.extend(
                [{"$type": "object_look_at", "other_object_id": self.o_ids[-1], "id": self.o_ids[-2]},
                 {"$type": "teleport_object_by", "position": {"x": 0, "y": 0, "z": velocity}, "id": self.o_ids[-2],
                  "absolute": False}])

            for j, data in enumerate(obstacle_data):
                if (calculate_dist(response, self.o_ids[j], self.o_ids[-2]) - (
                        data["bounds"] + obstacle_data[-1]["bounds"])) < (
                        data["height"] / velocity + velocity * 3):
                    # Handle obstacles and agent positioning based on horizontal distances.
                    agent_loc = {val: key for val, key in
                                 zip(['x', 'y', 'z'], get_mass_loc_rot(response, self.o_ids[-2])[1])}
                    object_loc = {val: key for val, key in
                                  zip(['x', 'y', 'z'], get_mass_loc_rot(response, self.o_ids[j])[1])}
                    agent_loc['y'], object_loc['y'] = 0, 0
                    data["dist_hor"] = TDWUtils.get_distance(agent_loc, object_loc)

                    if data["dist_hor"] < data["last_dist_hor"]:
                        cmds.append(
                            {"$type": "teleport_object_by", "position": {"x": 0, "y": velocity * 2, "z": 0},
                             "id": self.o_ids[-2], "absolute": True})

                    data["last_dist_hor"] = data["dist_hor"]

        if any(cmd['$type'] == 'teleport_object_by' for cmd in cmds):
            transitions.append(i)
        return cmds, transitions, agent_success

    def run_frame_by_frame(self, trial_type: str, tot_frames: int) -> dict:
        """
        Executes the simulation frame by frame based on the trial type.
        """
        velocity = [random.choice([-.1, 0, .1]) for _ in range(2)]
        transitions = [] if trial_type != 'physical' else None
        collision = False

        coll_mngr = CollisionManager(enter=True, stay=False, exit=False, objects=True, environment=True)
        self.add_ons.append(coll_mngr)

        if trial_type == 'psychological':
            velocity, total_bounds, scaled_force, agent_success, obstacle_data = self._initialize_psychological()
        elif trial_type == 'transitional':
            tot_bounds = self._initialize_transitional()

        for i in range(tot_frames):
            if trial_type == 'transitional':
                transitions = self._run_transitional(velocity, tot_bounds, transitions, i)
            elif trial_type == 'psychological':
                cmds, transitions, agent_success = self._run_psychological(velocity, total_bounds, scaled_force,
                                                                           agent_success, obstacle_data, transitions, i)
                response = self.communicate(cmds)
            elif trial_type == 'physical':
                self.communicate([])
            if coll_mngr.obj_collisions:
                collision = True

        self._cleanup_after_run()

        return self._get_results(trial_type, collision, transitions)

    def _cleanup_after_run(self):
        """
        Cleanup operations after a trial run.
        """
        destroy_commands = [{"$type": "destroy_object", "id": entity_id} for entity_id in self.o_ids]
        destroy_commands.append({"$type": "send_rigidbodies", "frequency": "never"})
        self.communicate(destroy_commands)

    def _get_results(self, trial_type: str, collision: bool, transitions: list) -> (int or list, bool):
        """
        Calculate the results based on the trial type, collision, and transitions.
        """
        if trial_type == 'physical' and not collision:
            print(console_msg(f'Objects did not collide, yet this is required for physical trials.', 'error'))
            success = collision
        elif trial_type == 'transitional':
            if collision:
                print(console_msg(f'Object failed to avoid collision', 'error'))
            if not transitions:
                print(console_msg(f'No transition happened in this trial', 'error'))
            success = not collision
        else:
            success = True

        return transitions if transitions else -1, success

    @staticmethod
    def generate_random_coordinate(min_val: float, max_val: float) -> float:
        """
        Generate a random floating-point value between the provided minimum and maximum values.
        """
        return random.uniform(min_val, max_val)

    def set_drop_loc(self) -> list:
        """
        Generate a random drop location and its associated location on the ground.
        """
        drop_loc = {"x": self.generate_random_coordinate(-1, 1),
                    "y": self.generate_random_coordinate(3, 5),
                    "z": self.generate_random_coordinate(-1, 1)}

        loc = {axis: drop_loc[axis] + self.generate_random_coordinate(-.1, .1) for axis in ['x', 'z']}
        loc['y'] = 0
        return [loc, drop_loc]

    def set_locs(self) -> list:
        """
        Generate random locations for entities called 'patient' and 'collider'.
        """
        coord_range = [-2.2, -1.5, 1.5, 2.2]
        collider_loc = {"x": random.choice(coord_range), "y": 0, "z": random.choice(coord_range)}

        patient_loc = {"x": self.generate_random_coordinate(-.5, .5),
                       "y": 0,
                       "z": self.generate_random_coordinate(-.5, .5)}

        return [patient_loc, collider_loc]

    def spawn_entity(self, cmds: list, rot: dict) -> list:
        """
        Generate commands to spawn entities in the simulation.
        """
        object_count = self.num_objects if self.trial_type != 'psychological' else self.num_objects - 1
        for i in range(object_count):
            cmds.extend(self.get_add_physics_object(
                model_name=self.entities[i],
                library='models_core.json',
                object_id=self.o_ids[i],
                position=self.positions[i],
                rotation=rot if i == 1 else {"x": 0, "y": 0, "z": 0},
                default_physics_values=False,
                mass=1,
                scale_mass=False,
            ))
        return cmds

    def get_entity_loc(self, entity_id: str, response: list) -> dict:
        """
        Extract the location of a given entity from the simulation response.
        """
        for i in range(len(response) - 1):
            resp_id = OutputData.get_data_type_id(response[i])
            if resp_id == "tran":
                transforms = Transforms(response[i])
                for j in range(transforms.get_num()):
                    if transforms.get_id(j) == entity_id:
                        return transforms.get_position(j)

    def spawn_target_entity(self, cmds: list) -> list:
        """
        Generate commands to spawn a target entity in the simulation.
        """
        target = self.o_ids[-1]

        target_loc = deepcopy(self.positions[-1])
        target_loc['z'] = -target_loc['z']
        target_loc['x'] = -target_loc['x']

        displacement = random.uniform(.2, .4)
        target_loc['z'] += displacement if target_loc['z'] < 0 else -displacement
        target_loc['x'] += displacement if target_loc['x'] < 0 else -displacement

        cmds, self.target_rec = target_cmd(target, target_loc, cmds)
        return cmds

    def set_camera(self) -> tuple:
        """
        Set the position and target for the camera.
        """
        loc, look_at = {"x": -3.0, "y": 3.1, "z": -3.3}, {"x": 0, "y": 0, "z": 0}
        self.camera = ThirdPersonCamera(position=loc,
                                        look_at=look_at,
                                        avatar_id='frames_temp')
        self.add_ons.append(self.camera)
        return loc, look_at

    def init_trial_cmds(self) -> list:
        """
        Initialize commands for a new trial in the simulation.
        """
        self.num_objects = 2 if self.trial_type != 'psychological' else random.randint(3, 4)
        self.o_ids = [self.get_unique_id() for _ in range(self.num_objects)]

        collision_type = random.choice(['fall', 'force']) if self.trial_type != 'psychological' else 'psychological'
        self.positions = self.set_locs() if collision_type != 'fall' else self.set_drop_loc()

        camera_turn = {"x": self.positions[0]['x'], "y": 0, "z": self.positions[0]['z']}
        self.camera.look_at(camera_turn)

        if self.num_objects == 4:
            self.positions.insert(0, self.positions[0])
            scale_factors = [random.uniform(1.3, 3.1) for _ in range(2)]
            self.positions[0:2] = [{k: (v / scale_factors[0] if idx == 0 else -v / scale_factors[1]) for k, v in
                                    self.positions[-1].items()} for idx in range(2)]

        random.shuffle(self.entities)

        random_rotation = lambda: random.choice([uniform(0, 360), 0])
        rot = {"x": random_rotation(), "y": random_rotation(),
               "z": random_rotation()} if collision_type == 'fall' else {"x": 0, "y": 0, "z": 0}

        cmds = self.spawn_entity(cmds=[], rot=rot)

        if collision_type == 'force':
            magnitude = random.uniform(18, 38)
            cmds.extend([
                {"$type": "object_look_at", "other_object_id": self.o_ids[0], "id": self.o_ids[1]},
                {"$type": "apply_force_magnitude_to_object", "magnitude": magnitude, "id": self.o_ids[1]}
            ])

        if collision_type == 'psychological':
            cmds = self.spawn_target_entity(cmds)
            self.names = {'agent': self.entities[self.num_objects - 2], 'target': self.target_rec.name,
                          'obstacles': self.entities[:2]}
        else:
            self.names = {'entity0': self.entities[0], 'entity1': self.entities[1]}

        cmds.extend([
            {"$type": "send_transforms", "frequency": "always"},
            {"$type": "send_rigidbodies", "frequency": "always"},
            {"$type": "send_static_rigidbodies", "frequency": "once"},
            {"$type": "send_collisions", "enter": True, "stay": False, "exit": False, "collision_types": ["obj"]}
        ])

        return cmds


if __name__ == "__main__":
    c = CollisionSimulator()

    args = build_arg_pars()
    print(console_msg('add_object_to_scene is set to False', 'warning'))
    success = c.run(num=args.num, pass_masks=args.pass_masks, room=args.room, tot_frames=args.tot_frames,
                    add_object_to_scene=False, trial_type=args.trial_type,
                    png=args.png, save_frames=args.save_frames, save_mp4=args.save_mp4)
    print(success)
