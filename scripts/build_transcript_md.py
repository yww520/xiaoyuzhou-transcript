#!/usr/bin/env python3
"""把 Whisper srt + xyz-dl 的 _metadata.md / _metadata.json 合并成带章节结构且适配 Obsidian Reading Hub 的逐字稿 md。

用法:
    build_transcript_md.py --srt <episode.srt> --meta <episode_metadata.md> --out <out.md> [--para-gap 90] [--obsidian-dir <dir>]

章节自动从 _metadata.md 的「时间轴」小节解析（行格式: "* 00:49 章节名" 或 "- 00:49 章节名"）。
若 metadata 中没有时间轴，则整篇归入一个章节。
同时自动提取元数据写入 Obsidian YAML frontmatter，并同步落盘至 Obsidian reading-hub 知识库。
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

DEFAULT_OBSIDIAN_DIR = Path("/Users/clawbot/AI/skywork/ai-workspace-hub/output/xiaoyuzhou")


def ts2sec(t: str) -> float:
    """支持 mm:ss 和 hh:mm:ss,mmm 两种格式"""
    t = t.replace(",", ".")
    parts = t.split(":")
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    h, m, s = parts
    return int(h) * 3600 + int(m) * 60 + float(s)


def fmt(sec: float) -> str:
    sec = int(sec)
    if sec >= 3600:
        return f"{sec // 3600}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"
    return f"{sec // 60:02d}:{sec % 60:02d}"


def parse_srt(path: Path):
    entries = []
    for block in path.read_text(encoding="utf-8").strip().split("\n\n"):
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue
        # 时间轴行可能在第1或第2行（vtt无序号行）
        m = None
        for line in lines[:2]:
            m = re.search(r"(\d{1,2}:\d{2}:\d{2}[,.]\d+)\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d+)", line)
            if m:
                break
        if not m:
            continue
        text_lines = lines[2:] if lines[0].strip().isdigit() else lines[1:]
        text = "".join(text_lines).strip()
        if text:
            entries.append((ts2sec(m.group(1)), ts2sec(m.group(2)), text))
    return entries


def clean_str(val: str) -> str:
    if not val:
        return ""
    return str(val).replace('"', '\\"').strip()


def parse_meta(path: Path):
    """返回 (title, intro_markdown, chapters[(sec, name)], meta_dict)"""
    text = path.read_text(encoding="utf-8")
    title_m = re.search(r"^#\s+(.+)$", text, re.M)
    title = title_m.group(1).strip() if title_m else path.stem.replace("_metadata", "")

    # 尝试读取同名或邻近的 json 元数据
    meta_json_path = path.with_suffix(".json")
    if not meta_json_path.exists():
        # 尝试查找同目录下的 *_metadata.json
        candidate = list(path.parent.glob("*_metadata.json"))
        if candidate:
            meta_json_path = candidate[0]

    json_info = {}
    if meta_json_path.exists():
        try:
            json_info = json.loads(meta_json_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 从 json 或 md 提取结构化信息
    channel = (
        json_info.get("author")
        or (json_info.get("podcast", {}).get("title") if isinstance(json_info.get("podcast"), dict) else None)
        or ""
    )
    if not channel:
        chan_m = re.search(r"\|\s*作者/播客\s*\|\s*([^|\n]+)\s*\|", text)
        if chan_m:
            channel = chan_m.group(1).strip()

    pub_date_raw = json_info.get("pub_date") or json_info.get("pubDate") or ""
    if not pub_date_raw:
        date_m = re.search(r"\|\s*发布日期\s*\|\s*([^|\n]+)\s*\|", text)
        if date_m:
            pub_date_raw = date_m.group(1).strip()

    date_str = ""
    if pub_date_raw:
        # 尝试截取 YYYY-MM-DD
        dm = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2})", pub_date_raw)
        if dm:
            date_str = dm.group(1).replace("/", "-")
    if not date_str:
        date_str = datetime.date.today().strftime("%Y-%m-%d")

    duration_sec = json_info.get("duration")
    duration_min = 0
    if duration_sec:
        duration_min = int(duration_sec) // 60
    else:
        dur_m = re.search(r"\|\s*时长\s*\|\s*(\d+)\s*分钟", text)
        if dur_m:
            duration_min = int(dur_m.group(1))

    eid = json_info.get("eid") or ""
    if not eid:
        eid_m = re.search(r"\|\s*ID\s*\|\s*([^|\n]+)\s*\|", text)
        if eid_m:
            eid = eid_m.group(1).strip()
    url = f"https://www.xiaoyuzhoufm.com/episode/{eid}" if eid else json_info.get("url", "")

    cover = ""
    img_val = (
        json_info.get("image")
        or json_info.get("cover")
        or (json_info.get("podcast", {}).get("image") if isinstance(json_info.get("podcast"), dict) else None)
    )
    if isinstance(img_val, dict):
        cover = img_val.get("picUrl") or img_val.get("largePicUrl") or img_val.get("thumbnailUrl") or ""
    elif isinstance(img_val, str):
        cover = img_val
    desc = json_info.get("description") or json_info.get("brief") or ""
    if not desc:
        desc_m = re.search(r"## 简介\s*\n+([\s\S]+?)(?=\n##|\Z)", text)
        if desc_m:
            desc = desc_m.group(1).strip()

    # 提取一句话摘要 (tldr)
    tldr = ""
    for line in desc.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("|") and not line.startswith("*"):
            tldr = line[:120]
            break

    # 简介：去掉首个 # 标题后的全部内容
    intro = text[title_m.end():].strip() if title_m else text.strip()

    # 时间轴小节：找「时间轴」标题下 "* mm:ss 名称" 或 "- mm:ss 名称" 行
    chapters = []
    tl_m = re.search(r"时间轴[^\n]*\n((?:[*\-]\s+.+\n?)+)", text)
    if tl_m:
        for line in tl_m.group(1).splitlines():
            m = re.match(r"[*\-]\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*(.*)", line.strip())
            if m:
                chapters.append((ts2sec(m.group(1)), m.group(2).strip()))
    chapters.sort(key=lambda c: c[0])
    if not chapters or chapters[0][0] > 0:
        chapters.insert(0, (0, "开场"))

    meta_dict = {
        "title": title,
        "title_zh": title,
        "date": date_str,
        "channel": channel,
        "duration_min": duration_min,
        "url": url,
        "cover": cover,
        "tldr_zh": tldr,
        "read_status": "未读",
        "transcript": True,
        "type": "xiaoyuzhou-transcript",
        "tags": ["播客转录", "小宇宙"],
    }
    return title, intro, chapters, meta_dict


def build_frontmatter(meta: dict) -> str:
    lines = ["---"]
    lines.append(f'title: "{clean_str(meta.get("title", ""))}"')
    lines.append(f'title_zh: "{clean_str(meta.get("title_zh", ""))}"')
    lines.append(f'date: "{meta.get("date", "")}"')
    if meta.get("channel"):
        lines.append(f'channel: "{clean_str(meta.get("channel", ""))}"')
    if meta.get("guest"):
        lines.append(f'guest: "{clean_str(meta.get("guest", ""))}"')
    if meta.get("duration_min"):
        lines.append(f'duration_min: {meta.get("duration_min")}')
    if meta.get("url"):
        lines.append(f'url: "{meta.get("url")}"')
    if meta.get("cover"):
        lines.append(f'cover: "{meta.get("cover")}"')
    if meta.get("tldr_zh"):
        lines.append(f'tldr_zh: "{clean_str(meta.get("tldr_zh", ""))}"')
    lines.append(f'read_status: "{meta.get("read_status", "未读")}"')
    lines.append('transcript: true')
    lines.append('type: "xiaoyuzhou-transcript"')
    lines.append("tags:")
    lines.append("  - 播客转录")
    lines.append("  - 小宇宙")
    lines.append("---\n")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="生成适配 Obsidian Reading Hub 的小宇宙逐字稿")
    ap.add_argument("--srt", required=True, help="Whisper 输出的 SRT 字幕文件")
    ap.add_argument("--meta", required=True, help="xyz-dl 生成的 _metadata.md 文件")
    ap.add_argument("--out", required=True, help="输出逐字稿 Markdown 路径")
    ap.add_argument("--para-gap", type=int, default=90, help="每段最长秒数，默认90")
    ap.add_argument(
        "--obsidian-dir",
        default=str(DEFAULT_OBSIDIAN_DIR),
        help=f"Obsidian 归档目录，默认: {DEFAULT_OBSIDIAN_DIR}",
    )
    ap.add_argument("--no-obsidian", action="store_true", help="不自动复制到 Obsidian 目录")
    args = ap.parse_args()

    entries = parse_srt(Path(args.srt))
    if not entries:
        sys.exit("错误: srt 中没有解析到任何字幕条目")
    title, intro, chapters, meta_dict = parse_meta(Path(args.meta))

    fm = build_frontmatter(meta_dict)
    out = [fm, f"# {title}\n", "## 简介\n", intro, "\n---\n", "## 逐字稿\n"]
    for i, (start, name) in enumerate(chapters):
        end = chapters[i + 1][0] if i + 1 < len(chapters) else float("inf")
        out.append(f"\n### {fmt(start)} {name}\n")
        buf, buf_start = [], None
        for s, e, text in entries:
            if not (start <= s < end):
                continue
            if buf_start is None:
                buf_start = s
            buf.append(text)
            if e - buf_start >= args.para_gap:
                out.append(f"**[{fmt(buf_start)}]** {''.join(buf)}\n")
                buf, buf_start = [], None
        if buf:
            out.append(f"**[{fmt(buf_start)}]** {''.join(buf)}\n")

    content = "\n".join(out)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"✅ 生成逐字稿: {out_path} ({out_path.stat().st_size // 1024} KB, {len(entries)} 条字幕, {len(chapters)} 个章节)")

    if not args.no_obsidian and args.obsidian_dir:
        obs_dir = Path(args.obsidian_dir)
        if obs_dir.exists():
            safe_title = re.sub(r'[\\/*?:"<>|]', "-", title).strip()
            date_prefix = meta_dict.get("date", datetime.date.today().strftime("%Y-%m-%d"))
            obs_file = obs_dir / f"{date_prefix}-{safe_title}.md"
            obs_file.write_text(content, encoding="utf-8")
            print(f"🏠 已同步至 Obsidian Reading Hub: {obs_file}")


if __name__ == "__main__":
    main()
