# xiaoyuzhou-transcript

小宇宙播客「单集链接 → 校对版逐字稿 → Obsidian Reading Hub 沉浸式阅读」全流程 Skill。

给 AI 助手一条小宇宙单集链接，自动完成 **免登录下载 → Apple Silicon 本地转写 → 章节排版并注入 Obsidian YAML 属性 → 去口语化 + 术语联网校对 → 自动落盘至 Obsidian Reading Hub 知识库**。

## 效果

输入：
```
转一下 https://www.xiaoyuzhoufm.com/episode/6ac49d68e742e36efcbedc0e
```

产出：
- `<标题>.md` —— 按 shownotes 时间轴分章节的逐字稿，约90秒一段，段首带 `[mm:ss]` 时间戳
- `<标题>-校对版.md` —— 去口语化重写版，所有英文/专业术语联网校对，文末附**术语校对记录表**和**口述数据勘误**
- **Obsidian Reading Hub 自动入库**：自动同步至 `ai-workspace-hub/output/xiaoyuzhou/<date>-<标题>-校对版.md`，并在 Obsidian 阅读台首页以折叠卡片展示，支持划线、批注与 AI 总结
- 中间产物：原始 m4a 音频、shownotes metadata（json/md）、srt/vtt/json/tsv 转写文件

## 工作流程

| 阶段 | 工具 | 说明 |
| --- | --- | --- |
| 1. 下载 | [xyz-dl](https://github.com/shiquda/xyz-dl) | 免登录抓取公开网页 `__NEXT_DATA__` 提取音频直链，不使用任何账号凭据，零风控风险 |
| 2. 转写 | [mlx-whisper](https://github.com/ml-explore/mlx-examples)（large-v3-turbo） | Apple Silicon 本地硬件加速，15分钟音频约2分钟，46分钟音频约4分钟转完 |
| 3. 排版 | `scripts/build_transcript_md.py` | 自动从 metadata 解析播出日期、时长、封面、单集链接并注入 Obsidian YAML Frontmatter，按时间轴切分段落 |
| 4. 校对 | AI 助手 + 联网搜索 | 去口语化重写；术语逐条联网核实（修正 Whisper 对英文专名与技术词的误识别，如 CUDA、DeepSeek、Claude Code 等）；口述数据与公开报道不符的单独勘误 |
| 5. 沉浸阅读 | [Obsidian Reading Hub](https://obsidian.md) | 自动落盘至 Obsidian「🎙️ 小宇宙转录稿」模块，支持选词高亮、想法批注、阅读状态流转及 AI 深度总结 |

## 安装

### 前置依赖

```bash
# 1. 下载器（推荐使用 uv tool 安装）
uv tool install --from "git+https://github.com/shiquda/xyz-dl.git" xyz-dl

# 2. 转写引擎（Apple Silicon Mac 推荐）
uv tool install mlx-whisper
# 若使用 SOCKS 代理，补齐代理库：
uv pip install --python ~/.local/share/uv/tools/mlx-whisper/bin/python socksio

# 3. 底层多媒体依赖
brew install ffmpeg
```

### 安装 Skill

将本仓库克隆至你的 Agent Skills 目录：

```bash
git clone https://github.com/yww520/xiaoyuzhou-transcript.git ~/.agents/skills/xiaoyuzhou-transcript
```

## 使用

在对话中直接发送小宇宙单集链接即可：

> 把这期小宇宙转成逐字稿：https://www.xiaoyuzhoufm.com/episode/xxxx

AI 将自动完成下载、转写、校对，并同步落盘至 Obsidian Reading Hub。

## 边界与限制

- **仅支持公开单集**的免登录下载；整专辑批量、付费/私有内容不在范围内
- 小宇宙 App 端的字幕接口需携带登录凭据且有极高账号封禁风险，本 Skill 采用**免登录音频下载 + 本地 ASR 高精转写**，安全合规
- Whisper 默认不区分说话人；多人对谈分角色可在校对阶段基于语义进行标注
- 转写与校对质量依赖模型能力，重要引用建议对照 srt 时间戳回听原文

## 合规声明

本 Skill 仅供个人离线学习使用。下载的音频与逐字稿版权归原作者所有，请勿公开传播或用于商业目的，使用时请遵守小宇宙平台条款。

## License

AGPL-3.0（跟随上游 xyz-dl 的许可证）
