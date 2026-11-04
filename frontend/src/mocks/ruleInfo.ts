// 가짜 규칙표의 식품 종류와 위험 이유 (개발 중 VITE_USE_MOCK 에서만 쓴다).
// 진짜 값은 서버 규칙표가 가진다. 처음 30개의 종류는 DATA-MODEL 5-3, 위험 식품 7개의 이유 한 줄은 DATA-MODEL 5-4 와 같다.
import type { Category } from '../types/food'

export interface RuleInfo {
  category: Category
  dangerNote: string | null // 위험 식품이 아니면 null
}

const VEG: RuleInfo = { category: 'vegetable', dangerNote: null }
const FRUIT: RuleInfo = { category: 'fruit', dangerNote: null }
const OTHER: RuleInfo = { category: 'other', dangerNote: null }

export const RULE_INFO: Record<string, RuleInfo> = {
  // 채소 (13)
  양파: VEG,
  대파: VEG,
  감자: VEG,
  당근: VEG,
  양배추: VEG,
  오이: VEG,
  상추: VEG,
  시금치: VEG,
  마늘: VEG,
  애호박: VEG,
  토마토: VEG,
  배추: VEG,
  버섯: VEG,
  // 과일 (6)
  사과: FRUIT,
  바나나: FRUIT,
  딸기: FRUIT,
  귤: FRUIT,
  포도: FRUIT,
  배: FRUIT,
  // 육류 (3) — 위험
  돼지고기: { category: 'meat', dangerNote: '돼지고기는 덜 익혀 먹으면 기생충과 식중독의 위험이 있어요' },
  소고기: { category: 'meat', dangerNote: '소고기는 덜 익혀 먹으면 식중독 균이 남아 있을 수 있어요' },
  닭고기: { category: 'meat', dangerNote: '닭고기는 덜 익혀 먹으면 살모넬라 같은 식중독의 위험이 있어요' },
  // 수산 (4) — 위험
  고등어: { category: 'seafood', dangerNote: '고등어는 쉽게 상하고, 상한 것을 먹으면 두드러기와 구토가 생길 수 있어요' },
  오징어: { category: 'seafood', dangerNote: '오징어는 날것이나 덜 익힌 것을 먹으면 식중독이 생기기 쉬워요' },
  새우: { category: 'seafood', dangerNote: '새우는 쉽게 상하고, 날것이나 덜 익힌 것을 먹으면 식중독이 생길 수 있어요' },
  연어: { category: 'seafood', dangerNote: '연어는 날것으로 먹으면 기생충이 있을 수 있어요' },
  // 그 밖 (4)
  달걀: OTHER,
  우유: OTHER,
  두부: OTHER,
  콩나물: OTHER,
}

// 이름이 규칙표에 있으면(별칭 제외 — 가짜 데이터는 정식 이름만 찾는다) 위험 · 종류 칸을 만들어 준다
export function ruleFields(name: string): { is_danger: boolean; danger_note: string | null; category: Category | null } {
  const info = RULE_INFO[name]
  if (!info) return { is_danger: false, danger_note: null, category: null } // 규칙표에서 못 찾음 (API-SPEC 5절 47번)
  return { is_danger: info.dangerNote !== null, danger_note: info.dangerNote, category: info.category }
}
