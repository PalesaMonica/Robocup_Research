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
        self.last_global_update = 0
        self.broadcast_interval = 40   # ms
        self.r = world.robot
        self.voting_group = {}
        self.total_players = 11
        self.cycle_time = self.broadcast_interval * self.total_players

    # ---------------- Ball state helpers ----------------
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

    # ---------------- Voting group logic ----------------
    def calculate_confidence_score(self, ball_pos, player_pos):
        distance = np.linalg.norm(ball_pos[:2] - player_pos[:2])
        return max(1.0 / (distance + 1.0), 0.1)

    def update_local_voting_group(self):
        group = dict()
        current_time = self.world.time_local_ms
        if self.world.ball_is_visible and self.world.ball_abs_pos is not None:
            confidence = self.calculate_confidence_score(
                self.world.ball_abs_pos, self.r.loc_head_position
            )
            group[self.r.unum] = {
                "ball_pos": self.world.ball_abs_pos[:2],
                "confidence": confidence,
                "timestamp": current_time
            }

        self.voting_group = group
        return self.voting_group
    
    def get_voting_group(self):
        return self.voting_group

    def turn_off_vision(self):
        group = self.get_voting_group()
        if group:
            agent_ids = set(group.keys())
            if self.r.unum in agent_ids:
                self.world.ball_is_visible = False

    def turn_on_vision(self):
        group = self.get_voting_group()
        if group:
            agent_ids = set(group.keys())
            if self.r.unum in agent_ids:
                self.world.ball_is_visible = True

    def scheduler(self, now_ms: int) -> int:
        """Return which agent ID owns the current slot"""
        cycle_position = (now_ms % self.cycle_time) // self.broadcast_interval
        return (cycle_position % self.total_players) + 1

    def should_broadcast(self):
        """Checks if the current agent should broadcast"""
        current_time = self.world.time_local_ms
        owner = self.scheduler(current_time) 
        return owner == self.r.unum

    # ---------------- Broadcast & Receive ----------------
    def broadcast(self):
        """Broadcast ball info every interval"""
        current_time = self.world.time_local_ms
        #self.update_local_voting_group()

        if (
            (current_time - self.last_broadcast_time >= self.broadcast_interval)
            and self.should_broadcast()
        ):
            message_str = f"Iamagent{self.r.unum}"
            if message_str:
                self.commit_announcement(message_str.encode("utf-8"))

                logging.info(
                    f"[BROADCAST] Time {current_time} ms | Agent {self.r.unum} broadcasting message → {message_str}"
                )

                #self.turn_off_vision()
                self.last_broadcast_time = current_time
            else:
                logging.warning(f"Agent {self.r.unum}: failed to create message")

    def receive(self, msg: bytearray):
        """Receive messages after comm cycle"""
        decoded = msg.decode("utf-8")
        if not decoded.startswith("Iamag"):
            return

        logging.info(
            f"[RECEIVE] Time {self.world.time_local_ms} ms | Agent {self.r.unum} received → {decoded}"
        )
