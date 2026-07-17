# -*- coding: utf-8 -*-
"""盯盯喵 v1.5-dev：健康检测、延时摄影与可换肤桌面猫。纯本地。"""
import sys, os, threading, time, shutil, tempfile, math, subprocess, webbrowser
import tkinter as tk
from datetime import datetime, timedelta
import center_nudge
import cat_visual
import cat_sprites
from camera_capture import CameraCapture, camera_needs_manual_restart, is_camera_signal_missing
import report_icon
import skin_system
import timelapse
import window_placement
from cup_detection import (
    decode_cup_boxes,
    face_focus_region,
    is_cup_near_face,
    largest_face,
    remap_boxes,
)
from face_detection import detect_face_boxes, load_face_cascades
from onboarding import should_show_onboarding, show_onboarding as open_onboarding
from report_icon import report_favicon_link
from session_state import SESSION_RESUME_SEC, is_present, is_session_locked, session_gap_expired
from status_label import render_status_label
from ui_behavior import compact_status, detail_bubble_top, pointer_keeps_details_open, status_label_y, video_bubble_top
from water_input import (
    WATER_ACTION_RADIUS,
    WATER_DIALOG_HEIGHT,
    WATER_DIALOG_RADIUS,
    WATER_DIALOG_WIDTH,
    WATER_PRESET_RADIUS,
    WATER_PRESETS,
    parse_water_amount,
)
from water_reminder import (
    DEFAULT_WATER_REMINDER_MIN,
    WATER_NUDGE_DISPLAY_SEC,
    WATER_REMINDER_OPTIONS,
    load_water_reminder,
    reminder_due,
    save_water_reminder,
    validate_water_reminder,
)
if getattr(sys, "frozen", False):
    _self = os.path.dirname(os.path.abspath(sys.executable))
else:
    _self = os.path.dirname(os.path.abspath(__file__))
import cv2
from PIL import Image, ImageTk, ImageDraw, ImageOps

# ─────────── 参数 ───────────
CAM_INDEX=0; CHECK_EVERY=0.5; SIT_LIMIT_MIN=45; GRACE_SEC=25; OVER_GRACE=5; BLOCK_LEVEL=22
CUP_HITS_NEEDED=3
WATER_TARGET_ML=2000
DRINK_ANIM_SEC=2.4
CUP_HOLD_AFTER_DRINK=6

INK="#1A1B18"; INK2="#585C57"; INK3="#8C918B"; PAPER="#F7F6F3"; SIG="#C15A34"; LINE="#D9D8D0"
TRANS="#FE00FE"

TEST = len(sys.argv)>1 and sys.argv[1]=="test"
if TEST: SIT_LIMIT_MIN, GRACE_SEC, OVER_GRACE = 0.7, 8, 3

LOG_DIR=os.path.join(_self,"logs"); os.makedirs(LOG_DIR, exist_ok=True)
TIMELAPSE_DIR=os.path.join(LOG_DIR,"timelapse")
SETTINGS_PATH=os.path.join(_self,"settings.json")
def _today(): return datetime.now().strftime("%Y%m%d")
def wlog_path(day=None): return os.path.join(LOG_DIR,"water_%s.csv"%(day or _today()))
def slog_path(day=None): return os.path.join(LOG_DIR,"sit_%s.csv"%(day or _today()))

# ─────────── 模型 ───────────
face_c,face_alt,face_profile=load_face_cascades(cv2)
m=os.path.join(_self,"models"); tmp=tempfile.gettempdir()
cfg=os.path.join(tmp,"y4t.cfg"); wp=os.path.join(tmp,"y4t.weights")
shutil.copy(os.path.join(m,"yolov4-tiny.cfg"),cfg); shutil.copy(os.path.join(m,"yolov4-tiny.weights"),wp)
net=cv2.dnn.readNetFromDarknet(cfg,wp); LN=net.getUnconnectedOutLayersNames()
TIMELAPSE=timelapse.TimelapseRecorder(
    cv2,
    TIMELAPSE_DIR,
)

def face_boxes(gray):
    return detect_face_boxes(gray,face_c,face_alt,face_profile)

def _cup_boxes_once(frame):
    H,W=frame.shape[:2]
    net.setInput(cv2.dnn.blobFromImage(frame,1/255.0,(416,416),swapRB=True,crop=False))
    return decode_cup_boxes(net.forward(LN),W,H)

def cup_boxes(frame,faces):
    face=largest_face(faces)
    if face is None:
        return _cup_boxes_once(frame)
    x1,y1,x2,y2=face_focus_region(frame.shape,face)
    if x2-x1<40 or y2-y1<40:
        return _cup_boxes_once(frame)
    focused=_cup_boxes_once(frame[y1:y2,x1:x2])
    return remap_boxes(focused,x1,y1)

# ─────────── 日志 ───────────
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
        return datetime.now().replace(hour=hh,minute=mm,second=ss,microsecond=0).timestamp()
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

def open_logs_folder():
    try: os.startfile(LOG_DIR)
    except Exception: pass

def open_timelapse_folder():
    os.makedirs(TIMELAPSE_DIR, exist_ok=True)
    try: os.startfile(TIMELAPSE_DIR)
    except Exception: pass

# ─────────── 状态 ───────────
_initial_drink_ts=last_drink_ts_today()
_started_at=time.time()
STATE={
    "mode":"init","sit":0,"away":0,
    "water":today_total(),"drink":False,"frame":None,
    "cup_hits":0, "last_drink_ts":_initial_drink_ts,
    "drink_anim_until":0.0, "cup_hold_until":0.0, "nudge_until":0.0,
    "water_reminder_anchor":_initial_drink_ts or _started_at,
    "last_nudge_ts":0.0,
    "water_reminder_min":load_water_reminder(SETTINGS_PATH),
    "center_nudge_enabled":center_nudge.load_enabled(SETTINGS_PATH),
    "skin_id":skin_system.load_skin(SETTINGS_PATH,cat_sprites.asset_root()),
    "detector_heartbeat":time.time(),
    "detector_error":None,
    "camera_off":False,
    "timelapse_active":False,
    "timelapse_frames":0,
    "timelapse_last_path":None,
    "timelapse_saved_until":0.0,
    "timelapse_error":None,
    "sit_session_start":None, "over_flag":False,
    "paused":False, "locked":False, "_toggle_eyes":False, "_show_onboarding":False, "_quit":False,
    "_manual_drink":False, "_toggle_timelapse":False, "_skin_request":None,
}

