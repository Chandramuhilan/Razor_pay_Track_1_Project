"""
Real A2A Protocol Client using a2a-sdk 1.1.2.

Sends HTTP requests to the merchant agent's A2A endpoint using
real protobuf types: SendMessageRequest, Message, Part, Role.
Parses SendMessageResponse via google.protobuf.json_format.
"""

import logging
import httpx
from a2a.types import (
    SendMessageRequest,
    SendMessageResponse,
    Message,
    Part,
    Role,
)
from google.protobuf import json_format

logger = logging.getLogger(__name__)


class A2AClient:
    def __init__(self, merchant_url: str):
        self.merchant_url = merchant_url.rstrip("/")

    async def get_agent_card(self) -> dict:
        """GET /.well-known/agent.json — returns the merchant's real A2A AgentCard."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.merchant_url}/.well-known/agent.json")
            resp.raise_for_status()
            return resp.json()

    async def send_message(self, text: str, context_id: str = None) -> dict:
        """
        Sends a real A2A SendMessageRequest to the merchant agent.

        Builds protobuf Message with Part.text, serializes via MessageToDict,
        POSTs to /api/a2a/message, returns the raw JSON response dict.
        """
        # Build real protobuf objects
        part = Part()
        part.text = text

        msg = Message()
        msg.role = Role.Value("ROLE_USER")
        msg.parts.append(part)
        if context_id:
            msg.context_id = context_id

        req = SendMessageRequest()
        req.message.CopyFrom(msg)

        req_dict = json_format.MessageToDict(
            req,
            preserving_proto_field_name=False,
            always_print_fields_with_no_presence=False,
        )

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.merchant_url}/api/a2a/message",
                json=req_dict,
            )
            resp.raise_for_status()
            return resp.json()

    async def check_merchant_online(self) -> bool:
        """Returns True if merchant agent is reachable."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.merchant_url}/.well-known/agent.json")
                return resp.status_code == 200
        except Exception:
            return False
