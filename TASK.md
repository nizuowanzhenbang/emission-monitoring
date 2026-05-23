# 任务跟踪

## v1.0（已完成，2026-05-23）

### 后端
- [x] 5 角色用户体系（ADMIN/OPERATOR/ANALYST/SUPERVISOR/VIEWER）+ JWT
- [x] 7 张表：User / Unit / EmissionPoint / CemsDevice / EmissionReading / EmissionAlert / EmissionStandard / EmissionReport
- [x] 机组台账：4 燃料 + 4 状态 + 容量 MW + 投产日期
- [x] 排放口：5 类（STACK/PRE_DESULFUR/POST_DESULFUR/PRE_DENOX/POST_DENOX），可绑定标准
- [x] CEMS 仪表：4 状态机 + 日校跟踪 + 检定有效期
- [x] 排放标准：超低/特别排放/一般火电三档可配
- [x] 时序读数 `POST /api/readings/ingest`：批量 ≤1000 条，入库一次性算好折算值
- [x] 基准氧折算 `(21-6)/(21-O2)` + O2 ≥ 20.5 异常跳过
- [x] 严重度判定：NORMAL / GENERAL / SEVERE（≥1.5×）
- [x] 自动告警：同点合并 + 峰值/持续/指标累加 + 30min 持续升级 ESCALATED
- [x] 告警状态机：OPEN → ACKNOWLEDGED → HANDLING → RESOLVED → CLOSED
- [x] CEMS CALIBRATING/FAULT 时自动覆盖 reading validity
- [x] 报表生成：日/月/年/AD_HOC，自动算每个合规口 均值/峰值/可用率/超限分钟/合规率
- [x] 报表状态机：DRAFT → SUBMITTED → APPROVED
- [x] Dashboard：overview / realtime / trend-24h / alert-distribution / point-compliance
- [x] 角色拦截：require_operator / require_analyst / require_supervisor / require_write
- [x] seed_data：5 用户 + 2 机组 6 排放口 + 6 CEMS + 48h × 5min × 6 点位 ~ 3456 条读数 + 2 告警样例（一般已关闭 + 严重处置中）+ 1 月报草稿

### 前端
- [x] 登录页（青色主题）+ Layout + 6 个菜单
- [x] Dashboard：KPI 卡片 + ECharts 趋势图 + 合规率柱图
- [x] RealtimeBoard：合规口实时数字 + 限值红线 + 颜色告警
- [x] UnitList：机组 + 排放口列表
- [x] CemsList：CEMS 仪表表格
- [x] AlertList：告警分页 + 多筛选 + 确认/处置/解决/归档全流程按钮
- [x] ReportList：报表分页 + 生成 Modal + 详情 Drawer + 提交/审批
- [x] stores/auth + ROLE_LABEL + axios 拦截器

### 文档
- [x] README.md
- [x] CLAUDE.md
- [x] TASK.md
- [x] .gitignore + backend/.env.example

## v2.0（远期规划）

### 调度器
- [ ] APScheduler：每月 1 号自动 `generate` 上月 MONTHLY 报表（草稿态）
- [ ] 每天扫 CEMS 30 天可用率，跌破 95% 告警合规线
- [ ] 每小时算 24h / 7d / 30d 滚动合规率，存 Dashboard 缓存表

### 系统集成（与兄弟系统）
- [ ] plant-safety：SEVERE/ESCALATED 告警 → POST `/api/integration/hazards`（X-Integration-Secret 头）
- [ ] equipment-inspection：CEMS 状态变 `FAULT` → 推一条点检缺陷（CRITICAL 等级）
- [ ] coal-quality-monitor：消费"入厂煤高硫"事件 → Dashboard Banner 提示，预备 SO₂ 突升
- [ ] 共享 `INTEGRATION_SECRET` 已在 config 预留

### 实时推送
- [ ] WebSocket `/ws?token=`：SEVERE 告警 / CEMS FAULT / 合规率跌破阈值 三类事件
- [ ] 前端 useRealtime hook + notification 弹窗
- [ ] RealtimeBoard 改为 WS 驱动（替代当前 5s 轮询）

### 数据
- [ ] PostgreSQL 时序分区（按月）
- [ ] 流量加权均值（按 `flow × concentration`）替代算术均值，更接近"质量排放"
- [ ] 累计排放质量（kg）逐日落库，月报直接取（`emission_calc.calc_emission_mass` 已具备）

### 附件存储
- [ ] 处置照片字段 + S3/MinIO（复用 equipment-inspection v3 的 `app/utils/storage.py`）

### 报送对接
- [ ] GB13223 月度归档导出（XML / 国控/省控规定格式）
- [ ] 与"重污染天气应急响应"对接：橙红色预警时自动加严限值，限值随机切档

### 运维
- [ ] backend / frontend Dockerfile + docker-compose.yml + nginx.conf

## v3.0（更远）

- [ ] 多电厂多机组架构（按 tenant 隔离）
- [ ] AI 异常检测：基于历史时序的 LSTM 预警（先于超标）
- [ ] 与厂级 DCS 直连：实时取 CEMS 一次仪表数据
- [ ] 公众透明排放大屏（脱敏 + 限速 + 防爬虫）
