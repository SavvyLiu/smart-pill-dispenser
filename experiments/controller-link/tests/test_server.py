import queue
import socket
import threading
import unittest

from host import Client, ResponseTimeout
from simulator import Controller, ControllerServer


class VisualServerTests(unittest.TestCase):
    def start_server(self, **kwargs):
        events = queue.Queue()
        server = ControllerServer(port=0, on_event=events.put, **kwargs)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        self.addCleanup(lambda: self.shutdown(server, thread))
        return server, events

    def shutdown(self, server, thread):
        server.stop()
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive(), "Listener did not stop")

    def connect(self, server):
        client = Client(f"socket://127.0.0.1:{server.address[1]}", timeout=0.2)
        self.addCleanup(client.close)
        client.connect()
        return client

    def test_default_is_localhost(self):
        server, _ = self.start_server()
        self.assertEqual(server.address[0], "127.0.0.1")

    def test_events_follow_real_messages(self):
        server, events = self.start_server()
        client = self.connect(server)
        response = client.command("OPEN", request_id="visible-123")
        client.close()
        seen = []
        while not seen or seen[-1]["kind"] != "disconnected":
            seen.append(events.get(timeout=3))
        messages = [e for e in seen if e["kind"] in ("received", "state", "sent")]
        self.assertEqual([e["kind"] for e in messages], ["received", "state", "sent"])
        self.assertTrue(all(e["message"]["id"] == "visible-123" for e in messages))
        self.assertEqual(response["state"], "OPENED")

    def test_rearming_drop_reply_and_reconnect(self):
        server, _ = self.start_server()
        client = self.connect(server)
        for i in range(2):
            server.arm_fault("timeout")
            with self.assertRaises(ResponseTimeout):
                client.command("OPEN", request_id=f"open-{i}")
            self.assertEqual(server.controller.states["compartment_1"], "OPENED")
            client.connect()
            self.assertEqual(client.command("STATUS")["state"], "OPENED")
            client.command("CLOSE")

    def test_stop_closes_active_connection(self):
        server, _ = self.start_server()
        client = self.connect(server)
        client.command("STATUS")
        server.stop()
        # Depending on the platform a closed stream returns EOF or raises.
        try:
            reply = client.connection.read(1)
        except OSError:
            pass
        else:
            self.assertEqual(reply, b"")

    def test_stop_start_can_preserve_model(self):
        model = Controller()
        first, _ = self.start_server(controller=model)
        client = self.connect(first)
        client.command("OPEN")
        first.stop()
        client.close()
        second, _ = self.start_server(controller=model)
        self.assertEqual(self.connect(second).command("STATUS")["state"], "OPENED")

    def test_reset_peer_does_not_kill_listener(self):
        server, _ = self.start_server()
        with socket.create_connection(server.address, timeout=2) as connection:
            connection.sendall(b"incomplete")
        client = self.connect(server)
        self.assertEqual(client.command("STATUS")["state"], "CLOSED")

    def test_optional_network_bind(self):
        # This is still a same-machine test. It does not claim a second computer
        # was reached; it checks the explicitly enabled LAN listener path.
        server, _ = self.start_server(bind="0.0.0.0")
        self.assertEqual(server.address[0], "0.0.0.0")
        self.assertEqual(self.connect(server).command("STATUS")["state"], "CLOSED")


if __name__ == "__main__":
    unittest.main()
