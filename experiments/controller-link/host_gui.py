"""Host window. All confirmed state comes from replies over the connection."""

import json
import queue
import threading
import tkinter as tk
from tkinter import ttk
import uuid

from host import Client
from visual_common import AMBER, BG, INK, Log, MUTED, status_label, window


class HostApp:
    def __init__(self):
        self.root, body = window("Host console", "APPLICATION A / SEND COMMANDS", "Controls the remote simulator through messages only.", 25)
        self.messages = queue.Queue()
        self.client = None
        self.busy = False
        self.connected = False
        self.last_state = None
        self.address = tk.StringVar(value="127.0.0.1")
        self.port = tk.StringVar(value="8765")
        self.status = tk.StringVar(value="Disconnected")
        self.state = tk.StringVar(value="No confirmed state")
        row = ttk.Frame(body)
        row.pack(fill="x")
        ttk.Label(row, text="Controller address").grid(row=0, column=0, sticky="w")
        ttk.Label(row, text="Port").grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.address_entry = ttk.Entry(row, textvariable=self.address, width=26)
        self.address_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.port_entry = ttk.Entry(row, textvariable=self.port, width=7)
        self.port_entry.grid(row=1, column=1, padx=8, pady=(4, 0))
        self.connect_button = ttk.Button(row, text="Connect", command=self.connect)
        self.connect_button.grid(row=1, column=2, pady=(4, 0))
        row.columnconfigure(0, weight=1)
        status_label(body, self.status)
        card = tk.Frame(body, bg="white", padx=18, pady=16)
        card.pack(fill="x")
        tk.Label(card, text="HOST'S KNOWLEDGE / COMPARTMENT 1", bg="white", fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.state_label = tk.Label(card, textvariable=self.state, bg="white", fg=INK, font=("Segoe UI", 20, "bold"), wraplength=465, anchor="w")
        self.state_label.pack(anchor="w", pady=(8, 2))
        tk.Label(card, text="Confirmed by a reply, never by a button press.", bg="white", fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w")
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=(14, 6))
        self.open_button = ttk.Button(actions, text="Open", command=lambda: self.send("OPEN"))
        self.close_button = ttk.Button(actions, text="Close", command=lambda: self.send("CLOSE"))
        self.status_button = ttk.Button(actions, text="Check status", command=lambda: self.send("STATUS"))
        for button in (self.open_button, self.close_button, self.status_button):
            button.pack(side="left", padx=(0, 8))
        self.disconnect_button = ttk.Button(body, text="Disconnect", command=self.disconnect)
        self.disconnect_button.pack(anchor="w")
        self.log = Log(body)
        self.log.add("Start the controller application, then connect.")
        self.log.add("Local: 127.0.0.1. Other computer: its LAN address.")
        self.refresh_controls()
        self.root.after(50, self.poll)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

    def refresh_controls(self):
        self.connect_button.configure(state="normal" if not self.busy and not self.connected else "disabled")
        for entry in (self.address_entry, self.port_entry):
            entry.configure(state="disabled" if self.busy or self.connected else "normal")
        unresolved = self.client is not None and "compartment_1" in self.client.unresolved
        for button in (self.open_button, self.close_button):
            button.configure(state="normal" if self.connected and not self.busy and not unresolved else "disabled")
        for button in (self.status_button, self.disconnect_button):
            button.configure(state="normal" if self.connected and not self.busy else "disabled")

    def work(self, job):
        self.busy = True
        self.refresh_controls()
        def run():
            try:
                self.messages.put(("result", job()))
            except Exception as exc:
                self.messages.put(("error", str(exc)))
        threading.Thread(target=run, daemon=True).start()

    def connect(self):
        try:
            address = self.address.get().strip()
            port = int(self.port.get())
            if not address or not 1 <= port <= 65535 or any(char in address for char in "/?:#"):
                raise ValueError("Enter a hostname or IPv4 address and a port from 1 to 65535")
            endpoint = f"socket://{address}:{port}"
            if self.client is None or self.client.port != endpoint:
                if self.client is not None and self.client.unresolved:
                    raise ValueError("Reconnect to the original controller to check the unresolved operation")
                self.client = Client(endpoint, timeout=2.0, on_event=lambda event: self.messages.put(("wire", event)))
            self.status.set("Connecting and checking status...")
            def job():
                self.client.connect()
                return self.client.command("STATUS", request_id=uuid.uuid4().hex[:8])
            self.work(job)
        except ValueError as exc:
            self.status.set(str(exc))

    def send(self, command):
        self.status.set(f"Waiting for {command} reply...")
        self.work(lambda: self.client.command(command, request_id=uuid.uuid4().hex[:8]))

    def disconnect(self):
        self.work(lambda: (self.client.close(), None)[1])

    def poll(self):
        while not self.messages.empty():
            kind, data = self.messages.get_nowait()
            if kind == "wire":
                if data["direction"] == "TX":
                    message = data["message"]
                    self.log.add(f"SEND #{message['id']}  {message['command']} compartment_1")
                else:
                    try:
                        message = json.loads(data["raw"])
                        self.log.add(f"REPLY #{message.get('id', '?')}  {message.get('state', 'invalid response')}")
                    except ValueError:
                        self.log.add("REPLY received, but could not be read")
                continue
            self.busy = False
            self.connected = self.client is not None and self.client.connection is not None
            if kind == "result" and data is not None:
                self.last_state = data["state"]
                self.state.set(self.last_state)
                self.state_label.configure(fg=INK)
                self.status.set("Connection verified / matching reply received")
            elif kind == "error":
                self.log.add(f"ERROR  {data}")
                self.status.set("Connection not verified. Reconnect to check status.")
                if self.client is not None and self.client.unresolved:
                    self.state.set("Outcome unknown")
                    self.state_label.configure(fg=AMBER)
                else:
                    self.state.set(f"Last confirmed: {self.last_state}" if self.last_state else "No confirmed state")
                if self.client is not None:
                    self.client.close()
                self.connected = False
            else:
                self.status.set("Disconnected")
                self.state.set(f"Last confirmed: {self.last_state}" if self.last_state else "No confirmed state")
                self.log.add("Connection closed by host")
            self.refresh_controls()
        self.root.after(50, self.poll)

    def quit(self):
        if self.client is not None:
            self.client.close()
        self.root.destroy()


if __name__ == "__main__":
    HostApp().root.mainloop()
