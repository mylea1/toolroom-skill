# Toolroom Skill

将本地项目变成可搜索的离线工具室。扫描项目与应用，整合重复副本，悬停查看 README、部署目录、版本与启动命令，并结合 Codex 历史整理实际用途。

## 安装

需要 Python 3.9+；读取 Git 信息需要 git。

```sh
git clone https://github.com/mylea1/toolroom-skill.git "${CODEX_HOME:-$HOME/.codex}/skills/toolroom"
```

已有同名目录时请先保留或合并现有内容。

## 使用

在 Codex 输入：

> 使用 $toolroom，扫描本机项目，合并重复副本，结合历史会话整理用途，生成可视化工具室。

也可单独生成本地目录快照：

```sh
python3 scripts/build_catalog.py --root /path/to/projects --output /path/to/output/index.html
```

直接打开 HTML 即可离线使用。历史用途由 agent 阅读证据后补充，并非扫描脚本自动推断。页面支持搜索、设备筛选、分页、缩放、悬停详情与副本切换；启动命令仅供复制，不会自动启动项目。合并为启发式判断，所有原始记录与本地文件保留。

## 数据

仓库只包含通用技能、脚本、模板和测试，不包含个人聊天、项目清单或生成页面。生成的 HTML/JSON 包含本地路径和 README，应按个人资料保管。

## 来源与许可

包含来自 [Workstation-OPC](https://github.com/cyberdaddyleo/workstation-OPC) 的场景代码。Developed by @赛博老爸。

本版本由他人修改，非作者原版。主要改动：本地项目扫描、重复副本整合、设备与机房界面调整、README 嵌入和悬停详情。上游部分适用 [个人免费使用许可](assets/workstation-LICENSE.txt)，商业使用需作者授权。

测试：`python3 -m unittest discover -s tests`。
