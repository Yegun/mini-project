import { useEffect, useState } from 'react'
import { getTips } from '../api/tips'
import type { Tip } from '../types/tips'
import './ThinkingScreen.css'

interface Props {
  message: string // 안내 한 줄: "지금 사진을 분석하고 있어요" / "추천을 만들고 있어요" (D-155)
  onCancel: () => void // 취소: 기다리기를 멈추고 이전 화면으로. 고른 것은 그대로 남는다 (D-154)
}

// 확인 중 화면에서 조언이 겹쳐 보이지 않게, 마지막에 보인 조언 번호를 기억해 다음에는 다른 것을 고른다 (D-156)
let lastTipIndex = -1

function pickTip(tips: Tip[]): Tip | null {
  if (tips.length === 0) return null
  let next = Math.floor(Math.random() * tips.length)
  if (tips.length > 1 && next === lastTipIndex) next = (next + 1) % tips.length
  lastTipIndex = next
  return tips[next]
}

// 확인 중 화면 (SCREEN-SPEC 15절, D-153 ~ D-158): 사진 읽기 · 음식 추천을 기다리는 동안 보인다.
// 그림과 안내 한 줄, 그 아래 냉장고 · 식품 관리 일반 조언 하나, 맨 아래 가운데 취소(엄지가 닿는 곳). 단계 목록과 진행률은 없다 (D-155).
// 열릴 때 오늘의 일반 조언(J1)을 받아 하나를 보인다. 받지 못해도 오류를 보이지 않고 조언 칸만 비운다.
export default function ThinkingScreen({ message, onCancel }: Props) {
  const [tip, setTip] = useState<Tip | null>(null)

  useEffect(() => {
    let cancelled = false
    getTips().then((data) => {
      if (!cancelled && data) setTip(pickTip(data.tips))
    })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="thinking">
      <div className="thinking__center">
        <svg className="thinking__art" viewBox="0 0 120 104" aria-hidden="true" focusable="false">
          <ellipse cx="62" cy="94" rx="46" ry="7" fill="rgba(0,0,0,.12)" />
          <path d="M82 40c18 2 26 20 18 38-6 12-22 14-30 6-10-10-6-40 12-44z" fill="#7a4fa8" />
          <path d="M80 38c-2-8 4-14 10-14 0 8-4 12-10 14z" fill="#3f9a4c" />
          <path d="M34 36c20-8 38 6 36 30-2 22-22 28-34 18-14-12-14-40-2-48z" fill="#e0454a" />
          <path d="M42 34c0-8 6-12 12-10-2 8-6 12-12 10z" fill="#3f9a4c" />
          <circle cx="22" cy="74" r="12" fill="#43b05c" />
          <circle cx="34" cy="68" r="10" fill="#56c46d" />
          <circle cx="14" cy="64" r="8" fill="#3da556" />
          <rect x="20" y="78" width="8" height="12" rx="3" fill="#8bc47a" />
          <circle cx="104" cy="30" r="9" fill="#ffd23f" />
        </svg>

        <p className="thinking__message" role="status">
          {message}
        </p>

        {tip && (
          <aside className="thinking__tip" aria-label="냉장고 관리 조언">
            <p className="thinking__tip-text">{tip.text}</p>
            {tip.from_ai && <small className="thinking__tip-note">AI 가 알려 준 일반적인 조언이에요</small>}
          </aside>
        )}

        <button type="button" className="thinking__cancel" onClick={onCancel}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true" focusable="false">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
          취소
        </button>
      </div>
    </main>
  )
}
