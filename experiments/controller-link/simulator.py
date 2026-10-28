"""Independent controller process, bound only to localhost."""

import argparse
from collections import OrderedDict
import json
import socket

from protocol import MAX_FRAME, ProtocolError, decode, encode, validate_request

FAULTS = ("none", "timeout", "malformed", "wrong-id", "disconnect")


class Controller:
    def __init__(self):
        self.states = {f"compartment_{i}": "CLOSED" for i in range(1, 7)}
        self.actuation_count = 0
        self.history = OrderedDict()

    def handle(self, request):
        validate_request(request)
        request_id = request["id"]
        if request_id in self.history:
            original, response = self.history[request_id]
            if original != request:
                raise ProtocolError("Request ID reused with a different payload")
            return dict(response)
        command, compartment = request["command"], request["compartment"]
        desired = {"OPEN": "OPENED", "CLOSE": "CLOSED"}.get(command)
        if desired is not None and self.states[compartment] != desired:
            self.states[compartment] = desired
            self.actuation_count += 1
        response = {**request, "state": self.states[compartment], "actuation_count": self.actuation_count}
        self.history[request_id] = (dict(request), dict(response))
        # Bounded, process-local replay cache; not a physical exactly-once guarantee.
        if len(self.history) > 256:
            self.history.popitem(last=False)
        return response


def serve(port=8765, fault="none"):
    controller = Controller()
    fault_used = False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", port))
        server.listen(1)
        print(json.dumps({"ready": True, "port": server.getsockname()[1], "fault": fault}), flush=True)
        while True:
            connection, _ = server.accept()
            with connection, connection.makefile("rb") as stream:
                while raw := stream.readline(MAX_FRAME + 1):
                    if len(raw) > MAX_FRAME:
                        break  # Close an oversized stream rather than lose frame boundaries.
                    try:
                        request = decode(raw)
                        response = controller.handle(request)
                    except ProtocolError as exc:
                        connection.sendall(encode({"v": 1, "error": str(exc)}))
                        continue
                    # Apply one fault AFTER the first OPEN is processed. A lost reply
                    # must not be interpreted as proof that nothing happened.
                    if not fault_used and request["command"] == "OPEN" and fault != "none":
                        fault_used = True
                        if fault == "timeout":
                            continue
                        if fault == "disconnect":
                            break
                        if fault == "malformed":
                            connection.sendall(b"{not-json}\n")
                            continue
                        if fault == "wrong-id":
                            response = {**response, "id": "unrelated-response"}
                    try:
                        connection.sendall(encode(response))
                    except (BrokenPipeError, ConnectionResetError):
                        break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765, help="Local TCP port; 0 selects an unused port")
    parser.add_argument("--fault", choices=FAULTS, default="none")
    args = parser.parse_args()
    try:
        serve(args.port, args.fault)
    except KeyboardInterrupt:
        pass
