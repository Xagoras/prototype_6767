# 法律论证标注系统（原型）

面向中文裁判文书"裁判理由"部分的法律论证结构标注与图示系统。依据《中文裁判文书说理部分法律论证结构标注与图示指南（v1.1）》，支持命题标注（SF/GF/SM/GM 及子类型）、五种论证关系（支持 S / 反对 A / 组合 J / 匹配 M / 同一 I，含嵌套结构）、论证图示自动生成、多版本裁定与数据导出。

## 技术栈

- **前端**：React 19 + Vite + TypeScript + React Flow（@xyflow/react）+ dagre + Zustand
- **后端**：FastAPI + SQLAlchemy 2.0 + SQLite + JWT
- **测试**：pytest（后端 21 例）、vitest（前端 treeToGraph 13 例）

## 快速开始

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python -m app.seed --reset     # 重置并导入演示数据
python -m uvicorn app.main:app --port 8000
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173（/api 代理到 8000）
```

### 3. 演示账号（密码均为 demo123）

| 账号 | 角色 | 用途 |
|---|---|---|
| admin | 管理员 | 用户管理、指南导入 |
| teacher | 教师（任务创建者/标准答案/裁定者） | 建任务、标标准答案、裁定 |
| stu1 | 学生（含 3 处故意标注差异） | 独立标注 |
| stu2 | 学生（与标准答案一致） | 独立标注（演示"一致性通过"） |
| arbiter | 裁定员 | 冲突裁定 |

## 演示流程（E2E 走查）

1. **teacher 登录** → 工作台可见"演示任务：劳务合同纠纷标注（文书一）"
2. 任务详情 → 文档"文书一"（已自动提取裁判理由、已切割、已分配）
3. **teacher 进入标注**（标准答案 P1–P13 / R1–R10 已预置）→ 右栏可见两个论证子图（支持●、反对○、组合/匹配⊕、嵌套结构）→ 拖拽节点、导出 PNG/SVG
4. **stu1 登录** → "我的任务队列" → 查看比对 → 与最终版差异（P4 类型差异、缺 R5、R9 方向反）
5. **teacher** → 裁定页 → 三个版本并排 → 差异清单 → 生成最终版工作副本 → 编辑 → 提交定稿
6. **teacher** → 导出中心 → 导出 JSON / Excel → 文档锁定（再编辑返回 403）→ 导出记录

### 从零开始创建任务

1. `/guides` 导入标注指南（PDF/Word/纯文本，taxonomy 可校对）
2. `/tasks/new` 五步向导：基本信息 → 上传/粘贴文书 → 裁判理由提取校正（边界把手）→ 颗粒度切割确认（合并/拆分）→ 案例信息 + 分配
3. 标注员从工作台"下一条"进入标注 → 提交
4. 裁定者进入裁定 → 最终版 → 导出

## 核心规则实现（对照指南 v1.1）

- **颗粒度**（§2.3）：句号第一次切割、句内逗号/分号考查子句、双引号内容为基本单位、过渡语词（"因此，"等）并入后一要素
- **要素类型**（§4）：IS / Non / SF / GF / SM（SM、SM-C）/ GM（GM-L、GM-I、GM-U、GM-M、GM-O），由指南 taxonomy 驱动，不硬编码
- **关系与嵌套**（§5.2/5.3）：`S(J(p1,p2),p3)`、`M(J(p1,p2),p3)`、`J(M1,M2)`、`S(M(p1,p2),p3)`、`A(p3,S(p1,p2))`、多层嵌套自内而外逐层构造
- **图示**（§6）：矩形=命题（仅序号）；●=支持、○=反对、⊕=组合/匹配、框内"/"=同一；嵌套按层级独立成节点
- **一致性控制**（§8）：双人独立标注、颗粒度差异率 10% 阈值提示、多版本比对裁定

## 测试

```bash
cd backend && python -m pytest tests/ -q    # 21 例
cd frontend && npm test                      # 13 例（treeToGraph 六类嵌套）
```

## 目录结构

```
backend/
  app/
    api/          # auth/users/guides/tasks/documents/assignments/annotations/adjudication/exports
    models/       # 11 张表（users/guides/tasks/documents/assignments/
                  #   annotation_versions/propositions/relation_nodes/adjudications/exports）
    services/     # parser 解析+规范化 / extraction 裁判理由提取 / segmentation 颗粒度切割
                  # expr 关系校验与表达式 / diff 多版本比对 / export_json / export_excel
    seed.py       # 演示数据种子
  tests/          # pytest：extraction/segmentation/expr/flow
frontend/
  src/
    components/
      annotate/   # TextPanel 选区高亮 / PropositionList / LabelPicker / RelationBuilder
      graph/      # treeToGraph 关系树→图示（核心）/ ArgumentGraph / 自定义节点
      adjudicate/ # VersionColumn / DiffPanel
    pages/        # 登录/工作台/指南/任务创建/任务详情/标注/裁定/比对/导出中心
    stores/       # authStore / annotationStore（undo/redo + 防抖保存）
    utils/        # charIndex 码点选区 / layout dagre / expr
