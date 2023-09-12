import argparse
import random
import numpy as np
import os
import shutil
import ffmpeg
from typing import List, Dict, Tuple
from entities import *
from tdw.controller import Controller
from tdw.librarian import ModelLibrarian
from tdw.tdw_utils import TDWUtils
from tdw.output_data import OutputData, Transforms, Rigidbodies, StaticRigidbodies
from scipy.spatial.transform import Rotation


class EntityProperties:
    """
    Class for representing the properties of an entity.
    """

    def __init__(self, id: int, rad: float, loc: Dict[str, float]):
        self.id = id
        self.rad = rad  # max radius determined by entity's bounds
        self.loc = loc


def get_entity_by_name(name: str, lib: str = 'models_full.json') -> ModelLibrarian:
    """
    Retrieve the entity record based on its name from the library.
    """
    return ModelLibrarian(lib).get_record(name)


def get_random_entity_pair(list1: List[str], list2: List[str], axes: List[int] = [0, 1, 2]) -> Tuple[
    List[str], List[List[float]]]:
    """
    Retrieve a random entity pair based on size requirements.
    """
    while True:
        list1_entity = get_entity_by_name(random.choice(list1))
        entity1_bounds = TDWUtils.get_bounds_extents(list1_entity.bounds)

        random.shuffle(list2)
        for name in list2:
            list2_entity = get_entity_by_name(name)
            entity2_bounds = TDWUtils.get_bounds_extents(list2_entity.bounds)

            axis_met = [axis for axis in axes if entity2_bounds[axis] > entity1_bounds[axis]]

            if axis_met == axes:
                return [list1_entity, list2_entity], [entity1_bounds, entity2_bounds]


def calculate_dist(response: List, entity1_id: int, entity2_id: int) -> float:
    """
    Calculate distance between two entities.
    """
    if not response:
        print('no response')
        return np.inf
    loc1 = dict(zip(['x', 'y', 'z'], get_mass_loc_rot(response, entity1_id)[1]))
    loc2 = dict(zip(['x', 'y', 'z'], get_mass_loc_rot(response, entity2_id)[1]))
    return TDWUtils.get_distance(loc1, loc2)


def get_random_entity_pos(min_rad: float, max_rad: float, min_y: float, max_y: float,
                          center: Dict[str, float], min_angle: float = 0,
                          max_angle: float = 360) -> Dict[str, float]:
    """
    Generate a random position for an entity.
    """
    rad = random.uniform(min_rad, max_rad)
    phi = np.radians(random.uniform(min_angle, max_angle))

    x = center["x"] + rad * np.cos(phi)
    y = random.uniform(min_y, max_y)
    z = center["z"] + rad * np.sin(phi)

    return {"x": x, "y": y, "z": z}


def get_mass_loc_rot(response: List, entity_id: int) -> Tuple[np.array, List[float], float]:
    """
    Retrieve mass, location, and rotation for an entity.
    """
    rot, loc, mass = None, None, None
    for i in range(len(response) - 1):
        res_id = OutputData.get_data_type_id(response[i])
        if res_id == "tran":
            transforms = Transforms(response[i])
            for j in range(transforms.get_num()):
                if transforms.get_id(j) == entity_id:
                    loc = transforms.get_position(j)
                    rot = Rotation.from_quat(transforms.get_rotation(j)).as_euler('xyz')
                    rot = np.degrees(rot)
        elif res_id == "srig":
            srigid_entities = StaticRigidbodies(response[i])
            for j in range(srigid_entities.get_num()):
                mass = srigid_entities.get_mass(j)

    return rot, loc, mass


def generate_mp4(img_path: str, mp4_name: str, framerate: int, masks: List[str], png: bool, keep_imgs: bool,
                 save_video: bool) -> Tuple[List[str], str]:
    """
    Generate mp4 videos from images and manage storage.
    """
    videos_path = []

    if save_video:
        for mask_type in masks:
            img_names = f'{img_path}/{mask_type.replace("_", "", 1)}_*'
            file_ex = '.jpg' if not png and mask_type == '_img' else '.png'
            img_names += file_ex

            (
                ffmpeg
                .input(img_names, pattern_type='glob', framerate=framerate)
                .filter('select', 'gte(n, 1)')
                .output(mp4_name + f'{mask_type}.mp4', loglevel="quiet")
                .run()
            )

            videos_path.append(mp4_name + f'{mask_type}.mp4')

    if keep_imgs:
        path_frames = f'{mp4_name}/'.replace('videos', 'frames')
        os.makedirs(path_frames, exist_ok=True)
        shutil.move(f'{img_path}/', path_frames)
        os.makedirs(f'{img_path}/', exist_ok=True)
    else:
        path_frames = None

    return videos_path, path_frames


