import type { CSSProperties } from 'react'
import { clipBar } from '../lib/week'
import { STATUS_LABEL, statusColor } from '../lib/statusColor'
import { STORAGE_LABEL, type Food } from '../types/food'
import DaysLeftBubble from './DaysLeftBubble'
import './FoodBarRow.css'

interface Props {
  food: Food
  weekDate: string // 보이는 주에 들어 있는 날짜. 이 주 7칸에 맞춰 막대를 자른다
  onSelect?: (id: string) => void // 식품 상세 화면으로
  index?: number // 줄 번호. 막대가 차오르는 시작 시각을 줄마다 조금씩 늦춘다
}

// 달력 안의 식품 한 줄. 보이는 주에 걸치지 않는 식품은 줄 자체를 그리지 않는다 (목록에는 남는다).
// 한 줄은 [이름] [요일 7칸 + 막대] [보관 방법] [남은 날] 네 칸이고, 칸마다 같은 높이의 둥근 네모 바탕이 깔린다 (SCREEN-SPEC 4.7).
// 막대가 지나가는 요일 7칸 뒤에는 줄마다 연한 바탕이 깔린다 (FoodBarRow.css).
export default function FoodBarRow({ food, weekDate, onSelect, index = 0 }: Props) {
  if (!food.show_on_calendar) return null // 달력에 보일지는 API 가 정한다
  const span = clipBar(weekDate, food.purchase_date, food.expiry_date)
  if (!span) return null

  const barStyle: CSSProperties = {
    gridColumn: `${span.startCol + 2} / ${span.endCol + 3}`, // 1열은 이름 칸
    background: statusColor(food.expiry_status),
    ['--i' as string]: index, // 차오르는 움직임의 줄별 지연 (FoodBarRow.css)
  }
  const description = `${food.name}, ${STORAGE_LABEL[food.storage]}, ${STATUS_LABEL[food.expiry_status]}`
  return (
    <div className="week-grid food-row">
      <button type="button" className="food-row__label" onClick={() => onSelect?.(food.id)}>
        <span
          className="food-row__pillar"
          data-status={food.expiry_status}
          style={{ background: statusColor(food.expiry_status) }}
          aria-hidden="true"
        />
        <span className="food-row__name">{food.name}</span>
      </button>
      <button
        type="button"
        className="food-row__bar"
        data-status={food.expiry_status}
        style={barStyle}
        aria-label={description}
        onClick={() => onSelect?.(food.id)}
      />
      <span className={`food-row__storage-box cap--${food.storage}`}>{STORAGE_LABEL[food.storage]}</span>
      <span className="food-row__bubble">
        <DaysLeftBubble status={food.expiry_status} daysLeft={food.days_left} signed />
      </span>
    </div>
  )
}
