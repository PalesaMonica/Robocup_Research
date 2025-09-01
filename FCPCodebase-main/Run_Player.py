from scripts.commons.Script import Script
from communication.Communicator import Communicator

script = Script(cpp_builder_unum=1)  # Initialize
a = script.args

if a.P:  # penalty shootout
    from agent.Agent_Penalty import Agent
else:  # normal agent
    from agent.Agent import Agent

# Create player agent
if a.D:  # debug mode
    player = Agent(a.i, a.p, a.m, a.u, a.t, True, True, False, a.F)
else:
    player = Agent(a.i, a.p, None, a.u, a.t, False, False, False, a.F)


BROADCAST_INTERVAL = 40  # ms
last_global_update = 0
cycle_time =20

while True:
    current_time = player.communicator.world.time_local_ms
    
    # Agent thinking & receiving
    player.think_and_send()
    player.scom.receive()
    
    # Step 1: Update local voting group every 40 ms
    if current_time - player.communicator.last_broadcast_time >= BROADCAST_INTERVAL:
        player.communicator.update_voting_group()
        player.communicator.last_broadcast_time = current_time
    
    # Step 2: Update and log global merged group every 40 ms
    if current_time - last_global_update >= (BROADCAST_INTERVAL+cycle_time):
        communicators = [player.communicator]  
        all_groups = [c.get_voting_group() for c in communicators]
        merged_group = Communicator.merge_groups(all_groups, min_conf=0.15)

        # Only log if merged group is not empty
        if merged_group:
            Communicator.log_group(merged_group, title="Global Voting Group")
        
        last_global_update = current_time


