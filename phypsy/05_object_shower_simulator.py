from typing import Union, Optional, Any

from simulation_handler import SimulationHandler
from tdw.add_ons.third_person_camera import ThirdPersonCamera
from random import uniform, choice
from utils import *


class ObjectShowerSimulator(SimulationHandler):
    def __init__(self, port: int = 1071):
        """
        Initialize the ObjectShowerSimulator with a set of predefined entity types.
        """
        self.ctrl_id: str = 'shower'
        lib = ModelLibrarian('models_core.json')
        self.recs: Dict[str, Any] = {record.name: record for record in lib.records}

        self.entities: List[str] = list(dict.fromkeys(CONTAINER_ENTITIES + CONTAINED_ENTITIES + OCCLUDER_ENTITIES +
                                                      TRANSPARENT_OCCLUDER_ENTITIES + OCCLUDED_ENTITIES + ROLLING_ENTITIES))

        self.camera_loc: Dict[str, float] = {"x": uniform(1.0, 2), "y": uniform(1.0, 2), "z": uniform(-0.5, 1)}
        super().__init__(port=port)

    def apply_force(self, cmds: Optional[List[Dict[str, Union[str, int, float, Dict[str, float]]]]] = None) -> List[Dict[str, Union[str, int, float, Dict[str, float]]]]:
        """
        Apply force or force at a position to an entity.
        """
        cmds = cmds or []

        force: float = scale_force(get_entity_by_name(self.entities[0]))

        if self._random_boolean():
            self._apply_direct_force(cmds, force)
        else:
            self._apply_positional_force(cmds, force)

        return cmds

    def _random_boolean(self) -> bool:
        """
        Returns a random boolean value.
        """
        return choice([True, False])

    def _apply_direct_force(self, cmds: List[Dict[str, Union[str, int, float, Dict[str, float]]]], force: float) -> None:
        """
          Applies a direct force to the object.
        """
        cmds.extend([
            {
                "$type": "object_look_at_position",
                "position": self._random_position(y_fixed=True),
                "id": self.o_ids[0]
            },
            {
                "$type": "apply_force_magnitude_to_object",
                "magnitude": force,
                "id": self.o_ids[0]
            }
        ])

    def _apply_positional_force(self, cmds: List[Dict[str, Union[str, int, float, Dict[str, float]]]], force: float) -> None:
        """
        Applies a force at a random position to the object.
        """
        cmds.append({
            "$type": "apply_force_at_position",
            "id": self.o_ids[0],
            "force": {
                "x": force if self._random_boolean() else 0,
                "y": force if self._random_boolean() else 0,
                "z": force if self._random_boolean() else 0
            },
            "position": self._random_position()
        })

    def _random_position(self, y_fixed: bool = False) -> Dict[str, float]:
        """
        Returns a random position. If y_fixed is set, y is fixed at 0.
        """
        position: Dict[str, float] = {
            "x": uniform(-10, 10),
            "y": 0 if y_fixed else uniform(0, 10),
            "z": uniform(-10, 10)
        }
        return position

    def set_camera(self) -> Tuple[Dict[str, float], Dict[str, int]]:
        """
        Set the camera to a third person view.
        """
        camera_look_at: Dict[str, int] = {"x": 0, "y": 0, "z": 0}
        self.camera = ThirdPersonCamera(position=self.camera_loc, look_at=camera_look_at, avatar_id='frames_temp')
        self.add_ons.append(self.camera)
        return self.camera_loc, camera_look_at

    def init_trial_cmds(self) -> List[Dict[str, Union[str, int, float, Dict[str, float]]]]:
        """
        Initialize trial commands based on a randomized scenario type.
        """
        scenario_type: List[str] = choice([['fall'], ['force'], ['fall', 'force']])
        self.o_ids = [self.get_unique_id()]
        cmds: List[Dict[str, Union[str, int, float, Dict[str, float]]]] = []

        loc: Dict[str, float] = {"x": 0, "z": 0, "y": uniform(0, 4) if 'fall' in scenario_type else 0}
        rot: Dict[str, float] = {
            axis: uniform(0, 360) if choice([True, False]) and 'fall' in scenario_type else 0
            for axis in ["x", "y", "z"]
        }

        cmds.extend(self.get_add_physics_object(model_name=self.entities[0],
                                                library='models_core.json',
                                                object_id=self.o_ids[0],
                                                position=loc,
                                                rotation=rot))
        self.names = {'object': self.entities.pop(0)}

        if 'force' in scenario_type:
            cmds = self.apply_force(cmds)

        return cmds


if __name__ == "__main__":
    c = ObjectShowerSimulator()
    args = build_arg_pars()
    print(console_msg('The trial_type param is ignored', 'warning'))
    success = c.run(num=args.num, pass_masks=args.pass_masks, room=args.room, tot_frames=args.tot_frames,
                    add_object_to_scene=args.add_object_to_scene,
                    png=args.png, save_frames=args.save_frames, save_mp4=args.save_mp4)
    print(success)

