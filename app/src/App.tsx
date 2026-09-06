import { Navigate, Route, Routes } from 'react-router'
import AdminLayout from '@/components/AdminLayout'
import Portal from '@/pages/Portal'
import Login from '@/pages/Login'
import Register from '@/pages/Register'
import SatelliteNetwork from '@/pages/satellite/SatelliteNetwork'
import SatelliteManage from '@/pages/satellite/SatelliteManage'
import SatelliteDetail from '@/pages/satellite/SatelliteDetail'
import TaskAttribute from '@/pages/satellite/TaskAttribute'
import TaskSetting from '@/pages/satellite/TaskSetting'
import ClusterManage from '@/pages/satellite/ClusterManage'
import GroundStation from '@/pages/satellite/GroundStation'
import CaseDemo from '@/pages/satellite/CaseDemo'
import Performance from '@/pages/satellite/Performance'
import SystemSettings from '@/pages/satellite/SystemSettings'
import NetworkParameters from '@/pages/satellite/NetworkParameters'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/portal" replace />} />
      <Route path="/portal" element={<Portal />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/satellite" element={<AdminLayout />}>
        <Route index element={<Navigate to="/satellite/satellite_network" replace />} />
        <Route path="satellite_network" element={<SatelliteNetwork />} />
        <Route path="weixing" element={<SatelliteManage />} />
        <Route path="Weixing/info/:name" element={<SatelliteDetail />} />
        <Route path="renwu/shuxing" element={<TaskAttribute />} />
        <Route path="renwu/shezhi" element={<TaskSetting />} />
        <Route path="xingcu" element={<ClusterManage />} />
        <Route path="ground_station" element={<GroundStation />} />
        <Route path="yongli" element={<CaseDemo />} />
        <Route path="xingneng" element={<Performance />} />
        <Route path="system_settings" element={<SystemSettings />} />
        <Route path="network_parameters" element={<NetworkParameters />} />
      </Route>
      <Route path="*" element={<Navigate to="/portal" replace />} />
    </Routes>
  )
}
