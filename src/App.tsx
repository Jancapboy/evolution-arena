import { Routes, Route } from 'react-router'
import Arena from './pages/Arena'
import Home from './pages/Home'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/arena" element={<Arena />} />
    </Routes>
  )
}
