# deployment-history · 部署工具回顾

一个 Codex skill：结合历史会话与本地项目文件，整理你曾经拉取、下载、安装、部署或配置过的工具，以及后来用它们做过什么，生成 Markdown 清单。

## 能做什么

- 读取本机 Codex 的 `sessions/` 和 `archived_sessions/` 历史。
- 支持消息、工具调用及返回、`item_completed` 中的命令执行与 MCP 调用。
- 保留会话 ID、时间、原始文件和行号，便于追溯。
- 根据工具名称、仓库、命令、目录等别名跨会话追踪后续用途。
- 检测到仓库、源码目录、下载包、应用文件或历史归档记录，就计为“已拉取／已获取”。
- 分别记录获取状态、运行状态和用途。没有使用记录时写“使用记录待补充”。

扫描器负责建立和检索证据索引；Codex 按 skill 指令阅读上下文、确认工具身份、合并重复记录并撰写报告。不是运行一次 Python 就能独立生成全部语义结论。

## 安装

需要 Codex、可访问的本地会话记录，以及 Python 3.9 或更高版本。扫描脚本只使用 Python 标准库。

将本仓库放进 Codex 技能目录中的 `deployment-history` 文件夹。通常为 `~/.codex/skills/deployment-history`；设置了 `CODEX_HOME` 时使用该目录下的 `skills`。

```sh
git clone https://github.com/mylea1/deployment-history.git "${CODEX_HOME:-$HOME/.codex}/skills/deployment-history"
```

若已有同名目录，请先保留现有版本，再决定合并或替换；上述命令不会覆盖已有目录。

## 使用

在 Codex 中输入：

> 使用 $deployment-history，整理本机拉取、下载、部署过的工具，说明用途和后续使用记录，生成 Markdown 文档。

也可以限定范围：

> 使用 $deployment-history，只整理移动应用开发和分析相关工具。

默认交付 `部署工具与使用记录.md`，包含工具总览、用途、获取和部署经过、后续任务、产物及来源索引。先做本机扫描；其他设备或云端历史需要相应可访问来源。

## 扫描器命令

在仓库根目录执行：

```sh
python3 scripts/scan_history.py build --db work/history.sqlite
python3 scripts/scan_history.py coverage --db work/history.sqlite
python3 scripts/scan_history.py candidates --db work/history.sqlite --limit 40 --offset 0
python3 scripts/scan_history.py search --db work/history.sqlite --term frida --term super-trouper
```

每页返回 `total` 和 `next_offset`；完整遍历请持续翻页，直到 `next_offset` 为 null。关键词命中只是线索。

```sh
python3 scripts/scan_history.py context --db work/history.sqlite \
  --source /absolute/path/to/session.jsonl --line 100 --context 20 --max-chars 0
```

`--max-chars 0` 返回完整相关记录。`build` 拒绝覆盖已有索引；重新扫描请换一个数据库文件名。用重复的 `--root /path/to/codex-home` 参数可扫描多个历史根目录。

## 数据与范围

历史以只读方式读取，不重新执行历史中的命令。索引保存在本地工作目录；脚本不主动上传历史。交给 Codex 分析的内容遵循你当前 Codex 服务与账号的数据设置。

脚本包含常见凭据模式的脱敏，但不是完整秘密检测器。不要将个人历史索引或未经检查的报告提交到公开仓库。本仓库不包含作者的聊天记录、索引或盘点报告。

历史格式可能随 Codex 版本变化；扫描结果中的未提取类型需结合实际格式检查。本地不存在、已删除、未同步或原本已截断的内容无法恢复。“已获取”不等于目前正在运行，也不等于曾完成某项具体任务。

## 目录

```text
SKILL.md                     技能入口与判定流程
agents/openai.yaml           Codex 技能展示信息
scripts/scan_history.py      本地索引与证据检索
references/report-schema.md  Markdown 报告规范
```

## 可搜索 HTML 工具工作室

离线工作室采用 Workstation-OPC 的原始机房场景：真实项目对应机柜、电脑和手机。悬停查看 README、部署目录、启动命令和历史用途；支持搜索、类型筛选、分页、缩放、固定详情与复制。扫描 JSON 保留副本比较与工作流数据。

```sh
python3 scripts/build_catalog.py --root /path/to/projects --output /path/to/private/index.html
```

直接打开生成的 HTML。用 `--annotations` 加入经会话核实的用途和工作流；脚本不会自行推断历史用途。详细格式与扫描边界见 [工作室规范](references/catalog.md)。

在 Codex 中可说：“使用 $deployment-history，扫描本地项目并生成工具工作室，补充启动方式、重复版本和历史工作流。”

测试：`python3 -m unittest discover -s tests`。

### 场景来源与许可

场景代码来自 [Workstation-OPC](https://github.com/cyberdaddyleo/workstation-OPC)，Developed by @赛博老爸。本版本由他人修改，非作者原版；主要改动为本地项目映射、README 嵌入与悬停详情。场景适用 [上游个人免费使用许可](assets/workstation-LICENSE.txt)，商业使用需作者授权。
