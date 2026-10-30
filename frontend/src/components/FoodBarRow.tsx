import type { CSSProperties } from 'react'
import { clipBar } from '../lib/week'
import { STATUS_LABEL, statusColor } from '../lib/statusColor'
import { STORAGE_LABEL, type Food } from '../types/food'
import './FoodBarRow.css'

interface Props {
  food: Food
  today: string // API 가 준 오늘 날짜
  onSelect?: (id: string) => void // 상세 화면 이동은 아직 없다 (이번 범위 밖)
}

// 달력 안의 식품 한 줄. 이번 주에 보이지 않는 식품은 줄 자체를 그리지 않는다 (목록에는 남는다).
export default function FoodBarRow({ food, today, onSelect }: Props) {
  if (!food.show_on_calendar) return null // 달력에 보일지는 API 가 정한다
  const span = clipBar(today, food.purchase_date, food.expiry_date)
  if (!span) return null

  const barStyle: CSSProperties = {
    gridColumn: `${span.startCol + 2} / ${span.endCol + 3}`, // 1열은 이름 칸
    background: statusColor(food.expiry_level),
  }
  const barClass = [
    'food-row__bar',
    span.clippedStart && 'food-row__bar--cut-start',
    span.clippedEnd && 'food-row__bar--cut-end',
  ]
    .filter(Boolean)
    .join(' ')
  const description = `${food.name}, ${STORAGE_LABEL[food.storage]}, ${STATUS_LABEL[food.expiry_level]}`

  return (
    <div className="week-grid food-row">
      <button type="button" className="food-row__label" onClick={() => onSelect?.(food.id)}>
        <span className="food-row__name">{food.name}</span>
        <span className="food-row__storage">{STORAGE_LABEL[food.storage]}</span>
      </button>
      <button
        type="button"
        className={barClass}
        style={barStyle}
        aria-label={description}
        onClick={() => onSelect?.(food.id)}
      />
    </div>
  )
}
