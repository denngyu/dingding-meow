# -*- coding: utf-8 -*-
"""盯盯喵 v1.1: 桌面小猫, 久坐+离座+喝水一只全管, 点眼睛看画面。纯本地。"""
import sys, os, threading, time, shutil, tempfile
import tkinter as tk
from datetime import datetime
if getattr(sys, "frozen", False):
    _self = os.path.dirname(os.path.abspath(sys.executable))
else:
    _self = os.path.dirname(os.path.abspath(__file__))
import cv2, numpy as np
from PIL import Image, ImageTk

CAM_INDEX=0; CHECK_EVERY=0.5; SIT_LIMIT_MIN=45; GRACE_SEC=25; OVER_GRACE=5; BLOCK_LEVEL=22
CONF=0.25; CUP_CLASSES={39,40,41}

INK="#1A1B18"; INK2="#585C57"; INK3="#8C918B"; PAPER="#F7F6F3"; SIG="#C15A34"; LINE="#D9D8D0"
FUR="#B8B4AC"; FUR_DARK="#8A867E"; FUR_LIGHT="#E4E0D6"; NOSE="#E8A5A0"; CHEEK="#F5C7C2"
TRANS="#FE00FE"

TEST = len(sys.argv)>1 and sys.argv[1]=="test"
if TEST: SIT_LIMIT_MIN, GRACE_SEC, OVER_GRACE = 0.7, 8, 3

LOG_DIR=os.path.join(_self,"logs"); os.makedirs(LOG_DIR, exist_ok=True)
WLOG=os.path.join(LOG_DIR,"water_%s.csv"%datetime.now().strftime("%Y%m%d"))

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
            if cid in CUP_CLASSES and sc[cid]>CONF:
                cx,cy,w,h=d[0]*W,d[1]*H,d[2]*W,d[3]*H
                out.append((int(cx-w/2),int(cy-h/2),int(w),int(h)))
    return out

def near(f,c):
    fx,fy,fw,fh=f; ex=fw*0.5; ey=fh*0.6
    fx-=ex; fy-=ey*0.3; fw+=2*ex; fh+=ey
    cx,cy,cw,ch=c
    return min(fx+fw,cx+cw)-max(fx,cx)>0 and min(fy+fh,cy+ch)-max(fy,cy)>0

def today_total():
    t=0
    if os.path.exists(WLOG):
        for ln in open(WLOG,encoding="utf-8-sig").read().splitlines()[1:]:
            p=ln.split(",")
            if len(p)>=2 and p[1].isdigit(): t+=int(p[1])
    return t

def wlog(ml,total):
    new=not os.path.exists(WLOG)
    with open(WLOG,"a",encoding="utf-8-sig") as f:
        if new: f.write("time,ml,今日累计\n")
        f.write("%s,%d,%d\n"%(datetime.now().strftime("%H:%M:%S"),ml,total))


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


STATE={"mode":"init","sit":0,"away":0,"water":today_total(),"drink":False,"frame":None}


def loop():
    cap=cv2.VideoCapture(CAM_INDEX,cv2.CAP_DSHOW)
    last_seen=sit_start=away_start=None; was=False
    while True:
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
            if sit_start is None: sit_start=last_seen
            sit=now-sit_start
            STATE.update(mode=("over" if sit/60>=SIT_LIMIT_MIN else "seated"), sit=sit, away=0)
            cups=cup_boxes(fr)
            drinking=any(near(f,c) for f in fb for c in cups)
            if drinking and not was: STATE["drink"]=True
            was=drinking
        else:
            sit_start=None; was=False
            if away_start is None: away_start=last_seen if last_seen else now
            STATE.update(mode=("blocked" if blocked else "away"), away=now-away_start, sit=0)
        disp=fr.copy()
        for (x,y,w,h) in fb: cv2.rectangle(disp,(x,y),(x+w,y+h),(0,220,0),2)
        for (x,y,w,h) in cups: cv2.rectangle(disp,(x,y),(x+w,y+h),(0,160,255),2)
        STATE["frame"]=cv2.cvtColor(cv2.resize(disp,(200,150)),cv2.COLOR_BGR2RGB)
        time.sleep(CHECK_EVERY)


