# ---------------- PREMIUM SCANNER UI (CACHE + SLIDER + EYE + STABLE) ---------------- #
import cv2
import time
import requests
import csv
import os
import json
from datetime import datetime
import platform
import numpy as np
from urllib.parse import urlparse

SERVER = "http://127.0.0.1:5000"
SETTINGS_FILE = "settings.json"
CACHE_FILE = "scan_log_backup.csv"
CACHE_TTL = 1.2
KEY_FILE = "keybinds.txt"

VIDEO_W, VIDEO_H = 1080, 640
PANEL_W, HEADER_H = 400, 120
WIN_W = VIDEO_W + PANEL_W + 80
WIN_H = VIDEO_H + HEADER_H + 100

BG = (22,18,18)
CARD = (42,34,34)
WHITE = (245,245,245)
GREEN = (110,220,100)
RED = (90,90,255)
YELLOW = (0,210,255)
GOLD = (40,190,235)
GRAY = (150,150,150)

DEFAULT_SETTINGS = {
    "exit_password":"0000",
    "admin_pin":"0000"
}


def ensure_cache():
    if not os.path.exists(CACHE_FILE):
        with open(CACHE_FILE,"w",newline="") as f:
            csv.writer(f).writerow(["time","token","status"])

def save_cache(row):
    with open(CACHE_FILE,"a",newline="") as f:
        csv.writer(f).writerow(row)

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
    with open(SETTINGS_FILE) as f:
        s=json.load(f)
    for k,v in DEFAULT_SETTINGS.items():
        s.setdefault(k,v)
    return s

def save_settings(s):
    with open(SETTINGS_FILE,"w") as f:
        json.dump(s,f,indent=2)

def load_keys():
    keys={
        "quit":"q",
        "snapshot":"s",
        "restart":"r",
        "admin":"p",
        "clear_cache":"c"
    }
    if not os.path.exists(KEY_FILE):
        with open(KEY_FILE,"w") as f:
            for k,v in keys.items():
                f.write(f"{k}={v}\n")
        return keys
    with open(KEY_FILE) as f:
        for line in f:
            if "=" in line:
                k,v=line.strip().split("=")
                keys[k]=v.lower()
    return keys

if platform.system()=="Windows":
    import winsound
    def beep_ok(): winsound.Beep(1200,120)
    def beep_fail(): winsound.Beep(400,300)
else:
    def beep_ok(): pass
    def beep_fail(): pass

def extract_token(d):
    d=d.strip()
    if d.startswith("http"):
        return urlparse(d).path.rstrip("/").split("/")[-1]
    return d

def draw_rounded_rect(img,p1,p2,color,th=-1,r=20):
    x1,y1=p1; x2,y2=p2
    cv2.rectangle(img,(x1+r,y1),(x2-r,y2),color,th)
    cv2.rectangle(img,(x1,y1+r),(x2,y2-r),color,th)
    cv2.circle(img,(x1+r,y1+r),r,color,th)
    cv2.circle(img,(x2-r,y1+r),r,color,th)
    cv2.circle(img,(x1+r,y2-r),r,color,th)
    cv2.circle(img,(x2-r,y2-r),r,color,th)

