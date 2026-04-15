import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar  from './Topbar'

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-[var(--cream)]">
      <Sidebar />
      <Topbar  />
      <main className="min-h-screen" style={{ marginLeft: '256px', paddingTop: '64px' }}>
        <div className="p-7 animate-fade-slide">
          <Outlet />
        </div>
      </main>
    </div>
  )
}