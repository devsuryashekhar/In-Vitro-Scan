import json
import os
import sys
import tkinter as tk
from tkinter import simpledialog, messagebox
from pathlib import Path

# ================= BASE DIR (exe safe) =================
def app_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

BASE_DIR = app_base_dir()
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

EVENTS_FILE = DATA_DIR / "events.json"

# ================= FILE HELPERS =================
def load_events():
    if not EVENTS_FILE.exists():
        data = {
            "active": None,
            "events": {}
        }
        save_events(data)
        return data

    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 🔒 SAFETY: ensure every event has db + csv
    changed = False
    for name, cfg in data.get("events", {}).items():
        if "db" not in cfg:
            cfg["db"] = f"{name}.db"
            changed = True
        if "csv" not in cfg:
            cfg["csv"] = f"{name}_invites.csv"
            changed = True

    if changed:
        save_events(data)

    return data


def save_events(data):
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ================= GUI =================
class EventManagerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Invitro Event Manager")
        self.root.geometry("380x260")
        self.root.resizable(False, False)

        self.data = load_events()

        tk.Label(
            self.root,
            text="EVENT MANAGER",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        self.active_label = tk.Label(self.root, font=("Arial", 10))
        self.active_label.pack(pady=4)

        self.var = tk.StringVar()

        self.dropdown = tk.OptionMenu(self.root, self.var, "")
        self.dropdown.config(width=25)
        self.dropdown.pack(pady=6)

        tk.Button(
            self.root,
            text="🔁 Switch Event",
            width=28,
            command=self.switch_event
        ).pack(pady=5)

        tk.Button(
            self.root,
            text="➕ Create New Event",
            width=28,
            command=self.create_event
        ).pack(pady=5)

        tk.Button(
            self.root,
            text="❌ Exit",
            width=28,
            command=self.root.destroy
        ).pack(pady=10)

        self.refresh()
        self.root.mainloop()

    # ================= UI HELPERS =================
    def refresh(self):
        self.data = load_events()

        # Dropdown refresh
        menu = self.dropdown["menu"]
        menu.delete(0, "end")

        for name in self.data["events"].keys():
            menu.add_command(
                label=name,
                command=lambda v=name: self.var.set(v)
            )

        active = self.data.get("active")
        self.var.set(active if active else "")

        if active:
            self.active_label.config(
                text=f"Active Event: {active}",
                fg="green"
            )
        else:
            self.active_label.config(
                text="Active Event: None",
                fg="red"
            )

    # ================= ACTIONS =================
    def create_event(self):
        name = simpledialog.askstring(
            "Create Event",
            "Enter event name:"
        )

        if not name:
            return

        if name in self.data["events"]:
            messagebox.showerror("Error", "Event already exists")
            return

        self.data["events"][name] = {
            "db": f"{name}.db",
            "csv": f"{name}_invites.csv"
        }
        self.data["active"] = name

        save_events(self.data)
        self.refresh()

        messagebox.showinfo(
            "Success",
            f"Event '{name}' created & activated"
        )

    def switch_event(self):
        choice = self.var.get()
        if not choice:
            return

        if choice not in self.data["events"]:
            messagebox.showerror("Error", "Invalid event")
            return

        self.data["active"] = choice
        save_events(self.data)
        self.refresh()

        messagebox.showinfo(
            "Switched",
            f"Active event: {choice}"
        )

# ================= RUN =================
if __name__ == "__main__":
    EventManagerGUI()
