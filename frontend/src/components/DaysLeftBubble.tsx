import type { ExpiryStatus } from '../types/food'
import './DaysLeftBubble.css'

interface Props {
  status: ExpiryStatus // API 가 판정한 상태. 화면은 색만 입힌다 (D-009)
  daysLeft: number // 기한 − 오늘. 지났으면 음수 (−1 = 하루 지남)
  signed?: boolean // 참이면 "+3일" · "-2일" 처럼 부호 있는 숫자 + 일로 보인다 (막대 달력의 남은 날 칸)
}

// 남은 날: 기본은 "2일 남음", "1일 지남" 글자. 색은 상태 색이고, 색만으로 구분하지 않도록 글자나 부호를 함께 둔다 (SCREEN-SPEC 4.3, D-142).
// signed 이면 숫자에 부호와 '일'을 붙인다: 남았으면 +3일, 지났으면 -2일, 기한 당일은 0일. 읽어 주는 글자는 "2일 남음"으로 그대로 둔다.
export default function DaysLeftBubble({ status, daysLeft, signed }: Props) {
  const words = daysLeft >= 0 ? `${daysLeft}일 남았어요` : `${-daysLeft}일 지났어요`
  const shown = signed ? `${daysLeft > 0 ? '+' : ''}${daysLeft}일` : words
  return (
    <span
      className={`bubble bubble--${status}`}
      data-status={status}
      aria-label={signed ? words : undefined}
      title={signed ? words : undefined}
    >
      {shown}
    </span>
  )
}
