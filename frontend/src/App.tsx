import { useState } from 'react'
import './App.css'
import FoodDetailPage from './pages/FoodDetailPage'
import HomePage from './pages/HomePage'
import RegisterPage from './pages/RegisterPage'

// 화면 전환은 상태값으로 한다 (홈 / 식품 등록 / 식품 상세). 상세에서 새로고침하면 홈으로 돌아온다.
type Screen =
  | { name: 'home' }
  | { name: 'register'; today: string }
  | { name: 'detail'; id: string }

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
  if (screen.name === 'detail') {
    return (
      <FoodDetailPage
        id={screen.id}
        onBack={() => setScreen({ name: 'home' })}
        onDone={() => setScreen({ name: 'home' })} // 저장 · 처리 · 삭제 성공 → 홈 (D-020). 홈이 목록을 새로 불러온다
      />
    )
  }
  return (
    <HomePage
      onAddFood={(today) => setScreen({ name: 'register', today })}
      onSelectFood={(id) => setScreen({ name: 'detail', id })}
    />
  )
}

export default App
