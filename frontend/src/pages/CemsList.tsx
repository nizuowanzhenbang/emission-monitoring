import { useEffect, useState } from 'react'
import { Card, Table, Tag, Button, Space, Select, message } from 'antd'
import { ApiOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { cemsApi } from '../api'
import { useAuthStore, canOperate } from '../stores/auth'
import type { CemsDevice, CemsStatus } from '../types'
import { CEMS_STATUS_LABEL } from '../types'

export default function CemsList() {
  const role = useAuthStore((s) => s.role)
  const operable = canOperate(role)

  const [rows, setRows] = useState<CemsDevice[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState<CemsStatus | undefined>()

  const load = () => {
    setLoading(true)
    cemsApi.list({ page, page_size: 15, status: statusFilter })
      .then((r) => { setRows(r.data.items); setTotal(r.data.total) })
      .finally(() => setLoading(false))
  }
  useEffect(load, [page, statusFilter])

  const statusTag = (s: CemsStatus) => {
    const c = s === 'ONLINE' ? 'green' : s === 'FAULT' ? 'red' :
      s === 'CALIBRATING' ? 'orange' : 'default'
    return <Tag color={c}>{CEMS_STATUS_LABEL[s]}</Tag>
  }

  return (
    <Card title={<Space><ApiOutlined />CEMS 监测仪表</Space>}
      extra={
        <Space>
          <Select<CemsStatus | undefined>
            placeholder="状态" allowClear style={{ width: 130 }} value={statusFilter}
            onChange={(v) => { setPage(1); setStatusFilter(v) }}
            options={Object.entries(CEMS_STATUS_LABEL).map(([k, v]) => ({ label: v, value: k }))}
          />
          <Button icon={<ReloadOutlined />} onClick={load} />
        </Space>
      }
    >
      <Table
        rowKey="id" loading={loading} dataSource={rows}
        pagination={{ current: page, pageSize: 15, total, onChange: setPage }}
        columns={[
          { title: '编号', dataIndex: 'code', width: 140 },
          { title: '名称', dataIndex: 'name' },
          { title: '所属点位', dataIndex: 'point_code', width: 130 },
          { title: '厂家', dataIndex: 'manufacturer', width: 110 },
          { title: '型号', dataIndex: 'model', width: 130 },
          { title: '状态', dataIndex: 'status', width: 100, render: (v) => statusTag(v) },
          { title: '上次校准', dataIndex: 'last_calibration_at', width: 150,
            render: (v) => v ? dayjs(v).format('MM-DD HH:mm') : '-' },
          { title: '下次校准', dataIndex: 'next_calibration_at', width: 150,
            render: (v) => v ? dayjs(v).format('MM-DD HH:mm') : '-' },
          { title: '检定有效期', dataIndex: 'certification_expiry', width: 120,
            render: (v) => v ? dayjs(v).format('YYYY-MM-DD') : '-' },
          {
            title: '操作', width: 200, fixed: 'right' as const,
            render: (_: any, r: CemsDevice) => operable ? (
              <Space size="small">
                {r.status !== 'CALIBRATING' && (
                  <Button size="small" onClick={async () => { await cemsApi.calibrateStart(r.id); message.success('已进入校准'); load() }}>开始校准</Button>
                )}
                {r.status === 'CALIBRATING' && (
                  <Button size="small" type="primary" onClick={async () => { await cemsApi.calibrateFinish(r.id); message.success('已恢复在线'); load() }}>校准完成</Button>
                )}
              </Space>
            ) : null,
          },
        ]}
        scroll={{ x: 1400 }}
      />
    </Card>
  )
}
