from world.World import World

class Communicate():
    def __init__(self, world: World, commit_announcement) -> None:
        self.world = world
        self.commit_announcement = commit_announcement
        self.last_broadcast_time = 0
        self.broadcast_interval = 40 
   
    def broadcast(self, message=None):
        current_time = self.world.time_local_ms
        if message or (current_time - self.last_broadcast_time > self.broadcast_interval):
            msg = message or "HelloWorld"
            self.commit_announcement(msg.encode())
            self.last_broadcast_time = current_time
            print(f"[Agent {self.world.robot.unum}] Broadcasted: {msg}")
    
    def receive(self, msg: bytearray):
        decoded = msg.decode("utf-8")
        print(f"Agent {self.world.robot.unum} received message: {decoded}")