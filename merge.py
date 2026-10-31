#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并多个公开 IPTV (m3u) 源，去重后生成统一播放列表 merged.m3u。

特性：
  - 仅用 Python 标准库（urllib），无需 pip 安装任何依赖。
  - 去重：先按流地址(URL)去重，再按频道名(name)去重；保留 sources.txt 中
    先出现的源（前面的源优先级更高）。
  - 排序：按 group-title 再按频道名，方便播放器分组浏览。
  - 健壮性：单个源拉取失败不影响整体，跳过并告警。

本机 macOS 运行说明（重要）：
  系统自带的 /usr/bin/python3 没有外网权限（连 baidu 都超时）。
  在本机联网运行本脚本，请使用 QClaw 真实 Python 二进制，例如：
    /Users/wufuhua/Library/Application\ Support/QClaw/python/bin/python3.11 merge.py
  在 GitHub Actions 上用官方 python:3.11 镜像运行，无需关心此问题。
"""
import urllib.request
import urllib.error
import re
import sys
import os
import time
from datetime import datetime

UA = "Mozilla/5.0 (compatible; iptv-merge/1.0)"


def fetch(url, timeout=25):
    """下载并解码 m3u 文本，兼容 utf-8 / gbk（部分国内源为 gbk）。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def norm_url(u):
    """归一化流地址：scheme/host 转小写，去末尾斜杠，用于去重。"""
    u = u.strip()
    m = re.match(r"^(https?|rtsp|rtmp)://([^/]+)(.*)$", u, re.I)
    if m:
        scheme, host, rest = m.groups()
        u = f"{scheme.lower()}://{host.lower()}{rest}"
    return u.rstrip("/")


def extinf_name(meta_lines):
    for ln in meta_lines:
        if ln.startswith("#EXTINF"):
            m = re.search(r'tvg-name="([^"]*)"', ln)
            if m and m.group(1).strip():
                return m.group(1).strip()
            if "," in ln:
                return ln.split(",", 1)[1].strip()
    return ""


def extinf_group(meta_lines):
    for ln in meta_lines:
        if ln.startswith("#EXTINF"):
            m = re.search(r'group-title="([^"]*)"', ln)
            if m:
                return m.group(1).strip()
    return "未分组"


def parse_m3u(text):
    """解析 m3u，返回 [(meta_block_lines, url), ...]，保持出现顺序。
    meta_block 包含 #EXTINF 及其后连续的 # 指令（如 #EXTGRP）。"""
    items = []
    meta = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if line.startswith("#EXTINF"):
                meta = [line]
            else:
                meta.append(line)
        else:
            if meta:
                items.append((list(meta), line))
                meta = []
            # 孤立 URL（无对应 EXTINF）忽略
    return items


def fetch_retry(url, tries=3, wait=2):
    """带重试的下载：国内源偶发超时，重试可大幅提升成功率。"""
    last = None
    for i in range(tries):
        try:
            return fetch(url)
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(wait)
    raise last


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src_file = os.path.join(here, "sources.txt")
    out_file = os.path.join(here, "merged.m3u")

    sources = []
    with open(src_file, encoding="utf-8") as f:
        for ln in f:
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            sources.append(s)

    seen_url = set()
    seen_name = set()
    merged = []          # (group, name, meta_lines, url)
    stats = []

    for line in sources:
        # 一行支持多个备用地址，用 | 分隔，依次尝试直到成功
        candidates = [u.strip() for u in line.split("|") if u.strip()]
        done = False
        for url in candidates:
            try:
                text = fetch_retry(url)
            except Exception as e:
                print(f"[WARN] 拉取失败，尝试下一个备用: {url}\n        {e}", file=sys.stderr)
                continue
            items = parse_m3u(text)
            kept = dup_url = dup_name = 0
            for meta, stream in items:
                nu = norm_url(stream)
                name = extinf_name(meta) or nu
                grp = extinf_group(meta)
                if nu in seen_url:
                    dup_url += 1
                    continue
                if name in seen_name:
                    dup_name += 1
                    seen_url.add(nu)
                    continue
                seen_url.add(nu)
                seen_name.add(name)
                merged.append((grp, name, meta, stream))
                kept += 1
            stats.append((url, f"kept={kept} dup_url={dup_url} dup_name={dup_name}"))
            done = True
            break
        if not done:
            stats.append((line, "ALL_FAIL"))

    merged.sort(key=lambda x: (x[0], x[1]))

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# merged by iptv-merge @ {datetime.now():%Y-%m-%d %H:%M}\n")
        for grp, name, meta, stream in merged:
            for ml in meta:
                f.write(ml + "\n")
            f.write(stream + "\n")

    print("=" * 56)
    for url, info in stats:
        print(f"源: {url}\n    {info}")
    print("-" * 56)
    print(f"最终频道数 : {len(merged)}")
    print(f"输出文件   : {out_file}")
    print("=" * 56)


if __name__ == "__main__":
    main()
