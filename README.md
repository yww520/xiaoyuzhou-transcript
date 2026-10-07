# xiaoyuzhou-transcript

小宇宙播客「单集链接 → 校对版逐字稿」全自动 Skill。给 AI 助手一条小宇宙单集链接，自动完成 **下载 → 转写 → 章节排版 → 去口语化 + 术语联网校对**，产出一份带时间轴章节、术语已核实的 Markdown 逐字稿。

## 效果

输入：
```
转一下 https://www.xiaoyuzhoufm.com/episode/6ac49d68e742e36efcbedc0e
```

产出：
- `<标题>.md` —— 按 shownotes 时间轴分章节的逐字稿，约90秒一段，段首带 `[mm:ss]` 时间戳
- `<标题>-校对版.md` —— 去口语化重写版，所有英文/专业术语联网校对，文末附**术语校对记录表**和**口述数据勘误**
- 中间产物：原始 m4a 音频、shownotes metadata（json/md）、srt/vtt/json/tsv 转写文件

## 工作流程

| 阶段 | 工具 | 说明 |
| --- | --- | --- |
| 1. 下载 | [xyz-dl](https://github.com/shiquda/xyz-dl) | 免登录抓取公开网页 `__NEXT_DATA__` 提取音频直链，不使用任何账号凭据 |
| 2. 转写 | [mlx-whisper](https://github.com/ml-explore/mlx-examples)（large-v3-turbo） | Apple Silicon 本地加速，46分钟音频约4分钟转完 |
| 3. 排版 | `scripts/build_transcript_md.py` | 自动从 shownotes 时间轴解析章节，合并成带时间戳的章节 md |
| 4. 校对 | AI 助手 + 联网搜索 | 去口语化重写；术语逐条联网核实（修正 Whisper 对英文专名的误识别，如 Cloud Tag→Claude Tag、H16Z→a16z）；口述数据与公开报道不符的单独勘误 |

## 安装

### 前置依赖

```bash
# 1. 下载器（需要 Python 3.13+ 和 uv）
uv tool install --from "git+https://github.com/shiquda/xyz-dl.git" xyz-dl

# 2. 转写引擎（Apple Silicon Mac 推荐）
pip install mlx-whisper
```

### 安装 Skill

将本仓库的 `SKILL.md` 和 `scripts/` 复制到你的 AI 助手 skills 目录（以 WorkBuddy / Claude Code 为例）：

```bash
git clone https://github.com/dake2482/xiaoyuzhou-transcript.git
mkdir -p ~/.workbuddy/skills
cp -r xiaoyuzhou-transcript ~/.workbuddy/skills/
```

## 使用

安装后直接给 AI 助手发一条小宇宙单集链接即可，例如：

> 把这期播客转成校对版逐字稿：https://www.xiaoyuzhoufm.com/episode/xxxx

AI 会按 SKILL.md 中的四阶段流程自动执行。

## 边界与限制

- **仅支持公开单集**的免登录下载；整专辑批量、付费/私有内容、字幕接口不在范围内
- xyz-dl 的登录态功能（refresh_token）**有账号风控风险**，本 Skill 明确不使用
- Whisper 不区分说话人；多人对谈分角色需要在校对阶段按语义标注
- 转写与校对质量依赖模型能力，重要引用建议对照 srt 时间戳回听原文

## 合规声明

本 Skill 仅供个人离线学习使用。下载的音频与逐字稿版权归原作者所有，请勿公开传播或用于商业目的，使用时请遵守小宇宙平台条款。

## License

AGPL-3.0（跟随上游 xyz-dl 的许可证）
