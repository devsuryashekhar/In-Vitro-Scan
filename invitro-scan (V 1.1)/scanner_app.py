import subprocess
import sys
import time
import requests
from pathlib import Path

# ------------------ BASE DIR (EXE SAFE) ------------------
def app_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

BASE_DIR = app_base_dir()

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
STATS_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/stats"

# ------------------ WAIT FOR SERVER ------------------
def wait_for_server(timeout=12):
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(STATS_URL, timeout=1)
            return True
        except:
            time.sleep(0.5)
    return False

# ------------------ MAIN ------------------
def main():
    server_exe = BASE_DIR / "server.exe"
    scanner_ui_exe = BASE_DIR / "scanner_ui.exe"

    # ------------ DEV MODE (Running .py files) ------------
    if not getattr(sys, "frozen", False):
        server = subprocess.Popen(
            [sys.executable, "server.py"],
            cwd=BASE_DIR
        )
    else:
        # ------------ EXE MODE ------------
        if not server_exe.exists():
            print("❌ server.exe not found")
            return

        server = subprocess.Popen(
            [str(server_exe)],
            cwd=BASE_DIR
        )

    # ------------ WAIT FOR SERVER ------------
    if not wait_for_server():
        print("❌ Server not responding")
        server.terminate()
        return

    # ------------ START SCANNER UI ------------
    if not getattr(sys, "frozen", False):
        subprocess.Popen(
            [sys.executable, "scanner_ui.py"],
            cwd=BASE_DIR
        ).wait()
    else:
        if not scanner_ui_exe.exists():
            print("❌ scanner_ui.exe not found")
        else:
            subprocess.Popen(
                [str(scanner_ui_exe)],
                cwd=BASE_DIR
            ).wait()

    # ------------ SHUTDOWN SERVER ------------
    server.terminate()

# ------------------ RUN ------------------
if __name__ == "__main__":
    main()