```

## 说明与取舍

- **序号不落库**：命题序号按原文字符偏移实时排序计算，删除/合并自动重排（Q8）
- **保存为全量替换**：undo/redo 快照恢复与防抖保存共用同一端点，规避操作逆运算复杂度
- **导出锁定**：任一导出记录产生即文档 OUTPUT，所有写端点 403（"导出后数据可查看但不可修改"）
- **图片导出**：前端 html-to-image 截取图示视口（后端不重复实现图元渲染，避免两套图元标准漂移）
- **压缩包下载**：原型以逐文件下载替代（需求 5.2 折衷）

---

# 开发者指南（二次修改 / Bug 修复）

> 使用 Claude Code 开发时请优先阅读仓库根目录的 **CLAUDE.md**（自动加载的项目速览）。
> 本节为人工阅读版，与 CLAUDE.md 内容一致。

## 架构与数据流

```
浏览器（React）
 ├─ TextPanel 选区 → charIndex.ts 计算码点偏移
 ├─ annotationStore（zustand）
 │    ├─ 本地模型：命题 seq / 关系 args 用 seq+下标
 │    ├─ undo/redo 快照栈（上限 50）+ 防抖保存（1.2s）
 │    └─ 保存 = 全量 PUT /versions/{id}/content（delete+insert）
 ├─ treeToGraph.ts：关系树 → React Flow 节点/边（六类嵌套）
 └─ ArgumentGraph：dagre 布局 + 手动位置优先 + 拖拽回写 graph_layout

后端（FastAPI + SQLite）
 ├─ parser.py：文件解析 + 文本规范化（服务器文本是唯一权威）
 ├─ extraction.py：裁判理由自动提取（judgment / guiding_case+ref_case 两套规则）
 ├─ segmentation.py：颗粒度切割（引号保护/句切/子句/过渡词归并）
 ├─ expr.py：关系树校验（元数/环/叶子）+ 形式化表达式
 ├─ diff.py：命题对齐（精确边界→IoU）+ 关系指纹差异 + 颗粒度差异率
 └─ 锁定：exports 记录产生 → document.status=OUTPUT → 写端点 403
```

## 按需求找文件（修改指引）

| 想改什么 | 改哪里 |
|---|---|
| 新增/调整标签（要素类型、子类型） | 指南 taxonomy（`backend/app/services/taxonomy.py` + `seed/guide_v1_1.json`），前端自动跟随，**勿在前端硬编码** |
| 新增关系类型 | taxonomy + `treeToGraph.ts` expand + 后端 `expr.py` 校验 + `RelationBuilder` REL_DEFS |
| 图示样式/图元 | `components/graph/nodes/*.tsx`（节点外观）+ `treeToGraph.ts`（结构） |
| 颗粒度切割规则 | `backend/app/services/segmentation.py`（+ `tests/test_segmentation.py`） |
| 裁判理由提取规则 | `backend/app/services/extraction.py`（+ `tests/test_extraction.py`） |
| 差异比对算法 | `backend/app/services/diff.py` |
| 导出格式 | `backend/app/services/export_json.py` / `export_excel.py` |
| 标注交互（选区/命题列表） | `TextPanel.tsx` / `PropositionList.tsx` / `annotationStore.ts` |
| 权限/流程控制 | `backend/app/auth.py`（依赖断言）+ 各 API 模块 |

## 关键约定（违反会产生隐蔽 bug）

1. **字符索引 = Unicode 码点**（JS `Array.from` / Python 切片天然一致），偏移相对 `reasoning_text`
2. **前端不二次规范化文本**——渲染与提交的文本一律来自服务器返回，否则偏移错位（保存时后端校验，不一致 409）
3. **关系 args 两套表示**：本地/保存 payload 用「seq + 数组下标」，服务器落库用「数据库主键」。
   前端 `relationsFromServer()` 负责转换——漏转会崩溃（历史 bug）
4. **保存后必须应用服务器响应**（全量替换后 id 已变）
5. **流程不可回退**：任务状态机单向流转（回退 409）；文档导出后锁定（写端点 403）

## 调试与排查

```bash
# API 调试：Swagger 文档（可直接调用接口）
http://localhost:8000/docs

# 重置数据（演示账号 demo123：admin/teacher/stu1/stu2/arbiter）
python -m app.seed --reset

# 快速验证一段逻辑（不需要起服务）
cd backend && python -c "from app.services.segmentation import segment_reasoning; print(segment_reasoning('测试。文本，切割。'))"

# 后端测试（21 例）/ 前端测试（13 例）
cd backend && python -m pytest tests/ -q
cd frontend && npm test
```

### 常见问题

| 现象 | 原因与处理 |
|---|---|
| 端口 8000/5173 被占用 | 用"启动.bat"会自愈清理；手动：`netstat -ano` 找 PID 后 `taskkill //F //PID <pid>`（Git Bash 双斜杠） |
| 标注页 RelationBuilder 白屏/报错 | 关系 args 转换遗漏——检查 `relationsFromServer` 调用点 |
| 保存命题返回 409 | 文本与服务器原文不一致（可能前端做了二次规范化），重新选区 |
| 测试失败找不到表 | TestClient 需 `with TestClient(app) as c:` 触发建表 |
| 中文文件名下载乱码 | 走 `exports.py` 的 RFC 5987 编码，勿改动 disposition 逻辑 |
| 一键启动 12 秒自动停止 | 浏览器页面未正常打开心跳未上报；确认页面已加载（心跳在 main.tsx 模块级） |

## 验证清单（改动后跑一遍）

1. `cd backend && python -m pytest tests/ -q` 全绿
2. `cd frontend && npx tsc -b && npm test` 全绿
3. `python -m app.seed --reset` 后按 README"演示流程"手工走查（teacher 标准答案 → stu1 比对 → 裁定 → 导出锁定）
