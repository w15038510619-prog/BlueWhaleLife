# 项目进展与接手开发指引 (PROJECT_STATUS.md)

本文档实时记录 `BlueWhaleLife`（大肥鱼的B站生活）的开发进度与技术交接指引。  
任何新进入本项目的开发者或 AI Agent，均可通过阅读本文件在 **3分钟内精准掌握当前地步与代码架构**。

---

## 一、当前开发阶段

**当前阶段：第一阶段（本地完整 MVP）已 100% 达成并通过全套单元测试与前端打包验证！**

```text
[阶段 1: 本地 MVP] -------------> [阶段 2: 真实数据深挖] -------------> [阶段 3: 记忆与桌宠进阶] -------------> [阶段 4: 打包发布]
   【已完成 100%】                    【即将开启】                           【待推进】                         【待推进】
```

---

## 二、第一阶段达成成果清单

| 模块 | 规划要求 | 落地实现状态 | 验证方法与证据 |
| :--- | :--- | :--- | :--- |
| **开源调研与安全边界** | 深入检查 OpenBiliClaw 与 bilibili-ai-bot，严禁非授权自动评论与账号写操作 | ✅ **已达成**。确立只读发现，所有评论草稿强制采用人工审核+手动复制模式。 | 见 `README.md` 与 `ARCHITECTURE.md` |
| **视频探索引擎** | 结合兴趣权重与新颖度探索，解释“为什么选择该视频” | ✅ **已达成**。实现 `DiscoveryEngine`，内置科学、AI、自然等候选池，透明生成 `reason`。 | 单元测试 `test_autonomous_exploration` 通过 |
| **视频深度理解** | 生成概述、所学、观点、存疑、价值评估、评论草稿 | ✅ **已达成**。实现 `VideoAnalyzer`，加入 Prompt Injection 防御标签与跨视频历史引用。 | 单元测试 `test_api_watch_and_diary` 通过 |
| **SQLite 长期记忆** | 观影轨迹、知识笔记、搜索、软遗忘、自动去重 | ✅ **已达成**。实现 `MemoryService`，5 张核心数据表自动初始化与事务支持。 | 单元测试 `test_memory_record_and_retrieve` 通过 |
| **日常反思与回滚** | 回顾四个核心问题，生成成长日志，性格版本化且可回滚 | ✅ **已达成**。实现 `ReflectionEngine` 与 `SoulEngine`，支持回滚至任意历史版本。 | 单元测试 `test_soul_evolution_and_rollback` 通过 |
| **桌面看板娘 (鲨鱼娘/鲸鱼娘)** | 参考社区爆火的 Q版二次元鲨鱼娘/鲸鱼娘（如 dsh-whale-musume），纯原创矢量 60FPS 动画，大尾巴摇动，6种拟人状态与摸头心动交互 | ✅ **已达成**。基于 PySide6 实现萌系水手服蓝发双马尾鲨鱼娘，抱笔记本写笔记、抱抱枕打瞌睡、摸头心动粒子与快捷聊天。 | `python -c "import desktop_pet.fish_renderer"` 0错误 |
| **全套打包与极简运行** | 前端静态内嵌 FastAPI + PyInstaller 桌宠打包 + 根目录单文件一键运行 | ✅ **已达成**。FastAPI 托管 `frontend/dist`，桌宠编译为 `dist/BlueWhalePet/BlueWhalePet.exe`，根目录提供 `启动大肥鱼.bat`。 | 双击启动、无需额外运行 npm 服务 |
| **管理面板前端** | React 18 + TypeScript + Vite，五大核心控制页面 | ✅ **已达成**。五大页面全部完成，与后端接口完全连通，支持评论草稿在线修改与一键复制。 | `npm run build` 耗时 2.46s，0 TypeScript/打包警告 |
| **Windows 批处理脚本** | 快速开箱运行，无门槛启动 | ✅ **已达成**。编写 `run_all.bat`, `run_backend.bat`, `run_frontend.bat`, `run_desktop_pet.bat`。 | 批处理测试有效 |
| **版本管理与文档** | Git 仓库初始化，排除敏感文件与密钥 | ✅ **已达成**。配置严密的 `.gitignore`，编写完整中英技术文档。 | Git 仓库已就绪 |

---

## 三、各模块代码位置速查

