"""First-run tutorial state and the small three-step onboarding window."""

import tkinter as tk

from settings_store import read_settings, update_settings


ONBOARDING_VERSION = 1
ONBOARDING_STEPS = (
    (
        "它会安静地陪你工作",
        "摄像头只在本机判断是否在座，画面不会上传。\n"
        "低频抽帧预览用于降低 CPU 占用，并非卡顿。\n"
        "坐着累计时间；离开或锁屏后自动暂停。",
    ),
    (
        "这样和小猫互动",
        "鼠标移到小猫上：查看久坐与饮水。\n"
        "点击小猫眼睛：展开或收起摄像头画面。\n"
        "按住拖动：把小猫放到顺手的位置。",
    ),
    (
        "提醒和记录都能调整",
        "右键小猫：设置喝水提醒、暂停检测。\n"
        "气泡里的“日志”和“报告”：查看本机记录。\n"
        "托盘菜单里的“新手教程”：随时再看一遍。",
    ),
)


def should_show_onboarding(path):
    value = read_settings(path).get("onboarding_version", 0)
    try:
        return int(value) < ONBOARDING_VERSION
    except (TypeError, ValueError):
        return True


def mark_onboarding_seen(path):
    update_settings(path, onboarding_version=ONBOARDING_VERSION)


def _rounded_rectangle(canvas, x1, y1, x2, y2, radius, **options):
    points = (
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    )
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **options)


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text,
        width,
        fill,
        hover_fill,
        foreground,
        font,
        command=None,
    ):
        super().__init__(
            parent,
            width=width,
            height=30,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=True,
        )
        self._text = text
        self._fill = fill
        self._hover_fill = hover_fill
        self._foreground = foreground
        self._font = font
        self._command = command
        self._enabled = True
        self._hovered = False
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonRelease-1>", self._click)
        self.bind("<Return>", self._click)
        self.bind("<space>", self._click)
        self._draw()

    def _draw(self):
        self.delete("all")
        fill = self._hover_fill if self._hovered and self._enabled else self._fill
        foreground = self._foreground if self._enabled else "#AAA8A3"
        _rounded_rectangle(self, 1, 1, int(self.cget("width")) - 1, 29, 11, fill=fill, outline="")
        self.create_text(
            int(self.cget("width")) // 2,
            15,
            text=self._text,
            fill=foreground,
            font=self._font,
        )

    def _enter(self, event=None):
        self._hovered = True
        self._draw()

    def _leave(self, event=None):
        self._hovered = False
        self._draw()

    def _click(self, event=None):
        if self._enabled and self._command is not None:
            self._command()

    def set_command(self, command):
        self._command = command

    def set_text(self, text):
        self._text = text
        self._draw()

    def set_enabled(self, enabled):
        self._enabled = bool(enabled)
        self.configure(cursor="hand2" if self._enabled else "arrow")
        self._draw()


