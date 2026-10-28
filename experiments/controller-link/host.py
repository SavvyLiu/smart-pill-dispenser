"""Small host-side communication client; no dosing or medication logic."""

import argparse
import json
import math
import uuid

import serial

from protocol import MAX_FRAME, ProtocolError, decode, encode, validate_request, validate_response


class LinkError(RuntimeError):
    pass


class ResponseTimeout(LinkError):
    pass


class UnresolvedOperation(LinkError):
    pass


class Client:
    def __init__(self, port, timeout=1.0, baudrate=115200):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Timeout must be a positive finite number")
        self.port, self.timeout, self.baudrate = port, timeout, baudrate
        self.connection = None
        self.unresolved = set()
        self.events = []

    def connect(self):
        self.close()
        self.connection = serial.serial_for_url(
            self.port, baudrate=self.baudrate, timeout=self.timeout, write_timeout=self.timeout
        )
        return self

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, *args):
        self.close()

    def command(self, command, compartment="compartment_1", request_id=None):
        request = {"v": 1, "id": request_id or uuid.uuid4().hex, "command": command, "compartment": compartment}
        validate_request(request)
        if command != "STATUS" and compartment in self.unresolved:
            raise UnresolvedOperation("Outcome unresolved: query STATUS before another operation")
        if self.connection is None:
            raise LinkError("Connect before sending a command")
        try:
            self.events.append({"direction": "TX", "message": request})
            raw = encode(request)
            if self.connection.write(raw) != len(raw):
                raise LinkError("Incomplete write")
            response_raw = self.connection.read_until(b"\n", MAX_FRAME + 1)
            if not response_raw:
                raise ResponseTimeout("No reply before timeout; operation outcome is unknown")
            self.events.append({"direction": "RX", "raw": response_raw.decode("utf-8", errors="replace")})
            response = decode(response_raw)
            validate_response(response, request)
        except (serial.SerialException, OSError, ProtocolError, LinkError) as exc:
            if command != "STATUS":
                self.unresolved.add(compartment)
            # Discard this stream after an error: a late or partial reply cannot be
            # mistaken for the next command's response. Never retry a command here.
            self.close()
            if isinstance(exc, (ProtocolError, LinkError)):
                raise
            raise LinkError(f"Connection failed: {exc}") from exc
        if command == "STATUS":
            self.unresolved.discard(compartment)
        return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="socket://127.0.0.1:8765")
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--command", choices=("OPEN", "CLOSE", "STATUS"), default="STATUS")
    parser.add_argument("--compartment", default="compartment_1")
    args = parser.parse_args()
    try:
        with Client(args.port, args.timeout, args.baudrate) as client:
            print(json.dumps(client.command(args.command, args.compartment), indent=2))
    except (LinkError, ProtocolError, serial.SerialException, ValueError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
