from typing import Union, Any
from tdw.add_ons.third_person_camera import ThirdPersonCamera
from simulation_handler import SimulationHandler
from utils import *
from tdw.output_data import Transforms, OutputData
from tdw.librarian import ModelLibrarian
import numpy as np
from copy import deepcopy


class OcclusionSimulator(SimulationHandler):
    def __init__(self, port=1071):
        self.ctrl_id = 'occlusion'
        lib = ModelLibrarian('models_core.json')
        self.recs = {record.name: record for record in lib.records}
        self.camera_loc = {"x": random.uniform(1.3, 1.9), "y": 0.2, "z": random.uniform(-0.8, 0.8)}
        super().__init__(port=port)

    def calculate_freeze_point(self) -> float:
        """Calculate the freeze point based on occluder and camera locations."""
        freeze = np.abs(self.occluder_z_loc - self.camera_loc['z'])
        if self.camera_loc['z'] > self.occluder_z_loc:
            return self.occluder_z_loc - freeze
        else:
            return self.occluder_z_loc + freeze

    def run_transitional_trial(self, freeze: float, i: int, velocity: float, transition_complete: bool) -> Tuple[List[int], bool, float]:
        """Handle the transitional trial logic."""
        transition = []
        if self.occluded_entity_loc['z'] > freeze and self.direction == 'left' or \
           self.occluded_entity_loc['z'] < freeze and self.direction == 'right':
            cmds = []
            if not transition_complete:
                velocity = random.choice([random.uniform(0.01, 0.3), 0])
                velocity = velocity if self.direction == 'right' else -velocity
                transition_complete = True
                cmds.extend(self.freeze_rigidbody(True))
            else:
                cmds.extend(self.freeze_rigidbody(False))
            transition.append(i)
            cmds.extend(self.teleport_object_by(velocity))
            self.communicate(cmds)
        else:
            response = self.communicate([])
            for index, val in zip(['x', 'y', 'z'], self.get_entity_loc(self.o_ids[0], response)):
                self.occluded_entity_loc[index] = val
        return transition, transition_complete, velocity

    def run_psychological_trial(self, i: int, velocity: float, total_bounds: float, agent_success: bool) -> Tuple[
        List[int], bool]:
        """Handle the psychological trial logic."""
        transition = []
        response = None  # Initialize response to avoid unresolved reference
        if i == 0 or not agent_success:
            response = self.communicate([])  # Fetch response to use it in the next line
            if (self.calculate_dist(response, self.o_ids[0], self.o_ids[2]) - total_bounds) < .05:
                cmds = [self.object_look_at(self.o_ids[2], self.o_ids[0]),
                        self.teleport_object_by(velocity, absolute=False)]
                response = self.communicate(cmds)
                transition.append(i)
        else:
            response = self.communicate([])
            agent_success = True
        return transition, agent_success

    def freeze_rigidbody(self, is_frozen: bool) -> List[dict]:
        """Generate commands to freeze/unfreeze the rigidbody."""
        val = 1 if is_frozen else 0
        return [{"$type": "set_rigidbody_constraints", "id": self.o_ids[0],
                 "freeze_position_axes": {"x": val, "y": val, "z": val},
                 "freeze_rotation_axes": {"x": val, "y": val, "z": val}}]

    def teleport_object_by(self, velocity: float, absolute: bool = True) -> dict:
        """Generate teleport command."""
        return {"$type": "teleport_object_by", "position": {"x": 0, "y": 0, "z": velocity},
                "id": self.o_ids[0], "absolute": absolute}

    def object_look_at(self, other_object_id: int, object_id: int) -> dict:
        """Generate look-at command."""
        return {"$type": "object_look_at", "other_object_id": other_object_id, "id": object_id}

    def run_frame_by_frame(self, trial_type: str, tot_frames: int) -> Union[str, Tuple[Union[int, List[int]], bool]]:
        """
        Run the trial frame by frame.
        """
        success = True
        velocity = .04
        transition_complete = False
        transition = None if trial_type == 'physical' else []
        freeze = self.calculate_freeze_point()

        for i in range(tot_frames):
            if trial_type == 'transitional':
                transition, transition_complete, velocity = self.run_transitional_trial(freeze, i, velocity, transition_complete)
            elif trial_type == 'physical':
                self.communicate([])
            elif trial_type == 'psychological':
                total_bounds = self.calculate_total_bounds()
                transition, agent_success = self.run_psychological_trial(i, velocity, total_bounds, agent_success)

            if i == 0:
                if self.is_occluder_blocking_view():
                    response = self.communicate([])
                    print(console_msg(f'The occluder might block too much of the view', 'error'))
                    success = False
                    break

        self.destroy_objects()
        if not success:
            return 'Fail', success
        return transition if transition else -1, True

    def set_occluder(self) -> Tuple[List[Dict[str, Any]], Tuple[Any, Any]]:
        recs, cmds = [], []

        recs, bounds = get_random_entity_pair(list1=OCCLUDED_ENTITIES, list2=OCCLUDER_ENTITIES, axes=[1, 2])

        self.all_names = [record.name for record in recs]
        for i, record in enumerate(recs):
            object_id = self.o_ids[0] if i == 0 else self.o_ids[1]
            position = self.occluded_entity_loc if i == 0 else {"x": 0, "y": 0, "z": self.occluder_z_loc}

            scale_factor = random.uniform(0.9, 1.1)

            rotation_y = random.uniform(-90, 90) if i == 0 else 0
            cmds.extend(self.get_add_physics_object(model_name=record.name,
                                                    library="models_core.json",
                                                    object_id=object_id,
                                                    position=position,
                                                    rotation={"x": 0, "y": rotation_y, "z": 0},
                                                    scale_factor={"x": scale_factor, "y": scale_factor, "z": scale_factor},
                                                    default_physics_values=False,
                                                    mass=1
                                                    ))

        self.names = {'object': self.all_names[0], 'collider': self.all_names[1]}
        return cmds, bounds

    def set_camera(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Set the camera's location and view direction."""
        look_at = {"x": 0, "y": 0, "z": 0}
        self.camera = ThirdPersonCamera(position=self.camera_loc,
                                        look_at=look_at,
                                        avatar_id='frames_temp')
        self.add_ons.append(self.camera)
        return self.camera_loc, look_at

    def get_entity_loc(self, entity_id: str, response: List[Any]) -> Dict[str, Any]:
        """Fetch the location of the entity given its ID."""
        for i in range(len(response) - 1):
            resp_id = OutputData.get_data_type_id(response[i])
            if resp_id == "tran":
                transforms = Transforms(response[i])
                for j in range(transforms.get_num()):
                    if transforms.get_id(j) == entity_id:
                        return transforms.get_position(j)
        return console_msg(f"Location data unavailable for {self.all_names[0]}", 'error')

    def spawn_target_entity(self, cmds: List[Dict[str, Any]], bounds: Any) -> List[Dict[str, Any]]:
        """Add a target entity to the list of commands."""
        loc = deepcopy(self.occluded_entity_loc)
        displacement = random.uniform(.3, 1)
        loc['z'] = loc['z'] + bounds[2] / 2 + displacement if self.direction == 'left' else loc['z'] - bounds[2] / 2 - displacement
        loc['x'] += random.uniform(-0.8, 0.8)

        cmds, self.target_rec = target_cmd(self.o_ids[2], loc, cmds)
        return cmds

    def set_camera_location(self, bounds: Any) -> None:
        """Set the location of the camera based on the entity's location."""
        self.camera_loc['x'] = -self.occluded_entity_loc['x']
        self.camera_loc['y'] = random.uniform(bounds[1][1] / 2, bounds[1][1])

    def apply_force_to_entity(self, occluded_entity_id: str) -> List[Dict[str, Any]]:
        """Apply force to the entity."""
        if self.trial_type == 'psychological':
            magnitude = random.uniform(80, 100)
        else:
            record_moving = get_entity_by_name(self.all_names[0])
            magnitude = scale_force(record_moving)

        return [{"$type": "object_look_at_position",
                 "position": {"x": self.occluded_entity_loc['x'],
                              "y": 0,
                              "z": 0},
                 "id": occluded_entity_id},
                {"$type": "apply_force_magnitude_to_object",
                 "magnitude": magnitude,
                 "id": occluded_entity_id}]

    def init_trial_cmds(self) -> List[Dict[str, Any]]:
        """Initialize commands for the trial."""
        self.set_direction()
        self.set_entity_and_occluder_location()
        cmds, bounds = self.set_occluder()

        if self.trial_type == 'psychological':
            cmds = self.spawn_target_entity(cmds, bounds[0])
            self.names['target'] = self.target_rec.name

        self.set_camera_location(bounds)
        self.camera.teleport(position=self.camera_loc)
        self.camera.rotate({"x": 0, "y": 0, "z": self.occluder_z_loc})

        moving_o_id = self.o_ids[2] if self.trial_type == 'psychological' else self.o_ids[0]
        force_cmds = self.apply_force_to_entity(moving_o_id)
        cmds.extend(force_cmds)
        cmds.extend(self.get_additional_commands())

        return cmds

    def set_direction(self) -> None:
        """Set the direction of the trial."""
        self.direction = random.choice(['left', 'right'])

    def set_entity_and_occluder_location(self) -> None:
        """Set the locations of the entity and occluder."""
        z = random.uniform(-5, -4) if self.direction == 'left' else random.uniform(5, 4)
        self.occluded_entity_loc = {"x": random.uniform(-2.5, -1), "y": 0, "z": z}
        self.occluder_z_loc = random.uniform(-.5, .5)

    def get_additional_commands(self) -> List[Dict[str, Any]]:
        """Get the common additional commands for the trial."""
        return [{"$type": "send_transforms", "frequency": "always"},
                {"$type": "send_rigidbodies", "frequency": "always"},
                {"$type": "send_static_rigidbodies", "frequency": "once"}]


if __name__ == "__main__":
    c = OcclusionSimulator()

    args = build_arg_pars()
    if '_mask' not in args.pass_masks:
        args.pass_masks.append('_masks')
        print(console_msg('_mask is added to pass_masks', 'warning'))
    print(console_msg('add_object_to_scene is set to False and tot_frames to 200', 'warning'))
    success = c.run(num=args.num, pass_masks=args.pass_masks, room=args.room, tot_frames=200,
                    add_object_to_scene=False, trial_type=args.trial_type,
                    png=args.png, save_frames=args.save_frames, save_mp4=args.save_mp4)
    print(success)