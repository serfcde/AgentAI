import json

from my_crew.a2a.message import AgentMessage


class A2AProtocol:

    @staticmethod
    def validate_message(message):

        required_fields = [
            "sender",
            "receiver",
            "content"
        ]

        for field in required_fields:

            if not hasattr(message, field):

                return False

        return True

    @staticmethod
    def serialize_message(message):

        try:

            message_data = {
                "sender": message.sender,
                "receiver": message.receiver,
                "content": message.content
            }

            return json.dumps(message_data, indent=2)

        except Exception as error:

            return f"Serialization Error: {str(error)}"

    @staticmethod
    def deserialize_message(message_json):

        try:

            data = json.loads(message_json)

            return AgentMessage(
                sender=data["sender"],
                receiver=data["receiver"],
                content=data["content"]
            )

        except Exception as error:

            return f"Deserialization Error: {str(error)}"