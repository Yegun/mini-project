// 줄 전체에 까는 종류 색 배경의 클래스 이름 (components/FoodCapsules.css 의 .tint--*). 종류를 모르면 배경이 없다.
import type { Category } from '../types/food'

export function categoryTintClass(category: Category | null): string {
  return category ? `tint tint--${category}` : ''
}
