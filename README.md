# BlueWhaleLife（大肥鱼的B站生活）

> 一个具备独立人格、真实内容探索、长期记忆沉淀与分级视频理解能力的 Windows 开源 AI 鲸鱼娘桌宠养成程序。

![大肥鱼鲸鱼娘立绘](desktop_pet/assets/whale/idle-cute.webp)

---

## ✨ 核心特性

### 1. 真实二次元鲸鱼娘桌宠（Whale Musume）
- **高品质立绘**：彻底告别简陋几何拼图，采用社区喜爱的 DeepSeek 蓝紫渐变发色、女仆头饰裙装、鲸鱼围裙、鲸鳍发饰与灵动鲸尾。
- **60 FPS 流畅动画**：
  - 自然呼吸微浮动、智能眨眼、尾巴悠悠摆动
  - 左右行走奔跑、活力跳跃抛物线
  - 鼠标拖拽悬空（可怜巴巴 dangling legs）与松开后的重力加速度落地多次缓冲反弹（Landing Rebound）
- **丰富互动与状态机**：
  - 情绪：思考、疑惑、开心欢呼、扁嘴委屈、得意叉腰
  - 日常：专注读书、编写代码、观察视频、伸懒腰、呼呼大睡
  - 抚摸与投喂：摸鱼头（脸红心动粒子）、喂小饼干（饼干碎屑掉落）、戳小肚皮（痒痒笑）、轻碰鲸鱼尾
- **Windows 原生集成**：完全透明无白边、窗口置顶、多显示器安全防跑飞、DPI 自适应缩放（0.75x ~ 1.5x）、鼠标点击穿透模式（Win32 `WS_EX_TRANSPARENT`）与系统托盘菜单。

### 2. 真实自主B站漫游探索
- **拒绝固定假数据池**：实时对接 B站公开只读排行榜（科技 rid 188、科学 rid 36、手作工程 rid 207、入站必刷热门）。
- **WBI 动态公开检索**：基于大肥鱼当下的兴趣偏好、未解疑问与喜爱的 UP 主发起公开搜索。
- **合规守正**：零 Cookie 注入、零破解绕过、零爬虫反制对抗，严格使用公开只读接口。

### 3. 分级视频理解与反思引擎（真相诚实原则）
- **分级理解度**：
  - **字幕完整研读**：成功获取公开外挂/AI 字幕时，全片时间戳梳理，建立证据映射（Evidence Mapping）。
  - **元数据初步理解**：无公开字幕时，诚实明确标注为“部分理解”，绝不编造看完整片画面的谎言。
- **观点与知识提炼**：产出内容概述、独立观点、知识笔记与存疑考证。
- **提示词注入防御**：严密过滤外部不可信文本，防御提示词越狱与人格覆盖。

### 4. 自主评论决策与多通道发布系统
- **大肥鱼拥有“不评论”的自由**：深度不够不评、套话废话不评、信息不足不评、雷同不评。
- **解耦发布通道（`CommentPublisher`）**：
  - `OfficialApiPublisher`：B站官方开放平台 API，自动附带 AI 透明度声明；缺少写权限时优雅降级。
  - `PendingApprovalPublisher`：安全待审队列，供主人一键复制或审查批准。
  - `WebhookPublisher`：推送至外部 Webhook（飞书、Discord 等）。
  - `LocalAuditPublisher`：本地合规审计。
- **安全保障**：主人紧急停止总开关、每小时 1 条与每日 3 条严格限额。

### 5. 自主生活作息调度器
- 后台循环自动巡检，无需每天手动点击“出去逛逛”。
- 深夜安静时段（23:00 - 07:00）自动呼呼大睡，不打扰主人。
- 每日探索预算控制，达成后进入知识沉淀与休息状态。

---

## 🛠️ 技术架构

- **后端**：Python 3.11+ / FastAPI / Uvicorn / Pydantic v2 / HTTPX
- **桌宠表现**：PySide6 6.11+（高性能 60FPS 粒子系统与动力学控制器）
- **持久化**：SQLite（非破坏性迁移，自动备份快照，测试隔离）
- **管理面板**：React 18 / TypeScript / Vite / TailwindCSS 样式
- **打包分发**：PyInstaller Windows 原生独立打包，双击即用

---

## 🚀 快速启动

### 运行打包好的单文件桌面应用
直接双击运行 `dist/BlueWhaleLife/BlueWhaleLife.exe`，应用将自动启动桌宠与管理面板。

### 本地源码开发模式

1. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   cd frontend && npm install && npm run build && cd ..
   ```

2. **启动综合主程序**：
   ```bash
   python app_launcher.py
   ```
   管理面板地址：`http://127.0.0.1:8000`

---

## 📜 许可证与致谢（Attributions & Credits）

本项目源代码遵循 MIT 开源许可证。

### 鲸鱼娘（Whale Musume）素材版权归属
- **立绘创作者**：[Sutera-Diffusus/dsh-whale-musume](https://github.com/Sutera-Diffusus/dsh-whale-musume)
- **Rust 原生移植参考**：[ClutchBear/workbuddy-whale-musume](https://github.com/ClutchBear/workbuddy-whale-musume)
- **许可证**：MIT License（Copyright (c) 2026 Sutera-Diffusus，详见 `desktop_pet/assets/THIRD-PARTY-LICENSES.md`）
- **动作流设计参考**：[YunYueSama/codex-deepseek-pet](https://github.com/YunYueSama/codex-deepseek-pet)

特此向开源社区贡献者致以崇高的敬意！
