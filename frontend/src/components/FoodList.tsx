import { STATUS_LABEL, statusColor } from '../lib/statusColor'
import { STORAGE_LABEL, type Food } from '../types/food'
import './FoodList.css'

interface Props {
  foods: Food[] // API 가 정렬해서 준 순서 그대로
  onSelect?: (id: string) => void // 식품 상세 화면으로
}

// 달력 아래 식품 목록. 달력에 안 보이는 식품도 여기에는 모두 나온다.
export default function FoodList({ foods, onSelect }: Props) {
  return (
    <ul className="food-list" aria-label="식품 목록">
      {foods.map((food) => (
        <li key={food.id}>
          <button type="button" className="food-list__item" onClick={() => onSelect?.(food.id)}>
            <span
              className="food-list__strip"
              style={{ background: statusColor(food.expiry_level) }}
              aria-hidden="true"
            />
            <span className="food-list__name">{food.name}</span>
            <span className="food-list__storage">{STORAGE_LABEL[food.storage]}</span>
            <span className="visually-hidden">{STATUS_LABEL[food.expiry_level]}</span>
          </button>
        </li>
      ))}
    </ul>
  )
}
