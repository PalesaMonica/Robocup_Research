from world.World import World
import numpy as np
import logging
import math
import os

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
        self.broadcasted_this_cycle = False
        self.message_sent_count = 0
        self.message_received_count = 0

       
        # ------------------ Logging setup per agent ------------------
        log_dir = "agent_logs"
        os.makedirs(log_dir, exist_ok=True)

        self.logger = logging.getLogger(f"Agent_{self.r.unum}")
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            # Main log (all levels, but INFO is minimum)
            fh_main = logging.FileHandler(f"{log_dir}/agent_{self.r.unum}.log",mode="w")
            fh_main.setLevel(logging.INFO)
            fh_main.setFormatter(logging.Formatter("%(asctime)s %(message)s"))

            # Error log (only WARNING and ERROR)
            fh_error = logging.FileHandler(f"{log_dir}/agent_{self.r.unum}_errors.log",mode="w")
            fh_error.setLevel(logging.WARNING)
            fh_error.setFormatter(logging.Formatter("%(asctime)s  %(message)s"))

            # Add handlers
            self.logger.addHandler(fh_main)
            self.logger.addHandler(fh_error)

    # ---------------- Ball state helpers ----------------
    def get_server_time(self):
        ''' Returns the current server time in milliseconds. '''
        return int(self.world.time_game * 1000)   
    
    def get_local_time(self):
        ''' Returns the local time in milliseconds. '''
        return self.world.time_local_ms

    def get_ball_position(self):
        ''' Returns the absolute ball position if visible, else None. '''
        return self.world.ball_abs_pos[:2] if self.world.ball_is_visible else None

    def broadcast_ball_condition(self) -> bool:
        ''' Determines if the ball position should be broadcasted. '''
        ball_pos = self.get_ball_position()
        if ball_pos is None:
            return False
        x, y = ball_pos[:2]
        return -15 <= x <= 15 and -10 <= y <= 10

    def ball_position_to_message(self, ball_pos, confidence):
        ''' Converts ball position and confidence to a formatted message string. '''
        if ball_pos is None:
            return None
        try:
            unum = self.r.unum
            x = round(float(ball_pos[0]), 2)
            y = round(float(ball_pos[1]), 2)
            c = round(float(confidence), 2)  

            message_str = f"A{unum}:{x},{y},{c}"

            if len(message_str) > 20:
                return None
            if any(ch in message_str for ch in [' ', '(', ')', '"', "'", '\\']):
                return None
            if message_str.startswith(";"):
                return None
            return message_str
        except (ValueError, TypeError):
            return None

    # ---------------- Voting logic ----------------
    def calculate_confidence_score(self, ball_pos, player_pos):
        ''' Calculates confidence score based on distance between ball and player. '''
        try:
            ball_pos = np.array(ball_pos, dtype=float)
            player_pos = np.array(player_pos, dtype=float)
            distance = np.linalg.norm(ball_pos[:2] - player_pos[:2])
            return max(1.0 / (distance + 1.0), 0.1)
        except (ValueError, TypeError):
            return 0.1

    def get_current_communication_cycle(self):
        ''' Determines the current communication cycle based on server time. '''
        try:
            return self.get_server_time() // (self.players * self.broadcast_interval)
        except (ZeroDivisionError, TypeError):
            return 0
    
    def check_and_handle_cycle_completion(self):
        ''' Checks if a communication cycle has completed and handles resets. '''
        new_cycle = self.get_current_communication_cycle()
        if new_cycle != self.current_cycle:
            if self.current_cycle != -1:
                self.logger.info(
                    f"[CYCLE_COMPLETE] Cycle {self.current_cycle} | "
                    f"Messages Sent: {self.message_sent_count} | "
                    f"Messages Received: {self.message_received_count}"
                )
                self.update_ball_weighted_average()
                self.voting_group_list = []
                self.logger.info(f"[RESET] Voting list reset for cycle {new_cycle}")
            self.current_cycle = new_cycle
            self.broadcasted_this_cycle = False
            self.message_sent_count = 0
            self.message_received_count = 0

    def add_to_voting_group(self, sender_id, ball_pos, confidence):
        ''' Adds a ball position and confidence from a sender to the voting group. '''
        try:
            if ball_pos is None or len(ball_pos) < 2:
                return
            ball_array = np.round(np.array([float(ball_pos[0]), float(ball_pos[1])], dtype=float), 2)
            confidence = round(float(confidence), 2)
            for entry in self.voting_group_list:
                if entry["sender"] == sender_id:
                    return
            entry = {"sender": sender_id, "ball_pos": ball_array, "confidence": confidence}
            self.voting_group_list.append(entry)
        except (ValueError, TypeError, IndexError) as e:
            self.logger.warning(f"[VOTING_ERROR] Failed to add to voting group: {e}")

    # ---------------- Communication Logic ----------------
    def round_robin_communicator(self, current_time: int) -> int:
        ''' Determines which player should broadcast at the given time. '''
        try:
            # Shift by half-interval to avoid boundary overlap
            cycle_position = (current_time // self.broadcast_interval) % self.players
            return self.players - cycle_position
        except (ZeroDivisionError, TypeError):
            return 0

    def should_broadcast_at_time(self, server_time: int) -> bool:
        ''' Checks if this agent should broadcast at the current server time. '''
        try:
            slot_owner = self.round_robin_communicator(server_time) 
            return self.r.unum == slot_owner
        except AttributeError:
            return False
       
    def broadcast(self):
        ''' Broadcasts the ball position if conditions are met. '''
        try:
            server_time = self.get_server_time()  
            local_time = self.get_local_time()    
            self.check_and_handle_cycle_completion()
           
            if (self.should_broadcast_at_time(server_time) and 
                local_time - self.last_broadcast_time >= self.broadcast_interval):
                if self.broadcasted_this_cycle:
                    return
        
                if self.broadcast_ball_condition():
                    ball_pos = self.get_ball_position()
                    if ball_pos is not None:
                        self.confidence = self.calculate_confidence_score(
                            ball_pos, self.r.loc_head_position
                        )
                        message_str = self.ball_position_to_message(ball_pos, self.confidence)
                        if message_str is not None:
                            self.commit_announcement(message_str.encode("utf-8"))
                            self.message_sent_count += 1
                            self.add_to_voting_group(self.r.unum, ball_pos, self.confidence)
                            self.last_broadcast_time = local_time 
                            self.broadcasted_this_cycle = True
        except Exception as e:
            self.logger.error(f"[BROADCAST_ERROR] Agent {getattr(self.r, 'unum', 'unknown')} | {e}")

    def validate_ball_estimated(self, ball_pos):
        """This is to validate that the estimated ball position is within the field boundaries."""
        field_x_min, field_x_max = -15.0, 15.0
        field_y_min, field_y_max = -10.0, 10.0
        try:
            ball_x = float(ball_pos[0])
            ball_y = float(ball_pos[1])
            return field_x_min <= ball_x <= field_x_max and field_y_min <= ball_y <= field_y_max
        except (ValueError, TypeError, IndexError):
            return False

    def update_ball_weighted_average(self):
        ''' Updates the ball position using a weighted average from voting group. '''
        if not self.voting_group_list:
            return
        try:
            group_sorted = sorted(self.voting_group_list, key=lambda e: e["sender"])

            power = 2.0
            total_confidence = math.fsum(entry["confidence"] ** power for entry in group_sorted)
            if total_confidence == 0:
                return

            weighted_x = math.fsum(entry["ball_pos"][0] * (entry["confidence"] ** power) for entry in group_sorted)
            weighted_y = math.fsum(entry["ball_pos"][1] * (entry["confidence"] ** power) for entry in group_sorted)
            avg_x = weighted_x / total_confidence
            avg_y = weighted_y / total_confidence

            # Validate before updating
            if not self.validate_ball_estimated([avg_x, avg_y]):
                self.logger.warning(
                    f"[BALL_UPDATE_INVALID] Agent {self.r.unum} | "
                    f"Estimated Ball=[{avg_x:.2f}, {avg_y:.2f}] is out of bounds."
                )
                return

            # Find previous ball position sent by this agent
            prev_ball_pos = None
            for entry in group_sorted:
                if entry["sender"] == self.r.unum:
                    prev_ball_pos = entry["ball_pos"]
                    break

            # Get actual ball position from vision if available
            actual_ball_pos = None
            if self.world.ball_is_visible:
                actual_ball_pos = self.world.ball_abs_pos[:2]

            if not self.world.ball_is_visible:
                # Only update if ball is not visible
                self.world.ball_abs_pos = np.array([avg_x, avg_y, 0.0])
                self.world.ball_abs_pos_last_update = self.get_local_time()
                self.world.is_ball_abs_pos_from_vision = False

            agent_position = self.r.loc_head_position[:2]
            self.logger.info(
                f"[BALL_UPDATE] Agent {self.r.unum} | "
                f"Sent ball={f'({round(prev_ball_pos[0], 2)}, {round(prev_ball_pos[1], 2)})' if prev_ball_pos is not None else 'N/A'} | "
                f"Vision Ball={f'({round(actual_ball_pos[0], 2)}, {round(actual_ball_pos[1], 2)})' if actual_ball_pos is not None else 'N/A'} | "
                f"Estimated Ball=[{avg_x:.2f}, {avg_y:.2f}] "
                f"Agent Pos=({round(agent_position[0], 2)}, {round(agent_position[1], 2)})"
            )
        except Exception as e:
            self.logger.error(f"[BALL_UPDATE_ERROR] Agent {getattr(self.r, 'unum', 'unknown')} | {e}")

    def receive(self, msg: bytearray):
        ''' Processes a received message containing ball position data. '''
        self.check_and_handle_cycle_completion()
        decoded = msg.decode("utf-8")
        if not decoded.startswith("A"):
            return
        try:
            if ":" not in decoded:
                self.logger.warning(f"[RECEIVE_ERROR] Invalid message format: {decoded}")
                return
            header, coords = decoded[1:].split(":", 1)
            sender_unum = int(header)

            coord_parts = coords.split(",")
            if len(coord_parts) != 3:
                self.logger.warning(f"[RECEIVE_ERROR] Invalid coordinates format: {coords}")
                return
                
            x_str, y_str, c_str = coord_parts
            ball_coords = np.array([float(x_str), float(y_str)], dtype=float)
            confidence = float(c_str)
            self.message_received_count += 1
            self.add_to_voting_group(sender_unum, ball_coords, confidence)
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"[RECEIVE_ERROR] Failed to process message '{decoded}': {e}")