def draw_text(img,t,pos,size=0.8,col=WHITE,th=2,center=False):
    font=cv2.FONT_HERSHEY_DUPLEX
    if center:
        s=cv2.getTextSize(str(t),font,size,th)[0]
        pos=(pos[0]-s[0]//2,pos[1])
    cv2.putText(img,str(t),pos,font,size,col,th,cv2.LINE_AA)

def draw_eye(img,pos,active):
    x,y=pos
    col = GOLD if active else GRAY
    cv2.ellipse(img,(x,y),(20,12),0,0,360,col,2)
    cv2.circle(img,(x,y),6,col,-1)
    if not active:
        cv2.line(img,(x-20,y-12),(x+20,y+12),col,2)
def main():
    ensure_cache()
    settings=load_settings()
    keys=load_keys()

    cap=cv2.VideoCapture(0)
    detector=cv2.QRCodeDetector()

    stats={"total":0,"used":0,"remaining":0}
    history=[]
    history_offset=0

    used_local=set()
    last_seen={}

    banner=None
    banner_time=0
    scan_y=100
    scan_dir=1

    show_exit=False
    exit_input=""
    exit_eye=False

    show_admin=False
    admin_pin=""
    admin_eye=False

    admin_panel=False
    field_edit=None
    temp_entry=""

    win="Invitro Scanner"
    cv2.namedWindow(win,cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win,WIN_W,WIN_H)

    while True:
        ret,frame=cap.read()
        if not ret:
            continue

        canvas=np.zeros((WIN_H,WIN_W,3),np.uint8)
        canvas[:]=BG

        # -------- HEADER --------
        draw_rounded_rect(canvas,(30,20),(WIN_W-30,HEADER_H+20),CARD)
        draw_text(canvas,"INVITRO SCANNER",(70,95),1.8,GOLD,3)

        now=datetime.now()
        draw_text(canvas,now.strftime("%H:%M:%S"),(WIN_W-300,75),1.3,WHITE,3)
        draw_text(canvas,now.strftime("%A, %d %B %Y"),(WIN_W-300,110),0.5,GOLD,1)

        # -------- CAMERA --------
        vx,vy=40,HEADER_H+50
        view=cv2.resize(frame,(VIDEO_W,VIDEO_H))
        canvas[vy:vy+VIDEO_H,vx:vx+VIDEO_W]=view

        # -------- SHORT SMOOTH LASER --------
        scan_y+=(scan_dir*8)
        if scan_y<=80 or scan_y>=VIDEO_H-80:
            scan_dir*=-1
        overlay=canvas.copy()
        cv2.line(overlay,(vx+40,vy+scan_y),(vx+VIDEO_W-40,vy+scan_y),GOLD,9)
        cv2.addWeighted(overlay,0.20,canvas,0.80,0,canvas)
        cv2.line(canvas,(vx+40,vy+scan_y),(vx+VIDEO_W-40,vy+scan_y),GOLD,3)

        # -------- CORNER ANGLES --------
        L=50
        T=5
        corners=[
            (vx+10,vy+10),(vx+VIDEO_W-10,vy+10),
            (vx+10,vy+VIDEO_H-10),(vx+VIDEO_W-10,vy+VIDEO_H-10)
        ]
        for x,y in corners:
            cv2.line(canvas,(x,y),(x+ (L if x<vx+VIDEO_W//2 else -L),y),GOLD,T)
            cv2.line(canvas,(x,y),(x,y+ (L if y<vy+VIDEO_H//2 else -L)),GOLD,T)

        # -------- SIDEBAR --------
        px=vx+VIDEO_W+30
        draw_rounded_rect(canvas,(px,vy),(px+PANEL_W,vy+VIDEO_H),CARD)
        draw_text(canvas,"SYSTEM METRICS",(px+40,vy+60),0.9,GOLD,2)

        m=vy+120
        for a,b in [("Total Scans",stats["total"]),
                    ("Inside Now",stats["used"]),
                    ("Available",stats["remaining"])]:
            draw_text(canvas,a,(px+40,m),0.6,GRAY,1)
            draw_text(canvas,str(b),(px+PANEL_W-110,m),0.9,WHITE,2)
            m+=60

        # -------- HISTORY + SLIDER --------
        draw_text(canvas,"RECENT ACTIVITY",(px+40,vy+350),0.8,GOLD,2)

        visible = history[-(10+history_offset):len(history)-history_offset] if history else []

        l=vy+400
        for h in visible[::-1]:
            col = GREEN if h[2]=="OK" else RED if h[2]=="DENIED" else YELLOW
            cv2.circle(canvas,(px+55,l-8),6,col,-1)
            draw_text(canvas,f"{h[0]} | {h[1]} | {h[2]}",(px+80,l),0.55,WHITE,1)
            l+=30

        # slider bar
        total=max(1,len(history))
        bar_h=int((VIDEO_H-380)*(len(visible)/total))
        bar_y=int((VIDEO_H-380)*(history_offset/max(1,total-10)))
        cv2.rectangle(canvas,(px+PANEL_W-25,vy+360+bar_y),(px+PANEL_W-10,vy+360+bar_y+bar_h),GOLD,-1)

        # -------- FOOTER --------
        draw_text(canvas,"© Invitro Entry System — Made with ❤️ by TECH NITRO",(WIN_W//2,WIN_H-20),0.6,GRAY,1,True)

        # -------- QR DETECTION --------
        try:
            ok,dec,pts,_=detector.detectAndDecodeMulti(view)
            tokens=[t for t in dec if t] if ok else []

            if not tokens:
                t,_=detector.detectAndDecode(view)[:2]
                if t:
                    tokens=[t]

            for token in tokens:
                token=extract_token(token)
                if not token or time.time()-last_seen.get(token,0)<CACHE_TTL: 
                    continue
                last_seen[token]=time.time()
                stats["total"]+=1

                if len(history)>=200:
                    history.pop(0)

                if token in used_local:
                    banner=("ALREADY ENTERED",YELLOW)
                    history.append((now.strftime("%H:%M:%S"),token,"ALREADY"))
                    save_cache([now.strftime("%H:%M:%S"),token,"ALREADY"])
                    beep_fail()
                    banner_time=time.time()
                    break

                try:
                    r=requests.post(f"{SERVER}/scan/{token}",json={},timeout=2)
                    j=r.json()
                    stats.update(requests.get(f"{SERVER}/stats").json())
                    if j.get("success"):
                        used_local.add(token)
                        banner=("ENTRY ALLOWED",GREEN)
                        history.append((now.strftime("%H:%M:%S"),token,"OK"))
                        save_cache([now.strftime("%H:%M:%S"),token,"OK"])
                        beep_ok()
                    else:
                        banner=(j.get("msg","DENIED").upper(),RED)
                        history.append((now.strftime("%H:%M:%S"),token,"DENIED"))
                        save_cache([now.strftime("%H:%M:%S"),token,"DENIED"])
                        beep_fail()
                    banner_time=time.time()
                except:
                    banner=("SERVER ERROR",RED)
                    history.append((now.strftime("%H:%M:%S"),token,"SERVER"))
                    save_cache([now.strftime("%H:%M:%S"),token,"SERVER"])
                    banner_time=time.time()
                    beep_fail()
        except:
            pass

        if banner and time.time()-banner_time<2:
            bx=vx+VIDEO_W//2
            by=vy+120
            draw_rounded_rect(canvas,(bx-260,by-50),(bx+260,by+50),banner[1])
            draw_text(canvas,banner[0],(bx,by+20),1.2,(20,20,20),3,True)

        key=cv2.waitKey(1)&0xFF
        k=chr(key).lower() if key!=255 else ""

        def match(x):
            return k==keys[x].lower()

        # scroll cache
        if key==ord(']') and history_offset<max(0,len(history)-10):
            history_offset+=1
        if key==ord('[') and history_offset>0:
            history_offset-=1

        if match("clear_cache"):
            history.clear()
            used_local.clear()
            open(CACHE_FILE,"w").write("time,token,status\n")

        if match("snapshot"):
            cv2.imwrite(f"snapshot_{now.strftime('%Y%m%d_%H%M%S')}.png",canvas)

        if match("restart"):
            cap.release()
            cap=cv2.VideoCapture(0)

        if match("admin"):
            show_admin=True

        if match("quit"):
            show_exit=True

        # ---------- EXIT PASSWORD ----------
        if show_exit:
            draw_rounded_rect(canvas,(500,250),(WIN_W-500,WIN_H-250),CARD)
            draw_text(canvas,"EXIT PASSWORD",(WIN_W//2,330),1,GOLD,2,True)
            stars = exit_input if exit_eye else "*"*len(exit_input)
            draw_text(canvas,stars,(WIN_W//2,400),1,WHITE,2,True)
            draw_eye(canvas,(WIN_W//2+180,370),exit_eye)

            if key==13 and exit_input==settings["exit_password"]:
                break
            elif key==27:
                show_exit=False
                exit_input=""
            elif key==8 and len(exit_input):
                exit_input=exit_input[:-1]
            elif key==ord('e'):
                exit_eye=not exit_eye
            elif key!=255:
                exit_input+=chr(key)
            cv2.imshow(win,canvas)
            continue

        # ---------- ADMIN PIN ----------
        if show_admin:
            draw_rounded_rect(canvas,(500,240),(WIN_W-500,WIN_H-240),CARD)
            draw_text(canvas,"ADMIN PIN",(WIN_W//2,320),1,GOLD,2,True)
            stars = admin_pin if admin_eye else "*"*len(admin_pin)
            draw_text(canvas,stars,(WIN_W//2,380),1,WHITE,2,True)
            draw_eye(canvas,(WIN_W//2+180,350),admin_eye)

            if key==13:
                if admin_pin==settings["admin_pin"]:
                    admin_panel=True
                show_admin=False
                admin_pin=""
            elif key==27:
                show_admin=False
                admin_pin=""
            elif key==ord('e'):
                admin_eye=not admin_eye
            elif key==8 and len(admin_pin):
                admin_pin=admin_pin[:-1]
            elif key!=255:
                admin_pin+=chr(key)
            cv2.imshow(win,canvas)
            continue

        # ---------- ADMIN PANEL ----------
        if admin_panel:
            draw_rounded_rect(canvas,(400,200),(WIN_W-400,WIN_H-200),CARD)
            draw_text(canvas,"ADMIN SETTINGS",(WIN_W//2,260),1.2,GOLD,2,True)
            draw_text(canvas,"1. Change Exit Password",(WIN_W//2-230,340),0.8,WHITE,2)
            draw_text(canvas,"2. Change Admin PIN",(WIN_W//2-230,380),0.8,WHITE,2)
            draw_text(canvas,"ESC to Close",(WIN_W//2-80,450),0.7,GRAY,2)

            if key==27:
                admin_panel=False
            elif key==ord('1'):
                field_edit="exit"
                temp_entry=""
            elif key==ord('2'):
                field_edit="admin"
                temp_entry=""

            if field_edit:
                draw_rounded_rect(canvas,(500,300),(WIN_W-500,WIN_H-300),CARD)
                draw_text(canvas,"ENTER NEW VALUE",(WIN_W//2,370),1,GOLD,2,True)
                draw_text(canvas,temp_entry,(WIN_W//2,430),1,WHITE,2,True)

                if key==13 and temp_entry:
                    if field_edit=="exit":
                        settings["exit_password"]=temp_entry
                    else:
                        settings["admin_pin"]=temp_entry
                    save_settings(settings)
                    field_edit=None
                elif key==27:
                    field_edit=None
                elif key==8 and len(temp_entry):
                    temp_entry=temp_entry[:-1]
                elif key!=255:
                    temp_entry+=chr(key)

            cv2.imshow(win,canvas)
            continue

        cv2.imshow(win,canvas)

    cap.release()
    cv2.destroyAllWindows()

if __name__=="__main__":
    main()
