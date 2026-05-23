import { Layout as AntLayout, Menu, Button, Typography, Space } from 'antd'
import {
  DashboardOutlined, FundOutlined, ApiOutlined, AlertOutlined,
  ProfileOutlined, LogoutOutlined, CloudOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore, ROLE_LABEL } from '../stores/auth'

const { Sider, Header, Content } = AntLayout
const { Title, Text } = Typography

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { username, role, logout } = useAuthStore()

  const menuItems = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: '/realtime', icon: <FundOutlined />, label: '实时大屏' },
    { key: '/units', icon: <CloudOutlined />, label: '机组与排放口' },
    { key: '/cems', icon: <ApiOutlined />, label: 'CEMS 设备' },
    { key: '/alerts', icon: <AlertOutlined />, label: '超标告警' },
    { key: '/reports', icon: <ProfileOutlined />, label: '排放报表' },
  ]

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider width={220} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
        <div style={{ padding: '20px 16px', borderBottom: '1px solid #f0f0f0' }}>
          <Space>
            <CloudOutlined style={{ fontSize: 22, color: '#2db7f5' }} />
            <Title level={5} style={{ margin: 0 }}>环保排放</Title>
          </Space>
        </div>
        <Menu mode="inline" selectedKeys={[location.pathname]} items={menuItems}
          onClick={({ key }) => navigate(key)} style={{ borderRight: 0 }} />
      </Sider>
      <AntLayout>
        <Header style={{
          background: '#fff', padding: '0 24px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          borderBottom: '1px solid #f0f0f0',
        }}>
          <Text strong style={{ fontSize: 16 }}>发电厂环保排放在线监测系统</Text>
          <Space>
            <Text type="secondary">{username} · {role ? ROLE_LABEL[role] || role : ''}</Text>
            <Button type="text" icon={<LogoutOutlined />} onClick={() => { logout(); navigate('/login') }}>
              退出
            </Button>
          </Space>
        </Header>
        <Content style={{ padding: 20, background: '#f5f5f5' }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
