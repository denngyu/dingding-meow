# -*- coding: utf-8 -*-
"""盯盯喵 v1.2: 桌面小猫, 久坐+离座+喝水+饮水目标+托盘+自启+每日报告。纯本地。"""
import sys, os, threading, time, shutil, tempfile, math, subprocess, webbrowser
import tkinter as tk
from datetime import datetime, timedelta
if getattr(sys, "frozen", False):
    _self = os.path.dirname(os.path.abspath(sys.executable))
else:
    _self = os.path.dirname(os.path.abspath(__file__))
import cv2, numpy as np
from PIL import Image, ImageTk, ImageDraw

# ─────────── 参数 ───────────
CAM_INDEX=0; CHECK_EVERY=0.5; SIT_LIMIT_MIN=45; GRACE_SEC=25; OVER_GRACE=5; BLOCK_LEVEL=22
CONF_CUP=0.4                # 提高置信阈值（v1.2 从 0.25 提到 0.4）
CUP_HITS_NEEDED=2           # 时间连续 2 帧命中才触发喝水
CUP_CLASSES={39,40,41}      # cup/bottle/wine glass
WATER_TARGET_ML=2000        # 每日饮水目标
WATER_NUDGE_GAP_MIN=60      # 超过多少分钟没喝就轻推
WATER_NUDGE_SHOW_SEC=15     # 提醒显示多久
DRINK_ANIM_SEC=2.4          # 猫喝水动画时长
CUP_HOLD_AFTER_DRINK=6      # 检测到喝水后爪里继续拿杯多久

INK="#1A1B18"; INK2="#585C57"; INK3="#8C918B"; PAPER="#F7F6F3"; SIG="#C15A34"; LINE="#D9D8D0"
FUR="#B8B4AC"; FUR_DARK="#8A867E"; FUR_LIGHT="#E4E0D6"; NOSE="#E8A5A0"; CHEEK="#F5C7C2"
CUP_BODY="#B0DDF0"; CUP_WATER="#4A9DC7"
TRANS="#FE00FE"

TEST = len(sys.argv)>1 and sys.argv[1]=="test"
if TEST: SIT_LIMIT_MIN, GRACE_SEC, OVER_GRACE, WATER_NUDGE_GAP_MIN = 0.7, 8, 3, 1

LOG_DIR=os.path.join(_self,"logs"); os.makedirs(LOG_DIR, exist_ok=True)
def _today(): return datetime.now().strftime("%Y%m%d")
def wlog_path(day=None): return os.path.join(LOG_DIR,"water_%s.csv"%(day or _today()))
def slog_path(day=None): return os.path.join(LOG_DIR,"sit_%s.csv"%(day or _today()))

# ─────────── 模型 ───────────
_hc=cv2.data.haarcascades
face_c=cv2.CascadeClassifier(_hc+"haarcascade_frontalface_default.xml")
face_alt=cv2.CascadeClassifier(_hc+"haarcascade_frontalface_alt.xml")
m=os.path.join(_self,"models"); tmp=tempfile.gettempdir()
cfg=os.path.join(tmp,"y4t.cfg"); wp=os.path.join(tmp,"y4t.weights")
shutil.copy(os.path.join(m,"yolov4-tiny.cfg"),cfg); shutil.copy(os.path.join(m,"yolov4-tiny.weights"),wp)
net=cv2.dnn.readNetFromDarknet(cfg,wp); LN=net.getUnconnectedOutLayersNames()

def face_boxes(gray):
    b=face_c.detectMultiScale(gray,1.1,5,minSize=(80,80))
    if len(b)==0: b=face_alt.detectMultiScale(gray,1.1,5,minSize=(80,80))
    return list(b)

def cup_boxes(frame):
    H,W=frame.shape[:2]
    net.setInput(cv2.dnn.blobFromImage(frame,1/255.0,(416,416),swapRB=True,crop=False))
    out=[]
    for o in net.forward(LN):
        for d in o:
            sc=d[5:]; cid=int(np.argmax(sc))
            if cid in CUP_CLASSES and sc[cid]>CONF_CUP:
                cx,cy,w,h=d[0]*W,d[1]*H,d[2]*W,d[3]*H
                out.append((int(cx-w/2),int(cy-h/2),int(w),int(h)))
    return out

def cup_near_face(f, c):
    """杯是否在脸的合理喝水位置：重叠 + 杯中心不能远远低于脸底。"""
    fx,fy,fw,fh=f
    ex=fw*0.5; ey=fh*0.6
    rx,ry,rw,rh=fx-ex, fy-ey*0.3, fw+2*ex, fh+ey
    cx,cy,cw,ch=c
    if not (min(rx+rw,cx+cw)-max(rx,cx)>0 and min(ry+rh,cy+ch)-max(ry,cy)>0):
        return False
    cup_cy = cy + ch/2
    face_bot = fy + fh
    if cup_cy - face_bot > fh * 0.6:  # 杯远远垂在脸下方 = 桌上放着，不算喝水
        return False
    return True

# ─────────── 日志聚合 ───────────
def today_total():
    t=0; p=wlog_path()
    if os.path.exists(p):
        for ln in open(p,encoding="utf-8-sig").read().splitlines()[1:]:
            pp=ln.split(",")
            if len(pp)>=2 and pp[1].isdigit(): t+=int(pp[1])
    return t

