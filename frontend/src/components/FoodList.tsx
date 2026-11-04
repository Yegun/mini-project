import { categoryTintClass } from '../lib/categoryTint'
import { STATUS_LABEL, statusColor } from '../lib/statusColor'
import type { Food } from '../types/food'
import DangerMark from './DangerMark'
import DaysLeftBubble from './DaysLeftBubble'
import { CategoryCapsule, StorageCapsule } from './FoodCapsules'
import './FoodList.css'

interface Props {
  foods: Food[] // API 가 정렬해서 준 순서 그대로
  onSelect?: (id: string) => void // 식품 상세 화면으로
  onTrash?: (food: Food) => void // 휴지통 버튼: 다 먹음 · 버림 · 삭제 선택창을 연다
}

// 달력 아래 식품 목록. 달력에 안 보이는 식품도 여기에는 모두 나온다 (SCREEN-SPEC 4.3, 4.8).
// 줄 = 상태 색 막대 · 이름(위험 식품이면 ⚠ 위험) · 보관 방법 캡슐 · 종류 캡슐 · 남은 날 말풍선 · 휴지통 버튼.
// 줄의 휴지통이 아닌 곳을 누르면 식품 상세로 간다. 줄 전체를 덮는 버튼을 뒤에 두고, 위의 ⚠ 와 휴지통만 따로 눌린다.
export default function FoodList({ foods, onSelect, onTrash }: Props) {
  return (
    <ul className="food-list" aria-label="식품 목록">
      {foods.map((food) => (
        <li key={food.id}>
          <div className={['food-list__item', categoryTintClass(food.category)].filter(Boolean).join(' ')}>
            <button
              type="button"
              className="food-list__open"
              aria-label={`${food.name} 상세 보기`}
              onClick={() => onSelect?.(food.id)}
            />
            <div className="food-list__content">
              <span
                className="food-list__strip"
                data-status={food.expiry_status}
                style={{ background: statusColor(food.expiry_status) }}
                aria-hidden="true"
              />
              <span className="food-list__main">
                <span className="food-list__name">{food.name}</span>
                {food.is_danger && <DangerMark note={food.danger_note} />}
                <span className="caps">
                  <StorageCapsule storage={food.storage} />
                  <CategoryCapsule category={food.category} />
                </span>
              </span>
              <DaysLeftBubble status={food.expiry_status} daysLeft={food.days_left} />
              <span className="visually-hidden">{STATUS_LABEL[food.expiry_status]}</span>
              <button
                type="button"
                className="food-list__trash"
                aria-label={`${food.name} 정리하기`}
                onClick={() => onTrash?.(food)}
              >
                <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
                  <path
                    d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v5M14 11v5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}
