import inspect
from typing import Text, Callable, Awaitable, Any

from rasa.core.channels.channel import (
    InputChannel,
    CollectingOutputChannel,
    OutputChannel,
    UserMessage,
)
from sanic import Blueprint, response
from sanic.request import Request
from sanic.response import HTTPResponse

from niceday_client.niceday_client import NicedayClient


class NicedayOutputChannel(OutputChannel):
    def __init__(self):
        self.niceday_client = NicedayClient()

    def name(self) -> Text:
        return "niceday_output_channel"

    async def send_text_message(
        self, recipient_id: Text, text: Text, **kwargs: Any
    ) -> None:
        """Send a message through this channel."""
        for message_part in text.strip().split("\n\n"):
            self.niceday_client.post_message(int(recipient_id), message_part)


class NicedayInputChannel(InputChannel):
    def __init__(self):
        self.output_channel = NicedayOutputChannel()

    def name(self) -> Text:
        return "niceday_input_channel"

    def blueprint(self, on_new_message: Callable[[UserMessage], Awaitable[None]]) -> Blueprint:
        custom_webhook = Blueprint(
            "custom_webhook_{}".format(type(self).__name__),
            inspect.getmodule(self).__name__,
        )

        @custom_webhook.route("/", methods=["GET"])
        async def health(request: Request) -> HTTPResponse:
            return response.json({"status": "ok"})

        @custom_webhook.route("/webhook", methods=["POST"])
        async def receive(request: Request) -> HTTPResponse:
            sender_id = request.json.get("sender")  # method to get sender_id
            text = request.json.get("message")  # method to fetch text

            collector = self.get_output_channel()
            await on_new_message(
                UserMessage(text, collector, sender_id, input_channel=self.name())
            )
            return response.text("success")

        return custom_webhook

    def get_output_channel(self) -> OutputChannel:
        return self.output_channel
