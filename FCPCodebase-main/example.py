from agent.Base_Agent import Base_Agent as Agent
from math_ops.Math_Ops import Math_Ops as M
from scripts.commons.Script import Script
script = Script()
a = script.args

p1 = Agent(a.i, a.p, a.m, a.u, a.r, a.t)
p2 = Agent(a.i, a.p, a.m, a.u, a.r, "Opponent")
players = [p1,p2]
p1.scom.unofficial_beam((-3,0,p1.world.robot.beam_height), 0)
p2.scom.unofficial_beam((-3,0,p2.world.robot.beam_height), 0)

getting_up = [False]*2
while True:
    for i in range(len(players)):
        p = players[i]
        w = p.world
        player_2d = w.robot.loc_head_position[:2]
        ball_2d = w.ball_abs_pos[:2]
        goal_dir = M.vector_angle( (15,0)-player_2d )
        if p.behavior.is_ready("Get_Up") or getting_up[i]:
            getting_up[i] = not p.behavior.execute("Get_Up")
        else:
            p.behavior.execute("Basic_Kick", goal_dir)
        p.scom.commit_and_send( w.robot.get_command() )
        p.think_and_send()

    p1.scom.receive()
    p2.scom.receive()