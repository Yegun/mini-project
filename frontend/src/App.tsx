import { useEffect, useState } from 'react'
import './App.css'

type ApiState = 'checking' | 'ok' | 'fail'

function App() {
  const [api, setApi] = useState<ApiState>('checking')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => setApi(res.ok ? 'ok' : 'fail'))
      .catch(() => setApi('fail'))
  }, [])

  const label = { checking: '확인 중...', ok: 'API 연결됨', fail: 'API 연결 안 됨' }[api]

  return (
    <main>
      <h1>task-flow</h1>
      <p>{label}</p>
    </main>
  )
}

export default App
