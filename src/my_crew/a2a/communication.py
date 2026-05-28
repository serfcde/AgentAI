from my_crew.a2a.message import AgentMessage


class CommunicationBus:

    def __init__(self):

        self.messages = []

    def send_message(self, sender, receiver, content):

        message = AgentMessage(
            sender,
            receiver,
            content
        )

        self.messages.append(message)

        print(message)

    def get_messages(self):

        return self.messages