from world.World import World
import numpy as np
from agent.Base_Agent import Base_Agent


class Round_Robin_Scheduler:
    def __init__(self, agents):
        self.agents = agents
        self.current_index = 0
        self.round_robin_interval = 40  
        self.last_switch_time = 0
        
    def get_next_agent(self):
        """Returns the next agent in a round-robin fashion."""
        if not self.agents:
            return None
        agent = self.agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.agents)
        return agent
    
    def sharing_information(self):
        pass
        
    

    
