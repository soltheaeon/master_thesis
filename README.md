# Master's Thesis Repository: PhyPsy Benchmark Dataset Creation

This repository contains the implementation and results for my (Marcel De Sutter's) Master's thesis which revolves around the creation of the "PhyPsy" benchmark dataset. PhyPsy focuses on prototypical scenarios for evaluating cognitive models, specifically within the realms of physical and psychological reasoning.

## Repository Structure
The repository is split into two main components:
1. `Loci-main` - This is a clone from the [Loci repository](https://github.com/CognitiveModeling/Loci). I originally planned to evaluate Loci on PhyPsy but this proved to be not feasible because the development of PhyPsy turned out much more involved as initially anticipated.
2. `phypsy` - This contains my primary contributions.

### PhyPsy Dataset Creation Pipeline

PhyPsy offers a unique benchmark dataset, covering four prototypical scenarios:
- Collision
- Occlusion
- Containment
- Rolling

Each scenario is explored with three different levels of agency:
- Physical trials (objects with no agency)
- Psychological trials (involving agents)
- Transitional trials (objects suddenly showing agency)

#### Files and Folders

- `01_collision_simulator.py` to `05_object_shower_controller.py`: These are TDW (ThreeDWorld) controllers that generate the simulation trials for each scenario. Notably, `05_object_shower_controller.py` serves as the "object shower", which generates trials with random parameterization of objects.
  
- `create_dataset.py`: An orchestrator script that leverages SimulationHandlers from `simulation_handler.py` to batch-produce trials.

- `entities.py`: Contains definitions and configurations for the objects and agents used in the trials.

- `simulation_handler.py`: Handles the execution and management of simulation controllers.

- `utils.py`: Houses utility functions and helpers for streamlining various tasks.

#### Generated Trials and Outputs

1. **A_example_trials**: Contains single example trials (both raw images and MP4) for all possible configurations. Due to storage constraints, only one example is provided for each configuration.
  
2. **B_object_shower_trials**: Features 6 example trials, specifically focusing on the "object shower" simulations.
   
3. **C_detailed_output_psychological**: An exhaustive collection of outputs for psychological trials across all scenarios. Each trial output includes frame data, videos, extracted background files, and an `log.csv` that summarizes the parameterizations of the generated trials. For scenarios like containment and rolling, supplementary objects (e.g., slopes) are also included as part of the background.

## Quick Start

   ```bash
   pip install -r requirements.txt
   cd phypsy
   python create_dataset.py
   ```

Kindly refer to `python create_dataset.py --help` to learn more about setting a parameterization for the trial generation.


## Detailed Description of the individual Simulators

#### simulation_handler.py

    Class Definition: SimulationHandler:
        - Inherits from Controller.
        - Main responsibility: Manage a simulation.

    Run Method:
        - Accepts various parameters for the trial setup, such as number of trials, trial type, frame rate, and others.
        - Executes the following steps:
            - Validates the inputs.
            - Initializes directories for storing data.
            - Generates a unique trial ID.
            - Sets up image capture and scene based on provided parameters.
            - Moves initial images to backgrounds path.
            - Initializes or reads from a logging file (log.csv).
            - Runs the simulation for each trial up to the specified number (num):
                - Initializes trial commands.
                - Runs the simulation frame by frame.
                - If the trial is successful, it generates a video (mp4) and logs relevant information.
                - If unsuccessful, it retries the current trial.
            - Terminates the simulation.
            - Deletes the frames directory.
            - Returns a success message.

    Utility Functions:
        - The class contains several utility functions to support the main run method.
            - validate_inputs: Checks the validity of provided parameters.
            - initialize_directories: Sets up directories for storing data.
            - get_scene_commands: Returns commands to set up the room or scene.
            - ... and several other helper functions.

    Main Execution:
        - If the file is run as a standalone script, it initializes a SimulationHandler instance.
        - Sets the control ID to 'default'.
        - Executes the run method for 10 trials with specific parameters.
        - Prints the result of the run.

#### create_dataset.py

    Purpose:
        - The script is designed to generate multiple simulation scenarios based on user-defined configurations. Each scenario runs a set number of simulations (batches) across various trial types.

    Argument Parsing:
        - Parses command-line arguments using the build_arg_pars function from utils.
        - Provides a warning to the user that the trial_type parameter will be ignored since all scenarios will be generated.

    User Input:
        - Prompts the user for the number of batches (simulation runs) they wish to create.
        - Validates the input to ensure it's an integer. If not, it provides an error and prompts the user again.

    Simulation Execution:
        - Iterates over each specified batch:
            - For each simulator type (collision, occlusion, containment, and rolling):
                - For each trial type (physical, transitional, psychological):
                    - Constructs a system command string based on:
                        - The simulator type (e.g., 01_collision_simulator.py).
                        - Various parsed arguments and the current trial type.
                    - Displays the constructed command.
                    - Executes the command using the system function from the os module, which runs the command in a subshell.

#### 01_collision_simulator.py

    - Initialization (__init__ method):
        - Inherits from SimulationHandler.
        - Sets up initial configurations, entities, and metadata for the simulator.

    - console_msg (standalone function):
        - Formats console messages with different colors based on the message type.

    - run:
        - Executes a set number of simulation trials.
        - For each trial: Initializes the environment, runs it, cleans up, and checks for results.

    - _initialize_environment:
        - Sets up the simulation scene with lighting, objects, and other essential entities.

    - _cleanup_after_run:
        - Performs cleanup operations after each simulation trial, destroying created objects.

    - _get_results:
        - Assesses the outcomes of a trial, checking collisions and transitions against the trial type.

    - generate_random_coordinate (static method):
        - Returns a random floating-point number within a given range.

    - set_drop_loc:
        - Creates random drop locations for an entity and its corresponding location on the ground.

    - set_locs:
        - Sets random positions for two main entities: 'patient' and 'collider'.

    - spawn_entity:
        - Constructs commands to spawn entities in the simulation, applying rotation if needed.

    - get_entity_loc:
        - Extracts the position of a specific entity from the simulation's response.

    - spawn_target_entity:
        - Constructs commands to spawn a target entity in relation to another entity's position.

    - set_camera:
        - Configures the camera's position and target in the simulation.

    - init_trial_cmds:
        - Composes a set of commands for initiating a new trial, including object placements, rotations, collision settings, and entity naming.

    - Execution Script (if __name__ == "__main__": block):
        - Initiates an instance of CollisionSimulator.
        - Retrieves and sets the required arguments and executes the simulation run, printing the outcomes.

#### 02_occlusion_simulator.py

    - Initialization (__init__):
        - Inherits from SimulationHandler.
        - Defines ctrl_id.
        - Loads models from models_core.json.
        - Initializes camera location randomly.
        - Invokes parent's initializer.

    - calculate_freeze_point:
        - Calculates where the occlusion should freeze based on occluder and camera locations.

    - run_transitional_trial:
        - Handles logic related to transitional trials.
        - Determines whether to transition objects or communicate with the simulation.

    - run_psychological_trial:
        - Handles logic related to psychological trials.
        - Determines whether to make the object look at another object and teleport it.

    - freeze_rigidbody:
        - Returns commands to freeze or unfreeze an object.

    - teleport_object_by:
        - Returns teleportation command for an object.

    - object_look_at:
        - Returns a command to make an object look at another object.

    - run_frame_by_frame:
        - Runs the trial frame-by-frame based on the trial type.

    - set_occluder:
        - Chooses and initializes occluder objects.

    - set_camera:
        - Defines the camera's position and view direction.

    - get_entity_loc:
        - Fetches the location of an entity given its ID.

    - spawn_target_entity:
        - Adds a target entity to the list of commands.

    - set_camera_location:
        - Sets the location of the camera based on the entity's location.

    - apply_force_to_entity:
        - Applies force to a specific entity.

    - init_trial_cmds:
        - Initializes commands for the trial.

    - set_direction:
        - Randomly determines the direction of the trial.

    - set_entity_and_occluder_location:
        - Sets the locations of the entity and occluder randomly.

    - get_additional_commands:
        - Returns a set of common additional commands for the trial.

    - Main Execution (__main__):
        - Creates an instance of OcclusionSimulator.
        - Builds argument parser.
        - Adds '_mask' to 'pass_masks' if it isn't present.
        - Sets the number of frames to 200 and informs the user.
        - Executes the simulation and prints the result.

#### 03_containment_simulator.py

    - Initialization (__init__):
        - Inherits from SimulationHandler.
        - Initializes with a default port.
        - Randomly sets x and z coordinates for object positioning.
        - Runs a given trial type (transitional, psychological, or physical) frame by frame.
        - Handles different trial types with specific logic:
            - For the transitional trial:
                - Waits for a random duration, then checks if an object's position and rotation are stabilized.
                - If stabilized, checks for transition start and applies forces if necessary.
            - For the psychological trial:
                - Moves an agent closer to a target over time.
                - Tracks the agent's success based on proximity to the target.
            - For the physical trial:
                - Just communicates without specific logic for a certain number of frames.
        - Cleans up at the end of each trial by destroying entities.

    - Helper Functions:
        - Generates random location offsets and rotations.
        - Retrieves the agent's location.
        - Constructs commands to add physics-based objects to the environment.
        - Creates methods to spawn target and regular entities in the environment.
        - Sets the camera's position and "look-at" point.

    - Initialization of a Trial:
        - Initializes the commands for a new trial.
        - Randomly selects pairs of contained and container entities.
        - Adds entities (object, container, and potentially target) to the environment based on the trial type.
        - Ensures rigid bodies and transforms are always sent for tracking.

    - Main Execution:
        - Initializes the ContainmentSimulator.
        - Parses arguments and provides default settings.
        - Executes the simulator and prints the result.

#### 04_rolling_simulator.py

    - RollingSimulator Class:

        - __init__: Initializes the RollingSimulator with default settings, a list of entities ("orange", "golf", "apple" etc.), and other relevant attributes.

        - apply_transitional_force: This function applies a transitional force to a rolling entity when it gets close to another entity (a barrier).

        - apply_psychological_interaction: This function simulates some form of psychological interaction between two objects. It's not completely clear what "psychological" means in this context, but the function seems to control how one object looks at another and how it moves.

        - destroy_entities: Destroys all the entities in the simulation and resets the communication.

        - run_frame_by_frame: This function runs the simulation frame by frame, applying either transitional or psychological interactions as required by the trial type.

        - _get_random: Generates a random float between a given range.

        - _add_physics_object: Adds a physics object (like the rolling entity or barriers) with specific properties to the simulator.

        - spawn_target_entity: Spawns a target entity in the simulation at a random location.

        - spawn_entity: This function spawns entities (like ramps or barriers) in the simulator.

        - set_camera: Configures the camera's position and orientation for the simulation.

        - init_trial_cmds: Initializes a set of commands for a new trial. Depending on the trial type, it may add different entities to the scene and set their properties.

    - Main Execution:

        - If the script is run as the main program, it creates an instance of RollingSimulator and then runs the simulator with certain parameters parsed from command-line arguments.

        - A console message is printed to indicate that the add_object_to_scene is set to True. This suggests there might be situations where you don't want to add objects, but in this default execution, they are added.

        - The run method of the simulator instance is then called with various parameters to execute the simulation, and the result is printed to the console.

#### 05_object_shower_simulator.py

    - Initialization (__init__ method):
        - Configures the simulator with predefined entity types.
        - Initializes control ID, model librarian, entities, and random camera location.

    - apply_force:
        - Apply either a direct force or force at a position to an entity.
        - Chooses between direct and positional force based on a random boolean.

    - _random_boolean:
        - Returns a random True or False value.

    - _apply_direct_force:
        - Directs the object to look at a random position.
        - Applies a specific force magnitude to the object.

    - _apply_positional_force:
        - Applies force at a random position on the object with force potentially applied in the x, y, or z direction.

    - _random_position:
        - Provides a random position in the simulator space.
        - Allows fixing the y-coordinate at 0.

    - set_camera:
        - Sets the camera in a third-person view relative to a specific point.
        - Utilizes the ThirdPersonCamera for this view configuration.

    - init_trial_cmds:
        - Initializes trial commands based on a random scenario type: 'fall', 'force', or both.
        - Determines object position based on scenario type.
        - Determines object rotation, especially if 'fall' is in the scenario type.
        - Calls apply_force if 'force' is in the scenario type.

    - Execution Script (if __name__ == "__main__": block):
        - Creates an instance of ObjectShowerSimulator.
        - Builds arguments for the simulator.
        - Provides a warning regarding an ignored parameter.
        - Executes the simulation run, printing the outcomes.


