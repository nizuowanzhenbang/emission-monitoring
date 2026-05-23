import { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, Progress, Typography, Space, Tag, Table } from 'antd'
import {
  ApiOutlined, AlertOutlined, SafetyCertificateTwoTone, FundOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { dashboardApi } from '../api'
import type { DashboardOverview } from '../types'

const { Title } = Typography

export default function Dashboard() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null)
  const [sevDist, setSevDist] = useState<Array<{ name: string; value: number }>>([])
  const [statusDist, setStatusDist] = useState<Array<{ name: string; value: number }>>([])
  const [pointCompliance, setPointCompliance] = useState<Array<{ point_code: string; compliance_pct: number; exceed_minutes: number }>>([])

  useEffect(() => {
    Promise.all([
      dashboardApi.overview(),
      dashboardApi.alertDistribution(30),
      dashboardApi.pointCompliance(30),
    ]).then(([o, ad, pc]) => {
      setOverview(o.data)
      setSevDist(ad.data.by_severity)
      setStatusDist(ad.data.by_status)
      setPointCompliance(pc.data)
    })
  }, [])

  const sevOption = {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      name: '告警等级', type: 'pie', radius: ['50%', '75%'],
      label: { formatter: '{b}: {c}' },
      data: sevDist,
    }],
  }
  const statusOption = {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      name: '告警状态', type: 'pie', radius: ['50%', '75%'],
      label: { formatter: '{b}: {c}' },
      data: statusDist,
    }],
  }

  const complianceOption = {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 30, top: 30, bottom: 60 },
    xAxis: { type: 'category', data: pointCompliance.map(p => p.point_code), axisLabel: { rotate: 30 } },
    yAxis: { type: 'value', min: 80, max: 100, name: '%' },
    series: [{
      name: '合规率', type: 'bar',
      data: pointCompliance.map(p => p.compliance_pct),
      itemStyle: { color: (params: any) =>
        params.value >= 99 ? '#52c41a' : params.value >= 95 ? '#faad14' : '#f5222d' },
      label: { show: true, position: 'top', formatter: '{c}%' },
    }],
  }

  return (
    <div>
      <Title level={4}>环保排放总览</Title>
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="CEMS 在线" value={overview?.cems.online ?? 0} suffix={`/ ${overview?.cems.total ?? 0}`}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
            <Tag color="red" style={{ marginTop: 8 }}>故障 {overview?.cems.fault ?? 0}</Tag>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="今日超标次数" value={overview?.alerts.today ?? 0}
              prefix={<AlertOutlined />} valueStyle={{ color: '#fa541c' }} />
            <Space style={{ fontSize: 12, color: '#888' }}>
              <Tag color="orange">未结 {overview?.alerts.open ?? 0}</Tag>
              <Tag color="red">严重 {overview?.alerts.severe_open ?? 0}</Tag>
            </Space>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="30 天合规率" value={overview?.compliance_30d_pct ?? 100} suffix="%"
              prefix={<SafetyCertificateTwoTone twoToneColor="#52c41a" />} />
            <Progress percent={overview?.compliance_30d_pct ?? 100} showInfo={false}
              strokeColor={(overview?.compliance_30d_pct ?? 100) >= 99 ? '#52c41a' : '#faad14'} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="30 天 CEMS 在线率" value={overview?.availability_30d_pct ?? 100} suffix="%"
              prefix={<FundOutlined />} />
            <Progress percent={overview?.availability_30d_pct ?? 100} showInfo={false}
              strokeColor={(overview?.availability_30d_pct ?? 100) >= (overview?.availability_target ?? 95) ? '#52c41a' : '#fa541c'} />
            <span style={{ fontSize: 12, color: '#888' }}>合规线 {overview?.availability_target ?? 95}%</span>
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={8}>
          <Card title="近 30 天告警等级"><ReactECharts option={sevOption} style={{ height: 280 }} /></Card>
        </Col>
        <Col span={8}>
          <Card title="近 30 天告警状态"><ReactECharts option={statusOption} style={{ height: 280 }} /></Card>
        </Col>
        <Col span={8}>
          <Card title="合规率倒序（小心 < 99%）" size="small">
            <Table size="small" pagination={false}
              rowKey="point_code" dataSource={pointCompliance}
              columns={[
                { title: '排放口', dataIndex: 'point_code' },
                { title: '合规率', dataIndex: 'compliance_pct', width: 120,
                  render: (v) => <Progress percent={v} size="small"
                    strokeColor={v >= 99 ? '#52c41a' : v >= 95 ? '#faad14' : '#f5222d'} /> },
                { title: '超限分钟', dataIndex: 'exceed_minutes', width: 100 },
              ]}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="各排放口 30 天合规率柱图">
            <ReactECharts option={complianceOption} style={{ height: 320 }} />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
