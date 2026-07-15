# GitHub Pages 入口同步

## 问题

- `promo.html` 已更新监控演示图与完整画幅，但 GitHub Pages 实际发布入口是 `index.html`。
- 远端 `main/index.html` 和公开链接仍包含旧的 `aspect-ratio:1/1.15`，未引用 `assets/preview_camera.png`。

## 修复

- 将已验收的 `promo.html` 内容同步到 `index.html`。
- 新增回归测试，要求 `index.html` 与 `promo.html` 字节级一致，防止以后只改宣传页源文件却漏掉 Pages 入口。

## 验收

- 修复前回归测试按预期失败；修复后通过。
- `index.html` 与 `promo.html` 的 SHA-256 完全一致。
- 推送后以公开 GitHub Pages 响应包含新版演示图路径和 1:1.32 画幅为最终验收条件。
