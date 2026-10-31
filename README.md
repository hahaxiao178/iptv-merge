# iptv-merge —— 自动合并去重的 IPTV 直播源

把多个公开 m3u 直播源合并、去重，生成一个统一播放列表 `merged.m3u`，
用 GitHub Actions 每天自动更新，产出一条常年稳定的订阅链接，填进 APTV 等播放器即可。

## 文件
- `sources.txt` —— 直播源清单（每行一个 m3u 地址，# 开头为注释）
- `merge.py`    —— 合并去重脚本（纯标准库，无依赖）
- `.github/workflows/update.yml` —— 每日定时合并并推回仓库
- `merged.m3u`  —— 合并产物（由脚本/ Actions 生成，不要手改）

## 去重规则
1. 按流地址(URL)去重；
2. 再按频道名(name)去重；
3. 同名/同地址只保留 `sources.txt` 中**先出现**的源（所以主源排最前）。

## 本地调试（macOS 重要）
系统 `/usr/bin/python3` 无外网权限，**本机联网运行请用 QClaw 真实 Python**：
```bash
/Users/wufuhua/Library/Application\ Support/QClaw/python/bin/python3.11 merge.py
```
运行后看统计输出，生成的 `merged.m3u` 可直接用 VLC 打开自测。

## 上线到 GitHub（得到稳定订阅链接）
1. 在 github.com 新建一个**空**仓库（如 `iptv-merge`，公开/私有均可；私有则 APTV
   需能访问 raw —— 私有仓库 raw 需 token，建议公开）。
2. 在本目录初始化并提交（已帮你 git init + 首次 commit，见下方）：
   ```bash
   cd /Users/wufuhua/.qclaw/workspace/iptv-merge
   git remote add origin https://github.com/<你的用户名>/iptv-merge.git
   git branch -M main
   git push -u origin main
   ```
3. 进入仓库 **Settings → Actions → General → Workflow permissions**，
   设为 **Read and write permissions**（脚本里已写 `permissions: contents: write`，
   此处需对应开启）。
4. 触发一次：Actions 标签页点 `Update IPTV Playlist` → Run workflow。
   之后每天 UTC 16:00（≈北京 0:00）自动跑。

## 稳定订阅链接（填进 APTV）
```
https://raw.githubusercontent.com/<你的用户名>/iptv-merge/main/merged.m3u
```
APTV：添加播放列表 → URL/远程 → 粘贴上面链接 → 保存。
之后每次打开 APTV 自动拉最新版（上游每日更新，失效源会被自动清掉）。

## 维护：加/换源
编辑 `sources.txt`，加一行 m3u 地址即可（主源放最前）。
需要立即生效就手动 Run workflow，否则等次日自动更新。

## 备注
- 公开 IPTV 源稳定性参差，热门赛事/晚会高峰易失效，可多挂几个源互补。
- 合规提示：公开源版权状态不一，请个人自用、合规使用。
