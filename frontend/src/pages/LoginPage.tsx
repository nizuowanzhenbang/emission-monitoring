import { useState } from 'react'
import { Card, Form, Input, Button, Typography, message } from 'antd'
import { UserOutlined, LockOutlined, CloudOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api'
import { useAuthStore } from '../stores/auth'

const { Title, Text } = Typography

export default function LoginPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const setAuth = useAuthStore((s) => s.setAuth)

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      const res = await authApi.login(values.username, values.password)
      const me = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${res.access_token}` },
      }).then((r) => r.json())
      setAuth(res.access_token, me.data.username, me.data.role)
      message.success('登录成功')
      navigate('/dashboard')
    } catch (e: unknown) {
      message.error((e as { detail?: string })?.detail || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex',
      justifyContent: 'center', alignItems: 'center',
      background: 'linear-gradient(135deg, #2db7f5 0%, #003d6b 100%)',
    }}>
      <Card style={{ width: 420, padding: 8 }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <CloudOutlined style={{ fontSize: 48, color: '#2db7f5' }} />
          <Title level={3} style={{ marginTop: 12, marginBottom: 4 }}>
            环保排放在线监测
          </Title>
          <Text type="secondary">CEMS · 折算浓度 · 超标闭环 · 合规报表</Text>
        </div>
        <Form onFinish={onFinish} layout="vertical" initialValues={{ username: 'admin' }}>
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" size="large" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" size="large" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block size="large">登录</Button>
          </Form.Item>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', lineHeight: 1.8 }}>
            默认账户：<br />
            admin / admin123（管理员）<br />
            operator / operator123（运行人员）<br />
            analyst / analyst123（环保分析）<br />
            supervisor / supervisor123（监督员）<br />
            viewer / viewer123（查看者）
          </Text>
        </Form>
      </Card>
    </div>
  )
}
