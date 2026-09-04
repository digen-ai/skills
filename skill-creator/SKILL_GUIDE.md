# Skill Agent 技能编写指南

本文档指导如何为 **`skill_agent` workflow**（`AgentHarness`）编写 Skills。

> | | Skill Agent Harness（当前唯一路径） |
> |---|---|
> | 编排器 | `core.agent.harness.agent.AgentHarness` |
> | 配置入口 | **`SKILL.md` 包**（+ 可选极简 `orchestrator_config.yaml`） |
> | 状态模型 | **无结构化项目状态**；进度靠对话 + 画布资产 + `write_todos` |
> | 能力来源 | 单 Agent + **渐进式披露的 Skill 指令** + 平台云端工具 |
> | 适用场景 | 可组合、可上传的能力包；用户/官方 Skill 市场 |

**不要**用已下线的 `data_schemas` / `operations` / Agent prompt YAML 来写 Skill。Skill 是给模型读的 **Markdown 操作手册**，不是数据契约配置。

参考实现：

- Skill 创作工具（对话中创建/发布用户 Skill）：`examples/skill_creator/` + `packages/core/src/core/tools/skill_authoring.py`
- 编排器：`packages/core/src/core/agent/harness/agent.py`
- 解析器：`packages/core/src/core/agent/skills/skill_loader.py`

---

## 目录

