import inspect
import os
import typing
from typing import Text, Callable, Awaitable, Any, Dict, List
import logging

from rasa.core.channels.channel import InputChannel, UserMessage, CollectingOutputChannel, OutputChannel
from sanic import Blueprint, response
from sanic.request import Request
from sanic.response import HTTPResponse

from niceday_client import NicedayClient


#NICEDAY_API_URL = os.getenv('NICEDAY_API_ENDPOINT')
NICEDAY_API_URL = "http://niceday_api:8080/"


class NicedayOutputChannel(CollectingOutputChannel):
    """
    Output channel that sends messages to Niceday server
    """

    @classmethod
    def name(cls) -> Text:
        return "niceday_output_channel"

    def _message(self, # pylint: disable=too-many-arguments, arguments-renamed
                 recipient_id: typing.Optional[str],
                 text: typing.Optional[str] = None,
                 image: typing.Optional[str] = None,
                 buttons: typing.Optional[List[Dict[str, Any]]] = None,
                 attachment: typing.Optional[str] = None,
                 custom: typing.Optional[Dict[str, Any]] = None
                 ) -> Dict:
        msg_metadata = None
        logging.info("sending message in method _message")
        if custom is not None:
            text = custom["text"]
            msg_metadata = custom["attachmentIds"]
            custom = None
        obj = {
            "recipient_id": recipient_id,
            "text": text,
            "image": image,
            "buttons": buttons,
            "attachment": attachment,
            "custom": custom,
            "metadata": msg_metadata
        }

        # filter out any values that are `None`
        return {k: v for k, v in obj.items() if v is not None}

class NicedayTriggerOutputChannel(OutputChannel):
    """
    Output channel that sends messages to Niceday server
    """
    def __init__(self):
        self.niceday_client = NicedayClient(niceday_api_uri=NICEDAY_API_URL)

    @classmethod
    def name(cls) -> Text:
        return "niceday_trigger_output_channel"

    async def send_text_message(
        self, recipient_id: Text, text: Text, **kwargs: Any
    ) -> None:
        """Send a message through this channel."""
        logging.info("sending a message")
        for message_part in text.strip().split("\n\n"):
            self.niceday_client.post_message(int(recipient_id), message_part)

class NicedayInputChannel(InputChannel):
    """
    Custom input channel for communication with Niceday server. Instead of directly returning the
    bot messages to the HTTP request that sends the message, it will use NicedayOutputChannel as
    a callback as soon as the rasa response is ready.
    """
    def __init__(self):
        self.output_channel = NicedayTriggerOutputChannel()

    @classmethod
    def name(cls) -> Text:
        return "niceday_input_channel"

    def blueprint(self, on_new_message: Callable[[UserMessage], Awaitable[None]]) -> Blueprint:
        custom_webhook = Blueprint(
            f"custom_webhook_{type(self).__name__}",
            inspect.getmodule(self).__name__,
        )

        @custom_webhook.route("/", methods=["GET"])
        async def health(request: Request) -> HTTPResponse:  # pylint: disable=unused-argument
            return response.json({"status": "ok"})

        @custom_webhook.route("/webhook", methods=["POST"])
        async def receive(request: Request) -> HTTPResponse:
            sender_id = request.json.get("sender")  # method to get sender_id
            text = request.json.get("message")  # method to fetch text
            metadata = request.json.get("metadata")
            collector = self.get_output_channel()
            await on_new_message(
                UserMessage(text,
                            collector,
                            sender_id,
                            input_channel=self.name(),
                            metadata=metadata)
            )
            return response.json(collector.messages)

        return custom_webhook

    def get_output_channel(self) -> CollectingOutputChannel:
        """
        Register output channel. This is the output channel that is used when calling the
        'trigger_intent' endpoint.
        """
        return NicedayTriggerOutputChannel()
