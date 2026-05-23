import { useEffect, useState } from 'react'
import { Card, Table, Tag, Space, Button, Drawer, List, Typography } from 'antd'
import { CloudOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { unitApi } from '../api'
import type { Unit, EmissionPoint } from '../types'
import { POINT_CATEGORY_LABEL } from '../types'

const { Text } = Typography

export default function UnitList() {
  const [units, setUnits] = useState<Unit[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [points, setPoints] = useState<EmissionPoint[]>([])
  const [currentUnit, setCurrentUnit] = useState<Unit | null>(null)

  const load = () => {
    setLoading(true)
    unitApi.list({ page_size: 50 })
      .then((r) => setUnits(r.data.items))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const showPoints = async (u: Unit) => {
    setCurrentUnit(u)
    const r = await unitApi.listPoints({ unit_id: u.id, page_size: 100 })
    setPoints(r.data.items)
    setDrawerOpen(true)
  }

  return (
    <Card title={<Space><CloudOutlined />发电机组与排放口</Space>}
      extra={<Button icon={<ReloadOutlined />} onClick={load} />}>
      <Table
        rowKey="id" loading={loading}
        dataSource={units} pagination={false}
        columns={[
          { title: '机组编号', dataIndex: 'code', width: 100 },
          { title: '名称', dataIndex: 'name' },
          { title: '容量', dataIndex: 'capacity_mw', width: 100, render: (v) => `${v} MW` },
          { title: '燃料', dataIndex: 'fuel_type', width: 80 },
          { title: '状态', dataIndex: 'status', width: 100,
            render: (v) => <Tag color={v === 'RUNNING' ? 'green' : v === 'OUTAGE' ? 'red' : 'default'}>{v}</Tag> },
          { title: '投产日期', dataIndex: 'commission_date', width: 120,
            render: (v) => v ? dayjs(v).format('YYYY-MM-DD') : '-' },
          { title: '排放口数', dataIndex: 'point_count', width: 100 },
          { title: '操作', width: 120, render: (_: any, u: Unit) => (
            <Button size="small" onClick={() => showPoints(u)}>查看排放口</Button>
          ) },
        ]}
      />

      <Drawer
        title={currentUnit ? `${currentUnit.code} · ${currentUnit.name} 的排放口` : '排放口'}
        open={drawerOpen} onClose={() => setDrawerOpen(false)} width={560}
      >
        <List
          dataSource={points}
          renderItem={(p) => (
            <List.Item>
              <List.Item.Meta
                title={
                  <Space>
                    <Tag>{p.code}</Tag>
                    <Text strong>{p.name}</Text>
                    <Tag color="blue">{POINT_CATEGORY_LABEL[p.category]}</Tag>
                    {p.is_compliance_point && <Tag color="green">合规上报口</Tag>}
                  </Space>
                }
                description={<>位置：{p.location || '-'} ｜ 标准 ID：{p.standard_id || '-'}</>}
              />
            </List.Item>
          )}
        />
      </Drawer>
    </Card>
  )
}
