import { useEffect, useState } from 'react'
import {
  Card, Table, Tag, Button, Space, Select, Modal, Form, Input, message, Typography,
} from 'antd'
import { AlertOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { alertApi } from '../api'
import { useAuthStore, canOperate, canSupervise } from '../stores/auth'
import type { EmissionAlert, AlertStatus, AlertSeverity } from '../types'
import { ALERT_STATUS_LABEL, ALERT_SEVERITY_LABEL } from '../types'

const { Text } = Typography

export default function AlertList() {
  const role = useAuthStore((s) => s.role)
  const operable = canOperate(role)
  const supervisor = canSupervise(role)

  const [rows, setRows] = useState<EmissionAlert[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState<{ status?: AlertStatus; severity?: AlertSeverity }>({})

  const [handleOpen, setHandleOpen] = useState(false)
  const [resolveOpen, setResolveOpen] = useState(false)
  const [current, setCurrent] = useState<EmissionAlert | null>(null)
  const [handleForm] = Form.useForm()
  const [resolveForm] = Form.useForm()

  const load = () => {
    setLoading(true)
    alertApi.list({ page, page_size: 15, ...filters })
      .then((r) => { setRows(r.data.items); setTotal(r.data.total) })
      .finally(() => setLoading(false))
  }
  useEffect(load, [page, filters])

  const sevTag = (s: AlertSeverity) =>
    <Tag color={s === 'ESCALATED' ? 'magenta' : s === 'SEVERE' ? 'red' : 'orange'}>{ALERT_SEVERITY_LABEL[s]}</Tag>

  const statusTag = (s: AlertStatus) => {
    const c = s === 'CLOSED' || s === 'RESOLVED' ? 'green' :
      s === 'HANDLING' ? 'blue' : s === 'ACKNOWLEDGED' ? 'cyan' : 'red'
    return <Tag color={c}>{ALERT_STATUS_LABEL[s]}</Tag>
  }

  const onHandle = async () => {
    const v = await handleForm.validateFields()
    await alertApi.handle(current!.id, v.handle_notes, v.resolution)
    message.success('已记录处置')
    setHandleOpen(false); handleForm.resetFields(); load()
  }

  const onResolve = async () => {
    const v = await resolveForm.validateFields()
    await alertApi.resolve(current!.id, v.resolution)
    message.success('已标记解决')
    setResolveOpen(false); resolveForm.resetFields(); load()
  }

  return (
    <Card title={<Space><AlertOutlined />超标告警</Space>}
      extra={
        <Space>
          <Select<AlertStatus | undefined>
            placeholder="状态" allowClear style={{ width: 130 }} value={filters.status}
            onChange={(v) => { setPage(1); setFilters({ ...filters, status: v }) }}
            options={Object.entries(ALERT_STATUS_LABEL).map(([k, v]) => ({ label: v, value: k }))}
          />
          <Select<AlertSeverity | undefined>
            placeholder="等级" allowClear style={{ width: 110 }} value={filters.severity}
            onChange={(v) => { setPage(1); setFilters({ ...filters, severity: v }) }}
            options={Object.entries(ALERT_SEVERITY_LABEL).map(([k, v]) => ({ label: v, value: k }))}
          />
          <Button icon={<ReloadOutlined />} onClick={load} />
        </Space>
      }
    >
      <Table
        rowKey="id" loading={loading} dataSource={rows}
        pagination={{ current: page, pageSize: 15, total, onChange: setPage }}
        columns={[
          { title: '告警号', dataIndex: 'alert_no', width: 170 },
          { title: '机组/排放口', render: (_: any, r: EmissionAlert) =>
            <><Text>{r.unit_name}</Text>{' '}<Text type="secondary">{r.point_code}</Text></> },
          { title: '超标指标', dataIndex: 'indicators', width: 130 },
          { title: '峰值', width: 200, render: (_: any, r: EmissionAlert) =>
            <Space size="small">
              {r.peak_so2 ? <Tag>SO₂ {r.peak_so2.toFixed(1)}</Tag> : null}
              {r.peak_nox ? <Tag>NOx {r.peak_nox.toFixed(1)}</Tag> : null}
              {r.peak_dust ? <Tag>烟尘 {r.peak_dust.toFixed(1)}</Tag> : null}
            </Space> },
          { title: '等级', dataIndex: 'severity', width: 90, render: (v) => sevTag(v) },
          { title: '状态', dataIndex: 'status', width: 110, render: (v) => statusTag(v) },
          { title: '开始时间', dataIndex: 'started_at', width: 150, render: (v) => dayjs(v).format('MM-DD HH:mm') },
          { title: '持续(分)', dataIndex: 'duration_minutes', width: 80 },
          {
            title: '操作', width: 240, fixed: 'right' as const,
            render: (_: any, r: EmissionAlert) => (
              <Space size="small" wrap>
                {operable && r.status === 'OPEN' && (
                  <Button size="small" onClick={async () => { await alertApi.acknowledge(r.id); message.success('已确认'); load() }}>确认</Button>
                )}
                {operable && (r.status === 'OPEN' || r.status === 'ACKNOWLEDGED' || r.status === 'HANDLING') && (
                  <Button size="small" onClick={() => { setCurrent(r); setHandleOpen(true) }}>处置</Button>
                )}
                {operable && (r.status === 'HANDLING' || r.status === 'ACKNOWLEDGED') && (
                  <Button size="small" type="primary" onClick={() => { setCurrent(r); setResolveOpen(true) }}>标记解决</Button>
                )}
                {supervisor && r.status === 'RESOLVED' && (
                  <Button size="small" type="primary" onClick={async () => { await alertApi.close(r.id); message.success('已归档'); load() }}>归档</Button>
                )}
              </Space>
            ),
          },
        ]}
        scroll={{ x: 1500 }}
      />

      <Modal title="处置记录" open={handleOpen} onOk={onHandle} onCancel={() => setHandleOpen(false)}>
        <Form form={handleForm} layout="vertical">
          <Form.Item name="handle_notes" label="处置措施" rules={[{ required: true }]}>
            <Input.TextArea rows={3} placeholder="例：调大石灰石浆液循环、检查脱硝喷氨阀" />
          </Form.Item>
          <Form.Item name="resolution" label="原因分析（可选）"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="标记解决" open={resolveOpen} onOk={onResolve} onCancel={() => setResolveOpen(false)}>
        <Form form={resolveForm} layout="vertical">
          <Form.Item name="resolution" label="解决结果与整改" rules={[{ required: true }]}>
            <Input.TextArea rows={4} placeholder="说明根因 + 整改结果" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
