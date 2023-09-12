"""
Script for generating simulations based on user input.

This script is designed to run multiple simulation scenarios, each having
its own configuration. For each scenario, it will run a number of simulations
(batches) for different trial types. Each simulation is executed as an external command.
"""

# Import required modules.
from os import system
from utils import build_arg_pars, console_msg

# Parse the command-line arguments.
args = build_arg_pars(masks=False)

# Print a warning to the user about the trial_type parameter being ignored.
print(console_msg('All scenarios will be generated, hence trial_type parameter will be ignored', 'warning'))

# Get the number of batches from the user.
user_input = False
while not user_input:
    try:
        batches = int(input('How many batches would you like to create?'))
        user_input = True
    except ValueError:
        # Prompt the user if the input was invalid.
        print(console_msg("Invalid choice: Number of batches must be an integer.", 'error'))

# Loop over each batch.
for i in range(batches):
    # For each simulator type.
    for simulator in ['01_collision_simulator.py', '02_occlusion_simulator.py', '03_containment_simulator.py',
                      '04_rolling_simulator.py']:


        # For each trial type.
        for trial_type in ['physical', 'transitional', 'psychological']:
            # Construct the command with required parameters.
            cmd_parts = [
                f'python {simulator}',
                f'--framerate {args.framerate}',
                f'--trial_type {trial_type}',
                f'--pass_masks {args.pass_masks}',
                f'--num {args.num}',
                f'--png {args.png}',
                f'--room {args.room}',
                f'--tot_frames {args.tot_frames}',
                f'--add_object_to_scene {args.add_object_to_scene}',
                f'--save_frames {args.save_frames}',
                f'--save_mp4 {args.save_mp4}',
            ]

            # Join the command parts into a single command string.
            cmd = ' '.join(cmd_parts)

            # Print and run the constructed command.
            print(cmd)
            system(cmd)
