"""Independent controller simulator. Localhost by default; LAN is opt-in."""

import argparse
from collections import OrderedDict
import json
import socket
import threading

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


class ControllerServer:
    """One client at a time; callbacks contain observations, not UI operations."""

    def __init__(self, port=8765, bind="127.0.0.1", fault="none", on_event=None, controller=None):
        self.controller = controller if controller is not None else Controller()
        self.on_event = on_event or (lambda event: None)
        self.stopped = threading.Event()
        self.connection = None
        self.fault_lock = threading.Lock()
        self.fault = fault
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.listener.bind((bind, port))
            self.listener.listen(1)
            self.listener.settimeout(0.2)
            self.address = self.listener.getsockname()
        except OSError:
            self.listener.close()
            raise

    def emit(self, kind, **details):
        self.on_event({"kind": kind, **details})

    def arm_fault(self, fault):
        if fault not in FAULTS:
            raise ValueError("Unknown fault")
        with self.fault_lock:
            self.fault = fault

    def stop(self):
        self.stopped.set()
        if self.connection is not None:
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self.listener.close()

    def run(self):
        self.emit("listening", address=self.address)
        try:
            while not self.stopped.is_set():
                try:
                    connection, peer = self.listener.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self.stopped.is_set():
                        break
                    raise
                self.connection = connection
                if self.stopped.is_set():
                    connection.close()
                    break
                self.emit("connected", peer=peer)
                try:
                    with connection, connection.makefile("rb") as stream:
                        self.exchange(connection, stream)
                except OSError as exc:
                    if not self.stopped.is_set():
                        self.emit("error", text=str(exc))
                finally:
                    self.connection = None
                    self.emit("disconnected")
        finally:
            self.listener.close()
            self.emit("stopped")

    def exchange(self, connection, stream):
        while not self.stopped.is_set() and (raw := stream.readline(MAX_FRAME + 1)):
            if len(raw) > MAX_FRAME:
                self.emit("error", text="Oversized frame; closing connection")
                return
            try:
                request = decode(raw)
                validate_request(request)
                self.emit("received", message=request)
                response = self.controller.handle(request)
                self.emit("state", message=response)
            except ProtocolError as exc:
                self.emit("error", text=str(exc))
                connection.sendall(encode({"v": 1, "error": str(exc)}))
                continue
            with self.fault_lock:
                fault = self.fault if request["command"] == "OPEN" else "none"
                if fault != "none":
                    self.fault = "none"
            # State changes precede fault injection: a lost reply is ambiguous.
            if fault != "none":
                self.emit("fault", fault=fault, message=request)
                if fault == "timeout":
                    continue
                if fault == "disconnect":
                    return
                if fault == "malformed":
                    connection.sendall(b"{not-json}\n")
                    continue
                if fault == "wrong-id":
                    response = {**response, "id": "unrelated-response"}
            connection.sendall(encode(response))
            self.emit("sent", message=response)


def serve(port=8765, fault="none", bind="127.0.0.1"):
    server = ControllerServer(port=port, bind=bind, fault=fault)
    print(json.dumps({"ready": True, "port": server.address[1], "bind": bind, "fault": fault}), flush=True)
    try:
        server.run()
    finally:
        server.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765, help="Local TCP port; 0 selects an unused port")
    parser.add_argument("--fault", choices=FAULTS, default="none")
    parser.add_argument("--bind", default="127.0.0.1", help="Use 0.0.0.0 to opt in to LAN connections")
    args = parser.parse_args()
    try:
        serve(args.port, args.fault, args.bind)
    except KeyboardInterrupt:
        pass
