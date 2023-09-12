from typing import Union

from tdw.add_ons.third_person_camera import ThirdPersonCamera
from simulation_handler import SimulationHandler
from utils import *


class RollingSimulator(SimulationHandler):
    def __init__(self):
        """
        Initialize the RollingSimulator with default settings.
        """
        super().__init__(port=1071)
        self.ctrl_id = 'rolling'
        self.entities = ["orange", "golf", "apple"]
        self.entities.extend(ROLLING_ENTITIES)

    def apply_transitional_force(self, response: Dict, rolling_entity_id: int, barrier_id: int) -> Tuple[List[Dict], bool]:
        """
        Apply a transitional force to a rolling entity when certain conditions are met.
        """
        if calculate_dist(response, rolling_entity_id, barrier_id) < .225 and not self.transition_started:
            return [{"$type": "add_constant_force",
                     "id": self.o_ids[0],
                     "force": {"x": -self.scaled_force, "y": 0, "z": 0},
                     "relative_force": {"x": 0, "y": 0, "z": 0},
                     "torque": {"x": 0, "y": 0, "z": 0},
                     "relative_torque": {"x": 0, "y": 0, "z": 0}}], True
        return [], False

    def apply_psychological_interaction(self, response: Dict) -> List[Dict]:
        """
        Apply psychological interactions based on the current state of the simulation.
        """
        commands = [{"$type": "object_look_at",
                     "other_object_id": self.o_ids[1],
                     "id": self.o_ids[0]},
                    {"$type": "teleport_object_by",
                     "position": {"x": 0, "y": 0, "z": self.velocity},
                     "id": self.o_ids[0], "absolute": False}]

        if not self.initial_response or (
                calculate_dist(response, self.o_ids[0], self.o_ids[1]) >= .1 and not self.agent_success):
            return commands
        return []

    def destroy_entities(self) -> None:
        """
        Destroy the entities and reset communication.
        """
        destroy_cmds = [{"$type": "destroy_object", "id": entity_id} for entity_id in self.o_ids]
        destroy_cmds.append({"$type": "send_rigidbodies", "frequency": "never"})
        self.communicate(destroy_cmds)

    def run_frame_by_frame(self, trial_type: str, tot_frames: int) -> Tuple[Union[List[int], int], bool]:
        """
        Run the simulation frame by frame and handle actions based on trial type.
        """
        self.transition_started = False
        self.scaled_force = scale_force(get_entity_by_name(self.entity_selection))
        self.velocity = .05
        self.initial_response = False
        self.agent_success = False
        rolling_entity_id, barrier_id = self.o_ids[0], self.scene_o_ids[1]

        trial_success = True
        transitions = [] if trial_type != 'physical' else None

        for i in range(tot_frames):
            try:
                if i >= 1 and trial_type == 'transitional':
                    commands, started = self.apply_transitional_force(response, rolling_entity_id, barrier_id)
                    self.transition_started = started
                    if started: transitions.append(i)
                elif trial_type == 'psychological':
                    commands = self.apply_psychological_interaction(response)
                    if commands: transitions.append(i)
                else:
                    commands = []
                response = self.communicate(commands)
            except TypeError:
                response = self.communicate([])
                trial_success = False
                break

        self.destroy_entities()
        return transitions if transitions else -1, trial_success

    def _get_random(self, start: float, end: float) -> float:
        """
        Generate a random float value between start and end.
        """
        return random.uniform(start, end)

    def _add_physics_object(self, model_name: str, library: str, object_id: int, position: Dict, rotation: Dict,
                            scale_factor: Dict = None, dynamic_friction: float = None, static_friction: float = None,
                            bounciness: float = None) -> List[Dict]:
        """
        Add a physics object with specific properties to the simulator.
        """
        cmd = self.get_add_physics_object(
            model_name=model_name,
            library=library,
            object_id=object_id,
            position=position,
            rotation=rotation,
            scale_factor=scale_factor or {},
            dynamic_friction=dynamic_friction,
            static_friction=static_friction
        )
        if bounciness:
            cmd.append({"$type": "set_physic_material", "bounciness": bounciness, "id": object_id})
        return cmd

    def spawn_target_entity(self, cmds: List[Dict[str, Union[str, float, Dict]]]) -> List[Dict[str, Union[str, float, Dict]]]:
        """
        Spawns a target entity in the simulation.
        """
        target_entity_id = self.o_ids[1]
        self.entity_loc.update({'y': self._get_random(1.3, 1.6), 'x': self._get_random(-.425, -.375)})
        cmds, self.target_rec = target_cmd(target_entity_id, self.entity_loc, cmds)
        return cmds

    def spawn_entity(self, cmds: List[Dict[str, Union[str, float, Dict]]] = None) -> List[Dict[str, Union[str, float, Dict]]]:
        """
        Spawns entities in the simulation.
        """
        cmds = cmds or []
        ids = [self.get_unique_id(), self.get_unique_id()]
        self.scene_o_ids = ids
        ramp_id, barrier_id = ids

        # Set rotation based on trial type
        rot_z = self._get_random(212, 232) if self.trial_type != 'psychological' else 244

        # Add a cube for the ramp
        cmds.extend(self._add_physics_object("cube", "models_flex.json", ramp_id,
                                             position={"x": -.45, "y": 0, "z": 0},
                                             rotation={"x": 0, "y": 0, "z": rot_z},
                                             scale_factor={"x": .89, "y": .89, "z": .89}))

        # Add a cube for the barrier if trial type is not psychological
        if self.trial_type != 'psychological':
            cmds.extend(self._add_physics_object("cube", "models_flex.json", barrier_id,
                                                 position={"x": .5, "y": 0, "z": 0},
                                                 rotation={"x": 0, "y": 180, "z": 0},
                                                 scale_factor={"x": .1, "y": .25, "z": .9},
                                                 bounciness=1))
        else:
            ids = [ramp_id]

        # Set color for entities
        clr = {"r": random.random(), "g": random.random(), "b": random.random(), "a": 0.5}
        for entity_id in ids:
            cmds.append({"$type": "set_color", "color": clr, "id": entity_id})
            # Adjust color transparency for next iteration if trial type is not psychological
            if self.trial_type != 'psychological':
                clr = {"r": random.random(), "g": random.random(), "b": random.random(), "a": 1.0}
            # Freeze object in place
            cmds.extend([{
                "$type": "set_rigidbody_constraints",
                "id": entity_id,
                "freeze_position_axes": {"x": 1, "y": 1, "z": 1},
                "freeze_rotation_axes": {"x": 1, "y": 1, "z": 1}
            }])
        return cmds

    def set_camera(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Sets the camera's position and look-at coordinates.
        """
        z = -2 if self.trial_type == 'psychological' else -1
        loc = {"x": 0, "y": 1.2, "z": z}
        look_at = {"x": 0, "y": 0, "z": 0}
        camera = ThirdPersonCamera(position=loc, look_at=look_at, avatar_id='frames_temp')
        self.add_ons.append(camera)
        return loc, look_at

    def init_trial_cmds(self) -> List[Dict[str, Union[str, float, Dict]]]:
        """
        Initializes commands for a new trial.
        """
        entity_id = self.get_unique_id()
        self.o_ids = [entity_id, self.get_unique_id()] if self.trial_type == 'psychological' else [entity_id]
        cmds = []
        self.entity_selection = random.choice(self.entities)
        self.names = {'object': self.entity_selection}
        rot_x = random.choice([80, -80]) if self.entity_selection in ROLLING_ENTITIES else 0

        # Define initial entity location
        self.entity_loc = {
            "x": self._get_random(-.14, -.11),
            "y": self._get_random(3.8, 4.5),
            "z": self._get_random(-.14, .14)
        }

        # For psychological trials, spawn a target entity and adjust the location
        if self.trial_type == 'psychological':
            cmds = self.spawn_target_entity(cmds)
            self.names['target'] = self.target_rec.name
            self.entity_loc = {
                "x": self._get_random(2.5, 3),
                "y": self._get_random(0, .5),
                "z": self._get_random(-.15, .15)
            }

        # Add a physics object with the chosen entity
        cmds.extend(self._add_physics_object(self.entity_selection, 'models_core.json', entity_id,
                                             position=self.entity_loc, rotation={"x": rot_x, "y": 0, "z": 0}))

        # Commands to continuously send updates about the objects and environment
        cmds.extend([{
            "$type": "send_transforms",
            "frequency": "always"
        }, {
            "$type": "send_rigidbodies",
            "frequency": "always"
        }, {
            "$type": "send_static_rigidbodies",
            "frequency": "once"
        }])
        return cmds


if __name__ == "__main__":
    c = RollingSimulator()

    args = build_arg_pars()
    print(console_msg('add_object_to_scene is set to True', 'warning'))
    success = c.run(num=args.num, pass_masks=args.pass_masks, room=args.room, tot_frames=args.tot_frames,
                    add_object_to_scene=True, trial_type=args.trial_type,
                    png=args.png, save_frames=args.save_frames, save_mp4=args.save_mp4)
    print(success)