import { useState } from 'react'
import './App.css'
import HomePage from './pages/HomePage'
import RegisterPage from './pages/RegisterPage'

// 화면 전환은 상태값으로 한다 (홈 / 식품 등록). 식품 상세는 이번 범위 밖이다.
type Screen = { name: 'home' } | { name: 'register'; today: string }

function App() {
  const [screen, setScreen] = useState<Screen>({ name: 'home' })

  if (screen.name === 'register') {
    return (
      <RegisterPage
        today={screen.today}
        onBack={() => setScreen({ name: 'home' })}
        onDone={() => setScreen({ name: 'home' })} // 홈이 다시 열리면서 목록을 새로 불러온다
      />
    )
  }
  return <HomePage onAddFood={(today) => setScreen({ name: 'register', today })} />
}

export default App
