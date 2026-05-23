# 发电厂环保排放在线监测系统

> CEMS 连续监测 + 基准氧折算 + 超标告警闭环 + 合规报表，适配燃煤机组**超低排放**（GB13223-2011）。

智慧发电厂 6 子系统中的"环保排放"模块，与 [equipment-inspection](https://github.com/nizuowanzhenbang/equipment-inspection)、[plant-safety](https://github.com/nizuowanzhenbang/plant-safety) 共享同一座电厂的设备/机组数据，但流程独立。

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | FastAPI · SQLAlchemy · Pydantic v2 · python-jose · passlib |
| 前端 | React 18 · TypeScript · Ant Design 5 · ECharts · Zustand · Vite |
| 数据 | SQLite（开发）/ PostgreSQL（生产） |
| 端口 | 后端 `8004` / 前端 `5176`（避开兄弟系统 8000/8001/8003 与 5173/5174/5175） |

## 快速开始

```bash
# 后端
cd backend
pip install -r requirements.txt
python seed_data.py                  # 初始化：5 用户 + 2 机组 6 排放口 + 6 CEMS + 48h 读数 + 2 告警 + 1 月报草稿
uvicorn app.main:app --reload --port 8004

# 前端
cd frontend
npm install
npm run dev                          # http://localhost:5176
```

打开 http://localhost:5176 → 用 `admin / admin123` 登录。

## 默认账户

| 用户名 | 密码 | 角色 | 主要权限 |
|---|---|---|---|
| `admin` | `admin123` | 环保部主任 | 全部 |
| `operator` | `operator123` | 运行人员 | 上传读数、确认/处置告警 |
| `analyst` | `analyst123` | 数据分析 | 生成/提交报表 |
| `supervisor` | `supervisor123` | 监督员 | 告警归档、报表审批 |
| `viewer` | `viewer123` | 只读 | 仅查看 |

## 业务能力（v1.0）

### 1. 机组 & 排放口台账
- 机组：编号 / 容量 MW / 燃料类型 / 投产日期 / 状态（RUNNING/STANDBY/OUTAGE/DECOMMISSIONED）
- 排放口分 5 类：`STACK`（烟囱出口，合规上报）/ `PRE_DESULFUR` / `POST_DESULFUR` / `PRE_DENOX` / `POST_DENOX`
- 每个点位绑定一份排放标准（默认"超低排放 2014"）

### 2. CEMS 仪表
- 状态机：`ONLINE` / `OFFLINE` / `CALIBRATING` / `FAULT`
- 日校 + 检定有效期跟踪
- CEMS 在 `CALIBRATING` 时入库读数自动标 `CALIBRATING`；`FAULT` 时标 `INVALID`

### 3. 时序读数（分钟级）
- `POST /api/readings/ingest` 批量摄取（≤1000 条/批）
- 入库时**一次性算好折算值**：`C折 = C实测 × (21 - 6) / (21 - O2实测)`（O2≥20.5 视为异常不折算）
- 每条标 `severity ∈ {NORMAL, GENERAL, SEVERE}` + `exceeded` 指标列表
- 仅 `VALID` 数据参与超标判定；仅合规上报口（`is_compliance_point=true`，即 STACK）触发告警

### 4. 超标告警闭环
- 自动建告警：同点位若已有 `OPEN/ACKNOWLEDGED/HANDLING` 未结告警则合并（更新峰值 + 持续分钟），否则新建
- 持续 ≥ `30min` 自动升级为 `ESCALATED`
- 严重度：超限 ≥1.5× 即 `SEVERE`
- 状态机：`OPEN → ACKNOWLEDGED → HANDLING → RESOLVED → CLOSED`（监督员归档）
- 恢复达标自动写 `ended_at`

### 5. 合规报表
- 日 / 月 / 年 / 临时四种类型
- 自动计算：每个合规上报口的 平均/峰值 SO₂/NOx/烟尘、可用率、超限分钟、合规率
- 状态机：`DRAFT → SUBMITTED → APPROVED → ARCHIVED`，DRAFT 由分析员生成，APPROVED 由监督员审批

### 6. Dashboard
- 概览 KPI：CEMS 在线/故障数、今日/未结/严重未结告警、30 天合规率、30 天 CEMS 可用率（合规线 95%）
- 实时大屏：每个合规口最新值 + 限值红线
- 24h 趋势（折算 SO₂/NOx/烟尘小时均值）
- 告警分布（按等级/状态）
- 各排放口合规率柱图

## 业务规则速查

| 项 | 阈值 |
|---|---|
| 基准氧（火电） | 6.0% |
| 超低限值 SO₂ / NOx / 烟尘 | 35 / 50 / 10 mg/Nm³（折算后） |
| 严重超标倍数 | ≥ 1.5 × 限值 |
| 持续升级阈值 | 30 min |
| CEMS 月在线率合规线 | 95% |
| O₂ 异常阈值 | ≥ 20.5% 不折算 |

## 目录结构

```
emission-monitoring/
├── backend/
│   ├── app/
│   │   ├── api/          # auth/units/cems/readings/alerts/standards/reports/dashboard
│   │   ├── models/       # user/unit/cems/reading/alert/standard/report
│   │   ├── schemas/      # Pydantic v2 入参/出参
│   │   ├── utils/        # emission_calc + helpers
│   │   ├── config.py     # 限值/基准氧/集成密钥
│   │   ├── database.py
│   │   └── main.py
│   ├── seed_data.py
│   └── requirements.txt
└── frontend/
    └── src/
        ├── pages/        # Login/Dashboard/RealtimeBoard/UnitList/CemsList/AlertList/ReportList
        ├── components/   # Layout
        ├── api/          # axios 实例 + 各模块 API
        ├── stores/auth   # zustand 持久化 token
        └── types/
```

## 与兄弟系统的关系

| 系统 | 端口 | 关系 |
|---|---|---|
| [equipment-inspection](https://github.com/nizuowanzhenbang/equipment-inspection) | 8003 / 5175 | 共享设备台账；未来 CEMS 故障可生成设备缺陷工单 |
| [plant-safety](https://github.com/nizuowanzhenbang/plant-safety) | 8000 / 5173 | 严重超标告警 → 推送环保隐患（v2 规划） |
| [coal-quality-monitor](https://github.com/nizuowanzhenbang/coal-quality-monitor) | – | 入厂煤质硫分异常 → 预警 SO₂ 突升（v2 规划） |
| [smart-power-plant](https://github.com/nizuowanzhenbang/smart-power-plant) | – | 总览门户，6 大子系统入口 |

`app/config.py` 已预留 `INTEGRATION_SECRET / SAFETY_SYSTEM_URL / INSPECTION_SYSTEM_URL` 用于 v2 联动。

## 已知简化

- 没有 APScheduler（v1 只有触发式告警；v2 加月报自动出 + CEMS 可用率扫描）
- 没有 WebSocket（v2 加严重超标实时推送）
- 没有真正的 GB13223 月度归档报送（仅站内闭环）
- 没有照片附件实际存储（v2 加 S3/MinIO）

## License

私有项目，未开源。
