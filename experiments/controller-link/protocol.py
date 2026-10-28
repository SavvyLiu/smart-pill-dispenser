"""Proposed lab protocol. This is not an agreed firmware interface."""

import json
import re

MAX_FRAME = 512
COMMANDS = {"OPEN", "CLOSE", "STATUS"}
COMPARTMENTS = {f"compartment_{i}" for i in range(1, 7)}


class ProtocolError(ValueError):
    pass


def encode(message):
    raw = (json.dumps(message, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    if len(raw) > MAX_FRAME:
        raise ProtocolError("Frame exceeds 512 bytes")
    return raw


def decode(raw):
    if len(raw) > MAX_FRAME or not raw.endswith(b"\n"):
        raise ProtocolError("Expected a complete newline-terminated frame of at most 512 bytes")
    try:
        message = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ProtocolError("Invalid UTF-8 or JSON") from exc
    if not isinstance(message, dict):
        raise ProtocolError("Expected a JSON object")
    return message


def validate_request(message):
    if set(message) != {"v", "id", "command", "compartment"}:
        raise ProtocolError("Unexpected request fields")
    if type(message["v"]) is not int or message["v"] != 1:
        raise ProtocolError("Unsupported protocol version")
    if not isinstance(message["id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", message["id"]):
        raise ProtocolError("Invalid request ID")
    if not isinstance(message["command"], str) or message["command"] not in COMMANDS:
        raise ProtocolError("Unknown command")
    if not isinstance(message["compartment"], str) or message["compartment"] not in COMPARTMENTS:
        raise ProtocolError("Unknown compartment")


def validate_response(message, request):
    if set(message) != {*request, "state", "actuation_count"}:
        raise ProtocolError("Unexpected response fields")
    for field, expected in request.items():
        if type(message[field]) is not type(expected) or message[field] != expected:
            raise ProtocolError(f"Response {field} does not match the request")
    if message["state"] not in ("OPENED", "CLOSED"):
        raise ProtocolError("Unknown compartment state")
    if type(message["actuation_count"]) is not int or message["actuation_count"] < 0:
        raise ProtocolError("Invalid actuation count")
    expected = {"OPEN": "OPENED", "CLOSE": "CLOSED"}.get(request["command"])
    if expected is not None and message["state"] != expected:
        raise ProtocolError("Response state does not confirm the requested operation")
