import tkinter as tk
from tkinter import messagebox, simpledialog
import subprocess
import sys
import json
from pathlib import Path

# ================= BASE DIR (EXE SAFE) =================
def app_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent

BASE_DIR = app_base_dir()

# ================= PATHS =================
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

EVENTS_FILE = DATA_DIR / "events.json"
SETTINGS_FILE = BASE_DIR / "settings.json"

# ================= DEFAULT SETTINGS =================
DEFAULT_SETTINGS = {
    "admin_pin": "0000"
}

# ================= SETTINGS HELPERS =================
def load_settings():
    if not SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2)
        return DEFAULT_SETTINGS.copy()

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for k, v in DEFAULT_SETTINGS.items():
        data.setdefault(k, v)

    return data

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ================= EVENT HELPERS =================
def load_events():
    if not EVENTS_FILE.exists():
        data = {"active": None, "events": {}}
        save_events(data)
        return data

    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_events(data):
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ================= ADMIN APP =================
class AdminApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Invitro Admin Panel")
        self.geometry("430x350")
        self.resizable(False, False)

        self.settings = load_settings()
        self.events = load_events()

        # 🔐 PIN LOCK
        if not self.verify_pin():
            self.destroy()
            return

        # ================= UI =================
        tk.Label(
            self,
            text="INVITRO ADMIN PANEL",
            font=("Arial", 16, "bold")
        ).pack(pady=10)

        self.active_label = tk.Label(self, text="", font=("Arial", 11))
        self.active_label.pack(pady=5)
        self.refresh_active()

        tk.Button(self, text="➕ Create New Event",
                  width=32, command=self.create_event).pack(pady=6)

        tk.Button(self, text="🔁 Switch Event",
                  width=32, command=self.switch_event).pack(pady=6)

        tk.Button(self, text="📦 Generate QR for Active Event",
                  width=32, command=self.generate_qr).pack(pady=6)

        tk.Button(self, text="🔐 Change Admin PIN",
                  width=32, command=self.change_pin).pack(pady=6)

        tk.Button(self, text="❌ Exit",
                  width=32, command=self.destroy).pack(pady=12)

    # ================= SECURITY =================
    def verify_pin(self):
        pin = simpledialog.askstring(
            "Admin Login",
            "Enter Admin PIN:",
            show="*"
        )
        if pin is None:
            return False
        if pin != self.settings["admin_pin"]:
            messagebox.showerror("Access Denied", "Incorrect PIN")
            return False
        return True

    def change_pin(self):
        new_pin = simpledialog.askstring(
            "Change PIN",
            "Enter new Admin PIN:",
            show="*"
        )
        if not new_pin:
            return
        self.settings["admin_pin"] = new_pin
        save_settings(self.settings)
        messagebox.showinfo("Success", "Admin PIN updated")

    # ================= EVENT UI =================
    def refresh_active(self):
        active = self.events.get("active")
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

    def create_event(self):
        name = simpledialog.askstring(
            "Create Event",
            "Enter event name:"
        )
        if not name:
            return

        if name in self.events["events"]:
            messagebox.showerror("Error", "Event already exists")
            return

        self.events["events"][name] = {"db": f"{name}.db"}
        self.events["active"] = name
        save_events(self.events)

        messagebox.showinfo(
            "Success",
            f"Event '{name}' created & activated"
        )
        self.refresh_active()

    def switch_event(self):
        if not self.events["events"]:
            messagebox.showerror("Error", "No events available")
            return

        choices = list(self.events["events"].keys())
        choice = simpledialog.askstring(
            "Switch Event",
            "Available events:\n\n" +
            "\n".join(choices) +
            "\n\nEnter event name:"
        )

        if choice not in choices:
            messagebox.showerror("Error", "Invalid event")
            return

        self.events["active"] = choice
        save_events(self.events)

        messagebox.showinfo(
            "Success",
            f"Switched to event '{choice}'"
        )
        self.refresh_active()

    # ================= QR GENERATION (FIXED) =================
    def generate_qr(self):
        active = self.events.get("active")
        if not active:
            messagebox.showerror("Error", "No active event selected")
            return

        try:
            if getattr(sys, "frozen", False):
                # 🔒 EXE MODE
                qr_exec = BASE_DIR / "qr_slips.exe"
                if not qr_exec.exists():
                    messagebox.showerror("Error", "qr_slips.exe not found")
                    return
                subprocess.Popen([str(qr_exec)], cwd=BASE_DIR)
            else:
                # 🧪 DEV MODE
                subprocess.Popen(
                    [sys.executable, "qr_slips.py"],
                    cwd=BASE_DIR
                )

            messagebox.showinfo(
                "QR Generation",
                f"QR generation started for event '{active}'"
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))

# ================= RUN =================
if __name__ == "__main__":
    app = AdminApp()
    app.mainloop()
