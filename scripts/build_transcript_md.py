#!/usr/bin/env python3
"""把 Whisper srt + xyz-dl 的 _metadata.md 合并成带章节结构的逐字稿 md。

用法:
    build_transcript_md.py --srt <episode.srt> --meta <episode_metadata.md> --out <out.md> [--para-gap 90]

章节自动从 _metadata.md 的「时间轴」小节解析（行格式: "* 00:49 章节名"）。
若 metadata 中没有时间轴，则整篇归入一个章节。
"""
import argparse
import re
import sys
from pathlib import Path


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


def parse_meta(path: Path):
    """返回 (title, intro_markdown, chapters[(sec, name)])"""
    text = path.read_text(encoding="utf-8")
    title_m = re.search(r"^#\s+(.+)$", text, re.M)
    title = title_m.group(1).strip() if title_m else path.stem

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
    return title, intro, chapters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--srt", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--para-gap", type=int, default=90, help="每段最长秒数，默认90")
    args = ap.parse_args()

    entries = parse_srt(Path(args.srt))
    if not entries:
        sys.exit("错误: srt 中没有解析到任何字幕条目")
    title, intro, chapters = parse_meta(Path(args.meta))

    out = [f"# {title}\n", "## 简介\n", intro, "\n---\n", "## 逐字稿\n"]
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

    Path(args.out).write_text("\n".join(out), encoding="utf-8")
    print(f"written: {args.out} ({Path(args.out).stat().st_size // 1024} KB, {len(entries)} 条字幕, {len(chapters)} 个章节)")


if __name__ == "__main__":
    main()
