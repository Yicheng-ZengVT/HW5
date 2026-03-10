# HW5

## Description

This homework is modified from the HW5 source code: https://github.com/vt-hri/HW5.git

In this homework assignment we will develop an assistive robot arm. By using the tested environment, you have my permission to use my API key but you may need to abide the confidential policies of its usage.

Currently we only have 3 cubes, a microwave and a cabinet, feel free to prompt the robot to do whatever you like, feel free to make it confused, I don't have too much task in mind yet.

## Install and Run

In the root folder of this code:

**Linux / Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install numpy pybullet openai httpx
python main.py
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate
pip install numpy pybullet openai httpx
python main.py
```

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install numpy pybullet openai httpx
python main.py
```

> **Note:** If you get an error about "Execution of scripts is disabled" in PowerShell, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` first.

### Usage

1. After the simulation start, you can choose to accept assistance from the LLM or not. Then, you may enter your goal and try to achieve it with or without the assistance from the robot.
2. After you typed your task, you can single click the gui to input your teleop.
 "W/A/S/D" is for horizonatal move, "Q/E" is up/down. "Z/X" is for opening/closing the gripper. 
3. If you choose assistance and the robot is annoying, you may input "." so robot is just inputing minimal input and you have top authority of what to do next.
4. After finish you can exit using "Ctrl + C", and tell the robot if your goal is achieved by typing (Y/N). Feel free to leave comments, your evaluation is also logged.



Example tasks:

(May help you)How to work with sim:
1. scroll mouse to zoom in/out.
2. ctrl + left mouse button to rotate