def set_water_reminder(minutes):
    minutes=validate_water_reminder(minutes)
    if minutes is None: return False
    try: save_water_reminder(SETTINGS_PATH,minutes)
    except OSError: return False
    STATE["water_reminder_min"]=minutes
    return True


def start_detection():
    STATE.update(paused=False,camera_off=False,mode="init",frame=None)


def toggle_detection():
    if STATE.get("paused") or STATE.get("camera_off"):
        start_detection()
    else:
        STATE.update(paused=True,camera_off=False)


def set_center_nudge_enabled(enabled):
    try: enabled=center_nudge.save_enabled(SETTINGS_PATH,enabled)
    except OSError: return False
    STATE["center_nudge_enabled"]=enabled
    return True

def loop():
    camera=CameraCapture(cv2,CAM_INDEX)
    last_seen=away_start=None; sit_start=None; session_away_start=None; was_drinking=False; prev_mode="init"
    read_failures=no_signal_frames=0
    while True:
        if STATE["_quit"]:
            camera.close()
            break
        now=time.time()
        STATE["detector_heartbeat"]=now
        locked=is_session_locked()
        camera.set_locked(locked,now)
        if locked:
            read_failures=no_signal_frames=0
            if prev_mode in ("seated","over") and sit_start is not None:
                slog_write(sit_start,now,STATE["over_flag"])
            sit_start=None; session_away_start=None; last_seen=None; was_drinking=False; STATE["cup_hits"]=0
            STATE["sit_session_start"]=None
            if away_start is None: away_start=now
            STATE.update(mode="away",locked=True,away=now-away_start,sit=0,frame=None)
            prev_mode="away"
            time.sleep(CHECK_EVERY)
            continue
        STATE["locked"]=False
        if STATE["paused"] or STATE.get("camera_off"):
            camera.suspend(now,retry_delay=0.5)
            STATE["mode"]="camera_off" if STATE.get("camera_off") else "paused"
            time.sleep(0.5); continue
        ok,fr=camera.read(now)
        if not ok or fr is None:
            read_failures+=1
            no_signal_frames=0
            now=time.time()
            if away_start is None: away_start=last_seen if last_seen else now
            if sit_start is not None and session_away_start is None:
                session_away_start=now
            expired=session_gap_expired(
                session_away_start,
                now,
                resume_seconds=SESSION_RESUME_SEC,
            )
            if sit_start is not None and expired:
                slog_write(sit_start,session_away_start,STATE["over_flag"])
                sit_start=None; session_away_start=None
                STATE["sit_session_start"]=None
            needs_restart=camera_needs_manual_restart(read_failures=read_failures)
            if needs_restart and sit_start is not None:
                slog_write(sit_start,session_away_start or now,STATE["over_flag"])
                sit_start=None; session_away_start=None
                STATE["sit_session_start"]=None
                camera.suspend(now,retry_delay=0.5)
            kept_sit=now-sit_start if sit_start is not None else 0
            STATE.update(
                mode="camera_off" if needs_restart else "away",
                camera_off=needs_restart,
                locked=False,
                away=now-away_start,
                sit=kept_sit,
                frame=None,
            )
            prev_mode=STATE["mode"]
            time.sleep(CHECK_EVERY)
            continue
        read_failures=0
        if is_camera_signal_missing(fr):
            no_signal_frames+=1
        else:
            no_signal_frames=0
        if camera_needs_manual_restart(no_signal_frames=no_signal_frames):
            if prev_mode in ("seated","over") and sit_start is not None:
                slog_write(sit_start,now,STATE["over_flag"])
            sit_start=None; session_away_start=None; last_seen=None; was_drinking=False
            STATE["cup_hits"]=0; STATE["sit_session_start"]=None
            camera.suspend(now,retry_delay=0.5)
            STATE.update(mode="camera_off",camera_off=True,frame=None,sit=0)
            prev_mode="camera_off"
            time.sleep(CHECK_EVERY)
            continue
        gray=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY); now=time.time()
        blocked=gray.mean()<BLOCK_LEVEL
        fb=[] if blocked else face_boxes(cv2.equalizeHist(gray))
        if fb: last_seen=now
        eff=OVER_GRACE if STATE["mode"]=="over" else GRACE_SEC
        present=is_present(blocked,False,last_seen,now,eff)
        cups=[]
        if present:
            away_start=None
            session_away_start=None
            if sit_start is None:
                sit_start=last_seen
                STATE["sit_session_start"]=sit_start; STATE["over_flag"]=False
            sit=now-sit_start
            new_mode="over" if sit/60>=SIT_LIMIT_MIN else "seated"
            if new_mode=="over": STATE["over_flag"]=True
            STATE.update(mode=new_mode, sit=sit, away=0)
            cups=cup_boxes(fr,fb)
            drinking=any(is_cup_near_face(f,c) for f in fb for c in cups)
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
            if reminder_due(
                now,
                STATE.get("water_reminder_anchor",_started_at),
                STATE.get("last_nudge_ts",0),
                STATE.get("water_reminder_min",DEFAULT_WATER_REMINDER_MIN),
                STATE["water"],
                WATER_TARGET_ML,
            ):
                STATE["nudge_until"]=now+WATER_NUDGE_DISPLAY_SEC
                STATE["last_nudge_ts"]=now
        else:
            if away_start is None: away_start=last_seen if last_seen else now
            if sit_start is not None and session_away_start is None:
                session_away_start=now
            expired=session_gap_expired(
                session_away_start,
                now,
                resume_seconds=SESSION_RESUME_SEC,
            )
            if sit_start is not None and expired:
                slog_write(sit_start,session_away_start,STATE["over_flag"])
                sit_start=None; session_away_start=None
                STATE["sit_session_start"]=None
            was_drinking=False; STATE["cup_hits"]=0
            kept_sit=now-sit_start if sit_start is not None else 0
            STATE.update(
                mode=("blocked" if blocked else "away"),
                away=now-away_start,
                sit=kept_sit,
            )
        prev_mode=STATE["mode"]
        disp=fr.copy()
        for (x,y,w,h) in fb: cv2.rectangle(disp,(x,y),(x+w,y+h),(0,220,0),2)
        for (x,y,w,h) in cups: cv2.rectangle(disp,(x,y),(x+w,y+h),(0,160,255),2)
        STATE["frame"]=cv2.cvtColor(cv2.resize(disp,(160,120)),cv2.COLOR_BGR2RGB)
        try:
            if TIMELAPSE.capture(fr,now=now,eligible=present and not blocked):
                STATE["timelapse_frames"]=TIMELAPSE.frame_count
            STATE["timelapse_active"]=TIMELAPSE.active
        except RuntimeError as exc:
            TIMELAPSE.stop(now=now)
            STATE["timelapse_active"]=False
            STATE["timelapse_error"]=str(exc)
        time.sleep(CHECK_EVERY)


