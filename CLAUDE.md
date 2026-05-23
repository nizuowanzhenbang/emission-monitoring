# Claude Code 项目规则

## 项目定位

发电厂环保排放在线监测系统。v1.0 聚焦"CEMS 时序读数 → 基准氧折算 → 超低限值判定 → 超标告警闭环 → 合规报表"。

与 [equipment-inspection](https://github.com/nizuowanzhenbang/equipment-inspection)（设备点检/缺陷）、[plant-safety](https://github.com/nizuowanzhenbang/plant-safety)（隐患排查）共用同一座电厂的机组数据，但流程独立。

## 技术栈约束

- 后端：FastAPI + SQLAlchemy + Pydantic v2，与 plant-safety / equipment-inspection 同款分层
- 前端：React 18 + TypeScript + Ant Design 5 + ECharts + Zustand + Vite
- 端口：后端 8004 / 前端 5176（避开 fuel-procurement 8000/5173、coal-yard 8001/5174、equipment-inspection 8003/5175）
- 数据库：SQLite（开发，`emission.db`）/ PostgreSQL（生产）

## 业务规则

### 排放限值（火电厂超低排放 GB13223-2011）

| 项 | 实测 → 折算到 6%O₂ 限值 (mg/Nm³) |
|---|---|
| SO₂ | 35 |
| NOx | 50 |
| 烟尘 | 10 |

可配（`app/config.py` 的 `LIMIT_SO2 / LIMIT_NOX / LIMIT_DUST / REFERENCE_O2`）。点位若绑定了其它 `EmissionStandard`，按标准里的限值算（覆盖默认）。

### 基准氧折算公式

```
C_折算 = C_实测 × (21 - 6) / (21 - O2_实测)
```

- `O2_实测 ∈ [0, 20.5)`，否则视为异常**不做折算**（返回 None）
- 折算字段（`so2_corrected / nox_corrected / dust_corrected`）在 `POST /api/readings/ingest` 写库时**一次性算好**，下游均值/告警直接读

### 数据有效性 `ReadingValidity`

| 值 | 含义 | 是否参与合规均值/超标判定 |
|---|---|---|
| `VALID` | 有效 | ✅ |
| `INVALID` | 无效（仪表故障/异常） | ❌ |
| `CALIBRATING` | 校准期 | ❌ |
| `SUBSTITUTED` | 替代值（规范填补） | ❌ |

`ingest` 时若 `cems_id` 对应仪表状态为 `CALIBRATING` 自动覆盖为 `CALIBRATING`，`FAULT` 覆盖为 `INVALID`。

### 严重度判定（仅 STACK 合规口）

| `severity` | 触发条件 |
|---|---|
| `NORMAL` | 三项折算值都 ≤ 限值 |
| `GENERAL` | 至少一项 > 限值，但都 < 1.5× |
| `SEVERE` | 至少一项 ≥ 1.5× 限值 |

仅 `is_compliance_point=True` 的点位会触发告警；非合规口（脱硫前/脱硫后）只记录、不告警。

### 告警状态机 `EmissionAlert`

```
OPEN → ACKNOWLEDGED → HANDLING → RESOLVED → CLOSED
```

- `OPEN`：自动建（首次超标）；同点位若已有未结告警则合并，更新 peak/duration/indicators
- `ACKNOWLEDGED`：operator 调 `/acknowledge`
- `HANDLING`：operator 调 `/handle`，可追加处置记录
- `RESOLVED`：operator 调 `/resolve`，必填 `resolution`
- `CLOSED`：supervisor 调 `/close` 归档
- 升级条件：`duration_minutes ≥ PERSIST_ESCALATE_MINUTES (30)` 自动升级到 `ESCALATED`；从 `GENERAL` 出现 `SEVERE` 段也升级
- 恢复达标：合并逻辑里若新读数 `severity==NORMAL`，会把未结告警的 `ended_at` 写当前 measured_at（不自动关闭，等人工处置）

### CEMS 状态

`ONLINE` ⇄ `OFFLINE` / `CALIBRATING` / `FAULT`。日校时间通过 `last_calibration_at` / `next_calibration_at` 跟踪。

### 报表状态机

```
DRAFT → SUBMITTED → APPROVED → ARCHIVED
```

- `DRAFT` 由 ANALYST（或 SUPERVISOR/ADMIN）调 `/api/reports/generate` 生成，自动算 `summary`（每个合规口的均值/峰值/可用率/超限分钟/合规率）
- `SUBMITTED` 由 ANALYST 提交
- `APPROVED` 由 SUPERVISOR 审批
- 类型：`DAILY / MONTHLY / YEARLY / AD_HOC`

### 编号规则

| 实体 | 格式 |
|---|---|
| 机组 | `UNIT-{N}` |
| 排放口 | `EP-U{N}-NNN` |
| CEMS | `CEMS-NNNN` |
| 告警 | `AL-YYYYMMDD-NNNN`（按"今日已建告警数"+1） |
| 报表 | `RPT-YYYYMM-NN` |

## 角色权限

| 角色 | 主要权限 |
|---|---|
| `ADMIN` | 全部 |
| `OPERATOR` | 上传读数（`/api/readings/ingest`）、告警 acknowledge/handle/resolve、CEMS 校准登记 |
| `ANALYST` | 生成 / 提交报表（`/api/reports/generate`, `/submit`） |
| `SUPERVISOR` | 报表 approve、告警归档（`/close`）、设备/排放口/标准管理 |
| `VIEWER` | 只读 |

后端通过 `deps.require_operator / require_analyst / require_supervisor / require_write` 拦截。

## 代码风格

- API 响应统一 `{code, message, data}`，使用 `utils.helpers.api_response`
- 分页用 `paginate_response`
- 中文 docstring + 中文 column comment
- 前端中文 locale + 中文 label
- Pydantic v2：`BaseModel + ConfigDict(from_attributes=True)`，`model_validate` 替代 `from_orm`
- SQLAlchemy 2.0 风格 ORM；查询用 `db.query(Model).filter(...).first()`

## 关键文件路径

| 关心啥 | 看哪 |
|---|---|
| 折算公式 | `backend/app/utils/emission_calc.py` |
| 限值/基准氧/严重倍数 | `backend/app/config.py` |
| 告警合并/升级逻辑 | `backend/app/api/readings.py:_ensure_alert` |
| 报表 summary 计算 | `backend/app/api/reports.py:_compute_summary` |
| Dashboard 五个查询 | `backend/app/api/dashboard.py` |
| 实时大屏组件 | `frontend/src/pages/RealtimeBoard.tsx` |

## 已知简化

- v1 没有 APScheduler（月报手动调 `/generate`；超标只在 ingest 触发，不主动巡检）
- v1 没有 WebSocket（v2 加严重告警实时推送）
- v1 没有真正的 S3 附件存储（处置记录无照片字段）
- v1 没有 GB13223 月度归档报送对接（仅站内闭环）

## v2.0 远期规划

- 内置调度器：每月 1 号自动出月报草稿；每天扫 CEMS 可用率合规线；每小时算 N 天滚动合规率
- 与 plant-safety 集成：SEVERE/ESCALATED 告警自动推一条"环保隐患"
- 与 equipment-inspection 集成：CEMS `FAULT` 状态自动建一条点检缺陷
- 与 coal-quality-monitor 集成：入厂煤硫分异常时推一条预警，前端 Banner 提示
- WebSocket 实时推送（前端 Realtime 大屏自动刷新而不是轮询）
- 附件存储抽象 + 处置照片
