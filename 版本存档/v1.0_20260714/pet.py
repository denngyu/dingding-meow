# -*- coding: utf-8 -*-
"""盯盯喵: 桌面小猫, 久坐+离座+喝水一只全管, 摄像头预览可展开。纯本地。"""
import sys, os, threading, time, shutil, tempfile
import tkinter as tk
from datetime import datetime
if getattr(sys, "frozen", False):
    _self = os.path.dirname(os.path.abspath(sys.executable))
else:
    _self = os.path.dirname(os.path.abspath(__file__))
import cv2, numpy as np
from PIL import Image, ImageTk

CAM_INDEX=0; CHECK_EVERY=1; SIT_LIMIT_MIN=45; GRACE_SEC=25; OVER_GRACE=5; BLOCK_LEVEL=22
CONF=0.25; CUP_CLASSES={39,40,41}
INK="#1A1B18"; INK3="#8C918B"; PAPER="#F7F6F3"; SIG="#C15A34"; LINE="#E7E6E0"
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
        STATE["frame"]=cv2.cvtColor(cv2.resize(disp,(184,138)),cv2.COLOR_BGR2RGB)
        time.sleep(CHECK_EVERY)

def dur(s):
    mm,x=divmod(int(s),60); return "%d分%d秒"%(mm,x) if mm else "%d秒"%x

LOOKS={"init":("(-_-)?","#6b5b4b",PAPER),"seated":("( ^ω^ )","#3f7d54",PAPER),
"over":("( >Д< )!",SIG,"#FBE3E0"),"away":("( -ω-)zzZ","#7a7a7a","#ECECEC"),
"blocked":("( ;ω; )","#7a7a7a","#ECECEC")}

class Pet:
    def __init__(s):
        r=tk.Tk(); s.r=r; r.overrideredirect(True); r.attributes("-topmost",True); r.attributes("-alpha",0.97)
        s.show=False; s.video=tk.Label(r,bg="#222")
        s.face=tk.Label(r,text="(-_-)",font=("Microsoft YaHei UI",20,"bold")); s.face.pack(pady=(10,0))
        s.msg=tk.Label(r,text="启动中…",font=("Microsoft YaHei UI",10)); s.msg.pack()
        s.wat=tk.Label(r,text="",font=("Microsoft YaHei UI",9)); s.wat.pack()
        s.btn=tk.Label(r,text="▸ 看画面",font=("Microsoft YaHei UI",8),fg="#3a7bd5",cursor="hand2"); s.btn.pack(pady=2)
        s.tip=tk.Label(r,text="盯盯喵 · 右键关闭",font=("Microsoft YaHei UI",7),fg="#c3b8a5"); s.tip.pack(side="bottom",pady=3)
        s.btn.bind("<Button-1>",s.toggle)
        for w in (r,s.face,s.msg,s.wat,s.tip):
            w.bind("<Button-1>",s._d); w.bind("<B1-Motion>",s._m); w.bind("<Button-3>",lambda e:s.r.destroy())
        sw,sh=r.winfo_screenwidth(),r.winfo_screenheight(); s.ax,s.ay=sw-230,sh-200
        s._resize(); threading.Thread(target=loop,daemon=True).start(); s._sh=0; s.tick(); r.mainloop()
    def _resize(s):
        h=300 if s.show else 150
        s.r.geometry("200x%d+%d+%d"%(h,s.r.winfo_x() if s.r.winfo_x()>0 else s.ax, s.r.winfo_y() if s.r.winfo_y()>0 else s.ay))
    def toggle(s,e):
        s.show=not s.show
        if s.show: s.video.pack(before=s.face,pady=(8,2)); s.btn.config(text="▾ 收起画面")
        else: s.video.pack_forget(); s.btn.config(text="▸ 看画面")
        s._resize()
    def _d(s,e): s.ox=e.x_root-s.r.winfo_x(); s.oy=e.y_root-s.r.winfo_y()
    def _m(s,e): s.r.geometry("+%d+%d"%(e.x_root-s.ox,e.y_root-s.oy))
    def tick(s):
        if s.show:
            fr=STATE.get("frame")
            if fr is not None:
                im=ImageTk.PhotoImage(Image.fromarray(fr)); s.video.config(image=im); s.video.image=im
        if STATE["drink"]:
            STATE["drink"]=False
            d=WaterDialog(s.r)
            if d.val: STATE["water"]+=d.val; wlog(d.val,STATE["water"])
        mm=STATE["mode"]; face,fg,bg=LOOKS.get(mm,LOOKS["init"])
        msg={"seated":"陪你工作 · 已坐 "+dur(STATE["sit"]),"away":"离开了 "+dur(STATE["away"]),
"over":"坐太久啦! 起来动动~","blocked":"咦…看不见了"}.get(mm,"准备好啦~")
        s.face.config(text=face,fg=fg,bg=bg); s.msg.config(text=msg,fg=fg,bg=bg)
        s.wat.config(text="今日饮水 %d ml"%STATE["water"],bg=bg,fg="#3a7bd5")
        s.r.config(bg=bg); s.tip.config(bg=bg); s.btn.config(bg=bg)
        if mm=="over":
            s._sh+=1; s.r.geometry("+%d+%d"%(s.r.winfo_x()+(4 if s._sh%2 else -4),s.r.winfo_y()))
        s.r.after(350,s.tick)

if __name__=="__main__": Pet()
