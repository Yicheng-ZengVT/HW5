# Homework 5

<p align="center">Yicheng Zeng</p>

[toc]

Requirements:
- a text document that explains your strategy for Step 1 and your desired characteristics (see Assignment in Github)
- your implemented strategy and final version of main.py (as well as other files you may have edited)
- a text document that explains your performance metrics
- a table that shows the values for these metrics with and without assistance
results from statistical tests for significance
- if your strategy succeeded, briefly explain why you think it worked. If it failed, explain what you would test next.

### Strategy

The code implemented such strategy of shared control: If the user selected 'yes' to the autonomy, then the robot will throw tasks to LLM and generate a sequence of actions. A toggle '.' is provided and $\alpha$ will be reduced to 0.05 if the user wants to teleop instead of let the robot proceed.

If the user decide to work without help of LLM, a task name is still provided, and metric is applied to evalueate success or not. Either way, user is able to provide their thoughts (success or not) and leave comments to the assistive robot.

The following instruction is provided to each user:
1. After the simulation start, you can choose to accept assistance from the LLM or not. Then, you may enter your goal and try to achieve it with or without the assistance from the robot.
2. After you typed your task, you can single click the gui to input your teleop.
 "W/A/S/D" is for horizonatal move, "Q/E" is up/down. "Z/X" is for opening/closing the gripper. 
3. If you choose assistance and the robot is annoying, you may input "." so robot is just inputing minimal input and you have top authority of what to do next.
4. After finish you can exit using "Ctrl + C", and tell the robot if your goal is achieved by typing (Y/N). Feel free to leave comments, your evaluation is also logged.



### Performance Metrics

The performance metrics includes the following:

completion_time,path_length,teleop_inputs and success_or_not(evaluated by user).

### Table of results

It is attached at trial_log.csv.

### Discussion

The t-test shows no significance in assistive strategy. I did the test with two of my friends and myself, and I have attached some discovers:

1. Some tasks is not able to have a clear LLM output, like "open cabinet" related task often fails to generate sequencial tasks by LLM, resulting in fallback to teleop mode and unsuccessful result. Perhaps the cabinet is out of operation space.
2. Teleop mode only provided yaw rotation, which is complained by users in some settings.
3. Some tasks is hard to evaluated, e.g., some user wants the robot to throw away the cube as far as possible, which is hard to put in the metric.
4. Sometimes assistive robot is doing extra steps, for example, if user is stacking the cubes, it also "stack" the first cube with redundant motions.