def detection_supervisor():
    while not STATE.get("_quit"):
        try:
            STATE["detector_error"]=None
            loop()
        except Exception as exc:
            STATE.update(
                mode="away",
                frame=None,
                detector_error=repr(exc),
                detector_heartbeat=time.time(),
            )
            time.sleep(1.0)

def dur(s):
    mm,x=divmod(int(s),60); return "%d分%d秒"%(mm,x) if mm else "%d秒"%x

# ─────────── UI 绘制 ───────────
def rr(c, x1, y1, x2, y2, r=12, **kw):
    pts=[x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2,
         x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
    return c.create_polygon(pts, smooth=True, **kw)

def draw_text_bubble(c, cx, cy_top, w, h, text, bg="#FFFFFF"):
    """文字气泡+底部两个按钮。返回按钮 hitbox 字典。"""
    x1, y1, x2, y2 = cx - w//2, cy_top, cx + w//2, cy_top + h
    rr(c, x1+2, y1+3, x2+2, y2+3, r=14, fill="#D9D8D0", outline="")
    rr(c, x1, y1, x2, y2, r=14, fill=bg, outline=LINE, width=1.3)
    tx = cx - 20
    c.create_polygon(tx-8, y2-1, tx+8, y2-1, tx, y2+11,
                     fill=bg, outline=LINE, width=1.3)
    c.create_line(tx-7, y2, tx+7, y2, fill=bg, width=3)

    # 文字：顶部 anchor 定位，确定不会压边
    c.create_text(cx, y1 + 12, text=text,
                  font=("Microsoft YaHei UI", 10),
                  fill=INK, width=w-18, justify="center", anchor="n")
    # 按钮区：底部固定 24px 高
    btn_h = 20
    btn_w = 66
    gap = 6
    by = y2 - btn_h - 8
    # 分隔线在按钮上方 6px
    c.create_line(x1+14, by-6, x2-14, by-6, fill=LINE, width=1)
    lx = cx - btn_w - gap//2
    rx_ = cx + gap//2
    rr(c, lx, by, lx+btn_w, by+btn_h, r=8, fill="#F5EEE8", outline=SIG, width=1)
    c.create_text(lx+btn_w/2, by+btn_h/2+1, text="📁  日志",
                  font=("Microsoft YaHei UI", 9), fill=INK)
    rr(c, rx_, by, rx_+btn_w, by+btn_h, r=8, fill=SIG, outline="")
    c.create_text(rx_+btn_w/2, by+btn_h/2+1, text="📊  报告",
                  font=("Microsoft YaHei UI", 9, "bold"), fill="#fff")
    return {"log":(lx, by, lx+btn_w, by+btn_h),
            "report":(rx_, by, rx_+btn_w, by+btn_h)}

def draw_video_bubble(c, cx, cy_top, w, h, photo):
    x1, y1, x2, y2 = cx - w//2, cy_top, cx + w//2, cy_top + h
    rr(c, x1+2, y1+3, x2+2, y2+3, r=14, fill="#B8B4AC", outline="")
    rr(c, x1, y1, x2, y2, r=14, fill="#1A1B18", outline="#3a3a37", width=1.3)
    if photo is not None:
        c.create_image(cx, y1 + 24 + (h - 34)//2, image=photo)
    else:
        c.create_text(cx, y1 + h//2, text="正在唤醒摄像头…",
                      font=("Microsoft YaHei UI", 8), fill="#9BA098")
    c.create_text(x1+10, y1+11, text="● 低频预览", anchor="w",
                  font=("Microsoft YaHei UI", 7, "bold"), fill=SIG)
    c.create_text(x2-10, y1+11, text="省 CPU", anchor="e",
                  font=("Microsoft YaHei UI", 7), fill="#8C918B")
    tx = cx - 18
    c.create_polygon(tx-7, y2-1, tx+7, y2-1, tx, y2+9,
                     fill="#1A1B18", outline="#3a3a37", width=1.3)
    c.create_line(tx-6, y2, tx+6, y2, fill="#1A1B18", width=3)

LOOKS_BG = {"seated":"#FFFFFF", "over":"#FBE3E0", "away":"#EDEDE8",
            "blocked":"#EDEDE8", "camera_off":"#EDEDE8",
            "init":"#FFFFFF", "paused":"#EDEDE8"}

# ─────────── 喝水对话框 ───────────
class WaterDialog:
    def _drag_start(s,event):
        s._drag_origin=(event.x_root,event.y_root,s.t.winfo_x(),s.t.winfo_y())

    def _drag_move(s,event):
        start_x,start_y,window_x,window_y=s._drag_origin
        s.t.geometry("+%d+%d"%(window_x+event.x_root-start_x,window_y+event.y_root-start_y))

    def _make_draggable(s,*widgets):
        for widget in widgets:
            widget.configure(cursor="fleur")
            widget.bind("<ButtonPress-1>",s._drag_start)
            widget.bind("<B1-Motion>",s._drag_move)

    def __init__(s,parent):
        s.val=None
        t=tk.Toplevel(parent); s.t=t; t.overrideredirect(1); t.attributes("-topmost",1); t.configure(bg=TRANS)
        try: t.wm_attributes("-transparentcolor",TRANS)
        except tk.TclError: pass
        W,H=WATER_DIALOG_WIDTH,WATER_DIALOG_HEIGHT; sw,sh=t.winfo_screenwidth(),t.winfo_screenheight()
        t.geometry("%dx%d+%d+%d"%(W,H,(sw-W)//2,(sh-H)//2))
        shell=tk.Canvas(t,width=W,height=H,bg=TRANS,highlightthickness=0)
        shell.pack(fill="both",expand=True)
        rr(shell,11,13,W-7,H-7,r=WATER_DIALOG_RADIUS,fill="#C9C3BA",outline="")
        rr(shell,7,7,W-11,H-11,r=WATER_DIALOG_RADIUS,fill=PAPER,outline="#E7E2DA",width=1)
        c=tk.Frame(shell,bg=PAPER)
        shell.create_window(W//2,H//2,window=c,width=W-38,height=H-38)

        close=tk.Canvas(c,width=30,height=30,bg=PAPER,highlightthickness=0,cursor="hand2")
        close.place(relx=1.0,x=-2,y=-2,anchor="ne")
        def draw_close(active=False):
            close.delete("all")
            close.create_oval(3,3,27,27,fill="#F5EEE8" if active else "#ECE8E1",outline="")
            close.create_text(15,15,text="×",font=("Microsoft YaHei UI",13),fill=SIG if active else INK3)
        draw_close()
        close.bind("<Enter>",lambda e:draw_close(True))
        close.bind("<Leave>",lambda e:draw_close(False))
        close.bind("<Button-1>",lambda e:s._cancel())

        icon=tk.Label(c,text="💧",font=("Segoe UI Emoji",32),bg=PAPER)
        icon.pack(pady=(12,0))
        title=tk.Label(c,text="喝水啦",font=("Microsoft YaHei UI",17,"bold"),bg=PAPER,fg=INK)
        title.pack()
        subtitle=tk.Label(c,text="这次喝了多少？",font=("Microsoft YaHei UI",10),bg=PAPER,fg=INK3)
        subtitle.pack(pady=(2,15))
        row=tk.Frame(c,bg=PAPER); row.pack()
        for lab,ml in WATER_PRESETS:
            card=tk.Canvas(row,width=67,height=62,bg=PAPER,highlightthickness=0,cursor="hand2")
            card.pack(side="left",padx=3)
            def draw_card(canvas,label,amount,active=False):
                canvas.delete("all")
                fill=SIG if active else "#FFFFFF"
                rr(canvas,2,2,65,60,r=WATER_PRESET_RADIUS,fill=fill,outline="" if active else LINE,width=1)
                canvas.create_text(33,23,text=label,font=("Microsoft YaHei UI",9,"bold"),fill="#fff" if active else INK)
                canvas.create_text(33,42,text=str(amount)+" ml",font=("Microsoft YaHei UI",8),fill="#fff" if active else INK3)
            draw_card(card,lab,ml)
            card.bind("<Enter>",lambda e,cv=card,la=lab,mm=ml:draw_card(cv,la,mm,True))
            card.bind("<Leave>",lambda e,cv=card,la=lab,mm=ml:draw_card(cv,la,mm,False))
            card.bind("<Button-1>",lambda e,mm=ml:s._choose(mm))

        f2=tk.Frame(c,bg=PAPER); f2.pack(pady=(18,0))
        tk.Label(f2,text="或自己填",font=("Microsoft YaHei UI",9),bg=PAPER,fg=INK3).pack(side="left")
        entry_shell=tk.Frame(f2,bg="#FFFFFF",highlightbackground="#E1DCD4",highlightthickness=1)
        entry_shell.pack(side="left",padx=7)
        s.e=tk.Entry(entry_shell,font=("Microsoft YaHei UI",11),width=6,justify="center",bd=0,bg="#FFFFFF",relief="flat")
        s.e.pack(padx=7,pady=5)
        tk.Label(f2,text="ml",bg=PAPER,fg=INK3).pack(side="left")
        s.error=tk.Label(c,text="",font=("Microsoft YaHei UI",8),bg=PAPER,fg="#B04430")
        s.error.pack(pady=(4,0))
        ok=tk.Canvas(c,width=W-78,height=44,bg=PAPER,highlightthickness=0,cursor="hand2",takefocus=1)
        ok.pack(pady=(7,0))
        def draw_ok(active=False):
            ok.delete("all")
            rr(ok,1,1,W-79,43,r=WATER_ACTION_RADIUS,fill="#A94A2B" if active else SIG,outline="")
            ok.create_text((W-78)//2,22,text="确 定",font=("Microsoft YaHei UI",11,"bold"),fill="#FFFFFF")
        draw_ok()
        ok.bind("<Enter>",lambda e:draw_ok(True))
        ok.bind("<Leave>",lambda e:draw_ok(False))
        ok.bind("<Button-1>",lambda e:s._c())
        hint=tk.Label(c,text="Enter 记录 · Esc 或右上 × 关闭误判",font=("Microsoft YaHei UI",7),bg=PAPER,fg="#AAA69E")
        hint.pack(pady=(6,8))
        s._make_draggable(shell,c,icon,title,subtitle,hint)
        s.e.bind("<Return>",lambda e:s._c())
        s.e.bind("<KP_Enter>",lambda e:s._c())
        s.e.bind("<Escape>",lambda e:s._cancel())
        t.bind("<Escape>",lambda e:s._cancel())
        t.grab_set()
        t.after_idle(lambda:(s.e.focus_force(),s.e.selection_range(0,"end")))
        parent.wait_window(t)
    def _choose(s,value):
        s.val=value
        s.t.destroy()
    def _c(s):
        value=parse_water_amount(s.e.get())
        if value is None:
            s.error.config(text="请输入 1–5000 ml 的整数")
            s.e.focus_force(); s.e.selection_range(0,"end")
            return
        s.val=value
        s.t.destroy()
    def _cancel(s):
        s.val=None
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
    lines=open(p,encoding="utf-8-sig").read().splitlines()
    if not lines: return out
    # 只认 v1.2+ 格式：start,end,minutes,over
    header=lines[0].lstrip("﻿")
    if not header.startswith("start"): return out
    for ln in lines[1:]:
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
    favicon=report_favicon_link()
    html=f'''<!doctype html><html><head><meta charset="utf-8">
{favicon}
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
    except Exception: pass

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
        ico=os.path.join(_self, "assets", "dingdingmeow.ico")
        icon_line=f'\n$l.IconLocation = "{ico}"' if os.path.exists(ico) else ""
        ps=f'''$s = New-Object -ComObject WScript.Shell
$l = $s.CreateShortcut("{lnk}")
$l.TargetPath = "{vbs}"
$l.WorkingDirectory = "{_self}"{icon_line}
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

# ─────────── 托盘 ───────────
def make_tray_icon():
    """托盘图标复用报告 favicon 的猫头裁剪，保证跨场景视觉一致。"""
    return report_icon.build_cat_head_image(64)

def start_tray(pet_ref):
    try:
        import pystray
    except Exception: return
    icon_img = make_tray_icon()
    def eyes_item(icon, item): STATE["_toggle_eyes"] = True
    def pause_item(icon, item): toggle_detection()
    def autostart_item(icon, item): set_autostart(not is_autostart_on())
    def report_item(icon, item): open_report()
    def logs_item(icon, item): open_logs_folder()
    def view_timelapse_item(icon, item): open_timelapse_folder()
    def onboarding_item(icon, item): STATE["_show_onboarding"] = True
    def manual_drink_item(icon, item): STATE["_manual_drink"] = True
    def timelapse_item(icon,item): STATE["_toggle_timelapse"] = True
    def skin_menu_item(skin):
        def select_skin(icon,item):
            STATE["_skin_request"]=skin.skin_id
        return pystray.MenuItem(
            skin.label,
            select_skin,
            checked=lambda item,skin_id=skin.skin_id:STATE.get("skin_id")==skin_id,
            radio=True,
        )
    def center_nudge_item(icon, item):
        if set_center_nudge_enabled(not STATE["center_nudge_enabled"]):
            try: icon.update_menu()
            except Exception: pass
    def interval_menu_item(minutes):
        def select_interval(icon, item):
            if set_water_reminder(minutes):
                try: icon.update_menu()
                except Exception: pass
        return pystray.MenuItem(
            "%d 分钟"%minutes,
            select_interval,
            checked=lambda item: STATE.get("water_reminder_min")==minutes,
            radio=True,
        )
    def quit_item(icon, item):
        STATE["_quit"] = True; icon.stop()
    interval_menu=pystray.Menu(*(interval_menu_item(value) for value in WATER_REMINDER_OPTIONS))
    skin_menu=pystray.Menu(*(skin_menu_item(skin) for skin in skin_system.discover_skins(cat_sprites.asset_root())))
    menu = pystray.Menu(
        pystray.MenuItem("手动记录喝水", manual_drink_item),
        pystray.MenuItem(
            "延时摄影（开始 / 停止保存）",
            timelapse_item,
            checked=lambda item:STATE.get("timelapse_active",False),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("看今日报告", report_item),
        pystray.MenuItem("查看延时摄影", view_timelapse_item),
        pystray.MenuItem("打开日志文件夹", logs_item),
        pystray.MenuItem("新手教程", onboarding_item),
        pystray.MenuItem("喝水提醒间隔", interval_menu),
        pystray.MenuItem("猫咪皮肤",skin_menu),
        pystray.MenuItem(
            "久坐中央叩屏",
            center_nudge_item,
            checked=lambda i: STATE["center_nudge_enabled"],
        ),
        pystray.MenuItem("睁眼 / 收起画面", eyes_item),
        pystray.MenuItem(
            "暂停 / 开始检测",
            pause_item,
            checked=lambda i:STATE["paused"] or STATE.get("camera_off",False),
        ),
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

        # v1.3.1 尺寸: 气泡加高加宽，字号 10，猫保持不变
        s.W = 236; s.H_CLOSED = 250; s.H_OPEN = 410
        s.BUBBLE_W = 210
        s.CAT_MARGIN_BOTTOM = 82   # 猫头中心 y = H_OPEN - 这个值
        s.CAT_SPRITE_SIZE = cat_sprites.DEFAULT_SPRITE_SIZE
        s.CAT_BOTTOM = s.H_OPEN - 6

        s.eyes_open = False; s.blink = False
        s._anim_started = time.monotonic()
        s._blink_next = time.monotonic() + 4
        s._panel_anim_token = 0
        s._drink_dialog_pending = False
        s._tray = None
        s._btn_boxes = {}
        s._details_visible = False
        s._detail_bounds = None
        s._status_text = None
        s._status_photo = None
        s._onboarding_window = None
        s._skin_id = STATE.get("skin_id",skin_system.DEFAULT_SKIN_ID)
        s._center_nudge_active = False
        s._center_nudge_started = 0.0
        s._center_nudge_origin = None
        s._center_nudge_target = None
        s._center_nudge_sample = None
        s._center_nudge_triggered_session = None
        s._center_nudge_restore_eyes = False
        s._center_nudge_window_pos = None
        s._center_nudge_message_photo = ImageTk.PhotoImage(
            render_status_label("坐满1小时啦 · 起来走走"),
            master=r,
        )

        s.canvas = tk.Canvas(r, width=s.W, height=s.H_OPEN, bg=TRANS, highlightthickness=0)
        s.canvas.pack()
        sprite_images = cat_sprites.load_sprite_images(s.CAT_SPRITE_SIZE,skin_id=s._skin_id)
        s._cat_photos = {key: ImageTk.PhotoImage(image, master=r) for key, image in sprite_images.items()}
        knock_images = cat_sprites.load_knock_frames(s.CAT_SPRITE_SIZE)
        s._knock_photos = {
            1:[ImageTk.PhotoImage(frame,master=r) for frame in knock_images],
            -1:[ImageTk.PhotoImage(ImageOps.mirror(frame),master=r) for frame in knock_images],
        }
        roll_images,s._roll_bottom_offset=cat_sprites.load_roll_frames(s.CAT_SPRITE_SIZE)
        s._roll_photos=[
            ImageTk.PhotoImage(frame,master=r)
            for frame in roll_images
        ]
        s.canvas.bind("<ButtonPress-1>", s._press)
        s.canvas.bind("<B1-Motion>", s._motion)
        s.canvas.bind("<Motion>", s._hover_motion)
        s.canvas.bind("<Leave>", s._hover_leave)
        s.canvas.bind("<ButtonRelease-1>", s._release)
        s.canvas.bind("<Button-3>", s._menu_close)

        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        s.ax = sw - s.W - 20; s.ay = sh - s.H_OPEN - 30
        r.geometry("%dx%d+%d+%d" % (s.W, s.H_OPEN, s.ax, s.ay))

        s._cur_h = s.H_CLOSED
        s._photo = None; s._photo_frame_ref = None; s._dragging = False
        s._last_screen_check = 0.0

        threading.Thread(target=detection_supervisor, daemon=True).start()
        threading.Thread(target=start_tray, args=(s,), daemon=True).start()
        s.tick()
        if should_show_onboarding(SETTINGS_PATH):
            r.after(700, s.show_onboarding)
        r.mainloop()

    def _press(s, e):
        if s._center_nudge_active: return
        s._px, s._py = e.x_root, e.y_root
        s._wx, s._wy = s.r.winfo_x(), s.r.winfo_y()
        s._dragging = False
        s._click_xy = (e.x, e.y)

    def _motion(s, e):
        if s._center_nudge_active: return
        dx, dy = e.x_root - s._px, e.y_root - s._py
        if abs(dx) + abs(dy) > 4:
            s._dragging = True
            s.r.geometry("+%d+%d" % (s._wx + dx, s._wy + dy))

    def _hover_motion(s,e):
        if s._dragging or s._center_nudge_active: return
        cx=s.W//2
        cat_bounds=(
            cx-s.CAT_SPRITE_SIZE//2,
            s.CAT_BOTTOM-s.CAT_SPRITE_SIZE,
            cx+s.CAT_SPRITE_SIZE//2,
            s.CAT_BOTTOM,
        )
        detail_bounds=s._detail_bounds if s._details_visible else None
        visible=pointer_keeps_details_open(e.x,e.y,cat_bounds,detail_bounds)
        if visible!=s._details_visible:
            s._details_visible=visible
            if not visible:
                s._btn_boxes={}; s._detail_bounds=None
            s.redraw()

    def _hover_leave(s,e):
        if s._center_nudge_active: return
        if s._details_visible:
            s._details_visible=False; s._btn_boxes={}; s._detail_bounds=None
            s.redraw()

    def _release(s, e):
        if s._dragging or s._center_nudge_active: return
        x, y = s._click_xy
        # 按钮
        for name,(x1,y1,x2,y2) in s._btn_boxes.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                if name == "log": open_logs_folder()
                elif name == "report": open_report()
                return
        if STATE.get("mode") in ("camera_off","paused"):
            start_detection(); return
        # 眼睛热区跟图片尺寸一起计算，换素材后不再依赖旧矢量坐标
        eye_box = cat_sprites.eye_hitbox(s.W//2, s.CAT_BOTTOM, s.CAT_SPRITE_SIZE)
        if eye_box[0] <= x <= eye_box[2] and eye_box[1] <= y <= eye_box[3]:
            s.toggle_eyes(); return

    def _menu_close(s, e):
        m = tk.Menu(s.r, tearoff=0)
        m.add_command(label="手动记录喝水", command=lambda: s._request_water_dialog(immediate=True))
        m.add_command(
            label="停止并保存延时摄影" if STATE.get("timelapse_active") else "开始延时摄影",
            command=s._toggle_timelapse,
        )
        m.add_separator()
        m.add_command(label="看今日报告", command=open_report)
        m.add_command(label="查看延时摄影", command=open_timelapse_folder)
        m.add_command(label="打开日志文件夹", command=open_logs_folder)
        m.add_command(label="新手教程", command=s.show_onboarding)
        reminder_menu=tk.Menu(m,tearoff=0)
        reminder_value=tk.IntVar(value=STATE.get("water_reminder_min",DEFAULT_WATER_REMINDER_MIN))
        for minutes in WATER_REMINDER_OPTIONS:
            reminder_menu.add_radiobutton(
                label="%d 分钟"%minutes,
                variable=reminder_value,
                value=minutes,
                command=lambda value=minutes:set_water_reminder(value),
            )
        m.add_cascade(label="喝水提醒间隔",menu=reminder_menu)
        skin_menu=tk.Menu(m,tearoff=0)
        skin_value=tk.StringVar(value=STATE.get("skin_id",skin_system.DEFAULT_SKIN_ID))
        for skin in skin_system.discover_skins(cat_sprites.asset_root()):
            skin_menu.add_radiobutton(
                label=skin.label,
                variable=skin_value,
                value=skin.skin_id,
                command=lambda skin_id=skin.skin_id:s._set_skin(skin_id),
            )
        m.add_cascade(label="猫咪皮肤",menu=skin_menu)
        center_value=tk.BooleanVar(value=STATE.get("center_nudge_enabled",True))
        m.add_checkbutton(
            label="久坐中央叩屏",
            variable=center_value,
            command=lambda:set_center_nudge_enabled(center_value.get()),
        )
        m.add_command(label="睁眼 / 收起画面", command=s.toggle_eyes)
        m.add_command(
            label="开始检测" if STATE["paused"] or STATE.get("camera_off") else "暂停检测",
            command=toggle_detection,
        )
        m.add_separator()
        m.add_command(label="退出盯盯喵", command=s._quit)
        try: m.tk_popup(e.x_root, e.y_root)
        finally: m.grab_release()

    def show_onboarding(s):
        window = s._onboarding_window
        try:
            if window is not None and window.winfo_exists():
                window.deiconify(); window.lift(); window.focus_force()
                return
        except tk.TclError:
            pass

        def clear_reference():
            s._onboarding_window = None

        s._onboarding_window = open_onboarding(
            s.r,
            SETTINGS_PATH,
            on_close=clear_reference,
        )

    def toggle_eyes(s):
        s.eyes_open = not s.eyes_open
        target = s.H_OPEN if s.eyes_open else s.H_CLOSED
        s._animate_h(target)

    def _animate_h(s, target_h, steps=8):
        s._panel_anim_token += 1
        token = s._panel_anim_token
        start = s._cur_h
        def step(i):
            if token != s._panel_anim_token:
                return
            progress = (i + 1) / steps
            eased = cat_visual.ease_out_quart(progress)
            s._cur_h = int(round(start + (target_h - start) * eased))
            if i == steps - 1:
                s._cur_h = target_h
            s.redraw()
            if i < steps - 1:
                s.r.after(24, lambda: step(i+1))
        step(0)

    def _quit(s):
        STATE["_quit"] = True
        result=TIMELAPSE.stop()
        STATE["timelapse_active"]=False
        if result is not None:
            STATE["timelapse_last_path"]=str(result.path)
            STATE["timelapse_saved_until"]=time.time()+12.0
        try:
            if s._tray: s._tray.stop()
        except Exception: pass
        s.r.destroy()

    def _toggle_timelapse(s):
        if TIMELAPSE.active:
            result=TIMELAPSE.stop()
            STATE["timelapse_active"]=False
            STATE["timelapse_frames"]=0
            if result is not None:
                STATE["timelapse_last_path"]=str(result.path)
                STATE["timelapse_saved_until"]=time.time()+12.0
        else:
            TIMELAPSE.start()
            STATE["timelapse_active"]=True
            STATE["timelapse_frames"]=0
            STATE["timelapse_saved_until"]=0.0
            STATE["timelapse_error"]=None
        try:
            if s._tray: s._tray.update_menu()
        except Exception:
            pass
        s.redraw()

    def _set_skin(s,skin_id):
        try:
            sprite_images=cat_sprites.load_sprite_images(s.CAT_SPRITE_SIZE,skin_id=skin_id)
            saved=skin_system.save_skin(SETTINGS_PATH,cat_sprites.asset_root(),skin_id)
        except (OSError,ValueError,FileNotFoundError):
            return False
        s._cat_photos={
            key:ImageTk.PhotoImage(image,master=s.r)
            for key,image in sprite_images.items()
        }
        s._skin_id=saved
        STATE["skin_id"]=saved
        s._status_text=None
        try:
            if s._tray: s._tray.update_menu()
        except Exception:
            pass
        s.redraw()
        return True

    def _request_water_dialog(s, immediate=False):
        """收拢的喝水弹窗触发入口。自动检测 immediate=False，走 DRINK_ANIM_SEC 延迟；
        手动菜单 immediate=True，立刻弹。_drink_dialog_pending 去重防叠开。"""
        if s._drink_dialog_pending or STATE.get("_quit"):
            return
        s._drink_dialog_pending = True
        delay = 0 if immediate else cat_visual.drink_prompt_delay_ms(DRINK_ANIM_SEC)
        s.r.after(delay, s._show_water_dialog)

    def _show_water_dialog(s):
        s._drink_dialog_pending = False
        if STATE.get("_quit"):
            return
        d = WaterDialog(s.r)
        if d.val:
            STATE["water"] += d.val
            wlog(d.val, STATE["water"])
            now=time.time()
            STATE["last_drink_ts"] = now
            STATE["water_reminder_anchor"] = now
            STATE["last_nudge_ts"] = 0.0
            STATE["nudge_until"] = 0.0

    def _start_center_nudge(s):
        s._center_nudge_active=True
        s._center_nudge_started=time.monotonic()
        s._center_nudge_origin=(s.r.winfo_x(),s.r.winfo_y())
        s._center_nudge_window_pos=s._center_nudge_origin
        s._center_nudge_restore_eyes=s.eyes_open
        s.eyes_open=False
        s._panel_anim_token+=1
        s._cur_h=s.H_CLOSED
        s._details_visible=False
        s._btn_boxes={}; s._detail_bounds=None
        sw=s.r.winfo_screenwidth()
        s._center_nudge_target=center_nudge.cat_center_target(
            sw,
            s._center_nudge_origin[1],
            s.W//2,
        )
        s._center_nudge_sample=center_nudge.sample_trip(
            0.0,
            s._center_nudge_origin,
            s._center_nudge_target,
        )

    def _set_center_nudge_window_position(s,x,y):
        if s._center_nudge_origin is not None:
            y=s._center_nudge_origin[1]
        position=(int(round(x)),int(round(y)))
        if position==s._center_nudge_window_pos:
            return
        s.r.geometry("%+d%+d"%position)
        s._center_nudge_window_pos=position

    def _update_center_nudge(s):
        if not s._center_nudge_active: return
        if center_nudge.should_cancel(
            STATE["mode"],
            STATE.get("locked",False),
            STATE.get("paused",False),
            STATE.get("center_nudge_enabled",True),
        ):
            s._finish_center_nudge()
            return
        elapsed=time.monotonic()-s._center_nudge_started
        sample=center_nudge.sample_trip(
            elapsed,
            s._center_nudge_origin,
            s._center_nudge_target,
        )
        s._center_nudge_sample=sample
        s._set_center_nudge_window_position(sample.x,sample.y)
        if sample.done:
            s._finish_center_nudge()

    def _finish_center_nudge(s):
        origin=s._center_nudge_origin
        if origin is not None and origin!=s._center_nudge_window_pos:
            s._set_center_nudge_window_position(*origin)
        s._center_nudge_active=False
        s._center_nudge_sample=None
        s._center_nudge_origin=None
        s._center_nudge_target=None
        s._center_nudge_window_pos=None
        s.eyes_open=s._center_nudge_restore_eyes
        s._cur_h=s.H_OPEN if s.eyes_open else s.H_CLOSED

    def _draw_angry_steam(s,c,cx,level,rotation_degrees):
        level=max(0.0,min(1.0,float(level)))
        if level<=0.06:
            return
        phase=math.radians(rotation_degrees)
        sway=math.sin(phase)*2.2
        rise=(1.0-level)*5.0
        radius=2.7+1.8*level
        for side in (-1,1):
            base_x=cx+side*(42+4*level)+side*sway
            base_y=s.CAT_BOTTOM-51-rise+side*math.cos(phase)*1.2
            lobes=(
                (0.0,0.0,1.00),
                (side*4.2,-3.0,0.84),
                (side*7.2,-7.1,0.66),
            )
            for dx,dy,scale in lobes:
                lobe_radius=radius*scale
                c.create_oval(
                    base_x+dx-lobe_radius,
                    base_y+dy-lobe_radius,
                    base_x+dx+lobe_radius,
                    base_y+dy+lobe_radius,
                    fill="#F4F1EB",
                    outline="#B8B4AD",
                    width=1,
                )

    def tick(s):
        heartbeat=STATE.get("detector_heartbeat",0)
        if time.time()-heartbeat>3.0 and STATE.get("mode") not in ("paused","away"):
            STATE.update(mode="away",frame=None)
        if STATE.get("_toggle_eyes"):
            STATE["_toggle_eyes"] = False
            s.toggle_eyes()
        if STATE.get("_show_onboarding"):
            STATE["_show_onboarding"] = False
            s.show_onboarding()
        if STATE.get("_toggle_timelapse"):
            STATE["_toggle_timelapse"]=False
            s._toggle_timelapse()
        requested_skin=STATE.get("_skin_request")
        if requested_skin:
            STATE["_skin_request"]=None
            s._set_skin(requested_skin)
        if STATE.get("_quit"):
            s._quit(); return

        if STATE["drink"]:
            STATE["drink"] = False
            s._request_water_dialog(immediate=False)
        if STATE.get("_manual_drink"):
            STATE["_manual_drink"] = False
            s._request_water_dialog(immediate=True)

        session_key=STATE.get("sit_session_start")
        if session_key!=s._center_nudge_triggered_session and center_nudge.should_start(
            STATE.get("sit",0),
            STATE.get("mode","init"),
            STATE.get("center_nudge_enabled",True),
            False,
            s._center_nudge_active,
        ):
            s._center_nudge_triggered_session=session_key
            s._start_center_nudge()
        if s._center_nudge_active:
            s._update_center_nudge()

        # 多屏切单屏守护：每 2 秒检查一次窗口中心点是否还在某块显示器上；
        # 副屏拔了 / 分辨率缩小导致中心点悬空 → snap 回主屏右下角。
        now_ts = time.time()
        if not s._dragging and not s._center_nudge_active and now_ts - s._last_screen_check > 2.0:
            s._last_screen_check = now_ts
            cur_x, cur_y = s.r.winfo_x(), s.r.winfo_y()
            if window_placement.needs_reposition(cur_x, cur_y, s.W, s.H_OPEN):
                sw = s.r.winfo_screenwidth()
                sh = s.r.winfo_screenheight()
                nx, ny = window_placement.snap_target(sw, sh, s.W, s.H_OPEN)
                s.r.geometry("+%d+%d" % (nx, ny))

        now = time.monotonic()
        if s.eyes_open and now >= s._blink_next:
            s.blink = True
            s.r.after(160, s._end_blink)
            elapsed = now - s._anim_started
            s._blink_next = now + 4.6 + 1.4 * (0.5 + 0.5 * math.sin(elapsed * 0.73))

        s.redraw()
        s.r.after(40, s.tick)

    def _end_blink(s):
        s.blink = False; s.redraw()

    def redraw(s):
        c = s.canvas
        c.delete("all")
        mm = STATE["mode"]
        bg = LOOKS_BG.get(mm, "#FFFFFF")
        cx = s.W // 2
        cat_cy = s.H_OPEN - s.CAT_MARGIN_BOTTOM
        now = time.time()
        pose = cat_visual.sample_cat_pose(time.monotonic() - s._anim_started, mm)

        if s._center_nudge_active and s._center_nudge_sample is not None:
            sample=s._center_nudge_sample
            cat_y=s.CAT_BOTTOM
            if sample.sprite=="roll":
                frame_index=cat_sprites.roll_frame_index(
                    sample.rotation_degrees,
                    len(s._roll_photos),
                )
                cat_photo=s._roll_photos[frame_index]
                cat_y+=s._roll_bottom_offset
            elif sample.sprite=="knock":
                frames=s._knock_photos[sample.facing]
                frame_index=cat_visual.action_frame_index(
                    sample.frame_progress,
                    len(frames),
                    1.0,
                )
                cat_photo=frames[frame_index]
            else:
                cat_photo=s._cat_photos.get(sample.sprite,s._cat_photos["idle"])
            if sample.show_message:
                c.create_image(
                    cx,
                    s.CAT_BOTTOM-s.CAT_SPRITE_SIZE-8,
                    image=s._center_nudge_message_photo,
                    anchor="s",
                )
            s._draw_angry_steam(
                c,
                cx,
                sample.steam,
                sample.rotation_degrees,
            )
            c.create_image(cx,cat_y,image=cat_photo,anchor="s")
            return

        msg = {
            "seated":"陪你工作 · 已坐 " + dur(STATE["sit"]),
            "away":  "咦你去哪了 · " + dur(STATE["away"]),
            "over":  "坐太久啦 快起来动动!",
            "blocked":"喵…看不见了",
            "camera_off":"摄像头已关闭 · 点击猫咪开始检测",
            "init":  "启动中…",
            "paused":"检测暂停中"
        }.get(mm, "准备好啦~")
        if STATE.get("locked"):
            msg="电脑已锁屏 · 算作离开"
        lines=[msg, "今日饮水 %d / %d ml"%(STATE["water"], WATER_TARGET_ML)]
        nudge_active=now < STATE.get("nudge_until",0) and mm in ("seated","over")
        if nudge_active:
            lines.append("💧 喝口水吧~")
        if STATE.get("timelapse_active"):
            lines.append("⏱ 延时摄影 · %d 帧"%STATE.get("timelapse_frames",0))
        elif now < STATE.get("timelapse_saved_until",0):
            lines.append("✓ 延时摄影已保存到日志")
        full = "\n".join(lines)

        # 气泡尺寸：文字顶 12 + 每行 ~17 + 分隔线 6 + 按钮 20 + 底 8
        # 2 行: 12 + 34 + 6 + 20 + 8 = 80  →  86 给点余量
        # 3 行: 12 + 51 + 6 + 20 + 8 = 97  → 104
        bubble_h = 86 + max(0,len(lines)-2)*18
        bubble_top = detail_bubble_top(cat_cy, bubble_h, mm)
        if s._details_visible:
            s._btn_boxes = draw_text_bubble(c, cx, bubble_top, w=s.BUBBLE_W, h=bubble_h, text=full, bg=bg)
            s._detail_bounds=(
                cx-s.BUBBLE_W//2,
                bubble_top,
                cx+s.BUBBLE_W//2,
                s.CAT_BOTTOM,
            )
        else:
            s._btn_boxes={}

        # 视频气泡
        video_h = 145; video_w = s.BUBBLE_W
        span = s.H_OPEN - s.H_CLOSED
        prog = 1.0 if s.eyes_open else 0.0
        if span > 0: prog = max(0.0, min(1.0, (s._cur_h - s.H_CLOSED) / span))
        if prog > 0.05:
            v_hidden = bubble_top - 4
            vtop = video_bubble_top(v_hidden, prog)
            fr = STATE.get("frame"); photo = s._photo
            if fr is not None:
                if fr is not s._photo_frame_ref:
                    try:
                        im = Image.fromarray(fr).resize((video_w - 20, video_h - 36))
                        photo = ImageTk.PhotoImage(im)
                        s._photo = photo
                        s._photo_frame_ref = fr
                    except Exception:
                        photo = s._photo
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

        sprite_key = cat_sprites.select_sprite(
            mood=mm,
            eyes_open=s.eyes_open,
            blink=s.blink,
            cup_state=cup_state,
            resting=(not s._details_visible and mm=="seated" and cup_state is None),
        )
        sprite_key = cat_sprites.enforce_display_invariants(
            sprite_key,
            eyes_open=s.eyes_open,
        )

        if not s._details_visible:
            status=compact_status(
                mm,
                sit_seconds=STATE.get("sit",0),
                away_seconds=STATE.get("away",0),
                locked=STATE.get("locked",False),
                water_nudge=nudge_active,
            )
            status_y=status_label_y(s.CAT_BOTTOM,s.CAT_SPRITE_SIZE,sprite_key)
            if status!=s._status_text:
                s._status_text=status
                s._status_photo=ImageTk.PhotoImage(render_status_label(status),master=s.r)
            c.create_image(cx,status_y,image=s._status_photo,anchor="s")

        c.create_image(
            cx + pose.alert_offset,
            s.CAT_BOTTOM + pose.head_bob,
            image=s._cat_photos[sprite_key],
            anchor="s",
        )

if __name__ == "__main__":
    Pet()
