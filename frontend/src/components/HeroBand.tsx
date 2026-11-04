import { formatKoreanDate } from '../lib/dateText'
import './HeroBand.css'

interface Props {
  today: string // API 가 준 오늘 날짜 (D-021). 화면 시계는 쓰지 않는다
}

// 홈 위쪽 띠: 포인트 색 그라데이션과 큰 채소 · 과일 그림, 안에는 오늘 날짜 한 줄 (SCREEN-SPEC 4.2, 13.2 의 7번).
// 그림은 임시 평면 그림이다. 실제 그림은 따로 만든다.
export default function HeroBand({ today }: Props) {
  return (
    <header className="hero">
      <p className="hero__date">{formatKoreanDate(today)}</p>
      <svg className="hero__art" viewBox="0 0 120 104" aria-hidden="true" focusable="false">
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
    </header>
  )
}
