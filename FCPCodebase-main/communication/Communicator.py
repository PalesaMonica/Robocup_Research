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
        self.voting_group_list = []
        self.teammate=world.teammates
        self.confidence = 0.0
        self.last_reset_cycle = -1  
        self.cycle_completed = False 
        self.current_cycle = -1

    # ---------------- Ball state helpers ----------------
    def is_ball_data_fresh(self, max_age_ms=40):
        return (self.world.time_local_ms - self.world.ball_abs_pos_last_update) <= max_age_ms

    def get_ball_position(self):
        """Returns ball position if visible, else None"""
        return self.world.ball_abs_pos if self.world.ball_is_visible else None

    def broadcast_ball_condition(self)-> bool:
        """Check if ball is visible and within field boundaries"""
        ball_pos = self.get_ball_position()
        if ball_pos is None:
            return False
        x, y = ball_pos[:2]
        return -15 <= x <= 15 and -10 <= y <= 10

    def ball_position_to_message(self, ball_pos, confidence):
        """Convert ball position to message string"""
        if ball_pos is None:
            return None
        message_str = f"B:{self.r.unum}:{ball_pos[0]:.1f},{ball_pos[1]:.1f},{confidence:.2f}"
        return message_str if len(message_str.encode("utf-8")) <= 20 else None

    # ---------------- Voting group logic ----------------
    def calculate_confidence_score(self, ball_pos, player_pos):
        '''Calculate confidence score based on distance to ball'''
        distance = np.linalg.norm(ball_pos[:2] - player_pos[:2])
        return max(1.0 / (distance + 1.0), 0.1)

    def get_current_communication_cycle(self):
        """Get the current communication cycle number"""
        return (self.world.time_local_ms // 40) // 11

    def last_agent_in_cycle(self):
        """Check if the last agent (1) has broadcasted in the current cycle"""
        return any(entry["sender"] == 1 for entry in self.voting_group_list)
    
    def check_and_handle_cycle_completion(self):
        """Check if we've moved to a new cycle and handle completion of previous cycle"""
        new_cycle = self.get_current_communication_cycle()
        if new_cycle != self.current_cycle and self.current_cycle != -1 or self.last_agent_in_cycle():
            self.cycle_completed = True
            
        if self.cycle_completed:
            logging.info(f"[CYCLE_COMPLETE] Agent {self.r.unum} | Cycle {self.current_cycle} | "
                        f"Voting list: {self.voting_group_list}")
            
            self.voting_group_list = []
            self.cycle_completed = False
            logging.info(f"[RESET] t={self.world.time_local_ms} ms | Agent {self.r.unum} | "
                        f"Voting list reset for cycle {new_cycle}")
        
        self.current_cycle = new_cycle
    

    def update_local_voting_group(self):
        """Add own ball info to voting list if visible"""
        self.check_and_handle_cycle_completion()
        
        if self.world.ball_is_visible and self.world.ball_abs_pos is not None:
            entry = {
                "sender": self.r.unum,
                "ball_pos": self.world.ball_abs_pos[:2],
                "confidence": self.confidence
            }
            self.voting_group_list.append(entry)
        
        return self.voting_group_list

    def get_voting_group(self):
        return self.voting_group_list

    def turn_off_vision(self):
        group = self.get_voting_group()
        if group:
            agent_ids = set(group.keys())
            if self.r.unum in agent_ids:
                self.world.ball_is_visible = False

    def round_robin_communicator(self, current_time: int) -> int:
        """Return which agent ID owns the current slot"""
        cycle_position = (current_time // 40) % 11 
        return 11 - cycle_position   
    

    def should_broadcast(self)-> bool:
        """Checks if the current agent should broadcast"""
        current_time = self.world.time_local_ms
        slot_owner  = self.round_robin_communicator(current_time) 
        return self.r.unum == slot_owner
       
    def broadcast(self):
        """Broadcast ball info with confidence"""
        current_time = self.world.time_local_ms
        
        self.check_and_handle_cycle_completion()
        
        if self.should_broadcast() and current_time - self.last_broadcast_time >= self.broadcast_interval:
            if self.broadcast_ball_condition():
                self.confidence = self.calculate_confidence_score(self.world.ball_abs_pos, self.r.loc_head_position)
                ball_pos = self.get_ball_position()
                message_str = self.ball_position_to_message(ball_pos, self.confidence)
                if message_str:
                    self.commit_announcement(message_str.encode("utf-8"))
                   # logging.info(f"[BROADCAST] t={current_time} ms | Agent {self.r.unum} broadcast → {message_str}")
                    self.last_broadcast_time = current_time
            
                    self.voting_group_list.append({
                        "sender": self.r.unum,
                        "ball_pos": ball_pos[:2],
                        "confidence": self.confidence
                    })
                self.turn_off_vision  
                 
    def update_ball_weighted_average(self):
        """Update world ball position using weighted average from voting group"""
        if not self.voting_group_list:
            return
        total_confidence = sum(entry["confidence"] for entry in self.voting_group_list)
        if total_confidence == 0:
            return
        weighted_x = sum(entry["ball_pos"][0] * entry["confidence"] for entry in self.voting_group_list)
        weighted_y = sum(entry["ball_pos"][1] * entry["confidence"] for entry in self.voting_group_list)
        avg_x = weighted_x / total_confidence
        avg_y = weighted_y / total_confidence
        self.world.ball_abs_pos = np.array([avg_x, avg_y, 0.0])
        self.world.ball_abs_pos_last_update = self.world.time_local_ms
        self.world.ball_is_visible = True
        

    def receive(self, msg: bytearray):
        """Process a message delivered by the server"""
        self.check_and_handle_cycle_completion()
        
        decoded = msg.decode("utf-8")
        parts = decoded.split(":")
        if len(parts) != 3 or parts[0] != "B":
            return

        sender_unum = int(parts[1])
        coords_conf = list(map(float, parts[2].split(",")))
        ball_coords = tuple(coords_conf[:2])
        confidence = coords_conf[2]

        entry = {
            "sender": sender_unum,
            "ball_pos": ball_coords,
            "confidence": confidence
        }
    
        self.voting_group_list.append(entry)
        # logging.info(
        #     f"[RECEIVE] t={self.world.time_local_ms} ms | Agent {self.r.unum} received from {sender_unum}"
        # )
    