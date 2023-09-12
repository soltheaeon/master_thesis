from random import uniform
from typing import Any

from tdw.add_ons.third_person_camera import ThirdPersonCamera
from simulation_handler import SimulationHandler
from utils import *
import numpy as np


class ContainmentSimulator(SimulationHandler):
    """
    Initializes the containment simulator.
    """
    def __init__(self, port: int = 1071):
        self.ctrl_id = 'containment'
        self.initialize_coordinates()
        super().__init__(port=port)

    def initialize_coordinates(self):
        """
        Initializes the x and z coordinates randomly.
        """
        self.x, self.z = self.get_random_coords(), self.get_random_coords()

    @staticmethod
    def get_random_coords() -> float:
        """
        Generates and returns a random coordinate value.
        """
        return random.uniform(-2.8, 2.8)

    def run_frame_by_frame(self, trial_type: str, tot_frames: int):
        """
        Runs the simulation frame by frame based on the trial type.
        """
        frames_until_end = random.randint(18, 42)
        # Choose the simulation type based on trial_type
        if trial_type == 'transitional':
            return self.run_transitional(tot_frames, frames_until_end)
        elif trial_type == 'psychological':
            return self.run_psychological(tot_frames, frames_until_end)
        else:
            return self.run_physical(tot_frames, frames_until_end)

    def run_transitional(self, tot_frames: int, frames_until_end: int):
        """
        Runs the transitional simulation.
        """
        rots, locs, transitions = [], [], []
        wait = random.randint(18, 42)
        transitions_skipped = 0

        for i in range(tot_frames):
            response = self.communicate([])
            cmds = self.handle_transitional_response(i, rots, locs, wait, transitions, transitions_skipped, response)
            response = self.communicate(cmds)

        return self.cleanup(frames_until_end)

    def handle_transitional_response(self, i: int, rots: list, locs: list, wait: int, transitions: list, transitions_skipped: int, response: dict) -> list:
        """
        Handles the transitional simulation's response and generates necessary commands.
        """
        cmds = []
        if i != 0:
            # Extract necessary information from the response
            entity_rot_degree, container_loc, _ = get_mass_loc_rot(response, self.o_ids[0])
            rots.append(entity_rot_degree)
            locs.append(container_loc)

            # If the wait duration is reached, generate transition commands
            if len(rots) == wait:
                cmds = self.get_transitional_cmds(i, rots, locs, transitions, transitions_skipped, container_loc,
                                                  response)
                rots, locs = rots[1:], locs[1:]
        return cmds

    def get_transitional_cmds(self, i: int, rots: list, locs: list, transitions: list, transitions_skipped: int, container_loc: list, response: dict) -> list:
        """
        Generates commands for the transitional simulation based on entity's rotation and location.
        """
        cmds = []
        # Check for stabilized rotation and location
        freeze_rot = np.array([np.std(np.array(rots)[:, idx]) < .28 for idx in range(3)]).all()
        freeze_loc = np.array([np.std(np.array(locs)[:, idx]) < .28 for idx in range(3)]).all()

        if freeze_rot and freeze_loc:
            # Calculate relative entity location and check for the start of transition
            entity_loc = get_mass_loc_rot(response, self.o_ids[1])[1]
            entity_rel_loc = np.abs(np.array(container_loc) - np.array(entity_loc))
            max_distance = np.abs(np.array([bound for bound in self.bounds[1]]))
            start_transition = (entity_rel_loc < max_distance).all()

            if start_transition:
                transitions.append(i + 1)
                scaled_force = scale_force(self.o_record) * .225
                cmds = self.create_force_cmds(scaled_force)
                transitions_skipped = 0
        return cmds

    def create_force_cmds(self, scaled_force: float) -> list:
        """
        Creates a command to apply force at a random position on an object.
        """
        return [{"$type": "apply_force_at_position",
                 "id": self.o_ids[1],
                 "force": {"x": scaled_force, "y": 0, "z": scaled_force},
                 "position": {"x": random.uniform(-10, 10), "y": 0, "z": random.uniform(-10, 10)}}]

    def run_psychological(self, tot_frames: int, frames_until_end: int) -> tuple:
        """
        Simulates a psychological test for a given number of frames.
        """
        # Initialize variables
        agent_success = False
        agent_bounds = np.max(TDWUtils.get_bounds_extents(self.o_record.bounds)) / 2
        target_bounds = np.max(TDWUtils.get_bounds_extents(self.target_rec.bounds)) * .2 / 2
        total_bounds = agent_bounds + target_bounds

        # Run the simulation loop
        for i in range(tot_frames):
            response = self.communicate([])
            response = self.communicate_psychological(i, total_bounds, agent_success, response, frames_until_end)
            if (calculate_dist(response, self.o_ids[1], self.o_ids[2]) - total_bounds) < .05:
                agent_success = True

        # Cleanup and return results
        return self.cleanup(frames_until_end)

    def communicate_psychological(self, i: int, total_bounds: float, agent_success: bool, response: dict, frames_until_end: int) -> dict:
        """
        Executes psychological communication commands.
        """
        cmds = self.get_psychological_cmds(i, total_bounds, agent_success, response, frames_until_end)
        return self.communicate(cmds)

    def get_psychological_cmds(self, i: int, total_bounds: float, agent_success: bool, response: dict, frames_until_end: int) -> list:
        """
        Generates psychological command sets based on current state.
        """
        # Initialize velocities
        velocity, vertical_velocity = .05, .05
        vertical_velocity -= .005 if vertical_velocity > 0 else 0
        cmds = [{"$type": "teleport_object_by", "position": {"x": 0, "y": vertical_velocity, "z": 0},
                 "id": self.o_ids[1], "absolute": True},
                {"$type": "teleport_object_by", "position": {"x": 0, "y": 0, "z": velocity},
                 "id": self.o_ids[1], "absolute": False},
                {"$type": "object_look_at", "other_object_id": self.o_ids[2], "id": self.o_ids[1]}, ]

        # Check conditions for termination or continuation
        if (calculate_dist(response, self.o_ids[1], self.o_ids[2]) - total_bounds) < .05 or i < frames_until_end or agent_success:
            return []

        return cmds

    def run_physical(self, tot_frames: int, frames_until_end: int) -> tuple:
        """
        Simulates a physical test for a given number of frames.
        """
        # Simulate the physical environment
        for _ in range(tot_frames - frames_until_end):
            self.communicate([])

        # Cleanup and return results
        return self.cleanup(frames_until_end)

    def cleanup(self, frames_until_end: int) -> tuple:
        """
        Cleans up the simulation environment.
        """
        # Generate entity destruction commands
        destroy_cmds = [{"$type": "destroy_object", "id": entity_id} for entity_id in self.o_ids]
        destroy_cmds.append({"$type": "send_rigidbodies", "frequency": "never"})
        self.communicate(destroy_cmds)

        return -1, True

    def random_location_offset(self, coord: float) -> float:
        """
        Generates a random offset for a given coordinate.
        """
        offset = random.uniform(1, .5)
        return coord + offset if random.choice([True, False]) else coord - offset

    def get_agent_location(self) -> dict:
        """
        Gets the random location of the agent.
        """
        x = self.random_location_offset(self.x)
        z = self.random_location_offset(self.z)
        return {"x": x, "y": random.uniform(0, 0.3), "z": z}

    def generate_object_position(self, y_offset: float = 0) -> Dict[str, float]:
        """
        Generate object position based on the class's x and z attributes with an optional y offset.
        """
        return {"x": self.x, "y": y_offset, "z": self.z}

    def generate_random_rotation(self, limit: int = 8) -> Dict[str, float]:
        """
        Generate a random rotation for an object.
        """
        return {"x": uniform(-limit, limit), "y": uniform(-limit, limit), "z": uniform(-limit, limit)}

    def add_physics_object(self, model_name: str, library: str, object_id: Any, position: Dict[str, float],
                           rotation: Dict[str, float], scale_factor: float = 1) -> List[Dict[str, Any]]:
        """
        Construct a list of commands to add a physics object to the environment.
        """
        cmds = []
        cmds.extend(self.get_add_physics_object(model_name=model_name,
                                                library=library,
                                                object_id=object_id,
                                                position=position,
                                                rotation=rotation,
                                                scale_factor=scale_factor))
        return cmds

    def spawn_target_entity(self, cmds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Spawn a target entity in the environment.
        """
        target = self.o_ids[2]
        agent_loc = self.get_agent_location()
        cmds, self.target_rec = target_cmd(target, agent_loc, cmds)
        return cmds

    def spawn_entity(self, cmds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Spawn an entity in the environment.
        """
        foundation_entity_name = random.choice([record.name for record in ModelLibrarian('models_flex.json').records])
        foundation_scale = .5
        foundation_entity = get_entity_by_name(foundation_entity_name, lib='models_flex.json')
        self.foundation_height = foundation_scale * TDWUtils.get_bounds_extents(foundation_entity.bounds)[1]
        entity_id = self.get_unique_id()

        cmds.extend(self.add_physics_object(foundation_entity_name, "models_flex.json", entity_id,
                                            self.generate_object_position(), TDWUtils.VECTOR3_ZERO, foundation_scale))

        cmds.extend([{"$type": "set_rigidbody_constraints", "id": entity_id,
                      "freeze_position_axes": {'x': 1, 'y': 1, 'z': 1},
                      "freeze_rotation_axes": {'x': 1, 'y': 1, 'z': 1}},
                     {"$type": "set_color",
                      "color": {"r": random.random(), "g": random.random(), "b": random.random(), "a": 0.5},
                      "id": entity_id}])
        return cmds

    def set_camera(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Set the camera's position and look-at point.
        """
        loc = {"x": self.x + uniform(-0.8, 0.8), "y": uniform(3.1, 3.5), "z": self.z + uniform(-0.8, 0.8)}
        look_at = {"x": self.x, "y": 1.0, "z": self.z}
        camera = ThirdPersonCamera(position=loc, look_at=look_at, avatar_id='frames_temp')
        self.add_ons.append(camera)
        return loc, look_at

    def init_trial_cmds(self) -> List[Dict[str, Any]]:
        """
        Initialize the commands for a trial.
        """
        cmds = []

        entities, self.bounds = get_random_entity_pair(list1=CONTAINED_ENTITIES, list2=CONTAINER_ENTITIES)
        h = self.foundation_height
        y = h + random.uniform(.15, .25)

        container_entity_id = self.get_unique_id()
        cmds.extend(self.add_physics_object(entities[1].name, 'models_core.json', container_entity_id,
                                            self.generate_object_position(y), self.generate_random_rotation()))

        self.o_record = entities[0]
        entity_id = self.get_unique_id()
        self.o_ids = [container_entity_id, entity_id] if self.trial_type != 'psychological' else [container_entity_id,
                                                                                                  entity_id,
                                                                                                  self.get_unique_id()]
        cmds.extend(self.add_physics_object(self.o_record.name, 'models_core.json', entity_id,
                                            self.generate_object_position(0.75), self.generate_random_rotation(45)))

        self.names = {'object': entities[0].name, 'container': entities[1].name}

        if self.trial_type == 'psychological':
            cmds = self.spawn_target_entity(cmds)
            self.names['target'] = self.target_rec.name

        cmds.extend([{"$type": "send_rigidbodies", "frequency": "always"},
                     {"$type": "send_transforms", "frequency": "always"}])

        return cmds


if __name__ == "__main__":
    c = ContainmentSimulator()

    args = build_arg_pars()
    print(console_msg('default: tot_frames = 200, add_object_to_scene = True', 'warning'))
    success = c.run(num=args.num, pass_masks=args.pass_masks, room=args.room, tot_frames=200,
                    add_object_to_scene=True, trial_type=args.trial_type,
                    png=args.png, save_frames=args.save_frames, save_mp4=args.save_mp4)
    print(success)