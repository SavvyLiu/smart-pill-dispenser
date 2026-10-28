"""Separate controller/motor-state simulator, with optional LAN listening."""

import queue
import threading
import tkinter as tk
from tkinter import ttk

from simulator import Controller, ControllerServer
from visual_common import Compartment, Log, status_label, window


class ControllerApp:
    def __init__(self):
        self.root, body = window("Controller simulator", "APPLICATION B / RECEIVE COMMANDS", "Simulates command handling and motor/lid state.", 635)
        self.messages = queue.Queue()
        self.model = Controller()
        self.server = None
        self.thread = None
        self.lan = tk.BooleanVar(value=False)
        self.drop = tk.BooleanVar(value=False)
        self.port = tk.StringVar(value="8765")
        self.status = tk.StringVar(value="Stopped / start listening to receive messages")
        row = ttk.Frame(body)
        row.pack(fill="x")
        ttk.Label(row, text="Port").pack(side="left")
        self.port_entry = ttk.Entry(row, textvariable=self.port, width=7)
        self.port_entry.pack(side="left", padx=8)
        self.start_button = ttk.Button(row, text="Start listening", command=self.start)
        self.start_button.pack(side="left", padx=(0, 8))
        self.stop_button = ttk.Button(row, text="Stop", command=self.stop, state="disabled")
        self.stop_button.pack(side="left")
        self.lan_check = ttk.Checkbutton(body, text="Allow a host on another computer (LAN)", variable=self.lan)
        self.lan_check.pack(anchor="w", pady=(10, 0))
        status_label(body, self.status)
        self.compartment = Compartment(body)
        self.drop_check = ttk.Checkbutton(body, text="Drop the next Open reply (optional failure test)", variable=self.drop, command=self.arm_fault)
        self.drop_check.pack(anchor="w", pady=(10, 2))
        self.log = Log(body)
        self.log.add("The compartment changes only on received commands.")
        self.log.add("No motor, board, or sensor is connected.")
        self.root.after(50, self.poll)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

    def start(self):
        try:
            port = int(self.port.get())
            if not 1 <= port <= 65535:
                raise ValueError("Port must be between 1 and 65535")
            bind = "0.0.0.0" if self.lan.get() else "127.0.0.1"
            self.server = ControllerServer(port=port, bind=bind, controller=self.model,
                fault="timeout" if self.drop.get() else "none", on_event=self.messages.put)
            self.thread = threading.Thread(target=self.server.run, daemon=True)
            self.thread.start()
            self.start_button.configure(state="disabled")
            self.lan_check.configure(state="disabled")
            self.port_entry.configure(state="disabled")
            self.stop_button.configure(state="normal")
        except (ValueError, OSError) as exc:
            self.status.set(f"Could not start: {exc}")

    def stop(self):
        if self.server is not None:
            self.server.stop()
        self.stop_button.configure(state="disabled")

    def arm_fault(self):
        if self.server is not None:
            self.server.arm_fault("timeout" if self.drop.get() else "none")

    def poll(self):
        while not self.messages.empty():
            event = self.messages.get_nowait()
            kind = event["kind"]
            if kind == "listening":
                bind, port = event["address"]
                self.status.set(f"Listening on {bind}:{port}")
                self.log.add(f"LISTEN {bind}:{port}")
                if bind == "0.0.0.0":
                    self.log.add("LAN enabled: give the host this computer's LAN IPv4 address.")
            elif kind == "connected":
                peer, _ = event["peer"]
                self.status.set(f"Host connected from {peer}")
                self.log.add(f"CONNECTED from {peer}")
            elif kind == "received":
                m = event["message"]
                self.log.add(f"RECEIVE #{m['id']}  {m['command']} {m['compartment']}")
            elif kind == "state":
                m = event["message"]
                if m["compartment"] == "compartment_1":
                    self.compartment.show(m["state"])
            elif kind == "sent":
                m = event["message"]
                self.log.add(f"SEND #{m['id']}  {m['state']}")
            elif kind == "fault":
                self.drop.set(False)
                self.log.add(f"DROPPED reply #{event['message']['id']}; compartment is already open")
            elif kind == "disconnected":
                self.log.add("Host disconnected; simulated state is retained")
                self.status.set("Host disconnected / waiting for a connection")
            elif kind == "error":
                self.log.add(f"ERROR {event['text']}")
            elif kind == "stopped":
                self.status.set("Stopped / compartment state retained")
                self.log.add("LISTENER stopped")
                self.start_button.configure(state="normal")
                self.lan_check.configure(state="normal")
                self.port_entry.configure(state="normal")
                self.stop_button.configure(state="disabled")
        self.root.after(50, self.poll)

    def quit(self):
        self.stop()
        self.root.destroy()


if __name__ == "__main__":
    ControllerApp().root.mainloop()
