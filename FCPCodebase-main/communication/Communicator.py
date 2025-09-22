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
np.set_printoptions(precision=2, suppress=True, floatmode="fixed")

class Communicator:
    def __init__(self, world: World, commit_announcement) -> None:
        self.world = world
        self.commit_announcement = commit_announcement
        self.last_broadcast_time = 0
        self.last_global_update = 0
        self.broadcast_interval = 40   # ms
        self.r = world.robot
        self.voting_group_list = []
        self.teammate = world.teammates
        self.confidence = 0.0
        self.last_reset_cycle = -1  
        self.cycle_completed = False 
        self.current_cycle = -1
        self.players = 11

    # ---------------- Ball state helpers ----------------
    def is_ball_data_fresh(self, max_age_ms=40):
        """Check data freshness using local time (for consistent interval measurement)"""
        return (self.get_local_time() - self.world.ball_abs_pos_last_update) <= max_age_ms

    def get_server_time(self):
        """server game time converted to milliseconds for synchronization between agents"""
        return int(self.world.time_game * 1000)   
    
    def get_local_time(self):
        """Use local simulation time for interval timing and local operations"""
        return self.world.time_local_ms

    def get_ball_position(self):
        """Returns ball position if visible, else None"""
        return self.world.ball_abs_pos[:2] if self.world.ball_is_visible else None

    def broadcast_ball_condition(self) -> bool:
        """Check if ball is visible and within field boundaries"""
        ball_pos = self.get_ball_position()
        if ball_pos is None:
            return False
        x, y = ball_pos[:2]
        return -15 <= x <= 15 and -10 <= y <= 10

    def ball_position_to_message(self, ball_pos, confidence):
        """Convert ball position to safe message string"""
        if ball_pos is None:
            return None

        unum = self.r.unum
        x = round(float(ball_pos[0]), 2)
        y = round(float(ball_pos[1]), 2)
        c = int(confidence * 100)  

        message_str = f"A{unum}:{x},{y},{c}"

        # Safety: enforce constraints
        if len(message_str) > 20:
            return None
        if any(ch in message_str for ch in [' ', '(', ')', '"', "'", '\\']):
            return None
        if message_str.startswith(";"):
            return None

        return message_str

    # ---------------- Voting logic ----------------
    def calculate_confidence_score(self, ball_pos, player_pos):
        """Calculate confidence score based on distance to ball"""
        ball_pos = np.array(ball_pos, dtype=float)
        player_pos = np.array(player_pos, dtype=float)
        distance = np.linalg.norm(ball_pos[:2] - player_pos[:2])
        return max(1.0 / (distance + 1.0), 0.1)

    def get_current_communication_cycle(self):
        """Get the current communication cycle number using server time"""
        return (self.get_server_time() // 40) // self.players
    
    def check_and_handle_cycle_completion(self):
        """Check if we've moved to a new cycle and handle completion of previous cycle"""
        new_cycle = self.get_current_communication_cycle()
        
        # Only process cycle completion once per cycle transition
        if new_cycle != self.current_cycle:
            if self.current_cycle != -1:  # Don't log for initial cycle
                logging.info(f"[CYCLE_COMPLETE] Agent {self.r.unum} | Cycle {self.current_cycle} | "
                            f"Server time: {self.get_server_time()} | "
                            f"Voting list: {self.voting_group_list}")
                # Update ball position based on voting results
                self.update_ball_weighted_average()
                # Reset voting list for new cycle
                self.voting_group_list = []
                
                logging.info(f"[RESET] server_t={self.get_server_time()} local_t={self.get_local_time()} ms | "
                           f"Agent {self.r.unum} | Voting list reset for cycle {new_cycle}")
            
            self.current_cycle = new_cycle

    def add_to_voting_group(self, sender_id, ball_pos, confidence):
        """Single source of truth for adding entries to voting list"""
        ball_array = np.round(np.array([
            float(ball_pos[0]),
            float(ball_pos[1])
        ], dtype=float), 2)

        confidence = round(float(confidence), 2)
        if not any(entry["sender"] == sender_id for entry in self.voting_group_list):
            entry = {
                "sender": sender_id,
                "ball_pos": ball_array,
                "confidence": confidence
            }
            self.voting_group_list.append(entry)

       
    def update_local_voting_group(self):
        """Add own ball info to voting list if visible"""
        self.check_and_handle_cycle_completion()
        
        if self.broadcast_ball_condition():
            ball_pos = self.get_ball_position()
            self.confidence = self.calculate_confidence_score(ball_pos, self.r.loc_head_position)
            self.add_to_voting_group(self.r.unum, ball_pos, self.confidence)
        
        return self.voting_group_list

    def get_voting_group(self):
        return self.voting_group_list

    # ----------------------------Communication Logic----------------------------
    def round_robin_communicator(self, current_time: int) -> int:
        """Return which agent ID owns the current slot"""
        cycle_position = (current_time // 40) % self.players
        return self.players - cycle_position   
    
    def should_broadcast_at_time(self, server_time: int) -> bool:
        """Checks if the current agent should broadcast using server time for synchronization"""
        slot_owner = self.round_robin_communicator(server_time) 
        return self.r.unum == slot_owner
       
    def should_broadcast(self) -> bool:
        """Checks if the current agent should broadcast using server time"""
        return self.should_broadcast_at_time(self.get_server_time())
       
    def broadcast(self):
        """Broadcast ball info with confidence"""
        server_time = self.get_server_time()  
        local_time = self.get_local_time()    
        
        self.check_and_handle_cycle_completion()
        
        if self.should_broadcast_at_time(server_time) and local_time - self.last_broadcast_time >= self.broadcast_interval:
            if self.broadcast_ball_condition():
                self.confidence = self.calculate_confidence_score(self.world.ball_abs_pos, self.r.loc_head_position)
                ball_pos = self.get_ball_position()
                message_str = self.ball_position_to_message(ball_pos, self.confidence)
                if message_str :
                    self.commit_announcement(message_str.encode("utf-8"))
                    self.last_broadcast_time = local_time 

                    self.add_to_voting_group(self.r.unum, ball_pos, self.confidence)
                 
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
        self.world.ball_abs_pos_last_update = self.get_local_time() 
        self.world.is_ball_abs_pos_from_vision = False  

        logging.info(f"[BALL_UPDATE] Agent {self.r.unum} | New ball pos: {self.world.ball_abs_pos[:2]}")

    def receive(self, msg: bytearray):
        """Process a message delivered by the server"""
        self.check_and_handle_cycle_completion()
        
        try:
            decoded = msg.decode("utf-8")
            if not decoded.startswith("A"):
                return
            
            header, coords = decoded[1:].split(":", 1)
            sender_unum = int(header)

            x_str, y_str, c_str = coords.split(",")
            ball_coords = np.array([float(x_str), float(y_str)], dtype=float)
            confidence = float(c_str) / 100.0  

            self.add_to_voting_group(sender_unum, ball_coords, confidence)

        except Exception as e:
            logging.warning(f"[RECEIVE_ERROR] Agent {self.r.unum} failed to parse message: {decoded} | {e}")