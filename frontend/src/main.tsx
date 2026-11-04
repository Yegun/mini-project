import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { startAppearance } from './lib/appearance'

// 저장된 밝기 · 포인트 색 · 글자 크기를 화면을 그리기 전에 입힌다 (로그인 화면에도 적용, SCREEN-SPEC 0절)
startAppearance()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
