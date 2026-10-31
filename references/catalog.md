# 本地工具工作室

HTML 是可直接打开的离线快照，无 CDN 或外部脚本。扫描只读文件和 Git 元数据，不安装依赖、不启动发现的项目。Python 3.9+；Git 信息需要本机 git。

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

支持全文检索、分类、启动中心、副本比较、工作流、常用、备注、Markdown/JSON 导出与 JSON 导入。常用和备注保存在浏览器 localStorage，导出 JSON 可备份。导入数据只影响当前页面，重新打开原 HTML 仍加载原快照。重新扫描必须运行脚本；浏览器不会自行读取电脑。

个人清单和注释保留在公共代码仓库之外。公开仓库只包含模板、脚本和虚构测试。HTML 界面为原创，不包含参考站点源码或素材。
