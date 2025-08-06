from world.World import World

class Communicate:
    """
    A simple test communication system where one agent broadcasts a message,
    and others print what they hear.
    """
    def __init__(self, world: World, commit_announcement) -> None:
        self.world = world
        self.commit_announcement = commit_announcement

    def broadcast(self):
        msg = "HelloWorld"
        self.commit_announcement(msg.encode())  # Send say message
        print(f"[Agent {self.world.robot.unum}] Broadcasted: {msg}")

    def receive(self, msg: bytearray):
        decoded = msg.decode("utf-8")
        print(f"Agent {self.world.robot.unum} received message: {decoded}")

