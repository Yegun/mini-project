import { CATEGORIES, CATEGORY_LABEL, type Category } from '../types/food'
import CategoryIcon from './CategoryIcon'
import './CategoryPicker.css'

interface Props {
  id: string // 이름표(FormField)와 이어지는 id
  value: Category | null
  disabled?: boolean
  onChange: (category: Category) => void
}

// 식품 종류 고르기: 채소 · 과일 · 육류 · 수산 · 기타. 보기 다섯 개는 종류 캡슐 모양(색 · 작은 그림 · 글자)이다
// (SCREEN-SPEC 5.2). 고른 것은 굵은 테두리로 보이고, 색은 홈 목록의 종류 캡슐과 같다.
export default function CategoryPicker({ id, value, disabled, onChange }: Props) {
  return (
    <div className="cat-picker" role="radiogroup" id={id} aria-labelledby={`${id}-label`}>
      {CATEGORIES.map((c) => (
        <button
          key={c}
          type="button"
          role="radio"
          aria-checked={value === c}
          disabled={disabled}
          className={value === c ? `cat-picker__item cat-picker__item--on cap--${c}` : `cat-picker__item cap--${c}`}
          onClick={() => onChange(c)}
        >
          <CategoryIcon category={c} className="cat-picker__icon" />
          {CATEGORY_LABEL[c]}
        </button>
      ))}
    </div>
  )
}
