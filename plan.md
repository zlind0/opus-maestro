# Classical Music Player - 设计文档 (v0.1.0)

> **最后更新**: 2026-04-19  
> **定位**: AI驱动的古典音乐智能流媒体系统

---

## 1. 术语定义

| 术语 | 定义 | 说明 |
|------|------|------|
| **Work (曲目)** | 一个完整的音乐作品 | 如"贝多芬第五交响曲"，有唯一作曲家、标题、目录编号 |
| **Movement (乐章)** | 作品的逻辑组成部分 | 如"第一乐章：快板"，有序号、标题、情绪标签 |
| **Audio Segment (音频段)** | 物理音频片段 | 可对应完整文件，或CUE切割的虚拟区段 |
| **Version (录音版本)** | 同一曲目的不同演绎 | 由指挥/乐团/年份/厂牌区分 |
| **Canonical String** | 作品规范化描述 | 用于向量检索的统一文本格式 |

---

## 2. 核心设计理念

### 2.1 用户价值
- **语义优先**: 用户通过自然语言表达需求（"播放莫扎特第40号交响曲"），系统自动映射到具体资源
- **技术透明**: 文件格式、CUE分割、音量标准化等细节对用户无感
- **检索融合**: 精确检索（作曲家/时代/类型）+ 语义检索（情绪/风格/描述）+ 语音指令

### 2.2 系统原则
```
1. 元数据以作曲家->作品->乐章为中心，而非文件为中心
2. LLM用于元数据增强，和推荐
3. 所有外部调用（LLM/FFmpeg）需有降级策略
4. 前端播放逻辑与后端流媒体解耦
```

---

## 3. 技术架构

### 3.1 组件概览
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   前端      │────▶│   后端      │────▶│   数据库    │
│  Vue3+PWA   │     │ FastAPI     │     │ PostgreSQL  │
└─────────────┘     └──────┬──────┘     │ + pgvector  │
                           │              └─────────────┘
                    ┌──────┴──────┐
                    │  外部服务   │
                    │ • LLM API   │
                    │ • FFmpeg    │
                    │ • NAS存储   │
                    └─────────────┘
```

### 3.2 技术栈
| 层级 | 技术选型 | 关键依赖 |
|------|----------|----------|
| 前端 | Vue 3 + TypeScript + Vite | Pinia, Vue Router, vite-plugin-pwa |
| 后端 | FastAPI + Python 3.12 | SQLAlchemy(async), pgvector, mutagen |
| 数据库 | PostgreSQL 15+ | pgvector 0.5+, 异步连接池 |
| 音频处理 | FFmpeg 6.0+ | 支持格式: MP3/FLAC/M4A/APE/WAV |
| LLM集成 | OpenAI Compatible API | text-embedding-3-small, 自定义模型 |
| 部署 | Docker Compose | Nginx反向代理, 卷挂载 |

---

## 4. 数据模型

### 4.1 核心实体关系
```
Work (1) ──┬── (N) Movement ──┬── (N) AudioSegment ── (1) AudioFile
           │                  │
           │                  └── (1) Version (N:1)
           │
           └── (N) Version
