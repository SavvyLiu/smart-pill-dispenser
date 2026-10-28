import socket
import unittest

from demo import CASES
from host import Client
from protocol import MAX_FRAME, ProtocolError, decode, encode, validate_request, validate_response
from simulator import Controller


def request(command="OPEN", request_id="test-1"):
    return {"v": 1, "id": request_id, "command": command, "compartment": "compartment_1"}


class ProtocolTests(unittest.TestCase):
    def test_fragmented_and_coalesced_frames(self):
        # Byte streams can split one frame or combine several writes. Verify the
        # actual simulator's reader, independently of the pySerial client.
        from demo import simulator
        with simulator() as port:
            host, number = port.removeprefix("socket://").split(":")
            with socket.create_connection((host, int(number)), timeout=3) as connection:
                with connection.makefile("rb") as stream:
                    first = encode(request())
                    connection.sendall(first[:5])
                    connection.sendall(first[5:] + encode(request("CLOSE", "test-2")))
                    self.assertEqual(decode(stream.readline())["state"], "OPENED")
                    self.assertEqual(decode(stream.readline())["state"], "CLOSED")

    def test_bad_frames(self):
        for frame in (b"{}", b"[]\n", b"broken\n", b"\xff\n", b"a" * (MAX_FRAME + 1) + b"\n"):
            with self.subTest(frame=frame[:20]), self.assertRaises(ProtocolError):
                decode(frame)

    def test_invalid_command_fields(self):
        for field, value in (("v", True), ("v", 2), ("id", ""), ("command", "DISPENSE"),
                             ("command", []), ("compartment", "compartment_99"), ("compartment", [])):
            with self.subTest(field=field, value=value), self.assertRaises(ProtocolError):
                validate_request({**request(), field: value})

    def test_id_collision_does_not_actuate(self):
        controller = Controller()
        controller.handle(request())
        with self.assertRaises(ProtocolError):
            controller.handle(request("CLOSE"))
        self.assertEqual(controller.states["compartment_1"], "OPENED")
        self.assertEqual(controller.actuation_count, 1)

    def test_status_is_read_only(self):
        controller = Controller()
        reply = controller.handle(request("STATUS"))
        self.assertEqual(reply["state"], "CLOSED")
        self.assertEqual(reply["actuation_count"], 0)

    def test_invalid_response_is_not_success(self):
        reply = Controller().handle(request())
        for field, value in (("id", "other"), ("command", "CLOSE"), ("compartment", "compartment_2"),
                             ("state", "CLOSED"), ("state", None), ("actuation_count", True)):
            with self.subTest(field=field, value=value), self.assertRaises(ProtocolError):
                validate_response({**reply, field: value}, request())

    def test_invalid_command_is_not_transmitted(self):
        client = Client("unused")
        with self.assertRaises(ProtocolError):
            client.command("DISPENSE")
        self.assertEqual(client.events, [])

    def test_replay_cache_is_bounded(self):
        controller = Controller()
        for i in range(300):
            controller.handle(request("STATUS", f"query-{i}"))
        self.assertEqual(len(controller.history), 256)

    def test_timeout_must_be_finite_and_positive(self):
        for value in (0, -1, float("inf"), float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Client("unused", timeout=value)


class ProcessIntegrationTests(unittest.TestCase):
    def test_demonstration_scenarios(self):
        for name, _, run in CASES:
            with self.subTest(name=name):
                result = run()
                self.assertTrue(result["wire_log"])


if __name__ == "__main__":
    unittest.main()
