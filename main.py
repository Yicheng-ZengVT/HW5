import pybullet as p
import pybullet_data
import numpy as np
import os
import time
import json
import csv
from robot import Panda
from objects import objects

################ HW5 setup ########################
import httpx
from openai import APIConnectionError, OpenAI
from teleop import KeyboardController

# Configure these via environment variables when possible.
# openai_api_key = os.environ.get("OPENAI_API_KEY", "")
openai_api_key = "sk-da4a2962fe31477691a649382243e726"
openai_api_base = os.environ.get("OPENAI_API_BASE", "https://llm-api.arc.vt.edu/api/v1")

import platform
_http_kwargs = {"timeout": 20.0}
# Force IPv4 on Linux to avoid IPv6 routing issues; skip on Windows where this can cause errors
if platform.system() != "Windows":
    _http_kwargs["transport"] = httpx.HTTPTransport(local_address="0.0.0.0")
client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
    http_client=httpx.Client(**_http_kwargs),
)

teleop = KeyboardController()

# parameters
control_dt = 1. / 240.

# create simulation and place camera
physicsClient = p.connect(p.GUI)
p.setGravity(0, 0, -9.81)
p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
p.configureDebugVisualizer(p.COV_ENABLE_KEYBOARD_SHORTCUTS, 0)
# p.resetDebugVisualizerCamera(cameraDistance=1.0,
#                                 cameraYaw=40.0,
#                                 cameraPitch=-40.0,
#                                 cameraTargetPosition=[0.5, 0.0, 0.2])
p.resetDebugVisualizerCamera(cameraDistance=1.0,
                                cameraYaw=-40.0,
                                cameraPitch=-40.0,
                                cameraTargetPosition=[0.5, 0.0, 0.2])

# load the objects
urdfRootPath = pybullet_data.getDataPath()
plane = p.loadURDF(os.path.join(urdfRootPath, "plane.urdf"), basePosition=[0, 0, -0.625])
table = p.loadURDF(os.path.join(urdfRootPath, "table/table.urdf"), basePosition=[0.5, 0, -0.625])
cube1 = objects.SimpleObject("cube.urdf", basePosition=[0.5, -0.3, 0.025], baseOrientation=p.getQuaternionFromEuler([0, 0, 0.7]))
cube2 = objects.SimpleObject("cube.urdf", basePosition=[0.4, -0.2, 0.025], baseOrientation=p.getQuaternionFromEuler([0, 0, -0.3]))
cube3 = objects.SimpleObject("cube.urdf", basePosition=[0.5, -0.1, 0.025], baseOrientation=p.getQuaternionFromEuler([0, 0, 0.2]))
cabinet = objects.CollabObject("cabinet.urdf", basePosition=[0.9, -0.3, 0.2], baseOrientation=p.getQuaternionFromEuler([0, -np.pi/6, np.pi]))
microwave = objects.CollabObject("microwave.urdf", basePosition=[0.5, 0.3, 0.2], baseOrientation=p.getQuaternionFromEuler([0, 0, -np.pi/2]))

# load the robot
jointStartPositions = [0.0, 0.0, 0.0, -2*np.pi/4, 0.0, np.pi/2, np.pi/4, 0.0, 0.0, 0.04, 0.04]
panda = Panda(basePosition=[0, 0, 0],
                baseOrientation=p.getQuaternionFromEuler([0, 0, 0]),
                jointStartPositions=jointStartPositions)

##################### Homework 5 code #####################
model = "gpt-oss-120b"

# ---- Helper: compute action toward a goal position ----
def action_to_goal(current_pos, goal_pos, step_size=0.001):
    """Returns a target position one step closer to goal_pos."""
    error = np.array(goal_pos) - np.array(current_pos)
    dist = np.linalg.norm(error)
    if dist < 0.005:
        return np.array(goal_pos), True  # close enough, mark reached
    direction = error / dist
    # adaptive velocity: move faster when far, slower when near
    speed = step_size * min(dist / 0.05, 1.0) + step_size * 0.5
    return np.array(current_pos) + speed * direction, False

# ---- Helper: get current environment description for the LLM ----
def get_env_description():
    c1 = cube1.get_state()
    c2 = cube2.get_state()
    c3 = cube3.get_state()
    cab = cabinet.get_state()
    mic = microwave.get_state()
    rob = panda.get_state()
    desc = (
        "Environment objects and their current positions (x, y, z):\n"
        f"- cube1: position {np.round(c1['position'], 3).tolist()}\n"
        f"- cube2: position {np.round(c2['position'], 3).tolist()}\n"
        f"- cube3: position {np.round(c3['position'], 3).tolist()}\n"
        f"- cabinet: base {np.round(cab['base_position'], 3).tolist()}, "
        f"handle {np.round(cab['handle_position'], 3).tolist()}, joint_angle {round(cab['joint_angle'], 3)}\n"
        f"- microwave: base {np.round(mic['base_position'], 3).tolist()}, "
        f"handle {np.round(mic['handle_position'], 3).tolist()}, joint_angle {round(mic['joint_angle'], 3)}\n"
        f"- robot end-effector: position {np.round(rob['ee-position'], 3).tolist()}\n"
        "\nThe robot gripper can open and close to grasp small cubes.\n"
        "The cabinet has a sliding drawer (prismatic joint). The microwave has a door (revolute joint).\n"
        "To open the cabinet: approach its handle, close gripper on handle, then pull in -x direction.\n"
        "To open the microwave: approach its handle, close gripper on handle, then pull in -y direction.\n"
        "To pick up a cube: move above cube, lower to cube height, close gripper, then lift.\n"
    )
    return desc

