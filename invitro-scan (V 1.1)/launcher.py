import subprocess
import tkinter as tk
from pathlib import Path
import sys

def app_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent

BASE_DIR = app_base_dir()

def launch_admin():
    subprocess.Popen([str(BASE_DIR / "admin.exe")], cwd=BASE_DIR)

def launch_scanner():
    subprocess.Popen([str(BASE_DIR / "scanner.exe")], cwd=BASE_DIR)

root = tk.Tk()
root.title("Invitro Entry System")
root.geometry("300x220")
root.resizable(False, False)

tk.Label(root, text="Invitro System", font=("Arial", 16, "bold")).pack(pady=15)

tk.Button(root, text="Admin Panel", width=25, command=launch_admin).pack(pady=10)
tk.Button(root, text="Scanner", width=25, command=launch_scanner).pack(pady=10)

root.mainloop()