def last_drink_ts_today():
    p=wlog_path()
    if not os.path.exists(p): return None
    lines=open(p,encoding="utf-8-sig").read().splitlines()[1:]
    if not lines: return None
    last=lines[-1].split(",")[0]
    try:
        hh,mm,ss=[int(x) for x in last.split(":")]
        d=datetime.now().replace(hour=hh,minute=mm,second=ss,microsecond=0)
        return d.timestamp()
    except: return None

def wlog(ml,total):
    p=wlog_path(); new=not os.path.exists(p)
    with open(p,"a",encoding="utf-8-sig") as f:
        if new: f.write("time,ml,今日累计\n")
        f.write("%s,%d,%d\n"%(datetime.now().strftime("%H:%M:%S"),ml,total))

def slog_write(start_ts, end_ts, over_flag):
    minutes=(end_ts-start_ts)/60
    if minutes<0.5: return
    p=slog_path(); new=not os.path.exists(p)
    with open(p,"a",encoding="utf-8-sig") as f:
        if new: f.write("start,end,minutes,over\n")
        f.write("%s,%s,%.1f,%d\n"%(
            datetime.fromtimestamp(start_ts).strftime("%H:%M:%S"),
            datetime.fromtimestamp(end_ts).strftime("%H:%M:%S"),
            minutes, 1 if over_flag else 0))

# ─────────── 状态 ───────────
STATE={
    "mode":"init","sit":0,"away":0,
    "water":today_total(),"drink":False,"frame":None,
    "cup_hits":0,
    "last_drink_ts":last_drink_ts_today(),
    "drink_anim_until":0.0,
    "cup_hold_until":0.0,
    "nudge_until":0.0,
    "sit_session_start":None,
    "over_flag":False,
    "paused":False,
    "_toggle_eyes":False,
    "_quit":False,
}

def loop():
    cap=cv2.VideoCapture(CAM_INDEX,cv2.CAP_DSHOW)
    last_seen=away_start=None; sit_start=None; was_drinking=False
    prev_mode="init"
    while True:
        if STATE["_quit"]: break
        if STATE["paused"]:
            STATE["mode"]="paused"
            time.sleep(0.5); continue
        ok,fr=cap.read()
        if not ok or fr is None:
            try: cap.release()
            except: pass
            time.sleep(1); cap=cv2.VideoCapture(CAM_INDEX,cv2.CAP_DSHOW); continue
        gray=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY); now=time.time()
        blocked=gray.mean()<BLOCK_LEVEL
        fb=[] if blocked else face_boxes(cv2.equalizeHist(gray))
        if fb: last_seen=now
        eff=OVER_GRACE if STATE["mode"]=="over" else GRACE_SEC
        present=(not blocked) and last_seen and (now-last_seen<eff)
        cups=[]
        if present:
            away_start=None
            if sit_start is None:
                sit_start=last_seen
                STATE["sit_session_start"]=sit_start
                STATE["over_flag"]=False
            sit=now-sit_start
            new_mode="over" if sit/60>=SIT_LIMIT_MIN else "seated"
            if new_mode=="over": STATE["over_flag"]=True
            STATE.update(mode=new_mode, sit=sit, away=0)
            cups=cup_boxes(fr)
            drinking=any(cup_near_face(f,c) for f in fb for c in cups)
            if drinking:
                STATE["cup_hits"]=min(STATE["cup_hits"]+1, CUP_HITS_NEEDED+2)
                if STATE["cup_hits"]>=CUP_HITS_NEEDED and not was_drinking:
                    STATE["drink"]=True
                    STATE["drink_anim_until"]=now+DRINK_ANIM_SEC
                    STATE["cup_hold_until"]=now+CUP_HOLD_AFTER_DRINK
                    was_drinking=True
            else:
                STATE["cup_hits"]=max(0, STATE["cup_hits"]-1)
                if STATE["cup_hits"]==0: was_drinking=False
            # 饮水轻推
            ldt=STATE.get("last_drink_ts") or 0
            gap=(now-ldt)/60 if ldt else 999
            if gap>WATER_NUDGE_GAP_MIN and STATE["water"]<WATER_TARGET_ML \
               and now>STATE.get("nudge_until",0)+WATER_NUDGE_SHOW_SEC*3:
                STATE["nudge_until"]=now+WATER_NUDGE_SHOW_SEC
        else:
            if prev_mode in ("seated","over") and sit_start is not None:
                slog_write(sit_start, now, STATE["over_flag"])
            sit_start=None; was_drinking=False; STATE["cup_hits"]=0
            STATE["sit_session_start"]=None
            if away_start is None: away_start=last_seen if last_seen else now
            STATE.update(mode=("blocked" if blocked else "away"), away=now-away_start, sit=0)
        prev_mode=STATE["mode"]
        disp=fr.copy()
        for (x,y,w,h) in fb: cv2.rectangle(disp,(x,y),(x+w,y+h),(0,220,0),2)
        for (x,y,w,h) in cups: cv2.rectangle(disp,(x,y),(x+w,y+h),(0,160,255),2)
        STATE["frame"]=cv2.cvtColor(cv2.resize(disp,(200,150)),cv2.COLOR_BGR2RGB)
        time.sleep(CHECK_EVERY)

def dur(s):
    mm,x=divmod(int(s),60); return "%d分%d秒"%(mm,x) if mm else "%d秒"%x

