# 盯盯喵 · DingDingMeow

> 一只桌面小猫，用你自己的摄像头替你盯健康。100% 本地跑，画面一帧都不上传。

[![Download](https://img.shields.io/badge/download-v1.5.1-C15A34)](https://github.com/denngyu/dingding-meow/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-1A1B18)](LICENSE)
[![Local-only](https://img.shields.io/badge/local--only-0%20network-2F6E54)](#)

## 它能干啥

- **中央叩屏提醒** — 连续久坐满 1 小时，猫缩成小毛球沿 X 轴滚到中央叩屏三次，再滚回原位
- **锁屏与离座续接** — 锁屏立即算离开；托腮或短暂丢脸 30 秒内回来继续累计
- **喝水记录 · 猫抱杯** — 识别到你举杯喝水，桌上的小猫也会举杯陪你喝
- **饮水目标 + 提醒** — 每天 2000ml 目标，默认 30 分钟提醒，可调 20–90 分钟
- **点眼睛看画面** — 默认闭眼只默默数着，点它眼睛监控画面从脑袋里升起
- **每日健康报告** — 气泡里的 📊 报告按钮或托盘菜单打开，饮水趋势、坐时长、7 天对比
- **托盘 + 开机自启** — 桌角一直有它，托盘可以随时暂停
- **更稳的人脸判断** — 双正脸分类器交叉确认、侧脸对称假目标过滤，降低柜子纹理误判
- **延时摄影**（v1.5 新）— 默认关闭，右键或托盘手动开始才录；每 60 秒一帧，停止时本地合成 MP4，菜单可直接「查看延时摄影」
- **猫咪皮肤**（v1.5 新）— 银灰经典 / 暖橘元气两套，右键或托盘切换，选择记在本地
- **摄像头没信号会自己让路**（v1.5.1 新）— 被别的软件占用或读不到画面时释放设备并显示「点击开始检测」，不再假装还在盯

宣传页 & 演示: <https://denngyu.github.io/dingding-meow/>
一张图看懂: [onepage.html](onepage.html)

## 下载

**推荐 · Windows 便携版**
从 [Releases](https://github.com/denngyu/dingding-meow/releases/latest) 下载 `DingDingMeow-windows.zip`，解压到任意目录，双击 `盯盯喵.vbs` 即可（全程无黑窗）。

**从源码跑**
```
pip install opencv-python==4.10.0.84 pillow numpy pystray
python pet.py
```

## 隐私与本地化

- 摄像头帧只在**本地内存**中处理，不上传、不缓存到磁盘（用户主动点"睁眼"看画面时才会显示到浮窗里，也只在本机内存里显示）
- 所有日志（久坐段、喝水记录）都写在项目本地 `logs/` 目录
- 不联网，不带任何 API 调用，`gh` / `pip` 是安装期依赖，运行期完全离线

## 技术栈

- Python 3.12 + tkinter Canvas + OpenCV 4.10 + YOLOv4-tiny + pystray + Pillow
- Windows 10/11（`-transparentcolor` 依赖 Windows API，暂不支持 macOS/Linux）
- exe 大小约 66MB（PyInstaller onefile，含 cv2/PIL/pystray）

## 项目结构

```
盯盯喵/
├── pet.py               主程序，检测循环+浮窗+托盘调度
├── cat_sprites.py       图片猫状态映射与素材加载
├── cat_visual.py        连续动画采样
├── face_detection.py    正脸/侧脸/翻转侧脸检测
├── cup_detection.py     杯子候选解码与近脸裁切
├── camera_capture.py    摄像头开关、锁屏释放与后端回退重连
├── session_state.py     Windows 锁屏检测
├── center_nudge.py      一小时中央滚动叩屏时间轴
├── timelapse.py         延时摄影抓帧与 MP4 合成
├── skin_system.py       皮肤发现、解析与持久化
├── window_placement.py  多屏切单屏时把浮窗拉回主屏
├── onboarding.py        首次启动教程
├── report_icon.py       健康报告的 favicon 内嵌
├── settings_store.py    settings.json 原子读写
├── ui_behavior.py       悬停行为与状态文案
├── status_label.py      无紫边状态签渲染
├── water_reminder.py    喝水提醒持久化
├── water_input.py       饮水弹窗尺寸与手填值校验
├── assets/cat_sprites/  8 张 384×384 透明 PNG（经典皮肤）
├── assets/skins/        可扩展皮肤包（orange = 暖橘元气）
├── assets/cat_animations/knock/  叩屏动作帧
├── assets/cat_animations/roll/   独立毛球素材
├── models/              YOLOv4-tiny.cfg/weights
├── tests/               单元测试
├── 工具/                辅助脚本（图集拆分等）
├── 版本存档/            历史 pet_v1.0~v1.2.py
├── 工作记录/            每日开发笔记（可选参考）
├── 盯盯喵.vbs           无黑窗启动器
├── 盯盯喵.bat           备用启动
├── index.html           宣传页（同 GitHub Pages 上那个）
├── onepage.html         一张图讲清全部功能
├── 交接文档.md          v1.5.0 详细技术交接
├── 项目复盘.md          从想法到落地的踩坑记录
├── CLAUDE.md            项目规范
└── error_log.md         严重错误档案
```

## 从源码打包 exe

```
pyinstaller --onefile --windowed --name 盯盯喵 \
  --collect-all cv2 --collect-all PIL --collect-all pystray pet.py
```

打完后把 `models/`、`assets/cat_sprites/`、`assets/cat_animations/knock/` 和
`assets/cat_animations/roll/` 复制到 `dist/` 里（跟 exe 平级），双击运行。

## 版本历史

- **v1.5.1 · 2026-07-16** — 摄像头无信号进入 camera_off 可点击恢复、菜单加「查看延时摄影」、饮水框加高到 420px 可拖动、快捷档改为一口 50 / 一大口 100 / 半杯 150 / 一杯 300
- v1.5.0 · 2026-07-16 — 延时摄影（默认关，手动开）、猫咪皮肤（银灰经典 / 暖橘元气）、饮水降误报、圆角饮水框、锁屏后摄像头自动恢复
- v1.4.0 · 2026-07-16 — 水平毛球滚动、中央叩屏三次、锁屏立即离开、30 秒会话续接、柜子误判收敛、饮水误判可关闭
- v1.0.1 · 2026-07-15 — 手动记录喝水、多屏切单屏自动归位、图标统一
- **v1.0.0 · 2026-07-15** — 首个正式发布：图片猫、锁屏检测、可调喝水提醒、悬停展开气泡、新手教程、报告 favicon
- v1.3 · 缩小 27%、猫咪重画更可爱、气泡加日志/报告按钮
- v1.2 · 猫抱杯动画、饮水目标、托盘、开机自启、每日报告
- v1.1 · Canvas 画猫、气泡框、点眼睛看画面
- v1.0-preview · 首个能跑的原型，文本颜文字猫

详细技术演化见 [交接文档.md](交接文档.md)。

## License

[MIT](LICENSE) · 拿去随便改随便发，署个名就行。

---

> 从一句"能不能看到我摄像头"到一只有名字有说明书有 exe 有安装包的桌面小猫。完结撒花。