# ---- Helper: ask LLM to generate a waypoint plan ----
def plan_task(user_command):
    env_desc = get_env_description()
    system_prompt = (
        "You are a robot task planner. Given a user command and the environment state, "
        "output a JSON list of steps. Each step is an object with:\n"
        '  "action": one of "move_to", "grasp", "release"\n'
        '  "target": [x, y, z] coordinates (only for "move_to")\n'
        '  "description": short text explaining the step\n'
        "Output ONLY valid JSON, no other text. Example:\n"
        '[{"action": "move_to", "target": [0.5, -0.3, 0.1], "description": "move above cube1"},\n'
        ' {"action": "move_to", "target": [0.5, -0.3, 0.03], "description": "lower to cube1"},\n'
        ' {"action": "grasp", "target": null, "description": "grasp cube1"},\n'
        ' {"action": "move_to", "target": [0.5, -0.3, 0.15], "description": "lift cube1"},\n'
        ' {"action": "move_to", "target": [0.5, 0.3, 0.15], "description": "move above microwave"},\n'
        ' {"action": "release", "target": null, "description": "release cube1 into microwave"}]\n'
        "Keep heights above 0.02 (table surface). Use the actual object positions from the environment."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Environment:\n{env_desc}\nUser command: {user_command}"},
    ]
    try:
        response = client.chat.completions.create(model=model, messages=messages)
        raw = response.choices[0].message.content.strip()
        # extract JSON from response (handle markdown code blocks)
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        plan = json.loads(raw)
        return plan
    except (APIConnectionError, json.JSONDecodeError, Exception) as e:
        print(f"LLM planning failed: {e}")
        return None

# ---- Metric logging ----
LOG_FILE = "trial_log.csv"
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["trial", "condition", "task", "completion_time", "path_length", "teleop_inputs", "success", "comments"])

trial_count = 0
# count existing trials
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r") as f:
        trial_count = max(0, sum(1 for _ in f) - 1)

# ---- Get initial robot state for target tracking ----
state = panda.get_state()
target_position = np.array(state["ee-position"])
target_quaternion = np.array(state["ee-quaternion"])

# ---- Ask user for task and condition ----
print("\n" + "="*60)
print("HW5 Assistive Robot")
print("="*60)
condition = input("Do you need assistance from the robot? (Y/N): ").strip()
if condition.upper() == "Y":
    condition = "assisted"
else:
    condition = "teleop_only"
task_command = input("Enter task command (e.g., 'put cube1 in the microwave'): ").strip()

# ---- Generate plan if assisted ----
waypoints = []
current_wp_idx = 0
if condition == "assisted":
    print("Generating plan with LLM...")
    plan = plan_task(task_command)
    if plan:
        waypoints = plan
        print(f"Plan generated with {len(waypoints)} steps:")
        for i, step in enumerate(waypoints):
            print(f"  {i+1}. [{step['action']}] {step['description']}")
    else:
        print("Plan generation failed. Running in teleop-only mode.")
        condition = "teleop_only"
else:
    print(f"Task: {task_command}")
    print("Running in teleop-only mode. Use keyboard to complete the task.")

# ---- Blending parameter ----
# Alpha = 0 means pure teleop, Alpha > 0 means robot assists
Alpha = 0.6 if condition == "assisted" else 0.0
Alpha_teleop = 0.05
gripper_timer = 0  # frames to hold gripper action after a grasp/release step

# ---- Metric tracking ----
task_start_time = time.time()
total_path_length = 0.0
teleop_input_count = 0
prev_position = np.array(target_position)

print("\nControls: WASD=move, QE=up/down, PL=rotate, ZX=gripper, '.'=toggle assistance")
print("Press Ctrl+C in terminal to end trial and log metrics.\n")

