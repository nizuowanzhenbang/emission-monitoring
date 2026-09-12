# 烟囱守夜人 · 发电厂环保排放在线监测系统

> 🔥 火电厂一旦 SO₂/NOx/烟尘超标，罚款按天计、严重的会被勒令停机。但 CEMS 每分钟上报一条、十几个排放口、365 × 24 不停转，人工根本盯不过来。

**这套系统帮你把烟囱"盯"起来**：把 CEMS 分钟级读数接进来，自动按 GB13223 折算到 6%O₂ 基准氧、对超低排放限值判定；任何一秒超标当场建告警、走五级闭环；月底一键出合规率 / 可用率 / 超限分钟的合规报表，所有处置过程都留痕可追溯。

> ⚠️ **免责声明**：本系统是 **厂内闭环管理工具**，不能替代国控点 CNEMC 联网上报，不能作为执法依据。

---

## ⚡ 30 秒看明白你能用它做什么

| 你是谁 | 它帮你做什么 |
|---|---|
| 🏢 环保部主任 | 大屏一眼看完今天的合规率、未结告警、CEMS 在线率 |
| 👷 运行人员 | 超标当场弹告警，按提示确认 → 处置 → 恢复达标，全程留痕 |
| 📈 数据分析 | 月底点一下"生成报表"，平均值/峰值/超限分钟/合规率自动算好 |
| 🛡️ 监督员 | 报表审批 + 告警归档，谁批的、什么时候批的可追溯 |

---

## ✨ 核心场景

### 🖥️ 实时大屏：六个排放口同框，限值红线压在曲线上
每个合规上报点（烟囱出口）显示最新折算 SO₂ / NOx / 烟尘 vs 超低限值（**35 / 50 / 10 mg/Nm³**），红线一过当场闪烁。

### 🚨 超标告警闭环：从"出事"到"归档"全链路
- 同一点位重复超标自动合并，累计持续时间，不刷屏
- 持续 ≥ 30 分钟自动升级 `ESCALATED`，强制监督员介入
- 严重度按 1.5 × 限值划线，分 `NORMAL` / `GENERAL` / `SEVERE`
- 状态机：`OPEN → ACKNOWLEDGED → HANDLING → RESOLVED → CLOSED`

### 📊 一键合规报表
日 / 月 / 年 / 临时四种类型，每个合规口自动算：
- 折算后**均值 / 峰值**
- **CEMS 可用率**（监管合规线 95%）
- **超限分钟数 + 合规率**

> 💡 **为什么要"折算"？**
> 排放浓度是会"骗人"的——烟气多稀释一点，浓度数字就下来了，但污染物总量并没减少。
> 所以 GB13223 规定：所有浓度都要折算到 6% 基准氧的"等效浓度"。公式：
> `C折 = C实测 × (21 - 6) / (21 - O₂实测)`
> 本系统在数据入库时**一次性算好折算值**，后续告警 / 均值 / 报表都直接读，不用每次重算。

---

## 🚀 快速开始

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

## 🔐 默认账户

| 用户名 | 密码 | 角色 | 主要权限 |
|---|---|---|---|
| `admin` | `admin123` | 环保部主任 | 全部 |
| `operator` | `operator123` | 运行人员 | 上传读数、确认/处置告警 |
| `analyst` | `analyst123` | 数据分析 | 生成/提交报表 |
| `supervisor` | `supervisor123` | 监督员 | 告警归档、报表审批 |
| `viewer` | `viewer123` | 只读 | 仅查看 |

> 🔒 生产部署请务必删掉 seed 用户、改强密码、关掉 `--reload`。

---

## 📋 业务规则速查

| 项 | 阈值 |
|---|---|
| 基准氧（火电） | 6.0% |
| 超低限值 SO₂ / NOx / 烟尘 | 35 / 50 / 10 mg/Nm³（折算后） |
| 严重超标倍数 | ≥ 1.5 × 限值 |
| 持续升级阈值 | 30 min |
| CEMS 月在线率合规线 | 95% |
| O₂ 异常阈值 | ≥ 20.5% 不折算 |

排放口分 5 类：`STACK`（烟囱出口，合规上报）/ `PRE_DESULFUR` / `POST_DESULFUR` / `PRE_DENOX` / `POST_DENOX`。**只有 STACK 触发告警**，其它点位只记录、用于对比脱硫脱硝效果。

---

## 🛠️ 技术栈

| 层 | 选型 |
|---|---|
| 后端 | FastAPI · SQLAlchemy · Pydantic v2 · python-jose · passlib |
| 前端 | React 18 · TypeScript · Ant Design 5 · ECharts · Zustand · Vite |
| 数据 | SQLite（开发）/ PostgreSQL（生产） |
| 端口 | 后端 `8004` / 前端 `5176` |

## 📁 目录结构

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

---

## 🔗 智慧发电厂全家桶中的位置

本项目是 [smart-power-plant](https://github.com/nizuowanzhenbang/smart-power-plant) 七大子系统中的"环保排放"模块，与下列兄弟系统共用同一座电厂的机组数据，但流程独立：

| 系统 | 端口 | 关系 |
|---|---|---|
| [equipment-inspection](https://github.com/nizuowanzhenbang/equipment-inspection) | 8003 / 5175 | 共享设备台账；未来 CEMS `FAULT` 自动生成设备缺陷工单 |
| [plant-safety](https://github.com/nizuowanzhenbang/plant-safety) | 8000 / 5173 | 严重超标告警 → 推送环保隐患（v2 规划） |
| [coal-quality-monitor](https://github.com/nizuowanzhenbang/coal-quality-monitor) | – | 入厂煤硫分异常 → 前端 Banner 预警 SO₂ 突升（v2 规划） |

> 🧩 `app/config.py` 已预留 `INTEGRATION_SECRET / SAFETY_SYSTEM_URL / INSPECTION_SYSTEM_URL`，v2 版本会把这三个系统真正打通。

---

## 🚧 已知简化（v1.0）

- 没有 APScheduler（v1 只有触发式告警；v2 加月报自动出 + CEMS 可用率扫描）
- 没有 WebSocket（v2 加严重超标实时推送）
- 没有真正的 GB13223 月度归档报送（仅站内闭环）
- 没有照片附件实际存储（v2 加 S3/MinIO）

## 📜 License

私有项目，未开源。


## 持续维护

[开发与验收说明](docs/MAINTENANCE.md)：自动检查、回归测试与演示边界。
