# BlueWhaleLife（大肥鱼的B站生活）架构与设计规范

## 一、项目愿景与定位

BlueWhaleLife 是一只 Windows 优先、基于真正网络流行鲸鱼娘（Whale Musume / Q版 DeepSeek 形象）的开源 AI 角色养成程序。

它不是营销机器人，也不是无脑刷评论工具，而是一只具备独立人格、真实内容探索、长期记忆沉淀与分级视频理解能力的桌面小鲸鱼。

核心理念：**给她探索的自由，而不是规定每天必须完成多少任务。**

---

## 二、系统总体架构

```
+-----------------------------------------------------------------------------------+
|                            Windows Desktop Pet (桌宠层)                            |
|  - Authentic Q-version Whale Musume (512x512 High-Res Assets, MIT Licensed)       |
|  - 60 FPS Animation Engine: Breathing float, eye blink, tail wag, walk, jump arc |
|  - Physics Rebound: Drag & drop gravity fall with multi-bounce ground settling    |
|  - Emotion & Activity States: Thinking, Confused, Happy, Aggrieved, Proud, Read,  |
|    Computer, Video Watch, Stretch, Sleep, Headpat, Feed crumb particles           |
|  - Windows Integration: Translucent, Topmost, DPI-aware, Click-through (WS_EX)    |
+-----------------------------------------------------------------------------------+
                                         |
                                         | Local REST / SSE / Signals (127.0.0.1:8000)
                                         v
+-----------------------------------------------------------------------------------+
|                             FastAPI Backend (后端核心)                            |
|                                                                                   |
|  +--------------------+  +----------------------+  +---------------------------+  |
|  | DiscoveryEngine    |  | VideoAnalyzer        |  | CommentDecisionEngine     |  |
|  | - Bilibili Rankings|  | - Evidence Mapping   |  | - Depth & Novelty Filter  |  |
|  | - WBI Keyword Search| | - Partial vs. Full   |  | - Rate Limits & Cliché    |  |
|  | - Soul Alignment   |  | - Prompt Inj Defense |  | - Emergency Stop Switch   |  |
|  +--------------------+  +----------------------+  +---------------------------+  |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | CommentPublisher Interface (发布通道解耦层)                                 |  |
|  | - OfficialApiPublisher: Bilibili OpenAPI with AI Disclosure                 |  |
|  | - PendingApprovalPublisher: Graceful fallback to Master Approval Queue      |  |
|  | - WebhookPublisher: Remote push notifications (Feishu/Discord/Scripts)      |  |
|  | - LocalAuditPublisher: Strict local audit logging                           |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | AutonomousScheduler (自主生活调度器)                                        |  |
|  | - Quiet Hours Protection (23:00 - 07:00 Sleep Mode)                          |  |
|  | - Daily Exploration & API Cost Budget                                       |  |
|  | - Background Async Lifecycle & Pet State Sync                                |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
|  +--------------------+  +----------------------+  +---------------------------+  |
|  | MemoryService      |  | SoulEngine           |  | Security & Storage        |  |
|  | - Watch History    |  | - Dynamic Moods      |  | - Loopback Bound 127.0.0.1|  |
|  | - Evidence Anchors |  | - Trait Versioning   |  | - Strict CORS Policy      |  |
|  | - Knowledge Notes  |  | - State Rollback     |  | - Machine Secret Protect  |  |
|  +--------------------+  +----------------------+  +---------------------------+  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        SQLite Database (whale_life.db)                            |
|  - watch_history (Comprehension Tier, Evidence Map, Comment Decisions, Publications)
|  - knowledge_notes (With Evidence Anchors and Deduplication)                      |
|  - reflection_logs (Growth score, viewpoint shifts, new interests)               |
|  - personality_states (Version history, traits, interests, rollback targets)      |
|  - comment_publications (Platform comment IDs, audit trail, scope logs)          |
|  - chat_messages (Persistent conversation history)                                |
|  - scheduler_state (Activity tracking, today counts, last run time)               |
+-----------------------------------------------------------------------------------+
```