def console_msg(msg: str, msg_type: str, indicator: int = None) -> str:
    """
    Generates a colored console message with an optional indicator bar.
    """

    prefix = {
        "success": "✅ success: ",
        "warning": "⚠️warning: ",
        "error": "❌ error: ",
    }.get(msg_type, "")

    color_code = {
        "error": "\033[91m",  # Red
        "warning": "\033[93m",  # Yellow
        "success": "\033[92m"  # Green
    }.get(msg_type, "")

    full_message = f"{prefix}{msg}"

    if indicator is not None:
        indicator_bar = f"[{'#' * indicator}{'-' * (10 - indicator)}] {indicator * 10}%"
        return f"{color_code}{full_message}\033[0m {indicator_bar}\r"

    return f"{color_code}{full_message}\033[0m\r"


def scale_force(entity, noise: float = 5) -> float:
    """
        Calculate a scaling force based on entity properties.
    """

    scale = (-TDWUtils.get_unit_scale(entity) * 1.9 + 48) / 1.8 + \
            (np.prod(TDWUtils.get_bounds_extents(entity.bounds)) * 12 + 13) / 2.1 - 3.8
    return scale + random.uniform(-noise, noise)


def is_sleeping(response, entity_id: int) -> bool:
    """
    Check if a given entity is sleeping based on the response data.
    """

    for data in response[:-1]:
        if OutputData.get_data_type_id(data) == "rigi":
            rigid_entities = Rigidbodies(data)
            for j in range(rigid_entities.get_num()):
                if rigid_entities.get_id(j) == entity_id:
                    return rigid_entities.is_sleeping(j)
    return False


def target_cmd(target_entity_id, agent_pos, cmds=[]):
    """
    Generate commands to target a random entity.
    """
    target = random.choice(TARGET_ENTITIES)
    scale, lib = (1, 'models_core.json') if target != 'sphere' else (0.2, 'models_flex.json')

    cmds.extend(Controller.get_add_physics_object(model_name=target,
                                                  library=lib,
                                                  object_id=target_entity_id,
                                                  position=agent_pos,
                                                  scale_factor={"x": scale, "y": scale, "z": scale},
                                                  default_physics_values=False,
                                                  mass=1,
                                                  scale_mass=False))
    return cmds, get_entity_by_name(target, lib=lib)


def build_arg_pars(masks: bool = True) -> argparse.Namespace:
    """
    Build and parse command line arguments.
    """

    parser = argparse.ArgumentParser(description="Specify the parameters for trial creation.")

    arguments = [
        {"flags": ["-n", "--num"], "type": int, "default": 1, "help": "Total trials count"},
        {"flags": ["-t", "--trial_type"], "type": str, "default": "physical",
         "choices": ["psychological", "transitional", "physical"],
         "help": "Type of trial (psychological, transitional, or physical)"},
        {"flags": ["--png"], "default": True, "type": bool, "help": "Use png or jpg?"},
        {"flags": ["--save_frames"], "default": True, "type": bool, "help": "Keep the frame images"},
        {"flags": ["--save_mp4"], "default": False, "type": bool, "help": "Save in mp4 format"},
        {"flags": ["--pass_masks"], "type": str, "default": "_img,_mask", "help": "Output masks"},
        {"flags": ["--framerate"], "type": int, "default": 30, "help": "FPS of output sequence"},
        {"flags": ["--room"], "default": "empty", "help": "Environment type; 'random_unsafe' for random untested room"},
        {"flags": ["--tot_frames"], "type": int, "default": 200,
         "help": "Max frames; may terminate earlier occasionally"},
        {"flags": ["--add_object_to_scene"], "default": False, "type": bool,
         "help": "Introduce items to scene & backdrop"}
    ]

    for arg in arguments:
        flags = arg.pop("flags")
        parser.add_argument(*flags, **arg)

    args = parser.parse_args()

    if '_img' not in args.pass_masks:
        print(console_msg('pass_masks must contain _img, adding it...', 'warning'))
        args.pass_masks += ',_img'
    if masks:
        args.pass_masks = args.pass_masks.split(",")

    return args
