# AI Factory 模拟后端 (sim_backend)

## 项目概述

制造业运营模拟系统的后端服务。模拟引擎产出毫秒级事件数据，通过 Omniverse Kit 的 Data Bridge 驱动 3D 设备动画（WebRTC 串流到前端）。

**三个组件协作：**
- `sim_backend`（本项目）— FastAPI + SimPy，模拟计算 + 数据持久化 + API
- `~/Downloads/web` — React 前端（图表展示 + 接收 Kit WebRTC 视频流）
- `~/Downloads/fii-kit-app-template` — Omniverse Kit App（3D 渲染 + WebRTC 串流）

## 技术栈

- Python 3.11+ / FastAPI / SQLAlchemy 2.0 / SimPy 4 / PostgreSQL
- 虚拟环境：`.venv/`，激活：`source .venv/bin/activate`
- 启动：`uvicorn app.main:app --reload --port 8000`
- Swagger UI：`http://localhost:8000/docs`
- DB：`postgresql://postgres:postgres@localhost:5432/aifactory_simulation`

## 项目结构

```
app/
├── main.py              # FastAPI 入口，CORS 配置
├── config.py            # pydantic-settings，读 .env
├── database.py          # SQLAlchemy engine + SessionLocal + Base
├── models/              # SQLAlchemy ORM（39张表，完全对齐「数据模型与业务对象.md」）
│   ├── md.py            # md_ 基础数据（20张）：Factory→Stage→ProductionLine→Operation→Equipment→BOP→BOPProcess...
│   ├── sim.py           # sim_ 模拟方案（4张）：SimulationPlan, SoftConstraintConfig, ParameterOverride, AnomalyInjection
│   ├── biz.py           # biz_ 业务快照（6张）：WorkOrder, ProductionTask, MaterialSupply, InventorySnapshot...
│   ├── res.py           # res_ 模拟结果（5张）：SimulationResult, LineBalanceResult, SMTCapacityResult, SimulationStateSnapshot...
│   ├── ai.py            # ai_ AI分析（2张）：AIAnalysisResult, ImprovementSuggestion
│   └── tpl.py           # tpl_ 模板（2张）：ParameterTemplate, PlanVersion
├── schemas/             # Pydantic 请求/响应模型
│   ├── md.py            # FactoryOut, StageOut, ProductionLineOut, OperationOut, BOPOut...
│   ├── sim.py           # PlanCreate/Update/Out, ConstraintSet/Out, OverrideCreate/Out, TaskCreate/Out...
│   └── res.py           # SimulationResultOut, LineBalanceResultOut, SimEventOut, SimulationEventsOut
├── api/v1/              # API 路由
│   ├── router.py        # 汇总所有子路由
│   ├── master_data.py   # GET /factories, /stages, /lines, /operations, /bop, /products
│   ├── plans.py         # CRUD /plans + /constraints, /overrides, /tasks, /anomalies
│   └── simulation.py    # POST /plans/{id}/run, GET /result, /line-balance, /snapshots, /events
├── api/deps.py          # get_db() 依赖注入
└── engine/              # 模拟引擎
    ├── common.py        # CT解析（覆盖优先级：EQUIPMENT>OPERATION>LINE>GLOBAL>BOP标准CT）、ResolvedProcess、SimEvent
    ├── line_balance.py  # 静态线平衡：LBR = ΣCT / (瓶颈CT × 工站数)，Takt = 可用秒 / 需求量
    └── des_engine.py    # SimPy DES：产品按BOP顺序流过工站，毫秒级事件，支持设备故障/WIP容量/异常注入
```

## 数据库表命名规范

| 前缀 | 层级 | 说明 |
|------|------|------|
| md_ | 基础数据 | 来自主数据平台，模拟模块只读 |
| sim_ | 模拟方案 | 方案配置，本模块读写 |
| biz_ | 业务快照 | 来自 ERP/MES/WMS，导入后只读 |
| res_ | 模拟结果 | 引擎输出，只读 |
| ai_ | AI分析 | AI 分析结果 |
| tpl_ | 模板版本 | 参数模板 + 方案归档 |

## 关键业务逻辑

### 模拟方案状态机
```
DRAFT → READY → RUNNING → COMPLETED → ARCHIVED
```
- DRAFT/READY 可编辑；RUNNING 锁定输入；COMPLETED 可归档

### 两个模拟器
1. **LINE_BALANCE（静态线平衡）**：纯数学计算，无时间推进，前端即时展示
2. **PRODUCTION（DES 生产过程模拟）**：SimPy 离散事件仿真，产品流过 BOP 工序

### 软约束（全部默认关闭）
- EQUIPMENT_FAILURE：按 MTBF/MTTR 随机触发设备故障
- MATERIAL_SUPPLY：考虑物料库存
- WIP_CAPACITY：线边仓容量限制
- MANPOWER：人员-CT 关系
- AGV_TRANSPORT：AGV 运输约束

### events 端点（供 Omniverse Kit 消费）
`GET /api/v1/plans/{id}/result/events` 返回毫秒级事件流。
设备通过 `md_equipment.creator_binding_id` 字段存储 USD prim path，Kit 用它定位 3D 模型。

## 设计文档（权威参考）

- `~/Downloads/web/5. 数据模型与业务对象.md` — 39张表的完整定义（字段/类型/约束/枚举/一致性规则）
- `~/Downloads/web/simulation-prd.md` — 产品需求文档（模拟器逻辑/LBR公式/CT解析规则/软约束行为）
- `~/Downloads/web/副本P9 CT收集表_1222.xlsx` — 实际产线CT数据（自动包装线18工站 + Module主线32工站）

## 常用命令

```bash
# 启动开发服务器
uvicorn app.main:app --reload --port 8000

# 数据库迁移
alembic revision --autogenerate -m "描述"
alembic upgrade head

# 验证模型加载
python -c "from app.database import Base; import app.models; print(len(Base.metadata.tables))"  # 应输出 39
```

## TODO

- [ ] 前端 API 对接（web 项目）
- [ ] Kit 侧 SimulationPlaybackController service
