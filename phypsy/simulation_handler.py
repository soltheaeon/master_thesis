from tdw.add_ons.third_person_camera import ThirdPersonCamera
from tdw.add_ons.image_capture import ImageCapture
from tdw.librarian import SceneLibrarian
from utils import *
from typing import List, Tuple, Optional, Union
import time
from tdw.librarian import ModelLibrarian
import pandas as pd


class SimulationHandler(Controller):
    """SimulationHandler is responsible for managing a simulation, including setting up
    the trial, running the simulation, and setting the camera.
    """
    def __init__(self, port=1071):
        lib = ModelLibrarian('models_core.json')
        self.recs = lib.records
        super().__init__(port=port)

    def init_trial_cmds(self) -> List[dict]:
        """Initialize the commands for the trial."""
        return []

    def run_frame_by_frame(self, trial_type: str, tot_frames: int) -> Tuple[Optional[str], bool]:
        """Execute the simulation frame by frame."""
        self._communicate_for_n_frames(tot_frames)

        destroy_cmds = self._get_destroy_cmds()
        destroy_cmds.append({"$type": "send_rigidbodies", "frequency": "never"})

        self.communicate(destroy_cmds)
        return None, True

    def run_mass_loc_rot(self, entity_id: str, cmds: List[dict]) -> Tuple[List[dict], dict]:
        """Execute the commands and retrieve transforms."""
        response = self.communicate(cmds)
        transforms = get_mass_loc_rot(response, entity_id)

        self._reset_frames_directory()

        return [], transforms

    def spawn_entity(self, cmds: Optional[List[dict]] = None) -> List[dict]:
        """Add object to the scene."""
        return cmds if cmds else []

    def set_camera(self) -> None:
        """Set the camera for the simulation."""
        self.camera = ThirdPersonCamera(position=self.camera_pos,
                                        look_at={"x": 0, "y": 0, "z": 0},
                                        avatar_id='frames_temp')
        self.add_ons.append(self.camera)

    def _communicate_for_n_frames(self, n: int) -> None:
        """Send communication command for n frames."""
        for _ in range(n):
            self.communicate([])

    def _get_destroy_cmds(self) -> List[dict]:
        """Generate destroy commands for all entities."""
        return [{"$type": "destroy_object", "id": entity_id} for entity_id in self.o_ids]

    def _reset_frames_directory(self) -> None:
        """Reset the frames directory."""
        path_frames = f'{self.path}/frames_temp'
        shutil.rmtree(path_frames)
        os.makedirs(path_frames, exist_ok=True)

    def validate_inputs(self, pass_masks: List[str], trial_type: str, tot_frames: int, add_object_to_scene: Union[bool, int]) -> Union[str, None]:
        """Validate the input arguments."""

        # Validate pass_masks
        available_masks = ['_img', '_id', '_albedo', '_category', '_flow', '_mask']
        if not isinstance(pass_masks, list):
            return console_msg("pass_masks is not a list", 'error')
        for mask in pass_masks:
            if mask not in available_masks:
                return console_msg(f'{mask} not in {available_masks}', 'error')
        if len(set(pass_masks)) != len(pass_masks):
            return console_msg('pass_masks cannot contain duplicates', 'error')

        # Validate trial_type
        if trial_type not in ['transitional', 'psychological', 'physical']:
            return console_msg("trial_type is not one of 'transitional', 'psychological' or 'physical'", 'error')
        if tot_frames < 100 and trial_type == 'transitional':
            return console_msg('Transitional trials require at least 100 frames', 'error')

        # Validate add_object_to_scene
        if not isinstance(add_object_to_scene, bool):
            return console_msg('add_object_to_scene is not boolean', 'error')
        if not add_object_to_scene and self.ctrl_id == 'rolling':
            return console_msg('Rolling trials require a slope, must set add_object_to_scene to True', 'error')

        return None

    def initialize_directories(self) -> Tuple[str, str, str]:
        """Setup directories for storing data."""
        curr_dir = os.getcwd()
        if curr_dir.endswith("controllers"):
            self.path = '../data/batch'
        else:
            self.path = 'data/batch'

        path = self.path
        paths = [f'{path}/{name}/{self.ctrl_id}/{self.trial_type}' for name in ['backgrounds', 'videos']]
        backgrounds_path, videos_path = paths
        frames_path = f'{path}/frames_temp'
        self.frames_path = frames_path
        paths.append(frames_path)

        # Remove and recreate directories
        for p in paths:
            try:
                shutil.rmtree(p)
            except FileNotFoundError:
                pass
            os.makedirs(p, exist_ok=True)

        return backgrounds_path, videos_path, frames_path

    def get_scene_commands(self, room: str) -> List[dict]:
        """Get commands to set up the room or scene."""
        lib = SceneLibrarian(library="scenes.json")
        available_scenes = [record.name for record in lib.records]
        if room == 'empty':
            return [TDWUtils.create_empty_room(12, 12)]
        elif room in available_scenes or room == 'random':
            selected_scene = random.choice(available_scenes) if room == 'random' else room
            print('Name of selected environment:', selected_scene)
            return [self.get_add_scene(scene_name=selected_scene)]
        else:
            console_msg(f"Scene should be one of the following: \n {available_scenes}", 'error')
            return []


    def run(self, num=5, trial_type='object', png=False, pass_masks=["_img", "_mask"], framerate=30, room='random',
            tot_frames=200, add_object_to_scene=False, save_frames=True, save_mp4=False):

        validation_message = self.validate_inputs(pass_masks, trial_type, tot_frames, add_object_to_scene)
        if validation_message:
            return validation_message

        self.trial_type = trial_type
        self.framerate = framerate
        self.add_ons.clear()

        camera_loc, camera_look_at = self.set_camera()

        backgrounds_path, videos_path, frames_path = self.initialize_directories()
        ctrl_id = self.ctrl_id

        curr_dir = os.getcwd()
        if curr_dir.endswith("controllers"):
            self.path = '../data/batch'
        else:
            self.path = 'data/batch'

        path = self.path
        paths= [f'{path}/{name}/{ctrl_id}/{trial_type}' for name in ['backgrounds', 'videos']]
        backgrounds_path, videos_path = paths
        frames_path = f'{path}/frames_temp'
        self.frames_path = frames_path
        paths.append(frames_path)

        try:
            shutil.rmtree(frames_path)
        except FileNotFoundError:
            pass

        for path in paths:
            os.makedirs(path, exist_ok=True)

        trial_id = random.randint(10 ** 16, 10 ** 17 - 1)
        print(f'Trial id: {trial_id}')

        self.add_ons.append(
            ImageCapture(path=path + '/', avatar_ids=['frames_temp'], png=png, pass_masks=pass_masks))

        lib = SceneLibrarian(library="scenes.json")
        available_scenes = [record.name for record in lib.records]
        if room == 'empty':
            cmds = [TDWUtils.create_empty_room(12, 12)]
        elif room in available_scenes or room == 'random':
            selected_scene = random.choice(available_scenes) if room == 'random' else room
            print('Name of selected environment:', selected_scene)
            cmds = [self.get_add_scene(scene_name=selected_scene)]
        else:
            return console_msg(
                f"Scene should be one of the following: \n {available_scenes}",
                'error')

        cmds.append({"$type": "set_target_framerate",
                         "framerate": framerate})

        if type(add_object_to_scene) == bool:
            if add_object_to_scene:
                cmds = self.spawn_entity(cmds)
            if not add_object_to_scene and self.ctrl_id == 'rolling':
                return console_msg('Rolling trials require a slope, must set add_object_to_scene to 1', 'error')

        else:
            return console_msg('add_object_to_scene is not boolean', 'error')

        self.communicate(cmds)
        extension = '.png' if png else '.jpg'
        moved = False
        while not moved:
            try:
                shutil.move(f'{frames_path}/img_0000{extension}',
                            f'{backgrounds_path}/background_{ctrl_id}{trial_id}{extension}')
                moved = True
            except FileNotFoundError:
                print(console_msg("Taking longer than expected...", 'warning'))
                time.sleep(5)

                self.communicate([])

        shutil.rmtree(frames_path)
        os.makedirs(frames_path)

        try:
            log = pd.read_csv(f'{path}/log.csv', index_col=False)
        except FileNotFoundError:
            log = pd.DataFrame(index=None, columns=(
                'id', 'batch', 'videos_path', 'frames_path', 'trial_type', 'objects',
                'png', 'pass_masks', 'framerate', 'room', 'tot_frames', 'add_object_to_scene',
                'save_frames', 'save_mp4', 'transition_frame', 'camera_loc', 'camera_look_at'))

        print(f"Videos will be saved in {videos_path}/{trial_type}/{trial_id}")
        n_trial = 0
        while n_trial != num:
            trial_cmds = self.init_trial_cmds()
            if type(trial_cmds) != list:
                return trial_cmds

            self.communicate(trial_cmds)

            try:
                shutil.rmtree(frames_path)
            except FileNotFoundError:
                pass
            os.makedirs(frames_path, exist_ok=True)

            transition_frame, success = self.run_frame_by_frame(trial_type=trial_type, tot_frames=tot_frames)

            if success:
                output = f"{videos_path}/{trial_id}_trial_{n_trial}"

                path_videos_saved, path_frames_saved = generate_mp4(frames_path, output, framerate, pass_masks,
                                                                    png, save_frames, save_mp4)

                columns = (
                    trial_id, n_trial, path_videos_saved, path_frames_saved, trial_type, self.names, png,
                    pass_masks, framerate, room, tot_frames, add_object_to_scene, save_frames, save_mp4,
                    transition_frame, camera_loc, camera_look_at)
                try:
                    log = log.drop(columns='Unnamed: 0')
                except KeyError:
                    pass
                log.loc[len(log)] = columns
                log.to_csv(f'{path}/info.csv')

                n_trial += 1
            else:
                print(console_msg(f'Trial {n_trial} failed. Retrying...', 'error'))

        self.communicate({"$type": "terminate"})

        shutil.rmtree(frames_path)

        return console_msg(
            f'Finished generation.',
            'success')


if __name__ == "__main__":
    c = SimulationHandler()
    c.ctrl_id = 'default'
    success = c.run(num=10, pass_masks=['_img'])
    print(success)