1. [工作原理（渐进式披露）](#1-工作原理渐进式披露)
2. [Skill 目录结构](#2-skill-目录结构)
3. [SKILL.md 格式](#3-skillmd-格式)
4. [编写正文（body）](#4-编写正文body)
5. [多阶段 Skill 与 references/](#5-多阶段-skill-与-references)
6. [平台工具清单与常用参数](#6-平台工具清单与常用参数)
7. [常驻工具（read_skill / write_todos / set_guidance）与需声明的记忆工具（memory_*）](#7-常驻工具)
8. [用户 Skill 限制（天花板）](#8-用户-skill-限制天花板)
9. [Skill 创作工具（skill-creator，仅官方 Skill 可声明）](#9-skill-创作工具skill-creator仅官方-skill-可声明)
10. [orchestrator_config（可选）](#10-orchestrator_config可选)
11. [完整示例](#11-完整示例)
12. [AI 编写检查清单](#12-ai-编写检查清单)

---

## 1. 工作原理（渐进式披露）

Skill Agent **不会**把每个 Skill 的全文塞进系统 prompt。披露分三层：

```
第一层（系统 prompt）  → 仅 name + description（索引，用于判断是否相关）
        ↓ 模型调用 read_skill(name)
第二层（工具返回）     → SKILL.md 正文 body + allowed_tools + reference_files 路径列表 + preset_assets 清单
        ↓ 模型按需调用 read_skill_file(name, path)
第三层（工具返回）     → references/ 下某个文本文件的完整内容
```

因此：

- **`description` 必须写好**：这是模型决定要不要 `read_skill` 的唯一依据。写得太窄会漏触发，太宽会误触发。
- **正文要可执行**：`read_skill` 之后，模型应能按步骤完成任务，不要假设它还记得别的配置文件。
- **细节放 references/**：长流程、模板、示例拆到引用文件，正文只放索引表 + 协作原则，避免一次读入过长上下文。
- **媒体走预设资产**：品牌 Logo、角色底图、参考配音等图片/视频/音频**不要**放进 zip；用公共 `preset_assets` 清单（含 `asset_id` + 稳定 `s3://` uri），见下文「预设资产」。

常驻可用（不依赖 `allowed-tools`）：`read_skill`、`read_skill_file`、`write_todos`；若 workflow 开启 `suggested_questions`（默认开），还有 `set_guidance`。**注意**：`memory_whoami` / `memory_query` / `skill_kb_query` / `memory_store` / `memory_forget` **不是**常驻工具，需要长期记忆/共享知识库能力的 Skill 必须在自己的 `allowed-tools` 里显式声明（见第 7.4 节）。

可执行能力 **只来自平台云端工具**（`generate_image`、`search_web`、`memory_*` 等）。Skill 包内的 `scripts/` **不会**被解析或执行（目录会被跳过）。

---

## 2. Skill 目录结构

```
my-skill/
├── SKILL.md                 # 必须：frontmatter + 正文
└── references/              # 可选：补充说明（渐进式披露第三层）
    ├── stage_a.md
    └── templates/
        └── outline.md
```

规则：

| 规则 | 说明 |
|---|---|
| 必须有 `SKILL.md` | 文件名大小写固定 |
| `name` 建议与目录名一致 | kebab-case（小写字母/数字 + 连字符），如 `image-generation` |
| 引用文件只收纯文本 | `.md` / `.yaml` / `.json` / `.txt` 等；图片/视频/zip 等二进制会被跳过 |
| 跳过的目录 | `scripts/`、`__pycache__/`、`.` 开头的目录 |
| 打包上传 | zip 根目录直接是 `SKILL.md`，或只有一层顶层子目录均可 |

### 预设资产（preset_assets）

与 `listing.required_assets`（仅 UI 提示用户「需要自备什么」）不同：**预设资产**是 Skill 自带的参考图/视频/音频。媒体以公共 `assets` 行存储（`is_public=true`），Skill 清单同时保存引用与稳定的 `s3://` 地址：

```json
[
  {
    "key": "brand_logo",
    "label": "品牌 Logo",
    "asset_id": "skpa_xxxx",
    "type": "image",
    "uri": "s3://bucket/path/logo.png",
    "providers": ["aws"]
  }
]
```

- zip **不**打包二进制；作者通过 HTTP API 上传/绑定，或在 skill-creator 对话里对用户附件调用 `bind_skill_preset_asset`。
- 安装不拷贝：安装者按 `asset_id` / `uri` 解析使用；**不要**把会过期的 https 预签名写入清单。
- 限额：`skills.preset_assets.max_count`（默认 10）；类型限 image / video / audio。
- 运行时：`read_skill` 返回含 `uri`/`providers` 的 `preset_assets`；生成类工具的 `input_urls` / `image_url` 可传 **`uri`（s3://）、`asset_id` 或预设 `key`**，由平台预签名；skill_agent 也会把已挂载 Skill 的预设资产注入 context。

导入本地目录示例：

```bash
source .venv/bin/activate
python -c "
from core.agent.skills.skill_loader import import_skills_from_directory
import asyncio
asyncio.run(import_skills_from_directory('examples/skill_demo/skills'))
"
```

---

## 3. SKILL.md 格式

```markdown
---
name: image-generation
description: 用户想要生成、绘制或创作一张图片（插画、海报、头像、场景图等）时使用
display_name: 图片生成          # 可选，UI 展示名
allowed-tools:
  - list_models
  - generate_image
---

# Image Generation

## 何时使用
...

## 步骤
...

## 注意事项
...
```

### Frontmatter 字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | 是 | Skill 唯一标识；系统 prompt 索引与 `read_skill(name)` 使用同一字符串。建议 kebab-case（`[a-z0-9]+(-[a-z0-9]+)*`，如 `image-generation`），不用下划线/驼峰 |
| `description` | 是 | **一句话触发条件**（见下）。只出现在第一层索引里 |
| `allowed-tools` | 强烈建议 | 本 Skill 需要用到的平台工具白名单。也支持 `allowed_tools` 或逗号分隔字符串 |
| `canvas` | 否 | 产物可见性控制：`model_control` / `hidden_tools` / `hidden_entity_types`（见第 6.2 节「隐藏中间产物」） |
| `model` | 否 | LLM 模型档位（`standard` / `uncensored`），官方 / 用户 Skill 均可声明（见第 6.5 节「模型档位切换」）。注意：与生成工具参数里的 **channel**（`model='i2v'` 等）不是同一概念 |
| `display_name` / `title` | 否 | 人类可读名称；不影响 LLM 调度 |
| 其他字段 | 否 | 保留为 `metadata`（如 `version`、`license`），不参与运行逻辑 |

`allowed-tools` 也可写成：`allowed-tools: search_web, generate_image`。

### 写好 description（最重要）

`description` 回答的是：**什么用户意图下应该启用本 Skill**，不是功能口号。

好的写法：

```yaml
description: 用户想要生成、绘制或创作一张图片（插画、海报、头像、场景图等）时使用
```

```yaml
description: 用户想要制作短剧（从一句话创意到成片：编剧、角色/场景视觉、分镜图/视频、配音、合成）时使用；只想推进/修改其中某一环节时也使用本 skill
```

坏的写法：

```yaml
description: 一个强大的图片工具          # 太虚，模型无法判断何时 read
description: 调用 generate_image         # 暴露实现细节，不是用户意图
description: 短剧                         # 过短，漏掉「改某一环也适用」等边界
```

技巧：用「用户想要…时使用」句式；把近义词/子场景写进括号；若局部修改也应触发，在 description 里明确写出来。

---

## 4. 编写正文（body）

正文是模型在 `read_skill` 之后唯一的操作说明书。推荐结构：

```markdown
# <可读标题>

一两句说明本 Skill 做什么，以及有无结构化状态（通常没有）。

## 何时使用
- 触发场景列表（与 description 呼应，可更细）

## 步骤
1. …
2. 调用 `tool_name`，参数约定：…
3. …

## 注意事项
- 失败/拒绝对策、不要编造 URL、内容政策等
```

### 正文写作原则（给 AI）

1. **只写本 Skill 需要的行为**：不要复述系统级规则（function calling、不要 JSON 输出等），编排器已注入。
2. **步骤可执行**：写清「先做什么 → 调哪个工具 → 传哪些关键参数 → 成功后如何回复用户」。
3. **参数约定写进 Skill**：尤其是 `name`、`entity_type`、`orientation`、生成类工具的 **`model=<channel>`**、prompt 语言（中/英）等；工具 schema 有默认值，但业务约定以 Skill 为准。涉及媒体生成时优先写死 channel，不要写物理模型名（见第 6.3 节）。
4. **不要假设 project state / operations**：没有 `characters` 集合可写；需要跨轮复用的内容用 Markdown 写在回复里，或引用画布上已有资产 URL。
5. **产物会自动上画布**：最终回复用自然语言概括即可，**不要大段粘贴 URL**。
6. **失败如实告知**：工具 `success=false` 时不要假装成功或编造资源链接。
7. **内容政策**：暴力/色情等请求礼貌拒绝，不调用生成工具。
8. **控制长度**：简单 Skill 控制在数百到一两千字；复杂流程拆到 `references/`。用户 Skill 正文默认上限约 `50000` 字符（见配置 `skills.user_authored.max_body_chars`）。

### 与「最终回复」相关的约定

- 需要边说边做时：同一轮可以输出文字并附带工具调用（文字会立刻展示）。
- 任务完成时：输出最终文字回复；若需推荐下一步，**同一轮**调用 `set_guidance`（见第 7 节），不要再调其他工具。
- 多步任务：先 `write_todos` 列出步骤，推进时整表更新 `status`。

---

## 5. 多阶段 Skill 与 references/

长流程（如短剧全链路）不要把所有细节塞进 `SKILL.md` 正文。正确模式：

**正文**：阶段索引表 + 协作原则 + 何时读哪个文件  
**references/\*.md**：每个阶段的详细步骤

正文示例骨架（参考 `examples/drama_skills/SKILL.md`）：

```markdown
## 制作阶段（references/）

每个阶段的详细步骤单独放在 `references/` 下。**不要一次性全读**：先判断当前阶段，只用 `read_skill_file` 读对应那一个文件。

| 阶段 | 文件 | 用到的工具 | 什么时候读 |
|---|---|---|---|
| 一、编剧 | `references/scriptwriting.md` | 无 | 用户给创意/要改剧本 |
| 二、视觉设计 | `references/visual_design.md` | `generate_image` | 需要角色/场景参考图 |
| … | … | … | … |

## 协作原则

- 用户说「一键生成」：按表顺序连续推进；每完成一阶段同步进度，立刻读下一阶段，**不要在阶段之间询问确认**。
- 用户只改某一环：只读对应文件，不要重做全流程。
- 仅当用户明确说「先确认」「等我看看」时才停下。
- 进入多阶段时先 `write_todos`；阶段边界停下或全流程完成时调用 `set_guidance`。
```

引用文件内部同样用「何时使用 / 步骤 / 注意事项」结构，并写明本阶段工具参数（如 `entity_type='characters'`）。

引用文件路径以相对 Skill 根目录为准（如 `references/visual_design.md`），必须与 `read_skill` 返回的 `reference_files` 列表一致。用户 Skill 默认最多约 `10` 个引用文件。

---

## 6. 平台工具清单与常用参数

Skill 只能声明并使用平台已注册的工具。用户自建 Skill 还受 **工具天花板** 约束（第 8 节）。

### 6.1 常用工具一览

| 工具 | 用途 | 典型参数 |
|---|---|---|
| `list_models` | 查看可用生成模型 / channel（起草时的兜底核对） | `model_type`: `image` / `video` / `tts` / `asr` / `music` 等；**不能替代** channel 目录（见 6.3） |
| `search_library` | 搜索资产库（公共库+个人库） | `keyword`；可选 `category`、`scope`（`all`/`personal`/`public`）、`limit`、`offset`；返回 `uri`+`providers`（无预签名 URL） |
| `get_library_item` | 获取库条目详情（含媒体 s3 引用） | `item_id`（来自 `search_library`）；返回 `media[].uri`/`providers` |
| `generate_image` | 文生图 / 图生图 | `prompt`；可选 `input_urls`、`orientation`、`resolution`、**`model`（写 channel，如 `t2i` / `i2i.hd`）**、`name`、`entity_type` |
| `generate_video` | 文生视频 / 图生视频 / 参考生视频等 | `prompt`；`input_urls`（`ref2v` 模式下至少 1 张参考图，`t2v` 可留空）；`orientation`、`resolution`、`duration`、**`model`（写 channel，如 `i2v` / `ref2v` / `t2v`；留空默认 `ref2v`；具体模型名会被拒绝）**、`name`、`entity_type` |
| `generate_tts` | 配音 | `text`；`voice_instruction`（`tts.design` 通道必填）或 `reference_audio_url`（`tts.clone` 通道必填）；可选 **`model`（写 channel，如 `tts.design` / `tts.clone`，模式完全由 channel 决定；留空按是否传了 `reference_audio_url` 自动选默认 channel）**、`name`、`entity_type` |
| `generate_music` | 文生音乐 | `prompt`；可选 `lyrics`（歌词，留空则纯音乐/模型即兴）、**`model='music'`**、`model_type`、`output_format`、`name`、`entity_type` |
| `mix_clips` | 多片段拼接混音 | `clips[]`（`video`/`videos` + `audio`/`audios`，每条轨道的 `url` 支持 asset_id / `s3://` / 真实 https，会自动解析预签名）；`name`、`entity_type`（对应 channel `clip-mixer`）；可选 `orientation`（画布占位方向，不影响合成结果，应与源片段方向一致，如竖屏短剧传 `portrait`） |
| `split_image` | 图片网格切割为瓦片 | `input_urls`；可选 `rows`、`cols`、`output_format`、`quality`、`border` |
| `recognize_image` | 识图 / 看图描述 | `image_url` 或 `image_base64`；可选 `prompt`、`media_type`、`model` |
| `recognize_video` | 视频理解 / 描述 | `video_url`；可选 `prompt`、`model` |
| `transcribe_audio` | 音频转写（含 SRT） | `audio_url`；可选 `cache`、**`model='asr'`** |
| `search_web` | 网络搜索 | `query`；可选 `search_depth`、`max_results` |
| `fetch_video_info` | 社媒视频元数据 | `url`（YouTube/TikTok/IG/FB/X/LinkedIn） |
| `download_video` | 社媒视频临时下载链 | `url`；可选 `quality`、`format`（仅 YT/TikTok/IG） |
| `create_document` | 新建一个 document 资产（与图片/视频/音频同级，进画布；总是新建，不会覆盖已有文档） | `content`；可选 `name`、`filename`、`content_type`（默认 `text/markdown`）、`entity_type` |
| `update_document` | 对已有 document 资产原地更新（同一 asset_id，画布卡片原地刷新，不产生新资产） | `asset_id`、`content`（全量覆盖）；可选 `name`、`content_type`、`entity_type`（不传则沿用原文档） |
| `get_document` | 按 asset_id 读取 document 资产正文 | `asset_id`（来自 `create_document` 或用户上传的文档） |

生成类 / 处理类产物工具（`generate_*`、`split_image`、`mix_clips`、`create_document`、`update_document`）成功后，资产会进入画布（若 workflow `add_to_canvas: true`）。`recognize_image` / `recognize_video` / `transcribe_audio` / `fetch_video_info` / `download_video` / `get_document` / `search_web` / `search_library` / `get_library_item` 为交互型结果，不上画布。

**资产库用法（`search_library` → `get_library_item` → 生成工具）**：先用 `search_library` 按关键字/类别/范围检索公共库或个人库（返回紧凑的 `uri`+`providers`，无预签名 URL），再用 `get_library_item(item_id=...)` 拿到 `media[].uri` / `providers`，写入项目资产或作为 `generate_image(input_urls=[uri])`、`generate_video`、`recognize_image` 的输入（传 s3://，系统执行前自动预签名）。

### 6.2 画布资产约定（强烈建议在 Skill 中写明）

调用 `generate_image` / `generate_video` / `generate_tts` / `generate_music` / `mix_clips` / `create_document` / `update_document` 等产物工具时：

- 传简短 **`name`**（角色名、镜头标题、成片名、曲名、文档标题等），便于画布展示。
- 传约定的 **`entity_type`**（未传时默认为 `skill_generation`）。常见取值：
  - 图片：`characters` / `locations` / `props` / `storyboard_images`
  - 视频：`storyboard_videos` / `final_videos`
  - 音频：按业务自定（如 `voiceovers` / `music`）
  - 文档：按业务自定（如 `scripts` / `reports`）
- **不要**让模型传 `group_id` / `index`（若系统有自动分配逻辑，由平台处理）。
- `download_video` 返回的 `downloadUrl` **有时效**，需在 `expiresIn` 内使用。
- `create_document` / `update_document` 产出的 document 资产存储模型与用户上传文档一致：S3 存原文，`document_contents` 存纯文本供 `get_document` / 上下文注入读取（不回源读 S3）。`create_document` 每次调用都会新建一个 asset_id + 新画布卡片；`update_document` 是 PUT 语义，按传入的既有 `asset_id` 原地刷新同一张卡片，不产生新卡片——修改已有文档用 `update_document`，新建文档用 `create_document`。两者的 `content` 都有长度上限（默认 `200000` 字符，见配置 `plugins/documents/config.yaml` 的 `create_document.max_content_chars` / `update_document.max_content_chars`），超限会返回 `success: false`，需要更大内容时应拆分为多个文档。

#### 隐藏中间产物（frontmatter `canvas:`）

产物默认上画布并在对话里出现资产卡片。若流程中有不希望用户看到的中间产物（待切割的网格图、待混剪的片段等），在 frontmatter 声明 `canvas:` 段：

```yaml
---
name: my-skill
description: ...
canvas:
  model_control: true                       # 允许模型逐次调用决定是否展示
  hidden_tools: [split_image]               # 该工具产物一律不展示
  hidden_entity_types: [work_in_progress]   # 该 entity_type 产物一律不展示
---
```

- 三个字段均可选。只写 `hidden_*`：纯规则式，模型无感知；只写 `model_control: true`：完全交给模型按正文约定逐次决定；两者可同时用（模型未显式传时回落到 `hidden_*` 规则）。
- `model_control: true` 时，产物类工具会多出一个可选参数 **`add_to_canvas`（默认 true）**。正文里要写死哪一步传 `false`，例如：「生成待切割的网格图时调用 `generate_image` 传 `add_to_canvas=false`；切割结果（瓦片）正常展示」。
- 隐藏语义：不发画布/对话资产卡片，并把资产加入 canvas hidden_ids。**产物照常计费、照常进资产库，URL 仍可作为后续工具的输入**——隐藏只影响展示。
- 规则按「本轮已挂载的所有 Skill 取并集」生效：一个 Skill 声明隐藏某 `entity_type`，同轮其他 Skill 用同名 `entity_type` 的产物也会被隐藏。约定 entity_type 命名时注意区分。
- workflow 级 `add_to_canvas: false`（orchestrator_config）仍是总开关，优先级高于以上一切。

### 6.3 生成 channel 选型（优先使用）

平台为图片 / 视频 / 配音 / 音乐等生成能力引入了稳定的 **model channel**。Skill 作者在正文里应把生成工具的 `model=` **写成 channel**（可选带 variant 后缀），**不要**硬编码物理模型名（如 `rm3.1-G`、`qwen-image`）。模型升级时，运营侧通过 channel binding 切换底层模型，Skill 无需重新发布。

> 权威目录：`examples/skill_creator/skills/skill-creator/references/available-models.md`（skill-creator 运行时用 `read_skill_file` 读取）。起草时以该表为准；`list_models` 只作兜底核对，不能替代目录、更不能凭记忆发明 channel。

**概念**：

- **channel**：稳定模态 ID，如 `t2i`、`i2v`、`ref2v`、`tts.design`。Skill 正文写 channel。
- **variant 后缀**：选择带 tag 的 binding，如 `i2v.nsfw`、`t2i.hd`、`i2i.hd.lite`（可组合；最长前缀 channel 匹配优先）。
- **裸 channel**（如 `i2v`）：走当前 **default** binding。
- **物理模型名**：仍可解析（兼容旧 Skill），但 **新 Skill 禁止再写**。

**常用 channel 速查**（完整说明与约束见 `available-models.md`）：

| Channel / Variant | 工具 | 模态 / 何时用 |
|---|---|---|
| `t2i` / `t2i.hd` / `t2i.hd.lite` | `generate_image` | 文生图；`.hd*` 更高质量且**不支持 NSFW** |
| `i2i` / `i2i.hd` / `i2i.hd.lite` | `generate_image` | 图生图（有参考图）；网格分镜优先 `.hd` / `.hd.lite`；`.hd*` **不支持 NSFW** |
| `i2v` / `i2v.nsfw` | `generate_video` | 图生视频；成人/高强度内容优先 `i2v.nsfw` |
| `fl2v` | `generate_video` | 首尾帧生视频（`input_urls` 为首帧+尾帧） |
| `ai2v` | `generate_video` | 图 + 音频驱动生视频 |
| `t2v` | `generate_video` | 通用文生/图生视频；显式传 `model='t2v'` 时 `input_urls` 可留空（纯文生视频） |
| `ref2v` | `generate_video` | 参考生视频（保角色一致性）；模态由 channel 直接决定，**无需**再传 `gen_mode`；至少 1 张参考图；可选 `audio_url`、`orientation`；**`model` 缺省时的默认 channel** |
| `clip-mixer` | `mix_clips` | 多片段拼接混音（合成通道，非生成模型） |
| `tts.design` / `tts.clone` | `generate_tts` | 模态由 channel 直接决定，**无需**再传 `mode`：`tts.design` 声音设计（需 `voice_instruction`）/ `tts.clone` 声音克隆（需 `reference_audio_url`） |
| `music` | `generate_music` | 文生音乐 |
| `asr` | `transcribe_audio` | 语音转写 |

**选型规则（写进 Skill 正文时）**：

1. 先按用户意图确定模态（文生图 / 图生图 / 图生视频 / 首尾帧 / 音频驱动 / 参考生视频 / Director / 配音 / 音乐 / 拼接）。
2. 选定工具后，在步骤里**硬编码** `model=<channel>`（及必要的输入约定：`input_urls`、`mode`、`audio_url`、`voice_instruction` 等）。需要 tagged binding 时用后缀（如 `model='i2v.nsfw'`、`model='t2i.hd'`）。
3. 图生视频：常规 → `i2v`；NSFW/成人 → `i2v.nsfw`。
4. 参考生视频：传 `model='ref2v'` 即可（模态完全由 channel 决定，**不需要**再传 `gen_mode`）；至少 1 张参考图。若还需音频驱动，另传 `audio_url`（可选 `audio_start_time`），不要把音频 URL 塞进 `input_urls`。
5. **禁止**在新 Skill 里写物理模型名——`generate_video` 会直接拒绝具体模型名（报错并提示改用 channel）；不要依赖下游 `list_models` 去猜 channel。

正文示例：

```markdown
- 文生图：`generate_image(prompt=..., model='t2i', name=..., entity_type='storyboard_images')`
- 图生视频（常规）：`generate_video(prompt=..., input_urls=[静帧], model='i2v', ...)`
- 参考生视频：`generate_video(..., model='ref2v', orientation='portrait')`
```

> 与 frontmatter 的 `model: uncensored`（第 6.5 节）区分：后者切换的是 **对话 LLM 档位**；本节的 channel 是 **生成工具** 的 `model=` 参数。

### 6.4 参数写作提示

在 Skill 正文或 references 里用「必须 / 可选 / 默认」写清业务默认值，例如：

```markdown
- 短剧默认 `orientation='portrait'`，除非用户明确要求横屏；分辨率无特殊要求时不传 `resolution`（走默认 `720P`）。
- 图片/视频 prompt 使用英文；对白文本保持用户语言。
- 图生视频：分镜静帧 URL 放入 `input_urls`（第 1 张为首帧）；`model='i2v'`（成人内容用 `i2v.nsfw`）。
- `mix_clips` 的 `clips[].video(s)/audio(s).url` 优先传本对话已生成资产的 asset_id（也支持 `s3://`/真实 https），禁止编造不存在的引用。
```

不要在 Skill 里复制整份工具 JSON Schema；只写本业务关心的字段与取值约定即可。模型侧仍能看到工具的 function calling schema。

> **尺寸参数：`orientation` + `resolution`（唯二暴露的尺寸参数）**：`generate_image` / `generate_video` 只接受两个尺寸相关枚举，不支持自由像素 `width`/`height`：
> - `orientation`：`landscape`（横屏 16:9）/ `portrait`（竖屏 9:16）/ `square`（方形 1:1，仅 `generate_image` 及部分视频模型支持，不支持的模型会自动归为横屏）
> - `resolution`：`480P` / `720P`（默认）/ `1080P` / `2K` / `4K`；具体模型的实际上限可能更低，超出会自动降到该模型支持的最高档位
>
> Skill 正文只需按业务约定 `orientation`（和必要时的 `resolution`），不要在正文里编造像素尺寸或旧的 `'1K'/'2K'/'4K'` 三档写法（图片已统一为上面的五档）。`resolution_model`（宽高比字符串，如 `'9:16'`）是历史遗留的高级覆盖参数，仅 `generate_video` 的 `ref2v` 等少数 channel 仍支持透传，新 Skill 优先用 `orientation` 表达方向。
>
> **精确比例覆盖：`aspect_ratio`（不常用，仅用户明确要求时才传）**：`orientation` 只覆盖三大类比例（16:9/9:16/1:1），若用户明确要求 `3:4`/`4:3` 等非标准比例，可传 `aspect_ratio='3:4'`（覆盖 `orientation`，其余仍按 `resolution` 档位对齐短边）。这是高级 escape hatch，绝大多数场景不需要传；Skill 正文不要把它当默认参数写死。

> **参数边界（平台钳制）**：`resolution` / `duration` 存在平台上限（`max_resolution` 面积上限、`max_duration` 时长上限；按模型/channel 云端配置 + 全局兜底），`batch_size` 锁死为 1（不开放单次多张生成）。Skill 正文**不要**写死超长时长或大于 1 的批量数——越界参数（含超出模型能力的 `resolution`）在工具执行前会被自动钳制/降档，并在工具返回的 `param_adjustments` 字段中说明。未指定 `orientation`/`resolution` 时，走云端 channel 配置或平台默认档位（`landscape` + `720P`）。

### 6.5 模型档位切换（frontmatter `model:` / `switch_model` 工具）

平台除标准模型（`standard`）外还接入了未审核模型（`uncensored`），用于处理成人/敏感等标准模型会拒答的内容。官方 Skill 与用户自建 Skill 均可使用。两种触发方式，可按需组合：

1. **Skill 声明**：当轮 "/" 显式调用该 skill、或运行中 `read_skill(name)` 命中该 skill 时，自动把后续 LLM 调用切到声明的档位，不需要模型自己判断：

   ```yaml
   ---
   name: nsfw-image
   description: ...
   model: uncensored
   ---
   ```

2. **模型自主判断**：任意 Skill 正文都可以写一句"识别到用户请求涉及成人/敏感内容、当前模型不适合直接处理时，调用 `switch_model(tier="uncensored", reason=...)`，切换后继续完成任务，不要直接拒绝"。`switch_model` 是常驻工具（同 `read_skill` / `write_todos`），无需写进 `allowed-tools`。

档位切换**只升不降**，且在整个会话内持续生效（下一轮直接从已升级的档位起步，不需要每轮重复调用，也不需要重新挂载 skill）。

`model` 字段在用户 skill 的 metadata 白名单内（与 `version` / `tags` 同类），保存时不会被剥离；能声明的档位仍受登记表限制（目前仅 `standard` / `uncensored`）。注意：`canvas` 等其余运行时字段仍仅官方 Skill 可设置。与第 6.3 节的生成 **channel**（工具参数 `model='i2v'`）不是同一概念。

---

## 7. 常驻工具

`read_skill` / `read_skill_file` / `write_todos` / `set_guidance` / `switch_model` **不必**写进 `allowed-tools`（写了也无妨）；编排器会始终注入（`set_guidance` 取决于 `suggested_questions`）。**例外**：7.4 节的 `memory_*` / `skill_kb_query` 不在此列，必须由 Skill 显式在 `allowed-tools` 中声明才可用，见该节说明。

### 7.1 `read_skill` / `read_skill_file`

- 相关时先 `read_skill(name)`，再按正文行动。
- 正文提到 `reference_files` 且需要细节时，再 `read_skill_file(name, path)`。
- **不要**在未读 Skill 的情况下猜测其步骤。

### 7.2 `write_todos`（多步进度）

整表替换（不是 merge），对齐 TodoWrite 契约：

```json
{
  "todos": [
    {"id": "script", "content": "编剧", "status": "in_progress"},
    {"id": "visual", "content": "视觉设计", "status": "pending"},
    {"id": "storyboard", "content": "分镜图", "status": "pending"}
  ]
}
```

规则：

- 每项：`content` 必填；`status` 为 `pending` | `in_progress` | `completed`；`id` 可选。
- **同时最多一条 `in_progress`**。
- 推进时再次调用并传入**完整列表**。
- 简单问答不必调用；空数组表示清空进度条。
- 最多 20 条。

在多阶段 Skill 的「协作原则」里明确要求模型使用本工具。

### 7.3 `set_guidance`（推荐操作按钮）

在输出**最终回复文字的同一轮**调用，给出下一步操作：

```json
{
  "suggested_questions": [
    {"text": "开始设计角色/场景视觉"},
    {"text": "再调整一下这场戏"}
  ]
}
```

也可用裸字符串（等价于 `{"text": "..."}`）。**条数不做产品层面的强制规定**——
工具本身只做纯工程安全兜底截断（防止异常输出打爆前端渲染），不代表条数上限
是产品规则；按当前场景给出合适数量即可，不必凑数或硬塞满某个数字，避免同质化
选项。

完整对象可含（客户端已支持以下全部字段）：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `text` | string | 是 | 按钮展示文字，含 emoji 也可 |
| `id` | string | 否 | 稳定标识，用于前端埋点/去重；同一会话内不应重复 |
| `icon` | string | 否 | 图标 key；不传/为 null 时前端用默认图标 |
| `action` | object | 否 | 缺省时等价于 `{"type": "send_message"}` |

`action` 按 `type` 取值展开：

| `action.type` | 行为 | 附加字段 |
|---|---|---|
| `send_message`（默认） | 在**当前会话**直接发送文本 | `content`（可选，缺省取外层 `text`） |
| `fill_input` | 填充到**当前会话**输入框，不自动发送 | `content`（必填，放入输入框的文字）；`replace`（可选 boolean，默认 `true`；`true`=覆盖现有内容，`false`=追加到末尾） |
| `new_conversation` | 打开**新会话**，可携带内容 | `content`（可选，不传则打开空白新会话）；`mode`（可选 `send`\|`prefill`，默认 `prefill`；`send`=进新会话后立即发送，`prefill`=仅放入新会话输入框）；`template_id`（可选，模板/路由标识，前端按此选模板或跳路由） |

写作要求：

- 推荐操作要与**当前阶段/产出**相关，避免泛泛的「还有什么可以帮你」。
- 连续推进、未在阶段边界停下时，可不调用。
- 调用本工具的那一轮不要再调用其他工具。
- 需要更完整的写作范例（每种 `action.type` 的具体用法）时参考
  `examples/skill_creator/skills/skill-creator/references/guidance-rules.md`。

### 7.4 长期记忆（`memory_*` / `skill_kb_query`，需在 `allowed-tools` 声明）

**与本节其余小节不同，这 5 个工具不是常驻工具**：只有在 `allowed-tools` 里声明了对应工具名的 Skill 挂载到会话时，模型才能调用它们。官方 Skill 声明不受用户工具天花板限制；用户自建 Skill 需要天花板放行这几个工具名（默认已放行，见第 8 节）。

两类数据源，**由两个独立工具分别检索，互不合并**：用户级长期记忆（跨会话保留偏好、事实、项目背景与人物关系）与 skill 级共享知识库（企业/运营方上传的产品文档/FAQ）。故意不做"自动合并成一次调用返回两类数据"的设计——让 LLM 通过**调哪个工具**而不是读结果里的某个 flag 来区分数据来源，避免把知识库内容误当成用户自己说的话（或反过来）。编排器会在系统提示中注入通用约定；需要**领域化读写策略**（如闲聊该记什么、客服该查哪个知识库）时，再写 Skill 正文补充（分别参考 `examples/skill_demo/skills/chat_memory/` 与 `examples/customer_service/skills/customer-service/`）。

| 工具 | 用途 | 参数 |
|---|---|---|
| `memory_whoami` | 读取身份摘要（会话开场的便宜 baseline） | 无参数 |
| `memory_query` | 按语义检索**用户自己的**个人记忆，不含任何 skill 共享知识库内容 | `query`（必填）；可选 `kind`、`limit` |
| `skill_kb_query` | 按语义检索**当前会话已挂载技能**的共享知识库，不含用户个人记忆；未挂载提供知识库的技能时返回空结果 | `query`（必填）；可选 `kind`、`limit` |
| `memory_store` | 写入跨会话有价值的事实/偏好（只写用户个人记忆，无法写共享知识库） | `content`（必填）；可选 `kind`、`tags`、`namespace`、`sensitivity` |
| `memory_forget` | 软删除一条用户个人记忆 | `memory_id`（来自 `memory_query` 返回的 `id`） |

**三层数据**：

| | 身份摘要（whoami） | 用户个人记忆（query / store / forget） | skill 共享知识库（skill_kb_query） |
|---|---|---|---|
| 存储 | 每用户一行 `summary` | 多条结构化条目 + 可选 embedding | 多条结构化条目（多为文档分片） |
| Agent | **只读** `memory_whoami` | 读写 `memory_query`/`store`/`forget` | **只读** `skill_kb_query` |
| 写入 | REST `PUT /memories/identity`；空摘要时用 `memory_store` 记事实即可 | Agent 侧 `memory_store` 或 REST `/api/v1/memories` | 仅 skill owner，通过文档上传或 REST `/api/v1/skills/{skill_id}/kb` |

`kind` 取值：`fact` / `preference` / `project` / `person` / `episode`。  
`sensitivity`：`normal`（默认） / `private`。  
`namespace`（仅 `memory_store` 可指定）默认 `default`，可按业务隔离；`memory_query` / `skill_kb_query` 均不接受也不需要 `namespace`，各自的检索范围已由工具本身固定。

**推荐用法（写进依赖记忆的 Skill 步骤）**：

1. **开场**：新对话或不清楚对方背景时先 `memory_whoami`；有摘要则自然融入语气/称呼，不要机械复读。
2. **答前检索**：涉及用户偏好、项目、人物、历史决策时先 `memory_query`；涉及产品知识库/FAQ/文档内容时改用 `skill_kb_query`；两者按问题类型选其一即可，不要混用或猜测。只依据返回的 `items`，没有命中就坦诚说没有，禁止编造。
3. **写入**：用户透露或确认了**跨会话仍有价值**的信息时立刻 `memory_store`；一条清晰陈述句即可。高度相似内容可能自动合并（`deduped=true`）。
4. **忘记/纠正**：「忘掉…」或发现过时 → 先 `memory_query` 取 `id`，再 `memory_forget`；以用户当场说法为准（仅适用于用户个人记忆，共享知识库的增删由 skill owner 通过 REST 管理）。

**该记 / 不该记**（仅 `memory_store`，即用户个人记忆）：

- **该记**：称呼与语气偏好、稳定兴趣/风格、长期项目设定、重要人物关系、用户明确要求记住的决策。
- **不该记**：一次性任务进度、临时草稿、工具中间结果、密码/密钥/验证码等敏感凭证、未经确认的猜测、与用户无关的百科常识。

**写 Skill 时的注意点**：

- 记忆工具**不是**常驻工具，需要哪个就在 `allowed-tools` 里声明哪个（如只需要个人记忆，不必声明 `skill_kb_query`）。
- 不要在正文假设「系统会自动记住」——必须通过工具读写。
- 召回后用自然语言引用（「上次你说更喜欢……」/「根据知识库……」），不要把原始 JSON / memory id 贴给用户。
- `memory_store` / `memory_query` / `skill_kb_query` 内部会调用 embedding；embedding 失败时会降级关键字检索，Skill 仍应按「无结果不编造」处理。

**REST 管理接口按数据归属严格分组，不共用一组路由**（与上面 Agent 侧两个独立工具的设计一致）：

| 数据归属 | REST 前缀 | 用途 |
|---|---|---|
| 用户个人记忆 | `/api/v1/memories`（`GET/POST` 列表创建、`DELETE` 清空全部、`GET/PUT/DELETE /{memory_id}`、`POST /query` 语义检索、`GET/PUT /identity`） | 用户查看/编辑/删除自己的记忆条目 |
| skill 共享知识库分片 | `/api/v1/skills/{skill_id}/kb`（`GET/POST /entries`、`PUT/DELETE /entries/{memory_id}`、`POST /query`） | skill owner 在文档导入（`kb-documents`）之外手工补充/修订/检索知识库分片 |

两组接口都要求 `X-User-Id`；skill KB 组额外校验当前用户是该 skill 的 owner，且更新/删除时会校验目标分片确实属于该 `skill_id` 的命名空间（同一个系统用户持有所有 skill 的共享知识库，仅按 owner 身份过滤不足以防止跨 skill 越权）。

### 7.5 `switch_model`（模型档位切换）

声明式工具：请求把后续 LLM 调用切到某个模型档位（`standard` / `uncensored`），本身无副作用，实际切换由编排器完成。用法、与 frontmatter `model:` 声明的关系、只升不降/跨轮粘性等细节见第 6.5 节「模型档位切换」，此处不重复。

---

## 8. 用户 Skill 限制（天花板）

官方 Skill 可声明更广的工具集；**用户自建 Skill** 的 `allowed-tools` 会与服务端天花板求交。默认天花板（`config/config.yaml` → `skills.user_authored.allowed_tools`）：

- `search_web`
- `generate_image`
- `generate_video`
- `generate_tts`
- `generate_music`
- `mix_clips`
- `list_models`
- `search_library`
- `get_library_item`
- `split_image`
- `recognize_image`
- `recognize_video`
- `transcribe_audio`
- `fetch_video_info`
- `download_video`
- `create_document`
- `update_document`
- `get_document`
- `memory_whoami`
- `memory_query`
- `skill_kb_query`
- `memory_store`
- `memory_forget`

`list_my_skills` / `read_my_skill` / `read_my_skill_file` / `write_skill_draft` / `write_skill_reference_file` / `publish_skill` / `bind_skill_preset_asset` / `unbind_skill_preset_asset` 这些 Skill 创作工具**不在天花板内、且永远不会被加入**：用户 Skill 无法声明它们，只有官方 Skill（如 `skill-creator`）能用（见第 9 节）。

同时还有数量限制（配置可调）：

- `max_body_chars`（默认 50000）
- `max_reference_files`（默认 15）
- `max_per_user`（默认 50）
- `skills.preset_assets.max_count`（默认 10）

为用户/市场编写 Skill 时，**不要**声明天花板之外的工具（会被过滤掉，模型侧也不可用）。

---

## 9. Skill 创作工具（skill-creator，仅官方 Skill 可声明）

Skill Agent 具备"在对话中帮用户创建/编辑/发布他自己的 Skill"的能力，由专用创作工具提供。**这些工具不在 `skills.user_authored.allowed_tools` 天花板内，只有官方 Skill 能在 `allowed-tools` 里声明它们**——否则用户 Skill 能再创建 Skill，绕开一切限额/权限控制。完整参考实现见 `examples/skill_creator/`（`skills/skill-creator/SKILL.md` + `references/skill-writing-guide.md` + `references/available-models.md`）。

| 工具 | 作用 |
|---|---|
| `list_my_skills` | 列出当前用户自建的全部 Skill（含未发布草稿），返回 `skill_id`/`name`/`display_name`/`description`/`enabled`/`has_draft`/`allowed_tools` |
| `read_my_skill` | 按 `skill_id` 读取某个自建 Skill 的完整内容（有草稿时优先返回草稿），还原为完整 SKILL.md 文本（`skill_md`）+ 引用文件**名列表**（不含全文）+ `preset_assets` |
| `read_my_skill_file` | 按 `skill_id` + `path` 读取草稿（无草稿则线上）中单个引用文件的全文；与 `read_skill_file` 同族但读的是编辑视图 |
| `write_skill_draft` | 把一份完整 SKILL.md 文本（+ 可选 `reference_files`）保存为草稿；`skill_id` 为空则新建，非空则覆盖既有 Skill 的草稿；**只写草稿，不影响线上版本**；不覆盖既有 `preset_assets`；正文/frontmatter 唯一写入口 |
| `write_skill_reference_file` | 新增/覆盖或删除草稿中单个引用文件（`content` 省略/`null` 即删除）；不影响正文与其余引用文件，与 `write_skill_draft` 的整表替换互补，适合单文件增删场景 |
| `publish_skill` | 把草稿发布为线上版本（`enabled=true`），进入用户 Skill 空间（含草稿中的 `preset_assets`） |
| `bind_skill_preset_asset` | 把本轮用户附件的 `asset_id` 绑到 skill 草稿预设清单（`key`/`label`）；资产会公开引用 |
| `unbind_skill_preset_asset` | 从草稿预设清单移除一项（不删底层 assets 行） |

### 9.1 前置条件

- 承载 Skill 的 workflow 必须是 **`skill_agent`**（见第 10 节）。这些创作工具靠 orchestrator 隐藏注入的 `_user_id` 做归属校验（LLM 不可见、不会主动传递，同 `read_skill` 的 `_scope` 注入机制）；`user_id` 缺失时调用会被拒绝并返回结构化错误。
- 只有官方 Skill（`owner_user_id IS NULL`）能声明这些工具；用户自建 Skill 的 `allowed-tools` 即使写了也会被服务端天花板过滤掉。

### 9.2 两段式草稿/发布

与官方 Skill 的 draft/publish 复用同一套 `skills.draft` JSONB 语义：

```
write_skill_draft(skill_md, reference_files?, skill_id?)
        ↓ 只写草稿，不影响线上版本；可反复调用直到用户满意
用户明确确认（正文必须要求：未经确认不得调用 publish_skill）
        ↓
publish_skill(skill_id)
        ↓ 草稿落主列 + enabled=true，进入用户空间（下一轮对话起可用）
```

`write_skill_draft` 返回 `{skill_id, name, warnings[], preview}`：`preview` 里的名称/描述/工具白名单要念给用户确认；`warnings` 列出因超出用户天花板（第 8 节）被裁掉的工具，正文必须要求如实告知，不能吞掉不提。限额校验（正文超长/引用文件过多/超过每用户 Skill 数上限）失败时返回结构化 `error`，按提示修正后重试。

只想增/改/删单个引用文件时不必走整份 `write_skill_draft`，用 `write_skill_reference_file(skill_id, path, content?)` 即可（同样只写草稿）：`content` 省略或为 `null` 表示删除该文件；`path` 不能是 `SKILL.md`（正文/frontmatter 只能经 `write_skill_draft`）。返回 `{skill_id, path, deleted, existed, reference_files}`；删除不存在的路径返回 `existed=false` 且不算错误，但也未做任何修改。

### 9.3 name 的 kebab-case 约束

模型生成的 SKILL.md frontmatter `name` 必须是 kebab-case（`xx-xx`，见第 3 节）。服务端会把它规范化：非 ASCII 字母数字字符（含中文、下划线、空格）一律折叠为连字符——若模型偷懒写中文或拼音，规范化后可能坍缩成一串没有语义的连字符甚至回退为 `skill`。因此 skill-creator 类 Skill 的正文/引用文件里必须明确要求：**`name` 用英文单词 + 连字符拟定**，中文可读名放 `display_name`；新建前建议先 `list_my_skills()` 检查是否与已有 Skill 撞名。

### 9.4 已知限制

- Skill 挂载集在每轮对话开始时解析一次；`publish_skill` 成功后**本轮不会立刻生效**，正文需告知用户"新 Skill 从下一轮对话起可用"。
- 用户 Skill 不写 `skill_revisions`（修订历史仅官方 Skill 归档），发布后没有历史版本可回滚，只能再次编辑草稿覆盖。
- `read_my_skill` / `read_my_skill_file` / `write_skill_draft` / `write_skill_reference_file` / `publish_skill` 均按 `(skill_id, owner_user_id)` 做归属校验，模型不能读取/修改/发布不属于当前用户的 Skill；越权调用返回结构化 `{"success": false, "error": ...}`，不是异常。
- `write_skill_reference_file` 与 `write_skill_draft` 都是"读草稿 → 内存合并 → 整体覆盖 `draft` JSONB"，两次并发调用会互相覆盖（后写者基于旧快照），无乐观锁；当前单会话交互场景下概率低，可接受。

---

## 10. orchestrator_config（可选）

`skill_agent` 类型 workflow 的编排配置很轻，**不是** Skill 正文的一部分。Skill 挂载一律按 `user_id` 动态解析（内置 + 我的 + 已安装 + `/` 强制挂载）；`skills` / `skill_scope` 若出现则忽略。示例见 `examples/assistant/orchestrator_config.yaml` / `examples/skill_demo/orchestrator_config.yaml`：

```yaml
orchestrator_name: skill_demo
role_description: "你是一个可以调用平台工具完成用户任务的智能助手。"

tools:                    # 不依赖任何 skill 也可直接调用的核心工具
  - list_models
  - search_library
  - get_library_item

max_iterations: 20
add_to_canvas: true
suggested_questions: true # 默认 true；关闭则模型不能用 set_guidance
timezone: UTC             # 可选，IANA 时区名；默认 UTC+0（全球用户），决定注入给模型的当前时间时区
```

> **当前时间**：每轮用户消息（HumanMessage 尾部）会自动附带一行当前时间（含时区与 UTC offset），模型可直接感知"现在几点"，无需调用工具。时间属于每轮易变信息，按 prefix-cache 约束**不会**出现在 system prompt 中；Skill 正文里需要按时间做判断时（如"今天/本周"），直接引用该行即可。

编写 **单个 Skill 包** 时通常只需关心 `SKILL.md` + `references/`；只有在创建/调整整个 `skill_agent` workflow 时才改上述 YAML。

---

## 11. 完整示例

### 11.1 单能力 Skill（简单）

见 `examples/skill_demo/skills/image_generation/SKILL.md`：

- `description` 描述用户意图（画图/海报/头像）
- `allowed-tools`: `list_models`、`generate_image`
- 正文：改写 prompt → 按模态写死 `model=<channel>`（如 `t2i` / `i2i`）→ 调用工具 → 简短回复
- 无 `references/`

同类：`examples/skill_demo/skills/web_research/SKILL.md`。

闲聊 / 跨会话记忆：`examples/skill_demo/skills/chat_memory/SKILL.md`（第 7.4 节）：

- `description` 覆盖「记住 / 回忆 / 忘记」与持续对话中的偏好/身份
- `allowed-tools` 必须声明用到的 `memory_*` 工具名（不再是常驻工具，不声明就调不到）
- 正文：whoami → query → store → forget，以及该记/不该记

### 11.2 多阶段 Skill（复杂）

见 `examples/drama_skills/`：

- 根 `SKILL.md`：触发描述、工具白名单、阶段表、协作原则（连续推进 / 局部修改 / todos / guidance）
- `references/*.md`：编剧、视觉、分镜图、分镜视频、配音、合成各阶段细节与 `entity_type` 约定

新增长流程 Skill 时，优先复制该目录的**信息架构**，再替换领域内容。

### 11.3 Skill 创作工具（skill-creator）

见 `examples/skill_creator/`（第 9 节）：

- `skills/skill-creator/SKILL.md`：`allowed-tools` 只声明 `list_my_skills` / `read_my_skill` / `write_skill_draft` / `publish_skill`；正文区分「新建」「修改既有」「查看」三条流程，强调发布前必须用户确认；涉及媒体生成时要求先读 `available-models.md` 并写死 **channel**
- `references/skill-writing-guide.md`：面向"帮用户写 Skill 的 Skill"的编写规范，含 kebab-case 命名约束、天花板内工具清单、**channel 选型**、产出前检查清单
- `references/available-models.md`：平台 channel 目录（权威）；起草时硬编码 channel，禁止物理模型名
- `orchestrator_config.yaml`：说明性配置，示范挂在 `skill_agent` 动态挂载 workflow 下

写"能创建 Skill 的 Skill"（元 Skill）时，优先复制该目录结构，替换成自己的业务规范文档。

---

## 12. AI 编写检查清单

写完或改完一个 Skill 后，逐项确认：

- [ ] 有合法 YAML frontmatter；`name`、`description` 非空
- [ ] `description` 是「用户意图触发条件」，不是功能广告或实现细节
- [ ] `allowed-tools` 只包含本 Skill 真正需要的工具，且在用户天花板内（若面向用户）
- [ ] 正文含「何时使用 / 步骤 / 注意事项」（或多阶段索引 + 协作原则）
- [ ] 步骤中的工具名与 `allowed-tools` 一致；关键参数（`name`、`entity_type`、`orientation`、生成步骤的 **`model=<channel>`** 等）有约定
- [ ] 涉及媒体生成时：已按第 6.3 节绑定正确 **channel**（对照 `available-models.md`；无物理模型名；图生视频 NSFW 优先 `i2v.nsfw`）
- [ ] 未引入 `data_schemas` / `operations` / 伪 JSON 状态协议
- [ ] 未依赖 Skill 包内 `scripts/`（不会被解析或执行）
- [ ] 长内容已拆到 `references/`，正文明确「按需 `read_skill_file`、不要一次全读」
- [ ] 多步流程要求使用 `write_todos`；阶段边界/完成时要求 `set_guidance`（若适用）
- [ ] 依赖跨会话记忆时：`allowed-tools` 已声明用到的 `memory_whoami` / `memory_query` / `memory_store` / `memory_forget`（不再常驻），并在步骤里写清调用时机与该记/不该记；依赖 skill 共享知识库时声明并使用 `skill_kb_query`，不要与 `memory_query` 混用（见 7.4）
- [ ] 要求失败如实反馈、禁止编造 URL、违规内容拒绝生成
- [ ] 有中间产物时已在 frontmatter `canvas:` 声明隐藏规则（`hidden_entity_types` / `hidden_tools`），或开启 `model_control` 并在正文写死哪些步骤传 `add_to_canvas=false`
- [ ] 涉及成人/敏感内容时：已在 frontmatter 声明 `model: uncensored`（LLM 档位），或在正文写清何时调用 `switch_model`（见 6.5）；与生成 channel（如 `i2v.nsfw`）按需同时约定；官方 / 用户 Skill 均可
- [ ] 最终回复要求自然语言概括，不粘贴长 URL
- [ ] 目录可被 `load_skill_from_directory` / zip 上传解析（`SKILL.md` 存在，引用路径正确）

---

## 附：常见误区

| 误区 | 正确做法 |
|---|---|
| 按旧 drama 配置写 `agents_config.yaml` | Skill Agent 只用 `SKILL.md` 包 |
| 把完整流程全塞进 body | 阶段细节放 `references/`，正文只留索引 |
| `description` 写「帮助用户创作」 | 写清具体意图与边界场景 |
| 在 Skill 里规定「输出必须是 JSON」 | 工具走原生 function calling；对用户用自然语言 |
| 假设有 `characters` 集合可 update | 用 Markdown 写设定，用画布 URL 引用已生成资产 |
| 忘记声明 `generate_image` 却在步骤里调用 | `allowed-tools` 与正文步骤保持一致 |
| 生成步骤硬编码物理模型名（`rm3.1-G`、`qwen-image`…） | 写稳定 **channel**（`i2v`、`t2i`…）；对照 `available-models.md`（见 6.3） |
| 用 `list_models` 现场猜模型代替 channel 目录 | 起草时以 `available-models.md` 为准；`list_models` 仅兜底 |
| 把 frontmatter `model: uncensored` 当成生成 channel | 前者是 LLM 档位（6.5）；生成用工具参数 `model='i2v.nsfw'` 等（6.3） |
| 阶段之间每次都问「是否继续」 | 默认连续推进；仅用户要求确认时停下 |
| 用户 Skill 里声明 `write_skill_draft` / `publish_skill` 等创作工具 | 仅官方 Skill 可声明，不在用户天花板内（见第 9 节），否则用户 Skill 可自我繁殖 |
| 假设系统会自动记住用户偏好 | 必须用 `memory_store` / `memory_query`；身份摘要靠 whoami（见 7.4） |
| 期望 `memory_query` 能查到 skill 知识库内容 | 用户记忆与共享知识库是两个独立工具，`memory_query` 只查个人记忆，知识库内容要用 `skill_kb_query`（见 7.4） |
| 用了 `memory_*` / `skill_kb_query` 却没写进 `allowed-tools` | 这 5 个工具不再常驻，必须显式声明才能被挂载调用（见 7.4） |
| `publish_skill` 成功后指望本轮就能用新 Skill | Skill 挂载集每轮开始时解析一次，新 Skill 下一轮对话起才生效（见 9.4） |
| skill-creator 类 Skill 里 `name` 允许用中文/下划线 | `name` 必须 kebab-case，非 ASCII 字符会被规范化坍缩，正文需强制要求英文+连字符（见 9.3） |
