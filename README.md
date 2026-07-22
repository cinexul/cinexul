<!--
	·		 ·	 |	·	 ·		|		·	 ·
	 ·	 |		·		·	|	 ·		|	·
		你好,看源码的人。
		这一页没有用任何现成组件:每张图都是手写的动画 SVG,
		由 profile/render.py 从 profile/live.json 冲洗出来,
		GitHub Actions 每 6 小时自动显影一次。
		拆解见 docs/技术手册.md。
	·		|	 ·		·	 |	·		 |		·
		 ·		·	 |		·		·	 |	 ·	·
-->

<div align="center">

<a href="https://cinexul.com"><img src="assets/hero.svg" width="100%" alt="cinexul — 暗室里还亮着一台机器。雨夜车窗:雨丝落下,水珠在玻璃上黏住又滑落,远处是路灯的琥珀和末班车的尾灯红。"/></a>

<a href="https://cinexul.com"><picture><source media="(prefers-color-scheme: light)" srcset="assets/nav-site-light.svg"><img src="assets/nav-site.svg" alt="主站 SITE" height="40"/></picture></a><a href="https://cinexul.com/photography"><picture><source media="(prefers-color-scheme: light)" srcset="assets/nav-photo-light.svg"><img src="assets/nav-photo.svg" alt="摄影 PHOTO" height="40"/></picture></a><a href="https://cinexul.com/essays"><picture><source media="(prefers-color-scheme: light)" srcset="assets/nav-essays-light.svg"><img src="assets/nav-essays.svg" alt="随笔 ESSAYS" height="40"/></picture></a><a href="https://cinexul.com/news"><picture><source media="(prefers-color-scheme: light)" srcset="assets/nav-news-light.svg"><img src="assets/nav-news.svg" alt="快讯 NEWS" height="40"/></picture></a><a href="https://cinexul.com/feed.xml"><picture><source media="(prefers-color-scheme: light)" srcset="assets/nav-feed-light.svg"><img src="assets/nav-feed.svg" alt="订阅 RSS" height="40"/></picture></a><a href="docs/技术手册.md"><picture><source media="(prefers-color-scheme: light)" srcset="assets/nav-how-light.svg"><img src="assets/nav-how.svg" alt="拆解 HOW" height="40"/></picture></a>

<picture><source media="(prefers-color-scheme: light)" srcset="assets/h1-light.svg"><img src="assets/h1.svg" width="100%" alt="01 · 以光为弦 — LANGUAGES AS STRINGS"/></picture>

<img src="assets/strings.svg" width="100%" alt="语言占比被画成几根发光的弦:Svelte 是尾灯红,TypeScript 是雾蓝,Rust 是路灯琥珀。每根弦轮流被拨一次,一段亮光沿弦身扫过。数据每 6 小时由 Actions 重新调音。"/>

<picture><source media="(prefers-color-scheme: light)" srcset="assets/h2-light.svg"><img src="assets/h2.svg" width="100%" alt="02 · 走马灯 — THE REVOLVING REEL"/></picture>

<img src="assets/reel.svg" width="100%" alt="一条带齿孔的胶片在灯前缓缓经过,每一格是 cinexul.com 最近的一个信号。"/>

<picture><source media="(prefers-color-scheme: light)" srcset="assets/h3-light.svg"><img src="assets/h3.svg" width="100%" alt="03 · 还亮着的机器 — THE MACHINE STILL ON"/></picture>

<img src="assets/terminal.svg" width="100%" alt="一台磷光 CRT 终端开着:whoami 打出 哭泣de御姐控,uptime 报出暗房天数,tail -f 滚动着来自 cinexul.com 的信号日志,光标还在闪。"/>

<img src="assets/tunnel.svg" width="100%" alt="显影隧道:一圈圈带红蓝色散的门框向灭点推进,隧道尽头,显影未完。"/>

<sub>雨夜 · 车窗 · 暗室 —— 本页由手写 SVG 构成,零框架零依赖,<a href="docs/技术手册.md">拆解在此</a>。</sub>

</div>

<details>
<summary>&nbsp;⚙︎ 这一页是怎么做出来的(点开)</summary>
<br>

GitHub 的 README 会剥掉一切 CSS / JS,但 `<img>` 里的 SVG 是一份独立文档——
内部的 CSS 动画、滤镜、渐变、蒙版全部生效。于是:

- **整页 = 若干张手写动画 SVG**,由 [`profile/render.py`](profile/render.py) 从数据渲染而来,伪随机数定种子,渲染结果字节级可复现;
- **雨、水珠、散景、打字、拨弦、胶片传送、CRT 打字、隧道推进**全部是 SVG 内部的 CSS 动画(为兼容性刻意不用 SMIL);胶片颗粒是渲染器手工编码的 PNG 噪点贴图;
- **数据是活的**:[`profile/fetch.py`](profile/fetch.py) 在 [GitHub Actions](.github/workflows/develop.yml) 里每 6 小时抓一次公开数据(语言字节、star、近期 push、博客 RSS),重渲染并自动提交——提交历史就是显影批号;
- **明暗主题**:分节标题与导航按钮用 `<picture>` + `prefers-color-scheme` 切换深浅两版;
- **尊重访客**:所有 SVG 内置 `prefers-reduced-motion` 守卫,系统开了减弱动态就静止。

完整拆解(以及"README 到底能玩到多复杂"的答案):[docs/技术手册.md](docs/技术手册.md)

</details>
