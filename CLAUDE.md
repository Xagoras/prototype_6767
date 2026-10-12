# CLAUDE.md — 项目速览（供 Claude Code 快速进入工作状态）

法律论证标注系统原型：对中文裁判文书"裁判理由"做法律论证结构标注与图示。
依据《中文裁判文书说理部分法律论证结构标注与图示指南 v1.1》（用户需求材料之二，
本仓库未含原始文档）。

## 技术栈与结构

- **后端** `backend/`：FastAPI + SQLAlchemy 2.0 + SQLite（`backend/data/app.db`）
  - `app/api/` 9 个路由模块：auth/users/guides/tasks/documents/assignments/annotations/adjudication/exports
  - `app/models/` 11 张表（见 README 目录结构节）
  - `app/services/`：parser（文件解析+文本规范化）、extraction（裁判理由提取）、
    segmentation（颗粒度切割）、expr（关系校验+表达式）、diff（多版本比对）、
    export_json / export_excel、guards（锁定守卫）、taxonomy（默认标签体系）
  - `app/seed.py` 演示数据种子；`seed/` 指南 v1.1 JSON 与文书一 txt
- **前端** `frontend/`：React 19 + Vite + TS + Zustand + React Flow（@xyflow/react）+ dagre
  - `src/components/graph/treeToGraph.ts` 关系树→图示转换（核心纯函数，六类嵌套）
  - `src/stores/annotationStore.ts` 标注状态（undo/redo 快照 + 防抖保存）
  - `src/utils/charIndex.ts` 选区码点偏移计算
  - `src/pages/` 9 个页面；`src/components/` annotate/graph/adjudicate/common 四组

## 常用命令（Windows，Git Bash）

```bash
# 一键启动（启动前后端+开浏览器，关网页自动停服务）
./启动.bat            # 或：python start_manager.py

# 后端
cd backend && pip install -r requirements.txt
python -m app.seed --reset          # 重置数据库+演示数据（演示账号密码 demo123）
python -m uvicorn app.main:app --port 8000
python -m pytest tests/ -q          # 21 例测试
# API 文档：http://localhost:8000/docs

# 前端
cd frontend && npm install
npm run dev                          # http://localhost:5173（/api 代理到 8000）
npm test                             # vitest 13 例（treeToGraph 六类嵌套）
npx tsc -b                           # 编译检查
```

## 关键设计约定（修改代码前必读，违反会导致隐蔽 bug）

1. **字符索引 = Unicode 码点**：前端 `Array.from` 计数、Python `str[start:end]` 切片天然一致。
   选区/命题偏移（char_start/char_end）相对 `documents.reasoning_text`。
2. **服务器文本是唯一权威**：文本规范化只在后端 parser.py 做，前端永远渲染服务器返回文本，
   不二次规范化，否则偏移错位。保存命题时后端校验 `reasoning_text[start:end] == text`，不一致 409。
3. **命题序号不落库**：按 char_start 排序实时计算（后端 `_version_out`、前端 `renumber()`）。
   删除/合并自动重排，seq 变化时关系 args 需重映射（见 annotationStore deleteProp/mergeProps）。
4. **关系 args 两套表示**：
   - 保存 payload / 前端本地：`{kind:"P",id:seq}` 与 `{kind:"R",id:数组下标}`
   - 服务器落库/返回：`{kind:"P"|"R",id:数据库主键}`
   - 转换函数：前端 `relationsFromServer()`（annotationStore.ts）；后端落库转换在
     `annotations.py save_content`。**漏转会导致 RelationBuilder 表达式递归越界崩溃**（曾出过此 bug）。
5. **保存 = 全量替换**（delete+insert），PUT `/versions/{id}/content`；undo/redo 快照恢复
   与防抖保存（1.2s）共用此端点。响应后必须用服务器返回内容更新 store（id 已变）。
6. **标签体系不硬编码**：标注按钮由指南 taxonomy JSON 动态生成（LabelPicker/TextPanel 浮动工具条）。
   改标签体系只改指南 taxonomy（seed 里 `taxonomy.py default_taxonomy()` + `seed/guide_v1_1.json`），
   不要在前端写死类型列表。
7. **流程单向与锁定**：任务状态机 CREATED→ANNOTATING→ADJUDICATING→OUTPUT（回退 409）；
   文档任一导出记录 → OUTPUT 锁定，所有写端点经 `guards.assert_not_locked` 返回 403。
8. **多角色版本**：同一文档每人一个版本行（annotation_versions，unique(document,user,kind)），
   kind：normal（标注员）/reference（标准答案）/final（裁定）。多角色取版本类型优先级
   annotator > reference（`_version_kind_for`）。

## 易错点 / 历史 bug

- bcrypt 与 passlib 不兼容 → 已改用 bcrypt 库直接调用（auth.py），不要引回 passlib
- Git Bash 下 `taskkill /F` 会被路径转换 → 用 `taskkill //F //PID`
- 中文文件名 HTTP 下载头需 RFC 5987 编码（exports.py `disposition()`）
- PDF 提取的中文间空格由 parser.py 规范化清除；测试文本定位用
  `re.search(r"\s*".join(re.escape(ch) for ch in txt), text)`（忽略空白）
- FastAPI TestClient 需 `with TestClient(app)` 才触发建表；测试用 `DB_URL` 环境变量隔离数据库
- 心跳机制：前端 main.tsx 模块级 fetch `/api/heartbeat`（3s），start_manager.py 超时 12s
  自动关停服务——不要移回 React 组件内（React 崩溃会中断心跳）

## 验证改动

- 后端：`cd backend && python -m pytest tests/ -q`（当前 21 例全过）
- 前端：`cd frontend && npx tsc -b && npm test`（当前 13 例全过）
- 端到端：`python -m app.seed --reset` 后用演示账号走 README"演示流程"；
  或 TestClient 脚本模拟（参考 tests/test_flow.py 的四阶段流程）

## Git / GitHub

- 远程：`https://github.com/Xagoras/prototype_6767`（SSH 不可用，走 HTTPS；`gh` 已登录）
- 提交信息中文，格式：`M# 主题：内容`；每个里程碑/功能完成即提交推送
