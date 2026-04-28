import { Routes, Route } from 'react-router'
import Arena from './pages/Arena'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Arena />} />
    </Routes>
  )
}
