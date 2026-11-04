import { CATEGORY_LABEL, STORAGE_LABEL, type Category, type Storage } from '../types/food'
import CategoryIcon from './CategoryIcon'
import './FoodCapsules.css'

// 보관 방법 캡슐: 글자만. 냉장 청록 · 상온 회색 · 냉동 남보라 (SCREEN-SPEC 4.8)
export function StorageCapsule({ storage }: { storage: Storage }) {
  return <span className={`cap cap--${storage}`}>{STORAGE_LABEL[storage]}</span>
}

// 종류 캡슐: 종류 색 · 작은 그림 · 글자. 종류를 모르면(null) 보이지 않는다 (API-SPEC 5절 47번)
export function CategoryCapsule({ category }: { category: Category | null }) {
  if (!category) return null
  return (
    <span className={`cap cap--${category}`}>
      <CategoryIcon category={category} className="cap__icon" />
      {CATEGORY_LABEL[category]}
    </span>
  )
}
