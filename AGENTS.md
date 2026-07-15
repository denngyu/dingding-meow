# 工作台说明（非 Claude harness 入口）

本仓库规范的唯一事实源是 [CLAUDE.md](CLAUDE.md)，本文件只做路径映射，不复制正文（复制会漂移）。

## 路径映射

- **技能库**：`.claude/skills/` 是唯一事实源；`.agents/skills/` 是供其他 harness 读取的镜像，内容改动一律先改 `.claude/skills/` 再同步过去。
- **子代理定义**：Claude Code 用 `.claude/agents/*.md`；Codex 用 `.codex/agents/*.toml`。
- **工作规则**：`.claude/rules/`（no_ai_style / error_log / sub_agent_dispatch / feishu_doc_write 等）。
- **工作流脚本**：`工具/`（anonymize.py 脱敏、restore.py 还原、数据体检.py 进场校验、一键脱敏.bat）。

## 执行约定

目录结构、脱敏合规工作流（强制）、开工前三道关卡、写作规范、技能名称对照表，全部以 [CLAUDE.md](CLAUDE.md) 原文为准执行。文中的「Claude」在其他 harness 环境下读作当前 agent 自身。

核心合规红线（此条例外，值得双写）：只读 `项目/<品牌>/data/masked/`，绝不读取 raw、已脱敏、敏感词表、脱敏映射文件；报告一律用代号。
