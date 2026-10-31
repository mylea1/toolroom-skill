# 本地工具工作室

HTML 是可直接打开的离线快照，无 CDN 或外部脚本。默认复用 Workstation-OPC 的原始 SVG 机房场景，将真实项目映射为服务器、电脑与手机；保留作者署名、开发者水印及 assets/workstation-LICENSE.txt。本版本由他人修改，非作者原版。扫描只读文件和 Git 元数据，不安装依赖、不启动发现的项目。Python 3.9+；Git 信息需要本机 git。

```sh
python3 scripts/build_catalog.py --root /path/to/projects --root /path/to/other \
  --annotations /path/to/private/annotations.json --output /path/to/output/index.html
```

输出 HTML 和同名 JSON。`--root` 可重复，`--max-depth` 默认 10。识别 Git、常见包配置、Xcode、带 README 的静态站和 .app；跳过依赖、构建产物和隐藏目录。嵌套工程内部仅独立 Git 项目和应用包另计。软链接按真实路径合并。扫描记录显示根目录、深度和读取错误；不是所有硬盘文件的穷尽搜索。

启动入口来自 package scripts、启动脚本、Compose、Xcode 和应用包；静态 HTTP 命令明确标为建议。命令从未自动执行，不代表依赖齐全或当前可启动。

重复组优先按规范化 remote，其次应用 bundle ID、包 name 判断身份；包名组可能是无关同名包，需要核对。显示版本、分支、提交、已跟踪文件修改状态，不凭目录同名合并，不删除副本。Fork 的 remote 不同则不会自动归为一组。

## 历史注释

扫描本身不能推断历史用途。按 SKILL 的证据流程读取会话后，写私有 annotations JSON：

```json
{
  "projects": [{
    "match": {"name": "example"},
    "description": "项目用途",
    "category": "开发工具",
    "uses": ["实际完成的任务及结果"],
    "evidence": "会话 ID、日期、来源文件与行号",
    "runStatus": "历史验证成功"
  }],
  "workflows": [{
    "title": "示例工作流",
    "description": "有依据的任务串联",
    "status": "历史完成情况",
    "evidence": "原始来源",
    "steps": [{"title": "步骤", "description": "做了什么", "projects": ["example"]}]
  }]
}
```

match 可用 name、path、repo，多字段同时匹配；同名多项目优先用 path。可添加 displayName、commands（label、command、source、kind）。工作流按项目名关联；检查每步 ids 是否匹配，避免把研究意图写成实际操作。没有用途记录的项目照常显示“使用记录待补充”。

支持全文检索（含 README）、设备类型筛选、每组 12 个项目分页、缩放和全屏。悬停设备打开详情，浮层支持滚动、复制路径/命令/README；点击设备固定，Esc 关闭。读取根目录 README，最多嵌入 1 MiB，超出时显示截断提示。README 以转义后的纯文本呈现，避免执行其中 HTML。未发现文件时明确显示。历史相关对话暂不单独链接。浏览器不会自行扫描磁盘，更新必须运行扫描脚本。

个人清单和注释保留在公共代码仓库之外。公开仓库只包含模板、脚本和虚构测试。场景源码来自 https://github.com/cyberdaddyleo/workstation-OPC ，适用随附个人免费使用许可；新增本地项目数据映射与悬停资料功能。
