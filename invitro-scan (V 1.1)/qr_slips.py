#!/usr/bin/env python3
import os
import uuid
import csv
import json
import sys
from pathlib import Path

import qrcode
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm


# ================= BASE DIR (exe-safe) =================
def app_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


BASE_DIR = app_base_dir()

# ================= PATHS =================
DATA_DIR = BASE_DIR / "data"
QRS_DIR = BASE_DIR / "qrs"
EVENTS_FILE = DATA_DIR / "events.json"

DATA_DIR.mkdir(exist_ok=True)
QRS_DIR.mkdir(exist_ok=True)

# ================= CONFIG =================
COUNT = 500
LAN_IP = "127.0.0.1"     # change if needed
BASE_URL = f"http://{LAN_IP}:5000/scan"

SLIPS_PER_ROW = 2
SLIPS_PER_COL = 4

SLIP_W = 90 * mm
SLIP_H = 60 * mm

QR_SIZE = int(48 * mm)        # large & readable


# ================= HELPERS =================
def load_events():
    if not EVENTS_FILE.exists():
        raise RuntimeError("events.json not found")
    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def make_token():
    return uuid.uuid4().hex[:12].upper()


# ================= MAIN =================
def generate_qrs():
    events = load_events()
    active = events.get("active")

    if not active:
        print("❌ No active event selected")
        return

    # ---------- Event folders / files ----------
    event_qr_dir = QRS_DIR / active
    event_qr_dir.mkdir(exist_ok=True)

    csv_file = BASE_DIR / f"{active}_invites.csv"
    pdf_file = BASE_DIR / f"{active}_qr_slips.pdf"

    records = []

    print(f"Generating {COUNT} QR codes for event '{active}'")

    # ---------- QR GENERATION ----------
    for i in range(COUNT):
        token = make_token()
        url = f"{BASE_URL}/{token}"

        img_path = event_qr_dir / f"{token}.png"

        qr = qrcode.QRCode(box_size=6, border=1)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(img_path)

        records.append({"token": token, "file": str(img_path)})

        if (i + 1) % 100 == 0:
            print(f"  • {i + 1}/{COUNT}")

    # ---------- CSV ----------
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["token"])
        for r in records:
            writer.writerow([r["token"]])

    print("CSV saved:", csv_file)

    # ---------- PDF ----------
    print("Creating printable PDF...")
    c = canvas.Canvas(str(pdf_file), pagesize=A4)
    page_w, page_h = A4

    margin_x = 12 * mm
    margin_y = 14 * mm

    gap_x = (page_w - 2 * margin_x - SLIPS_PER_ROW * SLIP_W) / (SLIPS_PER_ROW - 1)
    gap_y = (page_h - 2 * margin_y - SLIPS_PER_COL * SLIP_H) / (SLIPS_PER_COL - 1)

    x0 = margin_x
    y0 = page_h - margin_y - SLIP_H

    temp_img = BASE_DIR / "_tmp_qr.png"
    idx = 0

    for rec in records:
        if idx > 0 and idx % (SLIPS_PER_ROW * SLIPS_PER_COL) == 0:
            c.showPage()

        row = (idx // SLIPS_PER_ROW) % SLIPS_PER_COL
        col = idx % SLIPS_PER_ROW

        x = x0 + col * (SLIP_W + gap_x)
        y = y0 - row * (SLIP_H + gap_y)

        # ---- Border ----
        c.rect(x, y, SLIP_W, SLIP_H)

        # ---- ENTRY TEXT ----
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(
            x + SLIP_W / 2,
            y + SLIP_H - 13,
            "ENTRY QR"
        )

        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(
            x + SLIP_W / 2,
            y + SLIP_H - 28,
            "Scan at Entrance"
        )

        # ---- QR IMAGE (LOWERED) ----
        qr_img = Image.open(rec["file"]).convert("RGB")
        qr_img = qr_img.resize((QR_SIZE, QR_SIZE))
        qr_img.save(temp_img)

        qr_y = y + 1 * mm

        c.drawImage(
            str(temp_img),
            x + (SLIP_W - QR_SIZE) / 2,
            qr_y,
            width=QR_SIZE,
            height=QR_SIZE
        )

        idx += 1

    c.save()

    if temp_img.exists():
        temp_img.unlink()

    print("PDF saved:", pdf_file)
    print("✅ DONE — QR slips ready")


# ================= RUN =================
if __name__ == "__main__":
    generate_qrs()
