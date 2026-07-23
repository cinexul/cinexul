<!--
	·		 ·	 |	·	 ·		|		·	 ·
	 ·	 |		·		·	|	 ·		|	·
		你好,看源码的人。
		这一页没有用任何现成组件:每张图都是手写的动画 SVG,
		3D 展品是手写 WebGL 逐帧录制的动画 WebP,
		由 profile/ 下的渲染器冲洗而来,Actions 每 6 小时自动显影。
		拆解见 docs/技术手册.md。
	·		|	 ·		·	 |	·		 |		·
		 ·		·	 |		·		·	 |	 ·	·
-->

<div align="center">

<img src="assets/hero.svg" width="100%" alt="cinexul — 换了一把刻刀的手艺人。雨夜车窗:雨丝斜落,凝在玻璃上的水珠映着街灯,黏住又滑落;远处是路灯的琥珀和末班车的尾灯红。"/>

<picture><source media="(prefers-color-scheme: light)" srcset="assets/h1-light.svg"><img src="assets/h1.svg" width="100%" alt="01 · 展品 — EXHIBIT №001"/></picture>

<img src="assets/exhibit.webp" width="100%" alt="展品 №001 · 纸鹤:一只米白的折纸鹤停在夜水上方,在风里轻轻摇摆、扇翅,纸面透着背光;水面拖着街灯的琥珀倒影,雨点偶尔漾开涟漪,鹤的倒影随水纹微晃。手写 WebGL 渲染,十秒完美循环。"/>

<img src="assets/plaque.svg" width="100%" alt="展签 — 材质:一张方纸(程序折叠);工艺:折纸,不裁不剪,不用一滴胶;场景:夜水之上,街灯倒影,雨点涟漪。『纸很轻,折过之后,就敢站在风里了。』"/>

<picture><source media="(prefers-color-scheme: light)" srcset="assets/h2-light.svg"><img src="assets/h2.svg" width="100%" alt="02 · 以光为弦 — LANGUAGES AS STRINGS"/></picture>

<img src="assets/strings.svg" width="100%" alt="语言占比被画成几根发光的弦:Svelte 是尾灯红,TypeScript 是雾蓝,Rust 是路灯琥珀。每根弦轮流被拨一次,一段亮光沿弦身扫过。数据每 6 小时由 Actions 重新调音。"/>

<picture><source media="(prefers-color-scheme: light)" srcset="assets/h3-light.svg"><img src="assets/h3.svg" width="100%" alt="03 · 还亮着的机器 — THE MACHINE STILL ON"/></picture>

<img src="assets/terminal.svg" width="100%" alt="一台磷光 CRT 终端开着:whoami 打出 工艺美术师→程序员,uptime 报着工作台边的夜数,tail -f 滚动着 craft.log 里的手艺心得,光标还在闪。"/>

<img src="assets/tunnel.svg" width="100%" alt="显影隧道:一圈圈带红蓝色散的门框向灭点推进,隧道尽头,显影未完。"/>

<sub><a href="https://cinexul.com">cinexul.com</a>&nbsp;·&nbsp;<a href="https://cinexul.com/feed.xml">rss</a>&nbsp;·&nbsp;<a href="docs/技术手册.md">这一页的拆解</a></sub>

</div>

<details>
<summary>&nbsp;⚙︎ 这一页是怎么做出来的(点开)</summary>
<br>

GitHub 的 README 会剥掉一切 CSS / JS,但 `<img>` 里的 SVG 是一份独立文档——
内部的 CSS 动画、滤镜、渐变、蒙版全部生效。于是:

- **雨夜车窗、弦、终端、隧道**都是手写的动画 SVG,由 [`profile/render.py`](profile/render.py) 从数据渲染,伪随机定种子、字节级可复现;水珠按"透镜"画:暗芯、薄亮边、底部映街灯,蠕动式滑落并留下湿痕;
- **纸鹤**是手写 WebGL([`profile/exhibit/scene.html`](profile/exhibit/scene.html),无引擎):折痕即三角面、纸面两面受光并微微透光,夜水、街灯倒影、涟漪与倒影晃动都在着色器里;无头浏览器逐帧录制 200 帧,Pillow 合成 10 秒完美循环的动画 WebP;
- **数据是活的**:[`profile/fetch.py`](profile/fetch.py) 在 [Actions](.github/workflows/develop.yml) 里每 6 小时抓一次公开数据(语言字节、star、近期 push),重渲染并自动提交——提交历史就是显影批号;
- 分节标题用 `<picture>` + `prefers-color-scheme` 跟随明暗主题;所有 SVG 内置 `prefers-reduced-motion` 守卫。

完整拆解(以及"README 到底能玩到多复杂"的答案):[docs/技术手册.md](docs/技术手册.md)

</details>
