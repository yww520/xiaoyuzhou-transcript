---
name: xiaoyuzhou-transcript
description: 小宇宙播客「单集链接 → 校对版逐字稿 md」全流程。当用户给出一个 xiaoyuzhoufm.com/episode/ 链接（可带 ?s= 分享参数），并要求转文字/逐字稿/转录/校对稿时使用。覆盖四个阶段：xyz-dl 免登录下载音频、mlx_whisper 本地转写、按 shownotes 时间轴排版成章节 md、去口语化重写并联网校对全部英文与专业术语。仅支持公开单集；整专辑、付费内容、登录态功能不在本 skill 范围。
---

# 小宇宙播客逐字稿流水线

输入一条小宇宙单集链接，产出一份去口语化、术语已校对、带章节时间轴的 md 逐字稿。

## 环境与工具

- 下载器：`~/.local/bin/xyz-dl`（uv tool 安装，仓库 shiquda/xyz-dl）。免登录链路抓公开网页 `__NEXT_DATA__` 提取音频直链。**绝不要使用 --login / --refresh-token**（作者警告有封号风险）。
- 转写：`/Users/dake/.workbuddy/binaries/python/envs/default/bin/mlx_whisper`，模型 `mlx-community/whisper-large-v3-turbo`（已缓存）。46分钟音频约4分钟转完。
- Python：`/Users/dake/.workbuddy/binaries/python/envs/default/bin/python`
- 工作目录：默认 `/Users/dake/Documents/WorkBuddy/小宇宙/xyz-dl-data/`（xyz-dl 会在 cwd 写 xyz-config.json，因此始终 cd 到该目录再运行）。

**已知坑**：xyz-dl 启动时对 cwd 执行 `mkdir(exist_ok=True)`，会被 WorkBuddy 沙箱 shim 拦截报 `PermissionError: EEXIST`。若遇到，编辑 `~/.local/share/uv/tools/xyz-dl/lib/python3.13/site-packages/config.py` 第16行，把 `self.config_dir.mkdir(exist_ok=True)` 改为：
```python
if not self.config_dir.exists():
    self.config_dir.mkdir(exist_ok=True)
```
重装/升级 xyz-dl 后需重打此补丁。

## 阶段 1：下载

```bash
cd /Users/dake/Documents/WorkBuddy/小宇宙/xyz-dl-data
~/.local/bin/xyz-dl "<episode_url>" -o ./download
```

- 链接带 `?s=...` 参数不影响，工具只取 episode ID。
- 产物：`download/<播客名>/<标题>.m4a` + `<标题>_metadata.json` + `<标题>_metadata.md`（metadata.md 含 shownotes、时间轴、术语表，后续排版和校对都依赖它）。
- 用 `afinfo <file>.m4a` 验证音频完整（有 duration 和 bit rate）。
- 若输出提示"数据来源: api"而非 "public-web"，说明网页解析失败回退到了登录接口，此时应停止并告知用户（免登录链路不可用）。

## 阶段 2：转写

```bash
cd "download/<播客名>"
/Users/dake/.workbuddy/binaries/python/envs/default/bin/mlx_whisper "<标题>.m4a" \
  --model mlx-community/whisper-large-v3-turbo --language zh \
  --output-format all --output-dir ./transcript --verbose False
```

长音频放后台跑。产出 txt/srt/vtt/json/tsv 五个格式到 `transcript/`。

## 阶段 3：章节排版

```bash
/Users/dake/.workbuddy/binaries/python/envs/default/bin/python \
  ~/.workbuddy/skills/xiaoyuzhou-transcript/scripts/build_transcript_md.py \
  --srt "transcript/<标题>.srt" --meta "<标题>_metadata.md" \
  --out "transcript/<标题>.md"
```

脚本自动从 metadata 的「时间轴」小节解析章节，约90秒一段、段首带 `[mm:ss]`。若无时间轴则整篇一章。若 shownotes 没有时间轴但用户要求章节，可听写内容自行划分。

## 阶段 4：去口语化 + 术语校对（核心增值步骤，不可跳过）

逐章阅读阶段3的 md，产出 `<标题>-校对版.md`：

1. **术语联网校对**：列出稿中所有英文名词、产品名、公司名、人名、模型名、数据指标，逐条用 WebSearch 核实正确写法和基本事实（发布日期、归属公司、产品定位）。Whisper 对英文专名错误率很高，典型模式：音近误写（Cloud Tag→Claude Tag、H16Z→a16z、Panenteer→Palantir）、型号错配（GPT6 Ultra→GPT-6 Astra）、中英混排丢失。**不可凭记忆猜测，必须搜索确认**；搜索也查无实据的，在校对记录中标注"未能核实"。
2. **去口语化重写**：删除语气词（呢/吧/对吧/就是/那么/然后），理顺倒装和碎句，保留全部信息点和段落级 `[mm:ss]` 时间戳。观点、数字、案例保持主播原意，不增删观点。
3. **结构**：头部加播客名/主播/时长说明 → 简介（沿用 shownotes，术语表按校对结果修正扩充）→ 正文按章节 → 文末固定两个附录：
   - **术语校对记录表**：| 转写原文 | 校对后 | 说明 |
   - **数据勘误**：主播口述数字与公开报道不一致的，保留口述、标注实际数据和来源。

完成后用 present_files 交付 `-校对版.md`（可同时附 srt 供对照音频）。

## 失败处理

- 下载失败/0.01MB 小文件：内容为付费或私有，免登录无法下载，直接告知用户。
- 转写质量差（大量乱码）：换 `--model mlx-community/whisper-large-v3` 重转。
- 单集为多人对谈时 Whisper 不区分说话人；用户要求分角色时，基于语义在校对版中标注说话人。
