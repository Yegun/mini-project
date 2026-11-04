import { CATEGORY_LABEL, STORAGE_LABEL, type Category, type Storage } from '../types/food'
import CategoryIcon from './CategoryIcon'
import StorageIcon from './StorageIcon'
import './FoodCapsules.css'

// 보관 방법 캡슐: 냉장 청록 · 상온 살구 · 냉동 남보라 (SCREEN-SPEC 4.8). withIcon 이면 글자 앞에 작은 그림이 붙고,
// 그림 뒤에 은은한 빛이 들어간다 (cap--icon, FoodCapsules.css). 움직임은 없고 글자는 그대로 남는다
export function StorageCapsule({ storage, withIcon = false }: { storage: Storage; withIcon?: boolean }) {
  return (
    <span className={withIcon ? `cap cap--${storage} cap--icon` : `cap cap--${storage}`}>
      {withIcon && <StorageIcon storage={storage} className="cap__icon" />}
      {STORAGE_LABEL[storage]}
    </span>
  )
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