def dur(s):
    mm,x=divmod(int(s),60); return "%d分%d秒"%(mm,x) if mm else "%d秒"%x


# ─────────── UI 绘制 ───────────

def rr(c, x1, y1, x2, y2, r=14, **kw):
    """圆角矩形（smooth polygon 近似）"""
    pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2,
           x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
    return c.create_polygon(pts, smooth=True, **kw)


def draw_cat(c, cx, cy, eyes_open=False, blink=False, mood="seated", breath=0, tail_ang=0):
    """在 (cx, cy) 为头部中心的位置画一只小猫。"""
    body_y1 = cy + 30 + breath
    body_y2 = cy + 100 + breath
    # 尾巴（画在身体后）
    tail_x1, tail_y1 = cx+22, cy+38+breath
    tail_x2, tail_y2 = cx+82, cy+96+breath
    c.create_arc(tail_x1, tail_y1, tail_x2, tail_y2,
                 start=60+tail_ang, extent=200, style="arc",
                 outline=FUR, width=11)
    c.create_arc(tail_x1, tail_y1, tail_x2, tail_y2,
                 start=60+tail_ang, extent=200, style="arc",
                 outline=FUR_DARK, width=1)
    # 身体
    c.create_oval(cx-50, body_y1, cx+50, body_y2, fill=FUR, outline=FUR_DARK, width=1.2)
    # 胸口浅色围兜
    c.create_oval(cx-28, body_y1+8, cx+28, body_y2-4, fill=FUR_LIGHT, outline="")
    # 前爪
    c.create_oval(cx-34, body_y2-16, cx-10, body_y2-1, fill=FUR_LIGHT, outline=FUR_DARK, width=1)
    c.create_oval(cx+10, body_y2-16, cx+34, body_y2-1, fill=FUR_LIGHT, outline=FUR_DARK, width=1)
    for tx in (cx-28, cx-22, cx-16):
        c.create_oval(tx-1.5, body_y2-8, tx+1.5, body_y2-5, fill=NOSE, outline="")
    for tx in (cx+16, cx+22, cx+28):
        c.create_oval(tx-1.5, body_y2-8, tx+1.5, body_y2-5, fill=NOSE, outline="")

    # 耳朵（先画外层三角）
    c.create_polygon(cx-46, cy-30, cx-52, cy-66, cx-22, cy-38,
                     fill=FUR, outline=FUR_DARK, width=1.2, smooth=1)
    c.create_polygon(cx+46, cy-30, cx+52, cy-66, cx+22, cy-38,
                     fill=FUR, outline=FUR_DARK, width=1.2, smooth=1)
    # 耳朵内侧粉色
    c.create_polygon(cx-42, cy-33, cx-46, cy-56, cx-30, cy-38,
                     fill=NOSE, outline="", smooth=1)
    c.create_polygon(cx+42, cy-33, cx+46, cy-56, cx+30, cy-38,
                     fill=NOSE, outline="", smooth=1)

    # 头
    c.create_oval(cx-53, cy-40, cx+53, cy+45, fill=FUR, outline=FUR_DARK, width=1.2)
    # 头顶浅色脸盘
    c.create_oval(cx-32, cy-10, cx+32, cy+38, fill=FUR_LIGHT, outline="")

    # 腮红
    c.create_oval(cx-38, cy+6, cx-24, cy+18, fill=CHEEK, outline="")
    c.create_oval(cx+24, cy+6, cx+38, cy+18, fill=CHEEK, outline="")

    # 眼睛
    ex_l, ex_r = cx-18, cx+18
    ey = cy - 4
    if eyes_open and not blink:
        # 睁开：白色 + 瞳孔 + 高光
        c.create_oval(ex_l-11, ey-13, ex_l+11, ey+13, fill="#FFFFFF", outline=INK, width=1.6)
        c.create_oval(ex_r-11, ey-13, ex_r+11, ey+13, fill="#FFFFFF", outline=INK, width=1.6)
        c.create_oval(ex_l-6, ey-9, ex_l+6, ey+10, fill=INK, outline="")
        c.create_oval(ex_r-6, ey-9, ex_r+6, ey+10, fill=INK, outline="")
        c.create_oval(ex_l-3, ey-7, ex_l+2, ey-2, fill="#FFFFFF", outline="")
        c.create_oval(ex_l-4, ey+3, ex_l-2, ey+5, fill="#FFFFFF", outline="")
        c.create_oval(ex_r-3, ey-7, ex_r+2, ey-2, fill="#FFFFFF", outline="")
        c.create_oval(ex_r-4, ey+3, ex_r-2, ey+5, fill="#FFFFFF", outline="")
    else:
        # 闭眼：happy 弧 ⌒⌒
        c.create_arc(ex_l-10, ey-3, ex_l+10, ey+13, start=0, extent=180,
                     style="arc", outline=INK, width=2.4)
        c.create_arc(ex_r-10, ey-3, ex_r+10, ey+13, start=0, extent=180,
                     style="arc", outline=INK, width=2.4)

    # 鼻子
    c.create_polygon(cx-5, cy+13, cx+5, cy+13, cx, cy+19,
                     fill=NOSE, outline=INK, width=1.1, smooth=1)
    # 嘴（简单微笑，over 情绪时变皱眉）
    if mood == "over":
        c.create_arc(cx-9, cy+22, cx+9, cy+32, start=20, extent=140,
                     style="arc", outline=INK, width=1.5)
    else:
        c.create_line(cx, cy+19, cx, cy+22, fill=INK, width=1.2)
        c.create_arc(cx-9, cy+15, cx+1, cy+25, start=260, extent=90,
                     style="arc", outline=INK, width=1.4)
        c.create_arc(cx-1, cy+15, cx+9, cy+25, start=190, extent=90,
                     style="arc", outline=INK, width=1.4)

    # 胡须
    for dy in (-2, 3):
        c.create_line(cx-40, cy+8+dy, cx-56, cy+6+dy, fill=INK2, width=1)
        c.create_line(cx+40, cy+8+dy, cx+56, cy+6+dy, fill=INK2, width=1)


