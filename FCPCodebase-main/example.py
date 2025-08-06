from agent.Base_Agent import Base_Agent as Agent
from math_ops.Math_Ops import Math_Ops as M
from scripts.commons.Script import Script

script = Script()
a = script.args

# Create 3 agents
script.batch_create(Agent, ((a.i, a.p, a.m, u+1, a.r, "Home") for u in range(3)))

players = script.players
p_num = len(players)

# Beam players onto the field at fixed positions
script.batch_unofficial_beam(
    (-3, 4.5 - abs(3*i - 7.5), 0.5, 0) for i in range(p_num)
)

getting_up = [False] * p_num

while True:
    for i in range(p_num):
        p = players[i]
        w = p.world
        robot = w.robot

        player_2d = robot.loc_head_position[:2]
        ball_2d = w.ball_abs_pos[:2]
        goal_dir = M.vector_angle((15, 0) - player_2d)

        
        if robot.unum == 1:
            p.think_and_send()

        # Others just do regular behavior
        if p.behavior.is_ready("Get_Up") or getting_up[i]:
            getting_up[i] = not p.behavior.execute("Get_Up")
        else:
            p.behavior.execute("Basic_Kick", goal_dir)

    script.batch_commit_and_send()

    script.batch_receive()
