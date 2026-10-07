---
name: xiaoyuzhou-transcript
description: 小宇宙播客「单集链接 → 校对版逐字稿 md → Obsidian Reading Hub 沉浸式阅读」全流程。当用户给出一个 xiaoyuzhoufm.com/episode/ 链接（可带 ?s= 分享参数），并要求转文字/逐字稿/转录/校对稿时使用。覆盖五个步骤：xyz-dl 免登录下载音频、mlx_whisper 本地转写、按 shownotes 时间轴排版成带 YAML 属性的章节 md、去口语化重写并联网校对全部英文与专业术语、自动落盘至 Obsidian Reading Hub 知识库。
---

# 小宇宙播客逐字稿流水线（已接入 Obsidian Reading Hub）

输入一条小宇宙单集链接，产出一份去口语化、术语已校对、带章节时间轴与 Obsidian YAML 属性的 md 逐字稿，可在 Obsidian 阅读台（Reading Hub）沉浸式阅读与批注。

## 环境与工具

- 下载器：`~/.local/bin/xyz-dl`（uv tool 安装，仓库 shiquda/xyz-dl）。免登录链路抓公开网页 `__NEXT_DATA__` 提取音频直链。**绝不要使用 --login / --refresh-token**（作者警告有封号风险）。
- 转写：`~/.local/bin/mlx_whisper`（或 `mlx_whisper`），模型 `mlx-community/whisper-large-v3-turbo`（已支持 Apple Silicon MLX 硬件加速）。
- Python：`python3`
- 本地工作目录：默认 `~/.openclaw/data/xyz-dl-data/`（xyz-dl 会在 cwd 写 xyz-config.json，因此始终 cd 到该目录再运行）。
- 排版脚本：`~/.agents/skills/xiaoyuzhou-transcript/scripts/build_transcript_md.py`
- Obsidian 归档目录：`/Users/clawbot/AI/skywork/ai-workspace-hub/output/xiaoyuzhou/`
- Obsidian 阅读台入口：`[[reading-hub]]`（包含「🎙️ 小宇宙转录稿」专属折叠视图与「🎯 今日看什么」聚合）

**已知坑**：xyz-dl 启动时对 cwd 执行 `mkdir(exist_ok=True)`，若遇到 `PermissionError: EEXIST`，编辑 `~/.local/share/uv/tools/xyz-dl/lib/python3.13/site-packages/config.py` 第16行，把 `self.config_dir.mkdir(exist_ok=True)` 改为：
```python
if not self.config_dir.exists():
    self.config_dir.mkdir(parents=True, exist_ok=True)
```
重装/升级 xyz-dl 后需检查此补丁（本机已打好补丁）。

## 阶段 1：下载

```bash
mkdir -p ~/.openclaw/data/xyz-dl-data
cd ~/.openclaw/data/xyz-dl-data
xyz-dl "<episode_url>" -o ./download
```

- 链接带 `?s=...` 参数不影响，工具只取 episode ID。
- 产物：`download/<播客名>/<标题>.m4a` + `<标题>_metadata.json` + `<标题>_metadata.md`（metadata.md 含 shownotes、时间轴、术语表，后续排版和校对都依赖它）。
- 用 `afinfo <file>.m4a` 验证音频完整（有 duration 和 bit rate）。
- 若输出提示"数据来源: api"而非 "public-web"，说明网页解析失败回退到了登录接口，此时应停止并告知用户（免登录链路不可用）。

## 阶段 2：转写

```bash
cd ~/.openclaw/data/xyz-dl-data/"download/<播客名>"
mlx_whisper "<标题>.m4a" \
  --model mlx-community/whisper-large-v3-turbo --language zh \
  --output-format all --output-dir ./transcript --verbose False
```

长音频放后台跑。产出 txt/srt/vtt/json/tsv 五个格式到 `transcript/`。

## 阶段 3：章节排版与 Obsidian Frontmatter 注入

```bash
python3 ~/.agents/skills/xiaoyuzhou-transcript/scripts/build_transcript_md.py \
  --srt "transcript/<标题>.srt" --meta "<标题>_metadata.md" \
  --out "transcript/<标题>.md"
```

- 脚本自动从 `_metadata.json` / `_metadata.md` 提取标题、播客名、播出日期、时长、封面、链接、简介一句话等元数据，注入标准 Obsidian YAML Frontmatter：
  ```yaml
  ---
  title: "..."
  title_zh: "..."
  date: "YYYY-MM-DD"
  channel: "..."
  duration_min: 45
  url: "https://www.xiaoyuzhoufm.com/episode/..."
  cover: "..."
  tldr_zh: "..."
  read_status: "未读"
  transcript: true
  type: "xiaoyuzhou-transcript"
  tags:
    - 播客转录
    - 小宇宙
  ---
  ```
- 脚本自动从 metadata 的「时间轴」小节解析章节，约90秒一段、段首带 `[mm:ss]`。
- 脚本会自动将初步逐字稿同步一份到 `/Users/clawbot/AI/skywork/ai-workspace-hub/output/xiaoyuzhou/<date>-<标题>.md`。

## 阶段 4：去口语化 + 术语校对（核心增值步骤，不可跳过）

逐章阅读阶段3的 md，产出最终校对版并保存至 Obsidian：

1. **术语联网校对**：列出稿中所有英文名词、产品名、公司名、人名、模型名、数据指标，逐条用 WebSearch 核实正确写法和基本事实（发布日期、归属公司、产品定位）。Whisper 对英文专名错误率很高，典型模式：音近误写（Cloud Tag→Claude Tag、H16Z→a16z、Panenteer→Palantir）、型号错配（GPT6 Ultra→GPT-6 Astra）、中英混排丢失。**不可凭记忆猜测，必须搜索确认**；搜索也查无实据的，在校对记录中标注"未能核实"。
2. **去口语化重写**：删除语气词（呢/吧/对吧/就是/那么/然后），理顺倒装和碎句，保留全部信息点和段落级 `[mm:ss]` 时间戳。观点、数字、案例保持主播原意，不增删观点。
3. **结构**：头部保留 YAML Frontmatter（`read_status: "未读"`）→ 一级标题 → 简介（沿用 shownotes，术语表按校对结果修正扩充）→ 正文按章节 → 文末固定两个附录：
   - **术语校对记录表**：| 转写原文 | 校对后 | 说明 |
   - **数据勘误**：主播口述数字与公开报道不一致的，保留口述、标注实际数据和来源。
4. **保存到 Obsidian Reading Hub**：
   将最终成果保存为：
   `/Users/clawbot/AI/skywork/ai-workspace-hub/output/xiaoyuzhou/<date>-<标题>-校对版.md`

## 阶段 5：在 Obsidian Reading Hub 中阅读

文件落盘后，会自动出现在用户的 Obsidian `[[reading-hub]]`：
- **「🎙️ 小宇宙转录稿」**：以日期分组折叠卡片展示（含封面、标题、播客名、时长、原文链接、摘要）。
- **「🎯 今日看什么」**：近 3 天新入库待读汇总。
- **正文交互**：点击直接进入笔记，支持选词高亮划线、写批注想法、顶部状态切换（`未读` / `已读` / `精读` / `跳过`）以及一键 `✨ AI 总结`。

## 失败处理

- 下载失败/0.01MB 小文件：内容为付费或私有，免登录无法下载，直接告知用户。
- 转写质量差（大量乱码）：换 `--model mlx-community/whisper-large-v3` 重转。
- 单集为多人对谈时 Whisper 不区分说话人；用户要求分角色时，基于语义在校对版中标注说话人。