def draw_text_bubble(c, cx, cy_top, w, h, text, bg="#FFFFFF"):
    """文字气泡，尾巴朝下指向猫头。"""
    x1, y1, x2, y2 = cx - w//2, cy_top, cx + w//2, cy_top + h
    # 阴影
    rr(c, x1+2, y1+3, x2+2, y2+3, r=14, fill="#D9D8D0", outline="")
    # 主体
    rr(c, x1, y1, x2, y2, r=14, fill=bg, outline=LINE, width=1.5)
    # 尾巴（三角形指下）
    tx = cx - 22
    c.create_polygon(tx-8, y2-1, tx+8, y2-1, tx, y2+11,
                     fill=bg, outline=LINE, width=1.5)
    c.create_line(tx-7, y2, tx+7, y2, fill=bg, width=3)
    # 文本
    c.create_text(cx, cy_top + h//2, text=text, font=("Microsoft YaHei UI", 10),
                  fill=INK, width=w-22, justify="center")


def draw_video_bubble(c, cx, cy_top, w, h, photo):
    """摄像头气泡（深色）从头顶升起。"""
    x1, y1, x2, y2 = cx - w//2, cy_top, cx + w//2, cy_top + h
    # 阴影
    rr(c, x1+3, y1+4, x2+3, y2+4, r=16, fill="#B8B4AC", outline="")
    # 主体
    rr(c, x1, y1, x2, y2, r=16, fill="#1A1B18", outline="#3a3a37", width=1.5)
    # 视频区
    if photo is not None:
        c.create_image(cx, y1 + 28 + (h - 40)//2, image=photo)
    else:
        c.create_text(cx, y1 + h//2, text="正在唤醒摄像头…",
                      font=("Microsoft YaHei UI", 9), fill="#9BA098")
    # 顶栏 LIVE / CAM 标签
    c.create_text(x1+14, y1+13, text="● LIVE", anchor="w",
                  font=("Consolas", 9, "bold"), fill=SIG)
    c.create_text(x2-14, y1+13, text="CAM 0", anchor="e",
                  font=("Consolas", 8), fill="#8C918B")
    # 尾巴向下
    tx = cx - 22
    c.create_polygon(tx-8, y2-1, tx+8, y2-1, tx, y2+11,
                     fill="#1A1B18", outline="#3a3a37", width=1.5)
    c.create_line(tx-7, y2, tx+7, y2, fill="#1A1B18", width=3)


LOOKS_BG = {"seated":"#FFFFFF", "over":"#FBE3E0", "away":"#EDEDE8",
            "blocked":"#EDEDE8", "init":"#FFFFFF"}


class Pet:
    def __init__(s):
        r = tk.Tk(); s.r = r
        r.overrideredirect(True); r.attributes("-topmost", True)
        r.attributes("-alpha", 0.98)
        try:
            r.wm_attributes("-transparentcolor", TRANS)
        except tk.TclError:
            pass

        s.W = 280
        s.H_CLOSED = 250
        s.H_OPEN = 450
        s.eyes_open = False
        s.blink = False
        s.tail_ang = 0
        s.breath = 0
        s.anim_t = 0
        s._blink_next = time.time() + 4

        s.canvas = tk.Canvas(r, width=s.W, height=s.H_OPEN, bg=TRANS, highlightthickness=0)
        s.canvas.pack()

        s.canvas.bind("<ButtonPress-1>", s._press)
        s.canvas.bind("<B1-Motion>", s._motion)
        s.canvas.bind("<ButtonRelease-1>", s._release)
        s.canvas.bind("<Button-3>", lambda e: s.r.destroy())

        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        s.ax = sw - s.W - 30
        s.ay = sh - s.H_OPEN - 40  # 按最高高度定位，画布 always 保持 H_OPEN
        r.geometry("%dx%d+%d+%d" % (s.W, s.H_OPEN, s.ax, s.ay))

        s._cur_h = s.H_CLOSED   # 视觉上显示的高度（画布上部裁掉）
        s._photo = None
        s._dragging = False
        threading.Thread(target=loop, daemon=True).start()
        s.tick()
        r.mainloop()

    # ── 交互 ──
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
        # 眼睛点击热区（根据当前画布布局算）
        cat_cy = s.H_OPEN - 100
        if s.W//2 - 34 <= x <= s.W//2 + 34 and cat_cy - 22 <= y <= cat_cy + 14:
            s.toggle_eyes()

    def toggle_eyes(s):
        s.eyes_open = not s.eyes_open
        target = s.H_OPEN if s.eyes_open else s.H_CLOSED
        s._animate_h(target)

    def _animate_h(s, target_h, steps=8):
        start = s._cur_h
        delta = (target_h - start) / steps
        def step(i):
            s._cur_h = int(start + delta * (i+1))
            if i == steps - 1:
                s._cur_h = target_h
            if i < steps - 1:
                s.r.after(24, lambda: step(i+1))
        step(0)

    # ── tick ──
    def tick(s):
        if STATE["drink"]:
            STATE["drink"] = False
            d = WaterDialog(s.r)
            if d.val:
                STATE["water"] += d.val
                wlog(d.val, STATE["water"])

        now = time.time()
        if s.eyes_open and now >= s._blink_next:
            s.blink = True
            s.r.after(160, s._end_blink)
            s._blink_next = now + 4 + (s.anim_t % 4)

        s.anim_t += 1
        s.breath = 1 if (s.anim_t // 4) % 2 else -1
        s.tail_ang = int(14 * ((s.anim_t % 24) / 24 - 0.5))

        s.redraw()

        # over 情绪抖窗
        if STATE["mode"] == "over":
            s.r.geometry("+%d+%d" % (s.r.winfo_x() + (3 if s.anim_t % 2 else -3),
                                     s.r.winfo_y()))
        s.r.after(200, s.tick)

    def _end_blink(s):
        s.blink = False
        s.redraw()

    def redraw(s):
        c = s.canvas
        c.delete("all")
        mm = STATE["mode"]
        bg = LOOKS_BG.get(mm, "#FFFFFF")

        cx = s.W // 2
        cat_cy = s.H_OPEN - 100  # 画布高度固定，猫始终在同一位置

        # 屏蔽上方（未展开时）：画一个透明矩形其实不需要 —— 画布本身透明。
        # 但需要保证不显示 videobubble 时其位置为空即可。

        # 文字气泡内容
        msg = {
            "seated":"陪你工作 · 已坐 " + dur(STATE["sit"]),
            "away":  "咦你去哪了 · 离开 " + dur(STATE["away"]),
            "over":  "坐太久啦 快起来动动!",
            "blocked":"喵…看不见了",
            "init":  "启动中，找找你在不在…"
        }.get(mm, "准备好啦~")
        water_line = "今日饮水 %d ml" % STATE["water"]
        full = msg + "\n" + water_line

        bubble_h = 62
        bubble_top = cat_cy - 40 - 22 - bubble_h  # 头顶上方留 22 给尾巴
        draw_text_bubble(c, cx, bubble_top, w=240, h=bubble_h, text=full, bg=bg)

        # 视频气泡（仅在动画进度 > 60% 时才画，营造升起效果）
        video_target_top = 12
        video_h = 175
        video_w = 240
        # 视频气泡的顶部位置：根据当前 _cur_h 插值
        # _cur_h 从 H_CLOSED 到 H_OPEN 时，视频从藏起（top = bubble_top）滑到 video_target_top
        span = s.H_OPEN - s.H_CLOSED
        if span <= 0: prog = 1.0 if s.eyes_open else 0.0
        else: prog = max(0.0, min(1.0, (s._cur_h - s.H_CLOSED) / span))
        if prog > 0.05:
            v_hidden_top = bubble_top - 4   # 藏在文字气泡后面
            v_shown_top = video_target_top
            vtop = int(v_hidden_top + (v_shown_top - v_hidden_top) * prog)
            fr = STATE.get("frame")
            photo = None
            if fr is not None:
                try:
                    im = Image.fromarray(fr).resize((video_w - 22, video_h - 46))
                    photo = ImageTk.PhotoImage(im)
                    s._photo = photo
                except Exception:
                    photo = None
            draw_video_bubble(c, cx, vtop, video_w, video_h, photo)
            # 视频气泡半透明升起（用 stipple 覆盖一层 TRANS 制造消失）
            if prog < 0.9:
                fade = int((1 - prog) * 255)
                # 简化处理：不做半透明，直接用位置动画即可

        # 遮盖底部之外区域（把 H_OPEN 之上未展开部分抹掉）
        if s._cur_h < s.H_OPEN:
            hide = s.H_OPEN - s._cur_h
            c.create_rectangle(0, 0, s.W, hide, fill=TRANS, outline="")

        # 画猫（最上层）
        draw_cat(c, cx, cat_cy, eyes_open=s.eyes_open, blink=s.blink,
                 mood=mm, breath=s.breath, tail_ang=s.tail_ang)

        # 提示线（右键关闭）
        c.create_text(s.W - 8, s.H_OPEN - 6, text="右键关闭",
                      anchor="e", font=("Microsoft YaHei UI", 7), fill=INK3)


if __name__ == "__main__":
    Pet()
