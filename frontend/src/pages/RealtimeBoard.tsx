import { useEffect, useState } from 'react'
import { Row, Col, Card, Tag, Space, Select, Typography, Statistic } from 'antd'
import ReactECharts from 'echarts-for-react'
import dayjs from 'dayjs'
import { dashboardApi, readingApi } from '../api'
import type { RealtimeItem } from '../types'

const { Title, Text } = Typography

export default function RealtimeBoard() {
  const [limits, setLimits] = useState({ so2: 35, nox: 50, dust: 10 })
  const [items, setItems] = useState<RealtimeItem[]>([])
  const [selectedPoint, setSelectedPoint] = useState<number | null>(null)
  const [trend, setTrend] = useState<Array<{ hour: string; so2: number; nox: number; dust: number }>>([])

  const load = () => {
    dashboardApi.realtime().then((r) => {
      setLimits(r.data.limits)
      setItems(r.data.items)
      if (selectedPoint == null && r.data.items.length > 0) {
        setSelectedPoint(r.data.items[0].point_id)
      }
    })
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 30_000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    if (selectedPoint != null) {
      dashboardApi.trend24h(selectedPoint).then((r) => setTrend(r.data))
    }
  }, [selectedPoint])

  const trendOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['SO₂', 'NOx', '烟尘'] },
    grid: { left: 40, right: 20, top: 50, bottom: 40 },
    xAxis: { type: 'category', data: trend.map(t => t.hour) },
    yAxis: { type: 'value', name: 'mg/Nm³' },
    series: [
      { name: 'SO₂', type: 'line', smooth: true, data: trend.map(t => t.so2),
        markLine: { silent: true, lineStyle: { color: '#f5222d' }, data: [{ yAxis: limits.so2, name: 'SO₂ 限值' }] } },
      { name: 'NOx', type: 'line', smooth: true, data: trend.map(t => t.nox),
        markLine: { silent: true, lineStyle: { color: '#fa541c' }, data: [{ yAxis: limits.nox, name: 'NOx 限值' }] } },
      { name: '烟尘', type: 'line', smooth: true, data: trend.map(t => t.dust),
        markLine: { silent: true, lineStyle: { color: '#faad14' }, data: [{ yAxis: limits.dust, name: '烟尘限值' }] } },
    ],
  }

  return (
    <div>
      <Title level={4}>实时排放大屏</Title>
      <Text type="secondary">每 30 秒自动刷新 ｜ 浓度已折算至 6% 基准氧 ｜ 限值 SO₂ {limits.so2} / NOx {limits.nox} / 烟尘 {limits.dust} mg/Nm³</Text>

      <Row gutter={16} style={{ marginTop: 16 }}>
        {items.map((it) => {
          const isExceed = (it.exceeded?.length ?? 0) > 0
          return (
            <Col span={8} key={it.point_id} style={{ marginBottom: 12 }}>
              <Card
                style={{ borderTop: `4px solid ${isExceed ? '#f5222d' : '#52c41a'}` }}
                size="small"
                onClick={() => setSelectedPoint(it.point_id)}
                hoverable
              >
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Space>
                    <Tag color="blue">{it.unit_code}</Tag>
                    <Text strong>{it.point_name}</Text>
                  </Space>
                  {isExceed ? (
                    <Tag color="red">超标：{(it.exceeded || []).join(',')}</Tag>
                  ) : (
                    <Tag color="green">达标</Tag>
                  )}
                </Space>
                <Row gutter={12} style={{ marginTop: 12 }}>
                  <Col span={8}>
                    <Statistic title="SO₂ (mg/Nm³)" value={it.so2 ?? 0} precision={2}
                      valueStyle={{ color: (it.so2 ?? 0) > limits.so2 ? '#f5222d' : '#000', fontSize: 18 }} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="NOx" value={it.nox ?? 0} precision={2}
                      valueStyle={{ color: (it.nox ?? 0) > limits.nox ? '#f5222d' : '#000', fontSize: 18 }} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="烟尘" value={it.dust ?? 0} precision={2}
                      valueStyle={{ color: (it.dust ?? 0) > limits.dust ? '#f5222d' : '#000', fontSize: 18 }} />
                  </Col>
                </Row>
                <div style={{ fontSize: 12, color: '#888', marginTop: 8 }}>
                  O₂ {it.o2 ?? '-'}% · {it.flow ? `${Math.round(it.flow / 1000)} 千Nm³/h` : '-'} · 验证 {it.validity} · {it.measured_at ? dayjs(it.measured_at).format('HH:mm:ss') : '-'}
                </div>
              </Card>
            </Col>
          )
        })}
      </Row>

      <Card title={
        <Space>
          24 小时折算浓度趋势
          <Select
            style={{ width: 240 }}
            value={selectedPoint ?? undefined}
            onChange={setSelectedPoint}
            options={items.map(it => ({ label: `${it.point_code} · ${it.point_name}`, value: it.point_id }))}
          />
        </Space>
      }>
        <ReactECharts option={trendOption} style={{ height: 360 }} />
      </Card>
    </div>
  )
}
