from world.World import World

class Communicator():
    def __init__(self, world: World, commit_announcement) -> None:
        self.world = world
        self.commit_announcement = commit_announcement
        self.last_broadcast_time = 0
        self.broadcast_interval = 40 
        self.r = world.robot
   
    def can_send_message(self):
        player_positions=[2,6,9]
        if self.r.unum in player_positions:
            return True
        return False

    def broadcast(self):
        current_time = self.world.time_local_ms
        if self.can_send_message() and (current_time - self.last_broadcast_time >= self.broadcast_interval):
            msg ="HelloWorld"
            self.commit_announcement(msg.encode())
            self.last_broadcast_time = current_time
            print(f"[Agent {self.world.robot.unum}] Broadcasted: {msg}")
    
    def receive(self, msg: bytearray):
        decoded = msg.decode("utf-8")
        print(f"Agent {self.world.robot.unum} received message: {decoded}")
        