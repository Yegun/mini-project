import { categoryTintClass } from '../lib/categoryTint'
import { STATUS_LABEL, statusColor } from '../lib/statusColor'
import type { Food } from '../types/food'
import DaysLeftBubble from './DaysLeftBubble'
import { CategoryCapsule, StorageCapsule } from './FoodCapsules'
import './FoodList.css'

interface Props {
  foods: Food[] // API 가 정렬해서 준 순서 그대로
  onSelect?: (id: string) => void // 식품 상세 화면으로
}

// 달력 아래 식품 목록. 달력에 안 보이는 식품도 여기에는 모두 나온다.
// 줄 전체에 종류 색 배경이 깔리고, 이름 아래에 보관 방법 캡슐과 종류 캡슐이 있다 (SCREEN-SPEC 4.8).
export default function FoodList({ foods, onSelect }: Props) {
  return (
    <ul className="food-list" aria-label="식품 목록">
      {foods.map((food) => (
        <li key={food.id}>
          <button
            type="button"
            className={['food-list__item', categoryTintClass(food.category)].filter(Boolean).join(' ')}
            onClick={() => onSelect?.(food.id)}
          >
            <span
              className="food-list__strip"
              data-status={food.expiry_status}
              style={{ background: statusColor(food.expiry_status) }}
              aria-hidden="true"
            />
            <span className="food-list__main">
              <span className="food-list__name">{food.name}</span>
              <span className="caps">
                <StorageCapsule storage={food.storage} />
                <CategoryCapsule category={food.category} />
              </span>
            </span>
            <DaysLeftBubble status={food.expiry_status} daysLeft={food.days_left} />
            <span className="visually-hidden">{STATUS_LABEL[food.expiry_status]}</span>
          </button>
        </li>
      ))}
    </ul>
  )
}