```

### 4.2 关键字段契约

#### Work
```typescript
interface Work {
  id: UUID;                      // 主键
  composer: string;             // 作曲家（标准化中文名）【】
  era: string; //都用中文！【创作年代，文艺复兴、巴洛克、古典、浪漫、现代、后现代等，请补充】
  work_type: string; //都用中文！【交响曲，协奏曲，奏鸣曲等，请补充】
  catalog_number: string;       // 目录编号: K.550, Op.67, BWV.232
  title: string;                // 作品标题: "交响曲第40号"
  movement_count: number;       // 乐章编号（1，2，3...）
  canonical_string: string;     // 检索用规范文本
  summary?: string;             // LLM生成的作品简介
}
```

#### Movement
```typescript
interface Movement {
  id: UUID;
  work_id: UUID;                // 外键 → Work
  movement_number: number;      // 乐章序号 (1,2,3...)
  title: string;                // 乐章标题: "Allegro assai"
  mood?: 'joyful'|'melancholic'|'agitated'|'calm'|'mysterious'|'solemn'|'playful';
  embedding: number[];          // 1536维向量 (OpenAI embedding)
  description?: string;         // 乐章描述
}
```

#### AudioSegment
```typescript
interface AudioSegment {
  id: UUID;
  file_id: UUID;                // 外键 → AudioFile
  movement_id?: UUID;           // 外键 → Movement (可空)
  start_time_ms: number;        // 起始时间(毫秒)
  end_time_ms?: number;         // 结束时间(毫秒), 空表示到文件末尾
  is_virtual: boolean;          // 是否CUE生成的虚拟段
}
```

### 4.3 向量检索规范
- **嵌入模型**: `text-embedding-3-small` (1536维)
- **距离度量**: 余弦相似度 (cosine distance)
- **索引类型**: HNSW (`index_type=hnsw`, `m=16`, `ef_construction=64`)
- **检索阈值**: 相似度 ≥ 0.9 视为相关

---

## 5. API 接口规范

### 5.1 认证模块
| 方法 | 路径 | 参数 | 返回 | 说明 |
|------|------|------|------|------|
| POST | `/api/v1/auth/token` | `username`, `password` (form) | `{access_token, token_type, user}` | 获取JWT令牌 |
| GET | `/api/v1/auth/me` | Header: `Authorization: Bearer <token>` | `{username, role}` | 获取当前用户 |

### 5.2 音乐检索模块
| 方法 | 路径 | 参数 | 返回 | 说明 |
|------|------|------|------|------|
| GET | `/api/v1/works` | `limit?`, `offset?`, `composer?`, `era?`, `work_type?` | `Work[]` | 精确条件查询 |
| GET | `/api/v1/works/{id}` | - | `Work` | 获取曲目详情 |
| GET | `/api/v1/works/{id}/movements` | - | `Movement[]` | 获取乐章列表 |
| GET | `/api/v1/search` | `query` (语义) 或 `composer/era/work_type` (精确) | `{type: 'semantic'\|'precise', results: Work[]}` | 混合检索 |

### 5.3 播放模块
| 方法 | 路径 | 参数 | 返回 | 说明 |
|------|------|------|------|------|
| GET | `/api/v1/audio/segments/{id}` | `target_format?: 'flac'\|'mp3'` | `audio/*` (二进制流) | 流式获取音频 |
| GET | `/api/v1/recommend/{movement_id}` | `limit?: number` | `Movement[]` | 获取相似乐章推荐 |

### 5.4 系统管理模块
| 方法 | 路径 | 参数 | 返回 | 说明 |
|------|------|------|------|------|
| POST | `/api/v1/scan` | - | `{message: string}` | 触发音乐库扫描 |
| GET | `/api/v1/scan/status` | - | `{status, total, current, message}` | 获取索引进度 |

### 5.5 错误码规范
```typescript
type ErrorCode = 
  | 'AUTH_INVALID_CREDENTIALS'    // 401
  | 'AUTH_TOKEN_EXPIRED'          // 401
  | 'RESOURCE_NOT_FOUND'          // 404
  | 'AUDIO_CONVERSION_FAILED'     // 500
  | 'LLM_SERVICE_UNAVAILABLE'     // 503
  | 'INVALID_REQUEST_PARAMS';     // 400
```

---

## 6. 核心业务流程

### 6.1 音乐索引流程
```
1. 扫描目录 → 2. 识别新文件 → 3. 提取基础元数据 (mutagen)
       ↓
4. 构建LLM提示词 → 5. 调用LLM提取高级元数据
       ↓
6. 标准化输出 → 7. 创建/关联 Work → 8. 创建 Movement
       ↓
9. 生成 canonical_string → 10. 获取向量嵌入 → 11. 写入数据库
```

### 6.2 播放请求流程
```
1. 前端请求 segment_id → 2. 后端查询音频段元数据
       ↓
3. 确定源文件 + 时间范围 → 4. 生成FFmpeg命令
       ↓
5. 流式转换输出 → 6. 前端HTML5 Audio播放
       ↓
7. 播放结束 → 8. 请求推荐接口 → 9. 预加载下一首
```

### 6.3 语义检索流程
```
1. 用户输入自然语言 → 2. 后端调用LLM生成查询向量
       ↓
3. pgvector余弦搜索 → 4. 过滤权限/可用性
       ↓
5. 按相似度排序 → 6. 返回前N个Work/Movement
```

---

## 7. 前端关键实现规范

### 7.1 播放保活 (iOS兼容)
```typescript
// 必须实现 Media Session API
if ('mediaSession' in navigator) {
  navigator.mediaSession.metadata = new MediaMetadata({
    title: work.title,
    artist: work.composer,
    album: version?.label,
    artwork: [{ src: '/cover.jpg', sizes: '512x512', type: 'image/jpeg' }]
  });
  
  navigator.mediaSession.setActionHandler('play', () => audio.play());
  navigator.mediaSession.setActionHandler('pause', () => audio.pause());
  navigator.mediaSession.setActionHandler('previoustrack', playPrevious);
  navigator.mediaSession.setActionHandler('nexttrack', playNext);
}
```

### 7.2 PWA 配置要点
- `display: standalone` 确保全屏体验
- `start_url: '/'` 保证离线可访问
- 缓存策略: 静态资源 `CacheFirst`, API请求 `NetworkFirst`
- 后台同步: 播放进度定期上报 (IndexedDB + Background Sync)

### 7.3 状态管理 (Pinia)
```typescript
interface PlayerState {
  currentSegment?: AudioSegment;
  currentWork?: Work;
  isPlaying: boolean;
  progress: number;           // 当前播放位置(毫秒)
  queue: AudioSegment[];      // 播放队列
  volume: number;             // 0.0 ~ 1.0
}
```

### 7.4 UI风格

因为是一个古典音乐APP，所以要使用经典的拟物风格。ui_1.png ui_2.png展示了这种风格，不局限于这两张设计图，你自己考虑。类似于iOS5的风格。

---

## 8. 部署与运维

### 8.1 Docker Compose 服务
```yaml
services:
  db:
    image: postgres:15
    volumes: [pgdata:/var/lib/postgresql/data]
    environment: [POSTGRES_PASSWORD, POSTGRES_DB]
    
  backend:
    build: ./backend
    depends_on: [db]
    environment: [DATABASE_URL, OPENAI_API_KEY, MUSIC_PATH]
    volumes: [${MUSIC_PATH}:/music:ro]
    
  frontend:
    build: ./frontend
    ports: ["5173:80"]
    
  # 可选: Nginx反向代理 + SSL终止
```

### 8.2 环境变量要求
```env
# 必选
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.openai.com/v1  # 或本地兼容端点
DATABASE_URL=postgresql://user:pass@db:5432/music
MUSIC_PATH=/music
SECRET_KEY=jwt-signing-key-min-32-chars

# 可选
LOG_LEVEL=info
AUDIO_CACHE_TTL=3600  # 音频流缓存秒数
```

### 8.3 健康检查端点
```
GET /health
→ 200: { "status": "ok", "db": "connected", "llm": "available" }
→ 503: { "status": "degraded", "issues": ["llm_timeout"] }
```

### 8.4 前端调试建议

为了方便调试，应当具备一种prod模式和一种dev模式。dev模式下，确保前端代码一保存，浏览器就能刷新。

---

## 9. 测试策略

### 9.1 单元测试覆盖
- LLM提示词构建与解析
- 元数据标准化逻辑
- 向量相似度计算
- FFmpeg命令生成

### 9.2 集成测试场景
```gherkin
Scenario: 新用户播放莫扎特第40交响曲
  Given 用户已登录
  When 搜索 "莫扎特第40号交响曲"
  Then 返回 K.550 相关作品
  When 点击播放第一乐章
  Then 音频流正常播放且进度可更新

Scenario: CUE文件自动分割
  Given 存在 album.flac + album.cue
  When 触发索引扫描
  Then 生成多个 virtual audio_segment
  And 每个segment关联正确movement
```

### 9.3 LLM调试工具
```bash
# 单文件元数据提取调试
python tools/debug_extract.py /path/to/file.m4a --output prompt.txt

# 输出包含:
# - 原始标签
# - 发送给LLM的完整prompt
# - LLM返回的JSON
# - 标准化后的canonical_string
```

---

## 10. 非功能需求

| 类别 | 指标 | 验收标准 |
|------|------|----------|
| **性能** | 搜索响应 | P95 < 800ms (含LLM调用) |
| | 音频首帧 | < 2s (局域网) |
| | 并发播放 | ≥ 20 路同时流 |
| **可靠性** | 服务可用性 | ≥ 99.5% (月度) |
| | 错误恢复 | LLM超时自动降级为精确检索 |
| **安全** | 认证 | JWT + HTTPS + 密码加密存储 |
| | 权限 | 管理员/普通用户角色隔离 |
| **可维护** | 日志 | 结构化日志 + 请求追踪ID |
| | 配置 | 所有外部依赖可配置化 |

---

## 附录

### A. 支持音频格式
| 格式 | 输入支持 | 输出支持 | 备注 |
|------|----------|----------|------|
| MP3 | ✅ | ✅ | 原生流式 |
| FLAC | ✅ | ✅ | 原生流式 |
| M4A (AAC) | ✅ | ✅ | 原生流式 |
| M4A (ALAC) | ✅ | ✅ (转FLAC) | 自动转换 |
| APE | ✅ | ✅ (转FLAC) | 自动转换 |
| WAV | ✅ | ✅ | 原生流式 |
| CUE+FLAC | ✅ | ✅ (虚拟分割) | 自动识别 |

### B. LLM提示词设计原则
1. **结构化输出**: 强制JSON Schema，避免解析错误
2. **容错设计**: 字段可选，缺失时返回`null`而非失败
3. **语言中立**: 提示词用英文，输出字段值用目标语言(默认中文)
4. **降级策略**: LLM超时/失败时，回退到基础标签+规则匹配

### C. 版本演进路线
```
v0.1 (当前): 核心播放 + 基础检索 + 单用户
v0.2: 播放列表 + 用户系统 + 权限管理
v0.3: 语音指令 + 哼唱检索 + 个性化推荐
v1.0: 多租户 + 社交分享 + 移动端原生封装
```

---

> **文档维护**: 任何架构变更需同步更新本文件第3/4/5节，并标注版本号与变更日期。