"""Small shared presentation helpers; no connection or device state is shared."""

from datetime import datetime
import os
import tkinter as tk
from tkinter import ttk

BG = "#f1f4f6"
INK = "#162a39"
TEAL = "#087f75"
MUTED = "#526573"
AMBER = "#a65f00"


def window(title, role, subtitle, x):
    root = tk.Tk()
    root.title(title)
    root.geometry(f"580x700+{x}+40")
    root.minsize(550, 660)
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=INK, font=("Segoe UI", 10))
    style.configure("TButton", font=("Segoe UI", 10), padding=(12, 7))
    style.configure("TCheckbutton", background=BG, font=("Segoe UI", 10))
    header = tk.Frame(root, bg=INK, padx=24, pady=18)
    header.pack(fill="x")
    tk.Label(header, text=role, bg=INK, fg="#7cdbcc", font=("Segoe UI", 10, "bold")).pack(anchor="w")
    tk.Label(header, text=title, bg=INK, fg="white", font=("Segoe UI", 23, "bold")).pack(anchor="w", pady=(4, 2))
    tk.Label(header, text=subtitle, bg=INK, fg="#cfdae0", font=("Segoe UI", 10)).pack(anchor="w")
    body = ttk.Frame(root, padding=24)
    footer = tk.Label(root, text=f"Software feasibility experiment  |  Separate process {os.getpid()}", bg=BG, fg=MUTED, font=("Segoe UI", 9))
    footer.pack(side="bottom", pady=(0, 10))
    body.pack(fill="both", expand=True)
    return root, body


def status_label(parent, variable):
    label = tk.Label(parent, textvariable=variable, anchor="w", bg=BG, fg=TEAL, font=("Segoe UI", 12, "bold"), wraplength=510)
    label.pack(fill="x", pady=(10, 12))
    return label


class Log:
    def __init__(self, parent):
        ttk.Label(parent, text="MESSAGE HISTORY", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(12, 6))
        self.text = tk.Text(parent, height=9, bg="white", fg=INK, relief="flat", borderwidth=0,
                            font=("Consolas", 10), wrap="word", padx=10, pady=8, state="disabled")
        self.text.pack(fill="both", expand=True)

    def add(self, text):
        self.text.configure(state="normal")
        self.text.insert("end", f"{datetime.now():%H:%M:%S}  {text}\n")
        if int(self.text.index("end-1c").split(".")[0]) > 300:
            self.text.delete("1.0", "31.0")
        self.text.see("end")
        self.text.configure(state="disabled")


class Compartment:
    def __init__(self, parent):
        self.canvas = tk.Canvas(parent, width=510, height=165, bg="white", highlightthickness=0)
        self.canvas.pack(fill="x", pady=(6, 4))
        self.show("CLOSED")

    def show(self, state):
        c = self.canvas
        c.delete("all")
        opened = state == "OPENED"
        c.create_text(18, 18, text="SIMULATED COMPARTMENT 1", anchor="w", fill=MUTED, font=("Segoe UI", 9, "bold"))
        c.create_rectangle(28, 85, 212, 143, fill="#dce8e9", outline=TEAL, width=2)
        if opened:
            c.create_oval(100, 105, 143, 124, fill="white", outline=TEAL, width=2)
            c.create_line(121, 106, 121, 123, fill=TEAL)
            c.create_polygon(28, 85, 74, 42, 258, 42, 212, 85, fill="#b2ded6", outline=TEAL, width=2)
        else:
            c.create_rectangle(28, 75, 212, 100, fill="#b2ded6", outline=TEAL, width=2)
            c.create_line(100, 88, 140, 88, fill=TEAL, width=3)
        c.create_text(296, 87, text="OPEN" if opened else "CLOSED", anchor="w", fill=TEAL, font=("Segoe UI", 23, "bold"))
        c.create_text(296, 120, text="Virtual motor / lid state", anchor="w", fill=MUTED, font=("Segoe UI", 10))
