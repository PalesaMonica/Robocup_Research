from world.World import World
import numpy as np

class Communicator():
    def __init__(self, world: World, commit_announcement) -> None:
        self.world = world
        self.commit_announcement = commit_announcement
        self.last_broadcast_time = 0
        self.broadcast_interval = 40 
        self.world = world
        self.r = world.robot    
    
    @property
    def can_see_ball(self):
        "returns True if the agent can see the ball"
        if self.world.ball_is_visible:
            return True
        return False
    
    def is_ball_data_fresh(self, max_age_ms=50):
        """returns True if the ball position data is fresh enough to be used"""
        current_time = self.world.time_local_ms
        age = current_time - self.world.ball_abs_pos_last_update
        return age <= max_age_ms

    def should_use_ball_position(self):
        "returns True if the agent should use the ball position for broadcasting"
        return (self.can_see_ball and self.r.loc_is_up_to_date) or (self.is_ball_data_fresh(max_age_ms=40))
    
    def get_ball_position(self):
        "returns the ball position if the agent can see the ball"
        if self.should_use_ball_position():
            return self.world.ball_abs_pos
        return None


    def broadcast_ball_condition(self):
        "returns True if the agent can see the ball and is in a position to broadcast it"
        ball_pos = self.get_ball_position()
        player_list =[4,7,9,10]
        if ball_pos is None:
            return False
        x, y = ball_pos[0], ball_pos[1] 
        if -15 <= x <= 15 and -10 <= y <= 10 and  self.r.unum in player_list:
            return True
       
        return False

    def ball_position_to_message(self, ball_pos):
        """Converts the ball position to a message string if the position is valid"""
        if ball_pos is None:
            return None
        message_str = f"B:{ball_pos[0]:.1f},{ball_pos[1]:.1f}"
        if len(message_str.encode("utf-8")) > 20:
            return None  
        return message_str
    
    def calculate_confidence_score(self, ball_pos):
        """calculate the confindence an agent has in the ball position they are broadcasting"""
        agent_pos = self.r.loc_head_position  
        distance = np.linalg.norm(ball_pos[:2] - agent_pos[:2])  
        confidence = 1.0 /(distance + 1.0)  
        if confidence < 0.1:
            confidence = 0.1
        return confidence
    
    def broadcast(self):
        current_time = self.world.time_local_ms
        if self.broadcast_ball_condition() and (current_time - self.last_broadcast_time >= self.broadcast_interval):
            ball_pos = self.get_ball_position()
            message_str = self.ball_position_to_message(ball_pos)
            if message_str is not None: 
                message_bytes = message_str.encode("utf-8")
                self.commit_announcement(message_bytes)
                pos_x, pos_y = self.r.loc_head_position[:2]
                print(
                    f"Agent {self.r.unum} broadcasted message from position ({pos_x:.1f}, {pos_y:.1f}): "
                    f"{message_str} with confidence {self.calculate_confidence_score(ball_pos):.2f}"
                )
                self.last_broadcast_time = current_time
            else:
                print(f"Agent{self.r.unum}: failed to create message")

    def receive(self, msg: bytearray):
        decoded = msg.decode("utf-8")
        print(f"Agent {self.r.unum} received message: {decoded}")
        