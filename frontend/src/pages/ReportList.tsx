import { useEffect, useState } from 'react'
import {
  Card, Table, Tag, Button, Space, Modal, Form, Select, DatePicker, Input,
  Drawer, Descriptions, message,
} from 'antd'
import { ProfileOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { reportApi } from '../api'
import { useAuthStore, canAnalyze, canSupervise } from '../stores/auth'
import type { EmissionReport, ReportType, ReportStatus } from '../types'
import { REPORT_TYPE_LABEL, REPORT_STATUS_LABEL } from '../types'

const { RangePicker } = DatePicker

export default function ReportList() {
  const role = useAuthStore((s) => s.role)
  const analyzable = canAnalyze(role)
  const supervisor = canSupervise(role)

  const [rows, setRows] = useState<EmissionReport[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [generateOpen, setGenerateOpen] = useState(false)
  const [genForm] = Form.useForm()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [detail, setDetail] = useState<EmissionReport | null>(null)

  const load = () => {
    setLoading(true)
    reportApi.list({ page, page_size: 15 })
      .then((r) => { setRows(r.data.items); setTotal(r.data.total) })
      .finally(() => setLoading(false))
  }
  useEffect(load, [page])

  const onGenerate = async () => {
    const v = await genForm.validateFields()
    const [start, end] = v.range
    try {
      await reportApi.generate({
        report_type: v.report_type,
        period_start: start.toISOString(),
        period_end: end.toISOString(),
        title: v.title,
        notes: v.notes,
      })
      message.success('报表已生成')
      setGenerateOpen(false); genForm.resetFields(); load()
    } catch (e: any) {
      message.error(e?.detail || '生成失败')
    }
  }

  const openDetail = async (id: number) => {
    const r = await reportApi.get(id)
    setDetail(r.data); setDrawerOpen(true)
  }

  const statusTag = (s: ReportStatus) => {
    const c = s === 'APPROVED' ? 'green' : s === 'SUBMITTED' ? 'blue' :
      s === 'ARCHIVED' ? 'default' : 'orange'
    return <Tag color={c}>{REPORT_STATUS_LABEL[s]}</Tag>
  }

  return (
    <Card title={<Space><ProfileOutlined />排放报表</Space>}
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load} />
          {analyzable && <Button type="primary" icon={<PlusOutlined />} onClick={() => setGenerateOpen(true)}>生成报表</Button>}
        </Space>
      }
    >
      <Table
        rowKey="id" loading={loading} dataSource={rows}
        pagination={{ current: page, pageSize: 15, total, onChange: setPage }}
        columns={[
          { title: '报表编号', dataIndex: 'report_no', width: 140 },
          { title: '类型', dataIndex: 'report_type', width: 80, render: (v) => REPORT_TYPE_LABEL[v as ReportType] },
          { title: '标题', dataIndex: 'title' },
          { title: '统计区间', width: 220,
            render: (_: any, r: EmissionReport) => `${dayjs(r.period_start).format('MM-DD HH:mm')} ~ ${dayjs(r.period_end).format('MM-DD HH:mm')}` },
          { title: '状态', dataIndex: 'status', width: 100, render: (v) => statusTag(v) },
          { title: '生成人', dataIndex: 'generated_by', width: 100 },
          { title: '生成时间', dataIndex: 'generated_at', width: 150, render: (v) => dayjs(v).format('MM-DD HH:mm') },
          {
            title: '操作', width: 220, fixed: 'right' as const,
            render: (_: any, r: EmissionReport) => (
              <Space size="small">
                <Button size="small" onClick={() => openDetail(r.id)}>详情</Button>
                {analyzable && r.status === 'DRAFT' && (
                  <Button size="small" onClick={async () => { await reportApi.submit(r.id); message.success('已提交'); load() }}>提交</Button>
                )}
                {supervisor && r.status === 'SUBMITTED' && (
                  <Button size="small" type="primary" onClick={async () => { await reportApi.approve(r.id); message.success('已审批'); load() }}>审批</Button>
                )}
              </Space>
            ),
          },
        ]}
        scroll={{ x: 1400 }}
      />

      <Modal title="生成报表" open={generateOpen} onOk={onGenerate} onCancel={() => setGenerateOpen(false)} width={520}>
        <Form form={genForm} layout="vertical">
          <Form.Item name="report_type" label="类型" rules={[{ required: true }]} initialValue="MONTHLY">
            <Select options={Object.entries(REPORT_TYPE_LABEL).map(([k, v]) => ({ label: v, value: k }))} />
          </Form.Item>
          <Form.Item name="range" label="统计区间" rules={[{ required: true }]}>
            <RangePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="title" label="标题（可选）"><Input /></Form.Item>
          <Form.Item name="notes" label="备注"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>

      <Drawer title={detail?.title} open={drawerOpen} onClose={() => setDrawerOpen(false)} width={720}>
        {detail && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="报表编号">{detail.report_no}</Descriptions.Item>
            <Descriptions.Item label="类型">{REPORT_TYPE_LABEL[detail.report_type]}</Descriptions.Item>
            <Descriptions.Item label="区间">
              {dayjs(detail.period_start).format('YYYY-MM-DD HH:mm')} ~ {dayjs(detail.period_end).format('YYYY-MM-DD HH:mm')}
            </Descriptions.Item>
            <Descriptions.Item label="状态">{statusTag(detail.status)}</Descriptions.Item>
            <Descriptions.Item label="生成人">{detail.generated_by} @ {dayjs(detail.generated_at).format('YYYY-MM-DD HH:mm')}</Descriptions.Item>
            {detail.submitted_by && <Descriptions.Item label="提交">{detail.submitted_by} @ {detail.submitted_at && dayjs(detail.submitted_at).format('YYYY-MM-DD HH:mm')}</Descriptions.Item>}
            {detail.approved_by && <Descriptions.Item label="审批">{detail.approved_by} @ {detail.approved_at && dayjs(detail.approved_at).format('YYYY-MM-DD HH:mm')}</Descriptions.Item>}
            <Descriptions.Item label="备注">{detail.notes || '-'}</Descriptions.Item>
            <Descriptions.Item label="汇总数据">
              <pre style={{ maxHeight: 400, overflow: 'auto', background: '#fafafa', padding: 8 }}>
                {JSON.stringify(detail.summary, null, 2)}
              </pre>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </Card>
  )
}