# ─────────── UI 绘制 ───────────
def rr(c, x1, y1, x2, y2, r=14, **kw):
    pts=[x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2,
         x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
    return c.create_polygon(pts, smooth=True, **kw)

def draw_cup(c, x, y, tilt=0, scale=1.0):
    """在 (x,y) 画一只带水的杯。tilt 度（0 直立，正数向右倒）。"""
    tr=math.radians(tilt); ct,st=math.cos(tr),math.sin(tr)
    w,h=13*scale, 15*scale
    def R(px,py): return (x + (px*ct-py*st), y + (px*st+py*ct))
    v=[R(-w/2,-h/2), R(w/2,-h/2), R(w/2-2, h/2), R(-w/2+2, h/2)]
    pts=[]
    for p in v: pts.extend(p)
    c.create_polygon(pts, fill=CUP_BODY, outline=INK, width=1.3, smooth=1)
    wy=-h/2+3.5
    vw=[R(-w/2+1, wy), R(w/2-1, wy), R(w/2-2.5, h/2-1), R(-w/2+2.5, h/2-1)]
    wpts=[]
    for p in vw: wpts.extend(p)
    c.create_polygon(wpts, fill=CUP_WATER, outline="", smooth=1)
    c.create_line(*R(-w/2,-h/2+0.5), *R(w/2,-h/2+0.5), fill="#FFFFFF", width=1)
    hp=[R(w/2, -h/2+3), R(w/2+5, -h/2+4), R(w/2+5, h/2-4), R(w/2, h/2-3)]
    hpts=[]
    for p in hp: hpts.extend(p)
    c.create_line(hpts, fill=INK, width=1.3, smooth=1)

def draw_cat(c, cx, cy, eyes_open=False, blink=False, mood="seated",
             breath=0, tail_ang=0, cup_state=None):
    by1=cy+30+breath; by2=cy+100+breath
    c.create_arc(cx+22, cy+38+breath, cx+82, cy+96+breath,
                 start=60+tail_ang, extent=200, style="arc", outline=FUR, width=11)
    c.create_arc(cx+22, cy+38+breath, cx+82, cy+96+breath,
                 start=60+tail_ang, extent=200, style="arc", outline=FUR_DARK, width=1)
    c.create_oval(cx-50, by1, cx+50, by2, fill=FUR, outline=FUR_DARK, width=1.2)
    c.create_oval(cx-28, by1+8, cx+28, by2-4, fill=FUR_LIGHT, outline="")
    c.create_oval(cx-34, by2-16, cx-10, by2-1, fill=FUR_LIGHT, outline=FUR_DARK, width=1)
    c.create_oval(cx+10, by2-16, cx+34, by2-1, fill=FUR_LIGHT, outline=FUR_DARK, width=1)
    for tx in (cx-28, cx-22, cx-16):
        c.create_oval(tx-1.5, by2-8, tx+1.5, by2-5, fill=NOSE, outline="")
    for tx in (cx+16, cx+22, cx+28):
        c.create_oval(tx-1.5, by2-8, tx+1.5, by2-5, fill=NOSE, outline="")

    c.create_polygon(cx-46, cy-30, cx-52, cy-66, cx-22, cy-38,
                     fill=FUR, outline=FUR_DARK, width=1.2, smooth=1)
    c.create_polygon(cx+46, cy-30, cx+52, cy-66, cx+22, cy-38,
                     fill=FUR, outline=FUR_DARK, width=1.2, smooth=1)
    c.create_polygon(cx-42, cy-33, cx-46, cy-56, cx-30, cy-38,
                     fill=NOSE, outline="", smooth=1)
    c.create_polygon(cx+42, cy-33, cx+46, cy-56, cx+30, cy-38,
                     fill=NOSE, outline="", smooth=1)

    c.create_oval(cx-53, cy-40, cx+53, cy+45, fill=FUR, outline=FUR_DARK, width=1.2)
    c.create_oval(cx-32, cy-10, cx+32, cy+38, fill=FUR_LIGHT, outline="")

    c.create_oval(cx-38, cy+6, cx-24, cy+18, fill=CHEEK, outline="")
    c.create_oval(cx+24, cy+6, cx+38, cy+18, fill=CHEEK, outline="")

    ex_l, ex_r = cx-18, cx+18; ey = cy-4
    if eyes_open and not blink:
        c.create_oval(ex_l-11, ey-13, ex_l+11, ey+13, fill="#FFFFFF", outline=INK, width=1.6)
        c.create_oval(ex_r-11, ey-13, ex_r+11, ey+13, fill="#FFFFFF", outline=INK, width=1.6)
        c.create_oval(ex_l-6, ey-9, ex_l+6, ey+10, fill=INK, outline="")
        c.create_oval(ex_r-6, ey-9, ex_r+6, ey+10, fill=INK, outline="")
        c.create_oval(ex_l-3, ey-7, ex_l+2, ey-2, fill="#FFFFFF", outline="")
        c.create_oval(ex_l-4, ey+3, ex_l-2, ey+5, fill="#FFFFFF", outline="")
        c.create_oval(ex_r-3, ey-7, ex_r+2, ey-2, fill="#FFFFFF", outline="")
        c.create_oval(ex_r-4, ey+3, ex_r-2, ey+5, fill="#FFFFFF", outline="")
    else:
        c.create_arc(ex_l-10, ey-3, ex_l+10, ey+13, start=0, extent=180,
                     style="arc", outline=INK, width=2.4)
        c.create_arc(ex_r-10, ey-3, ex_r+10, ey+13, start=0, extent=180,
                     style="arc", outline=INK, width=2.4)

    c.create_polygon(cx-5, cy+13, cx+5, cy+13, cx, cy+19,
                     fill=NOSE, outline=INK, width=1.1, smooth=1)
    if mood == "over":
        c.create_arc(cx-9, cy+22, cx+9, cy+32, start=20, extent=140,
                     style="arc", outline=INK, width=1.5)
    elif cup_state and cup_state[0]=="drink" and 0.35<cup_state[1]<0.75:
        c.create_oval(cx-4, cy+19, cx+4, cy+25, fill="#5A2E28", outline=INK, width=1)
    else:
        c.create_line(cx, cy+19, cx, cy+22, fill=INK, width=1.2)
        c.create_arc(cx-9, cy+15, cx+1, cy+25, start=260, extent=90,
                     style="arc", outline=INK, width=1.4)
        c.create_arc(cx-1, cy+15, cx+9, cy+25, start=190, extent=90,
                     style="arc", outline=INK, width=1.4)
    for dy in (-2, 3):
        c.create_line(cx-40, cy+8+dy, cx-56, cy+6+dy, fill=INK2, width=1)
        c.create_line(cx+40, cy+8+dy, cx+56, cy+6+dy, fill=INK2, width=1)

    if cup_state:
        state, prog = cup_state
        base_x = cx-24; base_y = by2-24
        if state == "drink":
            if prog < 0.35:
                p = prog/0.35
                cur_x = int(base_x + (cx-6 - base_x)*p)
                cur_y = int(base_y + (cy+18 - base_y)*p - math.sin(p*math.pi)*8)
                tilt = int(p*35)
            elif prog < 0.75:
                cur_x, cur_y, tilt = cx-6, cy+18, 45
            else:
                p = (1-prog)/0.25
                cur_x = int(base_x + (cx-6 - base_x)*p)
                cur_y = int(base_y + (cy+18 - base_y)*p - math.sin(p*math.pi)*8)
                tilt = int(p*35)
        else:
            cur_x, cur_y, tilt = base_x, base_y, 0
        draw_cup(c, cur_x, cur_y, tilt=tilt)

def draw_text_bubble(c, cx, cy_top, w, h, text, bg="#FFFFFF"):
    x1, y1, x2, y2 = cx - w//2, cy_top, cx + w//2, cy_top + h
    rr(c, x1+2, y1+3, x2+2, y2+3, r=14, fill="#D9D8D0", outline="")
    rr(c, x1, y1, x2, y2, r=14, fill=bg, outline=LINE, width=1.5)
    tx = cx - 22
    c.create_polygon(tx-8, y2-1, tx+8, y2-1, tx, y2+11,
                     fill=bg, outline=LINE, width=1.5)
    c.create_line(tx-7, y2, tx+7, y2, fill=bg, width=3)
    c.create_text(cx, cy_top + h//2, text=text, font=("Microsoft YaHei UI", 10),
                  fill=INK, width=w-22, justify="center")

def draw_video_bubble(c, cx, cy_top, w, h, photo):
    x1, y1, x2, y2 = cx - w//2, cy_top, cx + w//2, cy_top + h
    rr(c, x1+3, y1+4, x2+3, y2+4, r=16, fill="#B8B4AC", outline="")
    rr(c, x1, y1, x2, y2, r=16, fill="#1A1B18", outline="#3a3a37", width=1.5)
    if photo is not None:
        c.create_image(cx, y1 + 28 + (h - 40)//2, image=photo)
    else:
        c.create_text(cx, y1 + h//2, text="正在唤醒摄像头…",
                      font=("Microsoft YaHei UI", 9), fill="#9BA098")
    c.create_text(x1+14, y1+13, text="● LIVE", anchor="w",
                  font=("Consolas", 9, "bold"), fill=SIG)
    c.create_text(x2-14, y1+13, text="CAM 0", anchor="e",
                  font=("Consolas", 8), fill="#8C918B")
    tx = cx - 22
    c.create_polygon(tx-8, y2-1, tx+8, y2-1, tx, y2+11,
                     fill="#1A1B18", outline="#3a3a37", width=1.5)
    c.create_line(tx-7, y2, tx+7, y2, fill="#1A1B18", width=3)

LOOKS_BG = {"seated":"#FFFFFF", "over":"#FBE3E0", "away":"#EDEDE8",
            "blocked":"#EDEDE8", "init":"#FFFFFF", "paused":"#EDEDE8"}

# ─────────── 喝水对话框 ───────────
class WaterDialog:
    def __init__(s,parent):
        s.val=None
        t=tk.Toplevel(parent); s.t=t; t.overrideredirect(1); t.attributes("-topmost",1); t.configure(bg=SIG)
        W,H=330,286; sw,sh=t.winfo_screenwidth(),t.winfo_screenheight()
        t.geometry("%dx%d+%d+%d"%(W,H,(sw-W)//2,(sh-H)//2))
        c=tk.Frame(t,bg=PAPER); c.pack(fill="both",expand=1,padx=2,pady=2)
        tk.Label(c,text="💧",font=("Segoe UI Emoji",34),bg=PAPER).pack(pady=(26,2))
        tk.Label(c,text="喝水啦",font=("Microsoft YaHei UI",16,"bold"),bg=PAPER,fg=INK).pack()
        tk.Label(c,text="这次喝了多少?",font=("Microsoft YaHei UI",10),bg=PAPER,fg=INK3).pack(pady=(3,18))
        row=tk.Frame(c,bg=PAPER); row.pack()
        for lab,ml in [("一口","100"),("半杯","150"),("一杯","250"),("一瓶","500")]:
            fr=tk.Frame(row,bg="#FFFFFF",highlightbackground=LINE,highlightthickness=1,cursor="hand2"); fr.pack(side="left",padx=6)
            l1=tk.Label(fr,text=lab,font=("Microsoft YaHei UI",10,"bold"),bg="#FFFFFF",fg=INK,width=5); l1.pack(pady=(9,0))
            l2=tk.Label(fr,text=ml+" ml",font=("Microsoft YaHei UI",8),bg="#FFFFFF",fg=INK3); l2.pack(pady=(0,9))
            def mk(fr,l1,l2,mm):
                def ent(e): fr.config(bg=SIG); l1.config(bg=SIG,fg="#fff"); l2.config(bg=SIG,fg="#fff")
                def lv(e): fr.config(bg="#FFFFFF"); l1.config(bg="#FFFFFF",fg=INK); l2.config(bg="#FFFFFF",fg=INK3)
                def cl(e): s.val=mm; s.t.destroy()
                for w in (fr,l1,l2): w.bind("<Enter>",ent); w.bind("<Leave>",lv); w.bind("<Button-1>",cl)
            mk(fr,l1,l2,int(ml))
        f2=tk.Frame(c,bg=PAPER); f2.pack(pady=(20,0))
        tk.Label(f2,text="或自己填",font=("Microsoft YaHei UI",9),bg=PAPER,fg=INK3).pack(side="left")
        s.e=tk.Entry(f2,font=("Microsoft YaHei UI",11),width=6,justify="center",bd=0,bg="#FFFFFF",highlightbackground=LINE,highlightthickness=1,relief="flat"); s.e.pack(side="left",padx=6,ipady=3)
        tk.Label(f2,text="ml",bg=PAPER,fg=INK3).pack(side="left")
        ok=tk.Label(c,text="确 定",font=("Microsoft YaHei UI",11,"bold"),bg=SIG,fg="#fff",cursor="hand2"); ok.pack(fill="x",padx=26,pady=(16,0),ipady=8)
        ok.bind("<Enter>",lambda e:ok.config(bg="#A54A28")); ok.bind("<Leave>",lambda e:ok.config(bg=SIG))
        ok.bind("<Button-1>",lambda e:s._c())
        tk.Label(c,text="点空白或按钮记录",font=("Microsoft YaHei UI",7),bg=PAPER,fg="#c9c4ba").pack(pady=(6,0))
        s.e.focus(); parent.wait_window(t)
    def _c(s):
        try: s.val=int(s.e.get())
        except: s.val=None
        s.t.destroy()

# ─────────── 每日报告 ───────────
def read_water_csv(day):
    p=wlog_path(day); out=[]
    if not os.path.exists(p): return out
    for ln in open(p,encoding="utf-8-sig").read().splitlines()[1:]:
        pp=ln.split(",")
        if len(pp)>=2 and pp[1].isdigit():
            out.append((pp[0], int(pp[1])))
    return out

def read_sit_csv(day):
    p=slog_path(day); out=[]
    if not os.path.exists(p): return out
    for ln in open(p,encoding="utf-8-sig").read().splitlines()[1:]:
        pp=ln.split(",")
        if len(pp)>=3:
            try: out.append((pp[0], pp[1], float(pp[2]), int(pp[3]) if len(pp)>3 else 0))
            except: pass
    return out

def svg_bar(data, w=560, h=180, target=None, unit=""):
    if not data: return '<div style="color:#8C918B;padding:24px 0">近 7 天暂无数据</div>'
    max_v=max(v for _,v in data)
    if target: max_v=max(max_v, target)
    if max_v==0: max_v=1
    bw=(w-60)/len(data); s=[]
    s.append(f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto">')
    for tick in (0.25, 0.5, 0.75, 1.0):
        y=h-30-(h-50)*tick
        s.append(f'<line x1="40" y1="{y:.0f}" x2="{w-10}" y2="{y:.0f}" stroke="#EDEDE8" stroke-width="1"/>')
        s.append(f'<text x="34" y="{y+3:.0f}" text-anchor="end" font-size="9" fill="#8C918B">{int(max_v*tick)}</text>')
    for i,(lab,v) in enumerate(data):
        bh=(v/max_v)*(h-50) if max_v else 0
        x=40+i*bw; bx=x+bw*0.18; bbw=bw*0.64
        color="#2F6E54" if target and v>=target else "#C15A34"
        s.append(f'<rect x="{bx:.1f}" y="{h-30-bh:.1f}" width="{bbw:.1f}" height="{bh:.1f}" rx="2" fill="{color}"/>')
        s.append(f'<text x="{x+bw/2:.1f}" y="{h-14}" text-anchor="middle" font-size="10" fill="#8C918B">{lab}</text>')
        s.append(f'<text x="{x+bw/2:.1f}" y="{h-33-bh:.1f}" text-anchor="middle" font-size="10" fill="#1A1B18" font-weight="600">{v}</text>')
    if target:
        ty=h-30-(target/max_v)*(h-50)
        s.append(f'<line x1="40" y1="{ty:.0f}" x2="{w-10}" y2="{ty:.0f}" stroke="#2F6E54" stroke-dasharray="4,3" stroke-width="1.5"/>')
        s.append(f'<text x="{w-14}" y="{ty-4:.0f}" text-anchor="end" font-size="10" fill="#2F6E54" font-weight="600">目标 {target}{unit}</text>')
    s.append('</svg>')
    return ''.join(s)

def gen_report_html():
    today=_today()
    days=[(datetime.now()-timedelta(days=i)).strftime("%Y%m%d") for i in range(6,-1,-1)]
    day_labels=[(datetime.now()-timedelta(days=i)).strftime("%m/%d") for i in range(6,-1,-1)]
    water_by_day=[(day_labels[i], sum(v for _,v in read_water_csv(d))) for i,d in enumerate(days)]
    sit_by_day=[(day_labels[i], int(sum(m for _,_,m,_ in read_sit_csv(d)))) for i,d in enumerate(days)]
    tw=read_water_csv(today); ts=read_sit_csv(today)
    total_w=sum(v for _,v in tw); total_sit=int(sum(m for _,_,m,_ in ts))
    over_cnt=sum(1 for _,_,_,o in ts if o); long_sit=max((m for _,_,m,_ in ts), default=0)
    water_rows="".join(f'<tr><td>{t}</td><td>{v} ml</td></tr>' for t,v in tw) or '<tr><td colspan="2" style="color:#8C918B">还没喝过水</td></tr>'
    sit_rows="".join(f'<tr><td>{a} → {b}</td><td>{m:.1f} 分</td><td>{"⚠️" if o else "·"}</td></tr>' for a,b,m,o in ts) or '<tr><td colspan="3" style="color:#8C918B">还没坐过</td></tr>'
    water_pct=min(100, int(total_w/WATER_TARGET_ML*100)) if WATER_TARGET_ML else 0
    html=f'''<!doctype html><html><head><meta charset="utf-8">
<title>盯盯喵 · {today} 健康报告</title>
<style>
:root{{--ink:#1A1B18;--ink2:#585C57;--ink3:#8C918B;--paper:#F7F6F3;--line:#E7E6E0;--sig:#C15A34;--good:#2F6E54}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--paper);color:var(--ink);line-height:1.6;padding:40px 24px}}
.wrap{{max-width:920px;margin:0 auto}}
h1{{font-size:26px;font-weight:800;letter-spacing:-.02em}}
h2{{font-size:16px;font-weight:700;margin:32px 0 12px;color:var(--ink)}}
.hint{{color:var(--ink3);font-size:13px;margin-top:4px}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:24px}}
.card{{background:#fff;border:1px solid var(--line);padding:18px;border-radius:8px}}
.card .k{{font-size:11px;color:var(--ink3);letter-spacing:.06em;text-transform:uppercase}}
.card .v{{font-size:28px;font-weight:800;margin-top:6px;letter-spacing:-.02em}}
.card .u{{font-size:12px;color:var(--ink3);font-weight:400}}
.progress{{height:8px;background:var(--line);border-radius:4px;margin-top:10px;overflow:hidden}}
.progress span{{display:block;height:100%;background:var(--sig)}}
.chart{{background:#fff;border:1px solid var(--line);padding:20px;border-radius:8px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden;font-size:13px}}
th,td{{padding:10px 14px;text-align:left;border-bottom:1px solid var(--line)}}
th{{background:#F7F6F3;color:var(--ink2);font-weight:600;font-size:11px;letter-spacing:.06em;text-transform:uppercase}}
tr:last-child td{{border-bottom:none}}
footer{{margin-top:40px;color:var(--ink3);font-size:12px;text-align:center}}
@media(max-width:640px){{.cards{{grid-template-columns:repeat(2,1fr)}}.grid2{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">
<h1>盯盯喵 · 今日健康报告</h1>
<div class="hint">{datetime.now().strftime("%Y-%m-%d %H:%M")} · 数据全部来自本地日志</div>

<div class="cards">
  <div class="card"><div class="k">今日饮水</div><div class="v">{total_w}<span class="u"> ml</span></div>
    <div class="progress"><span style="width:{water_pct}%"></span></div>
    <div class="hint" style="margin-top:6px">目标 {WATER_TARGET_ML} ml · 完成 {water_pct}%</div></div>
  <div class="card"><div class="k">今日坐时长</div><div class="v">{total_sit}<span class="u"> 分</span></div>
    <div class="hint" style="margin-top:6px">共 {len(ts)} 段</div></div>
  <div class="card"><div class="k">最长连续坐</div><div class="v">{int(long_sit)}<span class="u"> 分</span></div>
    <div class="hint" style="margin-top:6px">{"已经太久了~" if long_sit>=SIT_LIMIT_MIN else "还行"}</div></div>
  <div class="card"><div class="k">久坐超限次</div><div class="v">{over_cnt}<span class="u"> 次</span></div>
    <div class="hint" style="margin-top:6px">超 {SIT_LIMIT_MIN} 分才算</div></div>
</div>

<h2>近 7 天饮水趋势</h2>
<div class="chart">{svg_bar(water_by_day, target=WATER_TARGET_ML, unit="ml")}</div>

<h2>近 7 天坐时长</h2>
<div class="chart">{svg_bar(sit_by_day, target=int(SIT_LIMIT_MIN*6), unit="分")}</div>

<div class="grid2">
  <div><h2>今日饮水明细</h2><table><thead><tr><th>时间</th><th>量</th></tr></thead><tbody>{water_rows}</tbody></table></div>
  <div><h2>今日坐着的段</h2><table><thead><tr><th>时段</th><th>时长</th><th>超限</th></tr></thead><tbody>{sit_rows}</tbody></table></div>
</div>

<footer>盯盯喵 · 数据不出你的电脑 · 生成于 {datetime.now().strftime("%H:%M:%S")}</footer>
</div></body></html>'''
    out=os.path.join(LOG_DIR, "report.html")
    with open(out,"w",encoding="utf-8") as f: f.write(html)
    return out

def open_report():
    try:
        p=gen_report_html()
        webbrowser.open("file:///"+p.replace("\\","/"))
    except Exception:
        pass

# ─────────── 开机自启 ───────────
def autostart_lnk():
    return os.path.join(os.environ.get("APPDATA",""),
                        "Microsoft","Windows","Start Menu","Programs","Startup","盯盯喵.lnk")

def is_autostart_on():
    return os.path.exists(autostart_lnk())

def set_autostart(on):
    lnk=autostart_lnk()
    if on:
        vbs=os.path.join(_self, "盯盯喵.vbs")
        if not os.path.exists(vbs): return False
        ps=f'''$s = New-Object -ComObject WScript.Shell
$l = $s.CreateShortcut("{lnk}")
$l.TargetPath = "{vbs}"
$l.WorkingDirectory = "{_self}"
$l.Save()'''
        try:
            subprocess.run(["powershell","-NoProfile","-WindowStyle","Hidden","-Command",ps],
                           capture_output=True, timeout=8)
            return os.path.exists(lnk)
        except Exception: return False
    else:
        try:
            if os.path.exists(lnk): os.remove(lnk)
            return True
        except Exception: return False

# ─────────── 托盘图标 ───────────
def make_tray_icon():
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(10, 22), (16, 4), (28, 20)], fill=(184,180,172,255), outline=(88,92,87,255))
    d.polygon([(36, 20), (48, 4), (54, 22)], fill=(184,180,172,255), outline=(88,92,87,255))
    d.ellipse([8, 14, 56, 58], fill=(184,180,172,255), outline=(88,92,87,255), width=1)
    d.ellipse([20, 30, 28, 40], fill=(26,27,24,255))
    d.ellipse([36, 30, 44, 40], fill=(26,27,24,255))
    d.polygon([(30, 42), (34, 42), (32, 46)], fill=(232,165,160,255))
    d.arc([28, 44, 36, 52], 0, 180, fill=(26,27,24,255), width=2)
    return im

def start_tray(pet_ref):
    try:
        import pystray
    except Exception:
        return
    icon_img = make_tray_icon()
    def eyes_item(icon, item): STATE["_toggle_eyes"] = True
    def pause_item(icon, item): STATE["paused"] = not STATE["paused"]
    def autostart_item(icon, item): set_autostart(not is_autostart_on())
    def report_item(icon, item): open_report()
    def quit_item(icon, item):
        STATE["_quit"] = True
        icon.stop()
    menu = pystray.Menu(
        pystray.MenuItem("看今日报告", report_item),
        pystray.MenuItem("睁眼 / 收起画面", eyes_item),
        pystray.MenuItem("暂停检测", pause_item, checked=lambda i: STATE["paused"]),
        pystray.MenuItem("开机自启", autostart_item, checked=lambda i: is_autostart_on()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", quit_item),
    )
    icon = pystray.Icon("dingdingmeow", icon_img, "盯盯喵", menu)
    pet_ref._tray = icon
    icon.run()

# ─────────── 主窗 ───────────
class Pet:
    def __init__(s):
        r = tk.Tk(); s.r = r
        r.overrideredirect(True); r.attributes("-topmost", True); r.attributes("-alpha", 0.98)
        try: r.wm_attributes("-transparentcolor", TRANS)
        except tk.TclError: pass

        s.W = 300; s.H_CLOSED = 260; s.H_OPEN = 460
        s.eyes_open = False; s.blink = False
        s.tail_ang = 0; s.breath = 0; s.anim_t = 0
        s._blink_next = time.time() + 4
        s._tray = None

        s.canvas = tk.Canvas(r, width=s.W, height=s.H_OPEN, bg=TRANS, highlightthickness=0)
        s.canvas.pack()
        s.canvas.bind("<ButtonPress-1>", s._press)
        s.canvas.bind("<B1-Motion>", s._motion)
        s.canvas.bind("<ButtonRelease-1>", s._release)
        s.canvas.bind("<Button-3>", s._menu_close)

        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        s.ax = sw - s.W - 30; s.ay = sh - s.H_OPEN - 40
        r.geometry("%dx%d+%d+%d" % (s.W, s.H_OPEN, s.ax, s.ay))

        s._cur_h = s.H_CLOSED
        s._photo = None; s._dragging = False

        threading.Thread(target=loop, daemon=True).start()
        threading.Thread(target=start_tray, args=(s,), daemon=True).start()
        s.tick()
        r.mainloop()

    def _press(s, e):
        s._px, s._py = e.x_root, e.y_root
        s._wx, s._wy = s.r.winfo_x(), s.r.winfo_y()
        s._dragging = False
        s._click_xy = (e.x, e.y)

    def _motion(s, e):
        dx, dy = e.x_root - s._px, e.y_root - s._py
        if abs(dx) + abs(dy) > 4:
            s._dragging = True
            s.r.geometry("+%d+%d" % (s._wx + dx, s._wy + dy))

    def _release(s, e):
        if s._dragging: return
        x, y = s._click_xy
        cat_cy = s.H_OPEN - 100
        if s.W//2 - 34 <= x <= s.W//2 + 34 and cat_cy - 22 <= y <= cat_cy + 14:
            s.toggle_eyes()

    def _menu_close(s, e):
        m = tk.Menu(s.r, tearoff=0)
        m.add_command(label="看今日报告", command=open_report)
        m.add_command(label="睁眼 / 收起画面", command=s.toggle_eyes)
        m.add_command(label="暂停检测" if not STATE["paused"] else "恢复检测",
                      command=lambda: STATE.update(paused=not STATE["paused"]))
        m.add_separator()
        m.add_command(label="退出盯盯喵", command=s._quit)
        try: m.tk_popup(e.x_root, e.y_root)
        finally: m.grab_release()

    def toggle_eyes(s):
        s.eyes_open = not s.eyes_open
        target = s.H_OPEN if s.eyes_open else s.H_CLOSED
        s._animate_h(target)

    def _animate_h(s, target_h, steps=8):
        start = s._cur_h; delta = (target_h - start) / steps
        def step(i):
            s._cur_h = int(start + delta * (i+1))
            if i == steps - 1: s._cur_h = target_h
            if i < steps - 1: s.r.after(24, lambda: step(i+1))
        step(0)

    def _quit(s):
        STATE["_quit"] = True
        try:
            if s._tray: s._tray.stop()
        except Exception: pass
        s.r.destroy()

    def tick(s):
        if STATE.get("_toggle_eyes"):
            STATE["_toggle_eyes"] = False
            s.toggle_eyes()
        if STATE.get("_quit"):
            s._quit(); return

        if STATE["drink"]:
            STATE["drink"] = False
            d = WaterDialog(s.r)
            if d.val:
                STATE["water"] += d.val
                wlog(d.val, STATE["water"])
                STATE["last_drink_ts"] = time.time()

        now = time.time()
        if s.eyes_open and now >= s._blink_next:
            s.blink = True
            s.r.after(160, s._end_blink)
            s._blink_next = now + 4 + (s.anim_t % 4)

        s.anim_t += 1
        s.breath = 1 if (s.anim_t // 4) % 2 else -1
        s.tail_ang = int(14 * ((s.anim_t % 24) / 24 - 0.5))

        s.redraw()

        if STATE["mode"] == "over":
            s.r.geometry("+%d+%d" % (s.r.winfo_x() + (3 if s.anim_t % 2 else -3), s.r.winfo_y()))
        s.r.after(200, s.tick)

    def _end_blink(s):
        s.blink = False; s.redraw()

    def redraw(s):
        c = s.canvas
        c.delete("all")
        mm = STATE["mode"]
        bg = LOOKS_BG.get(mm, "#FFFFFF")
        cx = s.W // 2
        cat_cy = s.H_OPEN - 100
        now = time.time()

        msg = {
            "seated":"陪你工作 · 已坐 " + dur(STATE["sit"]),
            "away":  "咦你去哪了 · 离开 " + dur(STATE["away"]),
            "over":  "坐太久啦 快起来动动!",
            "blocked":"喵…看不见了",
            "init":  "启动中，找找你在不在…",
            "paused":"检测暂停中 · 右键菜单恢复"
        }.get(mm, "准备好啦~")
        lines=[msg, "今日饮水 %d / %d ml"%(STATE["water"], WATER_TARGET_ML)]
        if now < STATE.get("nudge_until",0) and mm in ("seated","over"):
            lines.append("💧 喝口水吧~")
        full = "\n".join(lines)

        bubble_h = 82 if len(lines)>2 else 62
        bubble_top = cat_cy - 40 - 22 - bubble_h
        draw_text_bubble(c, cx, bubble_top, w=250, h=bubble_h, text=full, bg=bg)

        video_h = 175; video_w = 250
        span = s.H_OPEN - s.H_CLOSED
        prog = 1.0 if s.eyes_open else 0.0
        if span > 0: prog = max(0.0, min(1.0, (s._cur_h - s.H_CLOSED) / span))
        if prog > 0.05:
            v_hidden = bubble_top - 4
            vtop = int(v_hidden + (12 - v_hidden) * prog)
            fr = STATE.get("frame"); photo = None
            if fr is not None:
                try:
                    im = Image.fromarray(fr).resize((video_w - 22, video_h - 46))
                    photo = ImageTk.PhotoImage(im)
                    s._photo = photo
                except Exception: photo = None
            draw_video_bubble(c, cx, vtop, video_w, video_h, photo)

        if s._cur_h < s.H_OPEN:
            hide = s.H_OPEN - s._cur_h
            c.create_rectangle(0, 0, s.W, hide, fill=TRANS, outline="")

        cup_state = None
        if now < STATE.get("drink_anim_until", 0):
            elapsed = DRINK_ANIM_SEC - (STATE["drink_anim_until"] - now)
            drp = elapsed / DRINK_ANIM_SEC
            cup_state = ("drink", drp)
        elif now < STATE.get("cup_hold_until", 0) or now < STATE.get("nudge_until", 0):
            cup_state = ("hold", 0)

        draw_cat(c, cx, cat_cy, eyes_open=s.eyes_open, blink=s.blink,
                 mood=mm, breath=s.breath, tail_ang=s.tail_ang, cup_state=cup_state)

        tip = "右键菜单"
        if STATE["paused"]: tip = "已暂停 · 右键菜单"
        c.create_text(s.W - 8, s.H_OPEN - 6, text=tip,
                      anchor="e", font=("Microsoft YaHei UI", 7), fill=INK3)


if __name__ == "__main__":
    Pet()
