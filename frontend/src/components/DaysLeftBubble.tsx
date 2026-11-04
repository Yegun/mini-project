import type { ExpiryStatus } from '../types/food'
import './DaysLeftBubble.css'

interface Props {
  status: ExpiryStatus // API 가 판정한 상태. 화면은 색만 입힌다 (D-009)
  daysLeft: number // 기한 − 오늘. 지났으면 음수 (−1 = 하루 지남)
}

// 남은 날 말풍선: "2일 남음", "1일 지남". 상태 색으로 보이고, 색만으로 구분하지 않도록 글자도 함께 둔다 (SCREEN-SPEC 4.3, D-142).
export default function DaysLeftBubble({ status, daysLeft }: Props) {
  const text = daysLeft >= 0 ? `${daysLeft}일 남음` : `${-daysLeft}일 지남`
  return (
    <span className={`bubble bubble--${status}`} data-status={status}>
      {text}
    </span>
  )
}
