"""盯盯喵的纯动画采样与Canvas矢量绘制，不依赖Tk实例或摄像头。"""

from dataclasses import dataclass
import math


INK = "#1A1B18"
INK2 = "#585C57"
FUR = "#B8B4AC"
FUR_DARK = "#817D75"
FUR_LIGHT = "#F0EDE5"
NOSE = "#E99A94"
CHEEK = "#F2B8B2"
EYE_AMBER = "#9A663D"
CUP_BODY = "#B0DDF0"
CUP_WATER = "#4A9DC7"

TAIL_CYCLE_SEC = 5.6
BREATH_CYCLE_SEC = 3.8


@dataclass(frozen=True)
class CatPose:
    breath: float
    tail_sway: float
    head_bob: float
    alert_offset: float
    ear_twitch: float


@dataclass(frozen=True)
class DrinkMotion:
    lift: float
    tilt: float
    sip: float


def clamp01(value):
    return max(0.0, min(1.0, float(value)))


def ease_out_quart(value):
    value = clamp01(value)
    return 1.0 - (1.0 - value) ** 4


def drink_prompt_delay_ms(animation_seconds):
    return max(0, int(round(float(animation_seconds) * 1000)))


def _rested_tail(elapsed, cycle=TAIL_CYCLE_SEC, amplitude=8.0):
    """一次摆动后停一会，循环两端的速度也归零。"""
    phase = (elapsed % cycle) / cycle
    if phase < 0.18 or phase > 0.82:
        return 0.0
    move = (phase - 0.18) / 0.64
    return amplitude * math.sin(math.tau * move) * math.sin(math.pi * move)


def _alert_offset(elapsed):
    """每2.8秒短促提醒一次，其余时间保持安静。"""
    phase = elapsed % 2.8
    if phase >= 0.42:
        return 0.0
    envelope = (1.0 - phase / 0.42) ** 2
    return 1.6 * math.sin(math.tau * 4.0 * phase) * envelope


def sample_cat_pose(elapsed, mood="seated"):
    elapsed = max(0.0, float(elapsed))
    breath = 0.5 - 0.5 * math.cos(math.tau * elapsed / BREATH_CYCLE_SEC)
    head_bob = -0.55 * breath
    ear_phase = elapsed % 10.4
    ear_twitch = math.sin(math.pi * ear_phase / 0.3) * 2.8 if ear_phase < 0.3 else 0.0

    if mood == "over":
        tail_sway = _rested_tail(elapsed, cycle=2.2, amplitude=5.0)
        alert_offset = _alert_offset(elapsed)
        ear_twitch = 0.0
    elif mood in ("away", "blocked", "paused"):
        tail_sway = _rested_tail(elapsed, cycle=8.2, amplitude=3.0)
        alert_offset = 0.0
        ear_twitch *= 0.35
        head_bob *= 0.65
    else:
        tail_sway = _rested_tail(elapsed)
        alert_offset = 0.0

    return CatPose(
        breath=breath,
        tail_sway=tail_sway,
        head_bob=head_bob,
        alert_offset=alert_offset,
        ear_twitch=ear_twitch,
    )


def sample_drink_motion(progress):
    progress = clamp01(progress)
    if progress < 0.32:
        lift = ease_out_quart(progress / 0.32)
    elif progress <= 0.72:
        lift = 1.0
    else:
        lift = 1.0 - ease_out_quart((progress - 0.72) / 0.28)
    sip = math.sin(math.pi * clamp01((progress - 0.34) / 0.34)) if 0.34 < progress < 0.68 else 0.0
    return DrinkMotion(lift=lift, tilt=38.0 * lift, sip=sip)


def draw_cup(canvas, x, y, tilt=0.0, scale=0.9):
    angle = math.radians(tilt)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    width, height = 12 * scale, 14 * scale

    def rotate(px, py):
        return x + px * cos_a - py * sin_a, y + px * sin_a + py * cos_a

    vessel = [rotate(-width / 2, -height / 2), rotate(width / 2, -height / 2),
              rotate(width / 2 - 2, height / 2), rotate(-width / 2 + 2, height / 2)]
    canvas.create_polygon([value for point in vessel for value in point],
                          fill=CUP_BODY, outline=INK, width=1.1, smooth=True)
    water_y = -height / 2 + 3
    water = [rotate(-width / 2 + 1, water_y), rotate(width / 2 - 1, water_y),
             rotate(width / 2 - 2.2, height / 2 - 1), rotate(-width / 2 + 2.2, height / 2 - 1)]
    canvas.create_polygon([value for point in water for value in point], fill=CUP_WATER, outline="", smooth=True)
    canvas.create_line(*rotate(-width / 2, -height / 2 + 0.5),
                       *rotate(width / 2, -height / 2 + 0.5), fill="#FFFFFF", width=1)
    handle = [rotate(width / 2, -height / 2 + 2.5), rotate(width / 2 + 4, -height / 2 + 3.5),
              rotate(width / 2 + 4, height / 2 - 3.5), rotate(width / 2, height / 2 - 2.5)]
    canvas.create_line([value for point in handle for value in point], fill=INK, width=1.1, smooth=True)