def show_onboarding(parent, settings_path, on_close=None):
    palette = {
        "paper": "#F7F6F3",
        "card": "#FFFFFF",
        "ink": "#1A1B18",
        "muted": "#686B66",
        "line": "#D9D8D0",
        "accent": "#C15A34",
    }
    window = tk.Toplevel(parent)
    window.title("欢迎使用盯盯喵")
    window.configure(bg=palette["paper"])
    window.resizable(False, False)
    window.transient(parent)
    window.attributes("-topmost", True)
    window.attributes("-alpha", 1.0)

    width, height = 390, 360
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x = max(0, (screen_w - width) // 2)
    y = max(0, (screen_h - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")

    shell = tk.Frame(window, bg=palette["paper"], padx=24, pady=20)
    shell.pack(fill="both", expand=True)
    brand = tk.Label(
        shell,
        text="盯盯喵  ·  第一次见面",
        font=("Microsoft YaHei UI", 10, "bold"),
        fg=palette["accent"],
        bg=palette["paper"],
    )
    brand.grid(row=0, column=0, sticky="w")

    card_canvas = tk.Canvas(shell, bg=palette["paper"], highlightthickness=0, bd=0)
    card_canvas.grid(row=1, column=0, sticky="nsew", pady=(12, 14))
    card = tk.Frame(card_canvas, bg=palette["card"])
    card_window = card_canvas.create_window(20, 16, window=card, anchor="nw")

    def resize_card(event):
        card_canvas.delete("card_shape")
        _rounded_rectangle(
            card_canvas,
            2,
            3,
            event.width - 1,
            event.height - 1,
            18,
            fill="#E6E2DB",
            outline="",
            tags="card_shape",
        )
        _rounded_rectangle(
            card_canvas,
            0,
            0,
            event.width - 3,
            event.height - 4,
            18,
            fill=palette["card"],
            outline="",
            tags="card_shape",
        )
        card_canvas.tag_lower("card_shape")
        card_canvas.coords(card_window, 20, 16)
        card_canvas.itemconfigure(
            card_window,
            width=max(1, event.width - 43),
            height=max(1, event.height - 36),
        )

    card_canvas.bind("<Configure>", resize_card)

    counter = tk.Label(card, font=("Microsoft YaHei UI", 9), fg=palette["muted"], bg=palette["card"])
    counter.pack(anchor="w")
    title = tk.Label(
        card,
        font=("Microsoft YaHei UI", 17, "bold"),
        fg=palette["ink"],
        bg=palette["card"],
        anchor="w",
    )
    title.pack(fill="x", pady=(8, 12))
    body = tk.Label(
        card,
        font=("Microsoft YaHei UI", 10),
        fg=palette["muted"],
        bg=palette["card"],
        justify="left",
        anchor="nw",
        wraplength=292,
    )
    body.pack(fill="both", expand=True)
    progress = tk.Label(card, font=("Microsoft YaHei UI", 10), fg=palette["accent"], bg=palette["card"])
    progress.pack(anchor="w", pady=(8, 0))

    controls = tk.Frame(shell, bg=palette["paper"])
    controls.grid(row=2, column=0, sticky="ew")
    shell.grid_columnconfigure(0, weight=1)
    shell.grid_rowconfigure(1, weight=1)
    skip_button = tk.Button(
        controls,
        text="跳过教程",
        relief="flat",
        bd=0,
        font=("Microsoft YaHei UI", 9),
        fg=palette["muted"],
        bg=palette["paper"],
        activebackground=palette["paper"],
        highlightthickness=0,
        cursor="hand2",
    )
    skip_button.pack(side="left")
    back_button = RoundedButton(
        controls,
        text="上一步",
        width=76,
        fill="#ECE9E3",
        hover_fill="#E2DED6",
        foreground=palette["ink"],
        font=("Microsoft YaHei UI", 9),
    )
    next_button = RoundedButton(
        controls,
        text="下一步",
        width=88,
        fill=palette["accent"],
        hover_fill="#A94D2C",
        foreground="#FFFFFF",
        font=("Microsoft YaHei UI", 9, "bold"),
    )
    next_button.pack(side="right")
    back_button.pack(side="right", padx=(0, 8))

    state = {"index": 0, "closed": False}

    def close():
        if state["closed"]:
            return
        state["closed"] = True
        try:
            mark_onboarding_seen(settings_path)
        except OSError:
            pass
        try:
            window.grab_release()
        except tk.TclError:
            pass
        window.destroy()
        if on_close is not None:
            on_close()

    def render():
        index = state["index"]
        step_title, step_body = ONBOARDING_STEPS[index]
        counter.configure(text=f"使用指南  {index + 1} / {len(ONBOARDING_STEPS)}")
        title.configure(text=step_title)
        body.configure(text=step_body)
        progress.configure(
            text="  ".join("●" if i == index else "○" for i in range(len(ONBOARDING_STEPS)))
        )
        back_button.set_enabled(index > 0)
        next_button.set_text("开始使用" if index == len(ONBOARDING_STEPS) - 1 else "下一步")

    def go_back():
        if state["index"] > 0:
            state["index"] -= 1
            render()

    def go_next():
        if state["index"] >= len(ONBOARDING_STEPS) - 1:
            close()
            return
        state["index"] += 1
        render()

    skip_button.configure(command=close)
    back_button.set_command(go_back)
    next_button.set_command(go_next)
    window.protocol("WM_DELETE_WINDOW", close)
    window.bind("<Escape>", lambda event: close())
    window.bind("<Left>", lambda event: go_back())
    window.bind("<Right>", lambda event: go_next())
    render()
    window.after_idle(window.grab_set)
    next_button.focus_set()
    return window