---

## 三、关键子系统设计

### 1. 桌宠表现与动力学渲染器（`desktop_pet/fish_renderer.py`）
- 彻底废除原有几何绘图，复用成熟的开源鲸鱼娘原画（MIT 许可证，原作者 Sutera-Diffusus）。
- 60 FPS 呼吸浮动算法：垂直位移 $y(t) = 2.5 \sin(0.05 t)$，体积缩放 $s_y = 1.0 + 0.015 \sin(0.05 t)$。
- 灵动眨眼与尾巴摆动：自然随机触发 `wink.webp` 与 `tail-swing.webp`。
- 落地缓冲动力学：松开鼠标后执行重力加速度仿真，着地时产生弹跳系数 $e \approx 0.42$ 的多次递减弹跳与压扁回弹 ($s_y = 0.88, s_x = 1.08$)。
- Windows 鼠标点击穿透：通过 Win32 API `WS_EX_TRANSPARENT` 与 `WS_EX_LAYERED`，支持托盘随时开关。

### 2. 真实B站只读发现引擎（`bilibili_source.py` / `discovery.py`）
- 拒绝固定演示候选池。实时抓取 B站科技（rid 188）、科学（rid 36）、手作工程（rid 207）排行榜及入站必刷热门。
- 内置标准 WBI 签名算法，依据大肥鱼未解决的疑问、顶级兴趣及喜爱的 UP 主发起动态公开检索。
- 零破解、零 Cookie 注入，完全遵循平台规则。

### 3. 分级视频理解与反思引擎（`analyzer.py`）
- **第 1 级（公开元数据）**：当视频未开启字幕时，明确标注为 `comprehension_tier = "metadata_only"` 与 `is_partial = True`，并在总结中坦诚声明“基于简介与标题的初步理解，无法获知未披露的细节，绝不伪造观看经历”。
- **第 2 级（公开/AI字幕）**：获取公开 JSON 字幕，解析全片时间戳，提炼时间线证据 `[MM:SS]`。
- **证据映射（Evidence Mapping）**：每个核心观点与提炼出的知识点必须关联对应来源依据。
- **提示词注入防御**：对外部标题与简介执行 HTML 转义与 `<untrusted_bilibili_content>` 隔离沙盒。

### 4. 自主评论决策与发布通道（`publisher.py`）
- **自主决策**：大肥鱼拥有“不评论”的自由。套话、过短、信息不足或雷同内容自动拒绝评论。
- **发布通道抽象（`CommentPublisher`）**：
  - `OfficialApiPublisher`：B站官方开放平台 API，自动附带 AI 身份透明度声明；在缺少写权限时优雅降级到待审队列。
  - `PendingApprovalPublisher`：安全待审队列，供主人一键复制或审查批准。
  - `WebhookPublisher`：推送至飞书/Discord/钉钉或自定义脚本。
  - `LocalAuditPublisher`：严格本地归档审计。
- **安全保障**：
  - 主人紧急停止开关（一键冻结所有外发操作）
  - 每小时 1 条、每日 3 条严格频次限额
  - 历史雷同度检测

### 5. 自主生活调度器（`scheduler.py`）
- 后台循环自动巡检，支持安静时段（深夜 23:00 - 07:00 自动切换为呼呼大睡状态）。
- 每日探索预算控制，达成后进入知识沉淀与休息状态。
- 状态实时同步至桌宠动作与心语弹窗。

---

## 四、安全与合规边界

1. **服务隔离**：FastAPI 严格绑定至 `127.0.0.1` 本地回环接口，CORS 仅允许本地受信任端口。
2. **密钥保护**：API Key 与 OAuth2 Token 经过本地机器指纹保护，响应中一律脱敏，绝不写入 Git 仓库。
3. **数据保护**：SQLite 数据库在迁移前执行自动安全快照备份，采用非破坏性 `ALTER TABLE` 保障既有数据不丢失。
