#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从本机网络逐个探测播放列表里每个流地址的可达性，
剔除连不上的（超时/拒绝/重置），产出"本网可播"精简版。
（本机与 Apple TV 同处家庭网络，探测结果对 Apple TV 有代表性）
"""
import sys
import os
import urllib.request
import urllib.error
import concurrent.futures

HERE = os.path.dirname(os.path.abspath(__file__))
IN_FILE = os.path.join(HERE, "merged.m3u")
FULL_BACKUP = os.path.join(HERE, "merged_full.m3u")
OUT_FILE = os.path.join(HERE, "merged.m3u")

TIMEOUT = 5.0
WORKERS = 30


def parse(path):
    items = []  # (meta_line, url)
    meta = None
    with open(path, encoding="utf-8", errors="ignore") as f:
        for ln in f:
            ln = ln.rstrip("\n")
            if ln.startswith("#EXTINF"):
                meta = ln
            elif ln.strip() and not ln.startswith("#"):
                if meta is not None:
                    items.append((meta, ln.strip()))
                    meta = None
    return items


def probe(url):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Range": "bytes=0-1023",
                "Connection": "close",
            },
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            r.read(2048)
        return True
    except urllib.error.HTTPError as e:
        # 3xx 重定向、206 分片均视为可达；403/404/401 视为不可达
        return e.code in (200, 206, 301, 302, 303, 307, 308)
    except Exception:
        return False


def main():
    items = parse(IN_FILE)
    total = len(items)
    print(f"待探测频道: {total}")

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        fut = {ex.submit(probe, u): i for i, (_, u) in enumerate(items)}
        done = 0
        for f in concurrent.futures.as_completed(fut):
            done += 1
            if done % 40 == 0:
                print(f"  已探测 {done}/{total} ...")
            idx = fut[f]
            results[idx] = f.result()

    kept = [(m, u) for i, (m, u) in enumerate(items) if results.get(i)]
    dropped = total - len(kept)
    print(f"可达: {len(kept)} | 不可达(剔除): {dropped} | 总数: {total}")

    # 备份完整版
    import shutil
    shutil.copy(IN_FILE, FULL_BACKUP)
    print(f"完整版已备份: {os.path.basename(FULL_BACKUP)}")

    with open(OUT_FILE, "w", encoding="utf-8") as out:
        out.write('#EXTM3U\n')
        out.write(f'# filtered by iptv-merge 可达性探测 @ 本机网络 保留{len(kept)}/{total}\n')
        for m, u in kept:
            out.write(m + "\n")
            out.write(u + "\n")
    print(f"已写出精简版: {os.path.basename(OUT_FILE)} ({len(kept)} 台)")


if __name__ == "__main__":
    main()