```
F:\脚本工具\大肥鱼\
├── backend/app/
│   ├── config.py             -> 核心配置与 API 密钥安全掩码管理
│   ├── database.py           -> SQLite 数据库连接池与表结构初始化
│   ├── main.py               -> FastAPI 路由注册（提供 Pet, Discovery, Videos, Memory, Soul, Settings API）
│   ├── models/               -> Pydantic Schema（video.py, memory.py, persona.py）
│   ├── services/
│   │   ├── analyzer.py       -> 视频理解、Prompt 注入防御、历史关联
│   │   ├── bilibili_source.py-> B站只读数据源适配（支持真实接口与本地候选池）
│   │   ├── discovery.py      -> 兴趣度打分、新颖度平衡与理由解释
│   │   ├── llm_client.py     -> OpenAI 兼容客户端与高拟真 Demo 兜底
│   │   ├── memory.py         -> 长期记忆 CRUD、关键字搜索、去重、遗忘
│   │   ├── reflection.py     -> 日常反思核心问答与成长日志
│   │   └── soul.py           -> 人格状态机、演进版本记录与回滚
│   └── tests/                -> 包含 11 个单元测试用例
├── desktop_pet/
│   ├── fish_renderer.py      -> QPainter 纯代码 60FPS 矢量绘图（idle, thinking, happy, confused, studying, resting）
│   ├── speech_bubble.py      -> 桌面浮动心境与想法气泡
│   ├── chat_dialog.py        -> 桌面即时快捷聊天对话框
│   ├── pet_window.py         -> 透明置顶主窗体、鼠标拖拽与托盘右键菜单
│   └── main.py               -> 桌宠运行主入口
├── frontend/
│   ├── src/
│   │   ├── api/client.ts     -> 统一封装的 REST 请求层
│   │   ├── pages/
│   │   │   ├── Home.tsx          -> 小肥鱼的家（实时心境、动向、成长值、聊天）
│   │   │   ├── Discoveries.tsx   -> 今天的发现（出去逛逛、候选卡片、选择原因、看视频）
│   │   │   ├── VideoDiary.tsx    -> 观影日记（四维总结、草稿微调、一键复制、直达B站）
│   │   │   ├── MemoryGrowth.tsx  -> 记忆与成长（知识笔记增删改查去重、反思、版本回滚）
│   │   │   └── Settings.tsx      -> 设置（API Base URL、Model、Key安全保存、演示模式）
│   │   ├── types/index.ts    -> 完整前后端契约接口定义
│   │   ├── App.tsx           -> 侧边导航与主界面布局
│   │   └── index.css         -> 现代海蓝色系设计样式
├── scripts/                  -> Windows 批处理一键启动脚本集
```

---

## 四、如何验证与运行测试

### 1. 运行所有后端单元测试
```powershell
python -m pytest backend/app/tests -v
```
预期输出：11 passed, 100% 通过。

### 2. 验证前端 TypeScript 编译与打包
```powershell
cd frontend
npm run build
```
预期输出：`✓ built in 2.xx s`，零错误。

### 3. 一键启动本地完整系统
直接运行 `scripts/run_all.bat`，或在不同终端执行：
```powershell
# 终端 1 (后端)
scripts\run_backend.bat

# 终端 2 (前端)
scripts\run_frontend.bat

# 终端 3 (桌宠)
scripts\run_desktop_pet.bat
```

---

## 五、后续阶段开发路线图 (Roadmap)

### 第二阶段：接入真实只读数据源与深度解析 (Phase 2)
1. **真实数据源增强**：
   - 接入 B站公开开放的只读接口，支持解析指定 BV 号的播放量、弹幕数、AI 自动生成的字幕文件（CC 字幕）。
   - 增强在无字幕、纯音频或长视频下的智能分段提炼。
2. **防风控与合规保障**：
   - 请求频率自适应衰减与退避策略（指数退避），坚决不绕过访问控制与平台限制。

### 第三阶段：向量语义检索与桌宠动效增强 (Phase 3)
1. **向量检索升级**：
   - 在现有 SQLite FTS/关键词搜索基础上，可选择性引入本地轻量 Embedding 模型（如 `all-MiniLM-L6-v2` 或 `bge-small-zh`），实现纯本地的高维向量相似度召回。
2. **桌宠更多情景音效与微表情**：
   - 增加水泡吐出音效（可选关闭）。
   - 增加夜间自动进入“休眠（resting）”模式的生物钟机制。

### 第四阶段：Windows 打包与发布 (Phase 4)
1. 使用 PyInstaller 将桌宠打包为单文件 `BlueWhalePet.exe`。
2. 前端静态网页通过 FastAPI 静态目录直接托管，做到双击单个主程序即可在浏览器中自动弹出。
