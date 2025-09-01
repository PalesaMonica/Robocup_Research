from world.World import World
import numpy as np

import logging

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("communicator.log"),  
        logging.StreamHandler()                   
    ]
)


class Communicator:
    def __init__(self, world: World, commit_announcement) -> None:
        self.world = world
        self.commit_announcement = commit_announcement
        self.last_broadcast_time = 0
        self.broadcast_interval = 40  # ms
        self.r = world.robot
        self.t = world.teammates
        self.voting_group = {}

    def is_ball_data_fresh(self, max_age_ms=40):
        return (self.world.time_local_ms - self.world.ball_abs_pos_last_update) <= max_age_ms

    def get_ball_position(self):
        return self.world.ball_abs_pos if self.world.ball_is_visible else None

    def broadcast_ball_condition(self):
        ball_pos = self.get_ball_position()
        if ball_pos is None:
            return False
        x, y = ball_pos[:2]
        return -15 <= x <= 15 and -10 <= y <= 10

    def ball_position_to_message(self, ball_pos):
        if ball_pos is None:
            return None
        message_str = f"B:{self.r.unum}:{ball_pos[0]:.1f},{ball_pos[1]:.1f}"
        return message_str if len(message_str.encode("utf-8")) <= 20 else None

    def calculate_confidence_score(self, ball_pos,player_pos):
        distance = np.linalg.norm(ball_pos[:2] - player_pos[:2])
        return max(1.0 / (distance + 1.0), 0.1)
    
    def update_voting_group(self):
        """
        Update the voting group based on teammates and self.
        Stores estimated ball positions, confidence, and timestamp.
        """
        group = dict()
        current_time = self.world.time_local_ms

        # Add teammates
        for teammate in self.world.teammates:
            if teammate.can_see_ball and teammate.ball_est_pos is not None:
                confidence = self.calculate_confidence_score(teammate.ball_est_pos,teammate.state_abs_pos)
                group[teammate.unum] = {
                    "ball_pos": teammate.ball_est_pos[:2],
                    "confidence": confidence,
                    "timestamp": current_time
                }

        # Include self
        if self.world.ball_is_visible:
            confidence = self.calculate_confidence_score(self.world.ball_abs_pos,self.r.loc_head_position)
            group[self.r.unum] = {
                "ball_pos": self.world.ball_abs_pos[:2],
                "confidence": confidence,
                "timestamp": current_time
            }

        self.voting_group = group
        return self.voting_group

    def get_voting_group(self):
        """Return current voting group for later use in voting"""
        return self.voting_group
    
    def turn_off_vision(self):
        """ 
        Turn off vision only for agents in the voting group.
        This ensures they use the initial ball positions for voting.
        """
        group = self.get_voting_group()
        if group:  
            agent_ids_in_group = set(group.keys())

            for agent in self.t:
                if agent.unum in agent_ids_in_group:
                    agent.can_see_ball = False 
            
            if self.r.unum in agent_ids_in_group:
                self.world.ball_is_visible = False

    def turn_on_vision(self):
        """Restore vision only for agents in the voting group."""
        group = self.get_voting_group()
        if group:
            agent_ids_in_group = set(group.keys())

            for agent in self.t:
                if agent.unum in agent_ids_in_group:
                    agent.can_see_ball = True

            if self.r.unum in agent_ids_in_group:
                self.world.ball_is_visible = True


    def broadcast(self):
        """Broadcast the ball position if conditions are met"""
        current_time = self.world.time_local_ms
        self.update_voting_group()  

        if self.broadcast_ball_condition() and (current_time - self.last_broadcast_time >= self.broadcast_interval):
            ball_pos = self.get_ball_position()
            message_str = self.ball_position_to_message(ball_pos)
            if message_str:
                self.commit_announcement(message_str.encode("utf-8"))
                self.last_broadcast_time = current_time
            else:
                print(f"Agent {self.r.unum}: failed to create message")

    def receive(self, msg: bytearray):
        """Decode and print received message"""
        decoded = msg.decode("utf-8")
        pass

    
    @staticmethod
    def merge_groups(group_list, min_conf=0.15):
        """
        Union multiple voting groups into one dictionary.
        Keeps the entry with the highest confidence if duplicates exist.
        Filters out agents below min_conf.
        """
        merged = {}
        for group in group_list:
            for agent_id, info in group.items():
                if info["confidence"] < min_conf:
                    continue
                # Keep higher confidence if duplicate
                if (agent_id not in merged) or (info["confidence"] > merged[agent_id]["confidence"]):
                    merged[agent_id] = info
        return merged
    
    @staticmethod
    def log_group(group, title="Merged Global Voting Group"):
        """Log the contents of a group dictionary"""
        if not group:
            logging.info(f"{title} is EMPTY.")
            return

        logging.info(f"=== {title} ===")
        for agent_id, info in group.items():
            pos = info["ball_pos"]
            conf = info["confidence"]
            ts = info["timestamp"]
            logging.info(
                f"Agent {agent_id} | Ball: {pos} | Confidence: {conf:.2f} | Time: {ts} ms"
            )
        logging.info("=" * (len(title) + 10))