# ---- Main loop ----
try:
    while True:
        # get all states
        robot_state = panda.get_state()
        ee_pos = np.array(robot_state["ee-position"])
        ee_quat = np.array(robot_state["ee-quaternion"])
        ee_euler = robot_state["ee-euler"]

        # track path length
        total_path_length += np.linalg.norm(ee_pos - prev_position)
        prev_position = ee_pos.copy()

        # ---- Read keyboard once per frame ----
        keys = p.getKeyboardEvents()

        # ---- Teleop input (reuse keys dict instead of calling getKeyboardEvents again) ----
        action = np.zeros(8, dtype=np.float32)
        for k, v in teleop.key_map.items():
            if k in keys and (keys[k] & p.KEY_IS_DOWN):
                action += v
        action[0:3] *= teleop.pos_step
        action[3:6] *= teleop.rot_step

        has_teleop_input = np.any(action[0:6] != 0) or action[6] != 0
        if has_teleop_input:
            teleop_input_count += 1

        human_position = target_position + action[0:3]
        human_quaternion = p.multiplyTransforms(
            [0, 0, 0], p.getQuaternionFromEuler(action[3:6]),
            [0, 0, 0], target_quaternion)[1]
        human_quaternion = np.array(human_quaternion)

        # ---- Toggle blending with "." ----
        # Use KEY_WAS_TRIGGERED for edge detection (fires once per press, not every frame)
        if ord(".") in keys and (keys[ord(".")] & p.KEY_WAS_TRIGGERED):
            if Alpha == Alpha_teleop:
                Alpha = 0.6
                print("[Toggle] Assistance ON (Alpha=0.6)")
            else:
                Alpha = Alpha_teleop
                print("[Toggle] Assistance OFF — pure teleop")

        # ---- Robot action from waypoint plan ----
        robot_target_pos = human_position  # fallback: follow human
        robot_target_quat = human_quaternion
        gripper_action = 0  # 0=no action, +1=open, -1=close

        if waypoints and current_wp_idx < len(waypoints):
            step = waypoints[current_wp_idx]

            if step["action"] == "move_to" and step["target"] is not None:
                goal = np.array(step["target"])
                robot_target_pos, reached = action_to_goal(ee_pos, goal)
                # keep end-effector pointing down
                robot_target_quat = np.array(p.getQuaternionFromEuler([np.pi, 0, ee_euler[2]]))
                if reached:
                    print(f"  [Step {current_wp_idx+1}/{len(waypoints)}] Done: {step['description']}")
                    current_wp_idx += 1

            elif step["action"] == "grasp":
                robot_target_pos = ee_pos  # stay in place
                robot_target_quat = ee_quat
                gripper_action = -1  # close
                gripper_timer += 1
                if gripper_timer > 120:  # hold for ~0.5s
                    print(f"  [Step {current_wp_idx+1}/{len(waypoints)}] Done: {step['description']}")
                    current_wp_idx += 1
                    gripper_timer = 0

            elif step["action"] == "release":
                robot_target_pos = ee_pos
                robot_target_quat = ee_quat
                gripper_action = +1  # open
                gripper_timer += 1
                if gripper_timer > 120:
                    print(f"  [Step {current_wp_idx+1}/{len(waypoints)}] Done: {step['description']}")
                    current_wp_idx += 1
                    gripper_timer = 0
            else:
                # unknown action, skip
                current_wp_idx += 1

        elif waypoints and current_wp_idx >= len(waypoints):
            # plan complete
            if Alpha > 0:
                print("[Plan complete] All steps finished!")
                Alpha = 0.0  # switch to pure teleop after plan is done

        # ---- Blend human and robot actions ----
        target_position = (1 - Alpha) * human_position + Alpha * robot_target_pos
        target_quaternion = np.array(p.getQuaternionSlerp(human_quaternion, robot_target_quat, Alpha))

        # workspace limit
        if target_position[2] < 0.02:
            target_position[2] = 0.02

        # move robot
        panda.move_to_pose(ee_position=target_position, ee_quaternion=target_quaternion, positionGain=1)

        # gripper: robot plan gripper actions when assisted, always allow human override
        if action[6] == +1:
            panda.open_gripper()
        elif action[6] == -1:
            panda.close_gripper()
        elif gripper_action == -1 and Alpha > 0:
            panda.close_gripper()
        elif gripper_action == +1 and Alpha > 0:
            panda.open_gripper()

        # step simulation
        p.stepSimulation()
        time.sleep(control_dt)

except KeyboardInterrupt:
    # ---- Log metrics on exit ----
    completion_time = round(time.time() - task_start_time, 2)
    total_path_length = round(total_path_length, 4)
    trial_count += 1

    print(f"\n{'='*60}")
    print(f"  Condition:       {condition}")
    print(f"  Task:            {task_command}")
    print(f"  Completion time: {completion_time}s")
    print(f"  Path length:     {total_path_length}")
    print(f"  Teleop inputs:   {teleop_input_count}")

    # quick survey — default to N if user just hits enter or Ctrl+C again
    try:
        success_input = input("Was the task completed successfully? (Y/N, default N): ").strip().upper()
        success = success_input == "Y"
        comments = input("Any comments? (press Enter to skip): ").strip()
    except (KeyboardInterrupt, EOFError):
        success = False
        comments = ""

    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([trial_count, condition, task_command, completion_time, total_path_length, teleop_input_count, success, comments])

    print(f"Trial {trial_count} logged (success={success})")
    print(f"Saved to {LOG_FILE}")
    print(f"{'='*60}")