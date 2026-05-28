class AgentMessage:

    def __init__(self, sender, receiver, content):

        self.sender = sender

        self.receiver = receiver

        self.content = content

    def __str__(self):

        return (
            f"\n[{self.sender} → {self.receiver}]\n"
            f"{self.content}\n"
        )