def draw_cat(canvas, cx, cy, eyes_open=False, blink=False, mood="seated", pose=None, cup_state=None):
    pose = pose or sample_cat_pose(0.0, mood)
    hx = cx + pose.alert_offset
    hy = cy + pose.head_bob
    body_expand = pose.breath * 0.8
    body_top = cy + 30 - body_expand
    body_bottom = cy + 72

    # 接地阴影、尾巴、身体，先后顺序保证尾巴从身体后方长出来。
    canvas.create_oval(cx - 31, cy + 66, cx + 34, cy + 76, fill="#DEDCD6", outline="")
    tail = [
        cx + 23, cy + 57,
        cx + 48, cy + 61 + pose.tail_sway * 0.18,
        cx + 58 + pose.tail_sway * 0.42, cy + 38,
        cx + 42 + pose.tail_sway, cy + 24,
    ]
    canvas.create_line(tail, fill=FUR, width=9, smooth=True, splinesteps=20,
                       capstyle="round", joinstyle="round")
    canvas.create_oval(cx - 30 - body_expand * 0.3, body_top,
                       cx + 30 + body_expand * 0.3, body_bottom,
                       fill=FUR, outline=FUR_DARK, width=1.1)
    canvas.create_oval(cx - 17, body_top + 6, cx + 17, body_bottom - 2,
                       fill=FUR_LIGHT, outline="")

    # 后脚形成稳定坐姿，前爪稍微压在身体前面。
    canvas.create_oval(cx - 31, body_bottom - 10, cx - 7, body_bottom,
                       fill=FUR, outline=FUR_DARK, width=1)
    canvas.create_oval(cx + 7, body_bottom - 10, cx + 31, body_bottom,
                       fill=FUR, outline=FUR_DARK, width=1)
    canvas.create_line(cx - 23, body_bottom - 4, cx - 14, body_bottom - 4, fill=FUR_DARK, width=0.8)
    canvas.create_line(cx + 14, body_bottom - 4, cx + 23, body_bottom - 4, fill=FUR_DARK, width=0.8)

    # 久坐状态把耳朵压低，平时只允许右耳偶尔轻弹。
    over = mood == "over"
    left_tip = (hx - 39, hy - (39 if over else 50))
    right_tip = (hx + 39, hy - (39 if over else 50) - pose.ear_twitch)
    canvas.create_polygon(hx - 32, hy - 20, *left_tip, hx - 14, hy - 27,
                          fill=FUR, outline=FUR_DARK, width=1.2, smooth=True)
    canvas.create_polygon(hx + 32, hy - 20, *right_tip, hx + 14, hy - 27,
                          fill=FUR, outline=FUR_DARK, width=1.2, smooth=True)
    canvas.create_polygon(hx - 29, hy - 23, hx - 35, hy - (35 if over else 44), hx - 20, hy - 28,
                          fill=NOSE, outline="", smooth=True)
    canvas.create_polygon(hx + 29, hy - 23, hx + 35, hy - (35 if over else 44) - pose.ear_twitch * 0.75,
                          hx + 20, hy - 28, fill=NOSE, outline="", smooth=True)
    canvas.create_oval(hx - 38, hy - 32, hx + 38, hy + 38,
                       fill=FUR, outline=FUR_DARK, width=1.2)

    # 小块口鼻浅色替代整张奶油色面罩，轮廓更像猫。
    canvas.create_oval(hx - 19, hy + 6, hx + 1, hy + 28, fill=FUR_LIGHT, outline="")
    canvas.create_oval(hx - 1, hy + 6, hx + 19, hy + 28, fill=FUR_LIGHT, outline="")
    canvas.create_line(hx - 9, hy - 25, hx - 6, hy - 18, fill=FUR_DARK, width=1.4)
    canvas.create_line(hx, hy - 27, hx, hy - 18, fill=FUR_DARK, width=1.4)
    canvas.create_line(hx + 9, hy - 25, hx + 6, hy - 18, fill=FUR_DARK, width=1.4)

    eye_y = hy - 3
    eye_left, eye_right = hx - 13, hx + 13
    if eyes_open and not blink:
        for eye_x in (eye_left, eye_right):
            canvas.create_oval(eye_x - 8, eye_y - 9, eye_x + 8, eye_y + 9,
                               fill="#FFFFFF", outline=INK, width=1.25)
            canvas.create_oval(eye_x - 4.8, eye_y - 6.5, eye_x + 4.8, eye_y + 7,
                               fill=EYE_AMBER, outline="")
            canvas.create_oval(eye_x - 2.5, eye_y - 5.5, eye_x + 2.5, eye_y + 6,
                               fill=INK, outline="")
            canvas.create_oval(eye_x - 2.8, eye_y - 5.8, eye_x - 0.2, eye_y - 3.2,
                               fill="#FFFFFF", outline="")
    elif over:
        canvas.create_line(eye_left - 7, eye_y + 2, eye_left + 7, eye_y - 1, fill=INK, width=2.1)
        canvas.create_line(eye_right - 7, eye_y - 1, eye_right + 7, eye_y + 2, fill=INK, width=2.1)
    else:
        canvas.create_arc(eye_left - 7, eye_y, eye_left + 7, eye_y + 10,
                          start=8, extent=164, style="arc", outline=INK, width=2)
        canvas.create_arc(eye_right - 7, eye_y, eye_right + 7, eye_y + 10,
                          start=8, extent=164, style="arc", outline=INK, width=2)

    canvas.create_oval(hx - 25, hy + 7, hx - 15, hy + 13, fill=CHEEK, outline="")
    canvas.create_oval(hx + 15, hy + 7, hx + 25, hy + 13, fill=CHEEK, outline="")
    canvas.create_polygon(hx - 3.5, hy + 11, hx + 3.5, hy + 11, hx, hy + 15,
                          fill=NOSE, outline=INK, width=0.9, smooth=True)

    drinking = False
    if cup_state and cup_state[0] == "drink":
        drinking = sample_drink_motion(cup_state[1]).sip > 0.18
    if over:
        canvas.create_arc(hx - 6, hy + 18, hx + 6, hy + 26,
                          start=20, extent=140, style="arc", outline=INK, width=1.3)
    elif drinking:
        canvas.create_oval(hx - 2.7, hy + 16, hx + 2.7, hy + 21, fill="#5A2E28", outline=INK, width=0.8)
    else:
        canvas.create_line(hx, hy + 15, hx, hy + 17, fill=INK, width=1)
        canvas.create_arc(hx - 6, hy + 13, hx, hy + 20, start=260, extent=90,
                          style="arc", outline=INK, width=1.1)
        canvas.create_arc(hx, hy + 13, hx + 6, hy + 20, start=190, extent=90,
                          style="arc", outline=INK, width=1.1)

    for whisker_y, slope in ((hy + 7, -1), (hy + 11, 1)):
        canvas.create_line(hx - 24, whisker_y, hx - 40, whisker_y + slope, fill=INK2, width=0.8)
        canvas.create_line(hx + 24, whisker_y, hx + 40, whisker_y + slope, fill=INK2, width=0.8)

    if cup_state:
        state, progress = cup_state
        motion = sample_drink_motion(progress) if state == "drink" else DrinkMotion(0.0, 0.0, 0.0)
        base_x, base_y = cx - 16, body_bottom - 16
        cup_x = base_x + (hx - 4 - base_x) * motion.lift
        cup_y = base_y + (hy + 13 - base_y) * motion.lift - math.sin(math.pi * motion.lift) * 3
        paw_x = cx - 13 + (hx - 9 - (cx - 13)) * motion.lift
        paw_y = body_bottom - 18 + (hy + 19 - (body_bottom - 18)) * motion.lift
        canvas.create_oval(paw_x - 6, paw_y - 5, paw_x + 5, paw_y + 5,
                           fill=FUR_LIGHT, outline=FUR_DARK, width=0.9)
        draw_cup(canvas, cup_x, cup_y, tilt=motion.tilt, scale=0.86)
