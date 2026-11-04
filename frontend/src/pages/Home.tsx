import { useState } from 'react'
import EmptyHome from '../components/EmptyHome'
import ErrorNotice from '../components/ErrorNotice'
import FoodFilters, {
  type CategoryFilter,
  type StatusFilter,
  type StorageFilter,
} from '../components/FoodFilters'
import FoodList from '../components/FoodList'
import HeroBand from '../components/HeroBand'
import WeekCalendar from '../components/WeekCalendar'
import type { FoodsResult } from '../hooks/useFoods'
import type { ExpiryStatus, Food } from '../types/food'
import '../components/StateNotice.css'

interface Props {
  result: FoodsResult
  onRetry: () => void
  onSelectFood?: (id: string) => void // 식품 상세 화면으로
  onAddFood?: () => void // 식품 등록 화면으로
  onTrash?: (food: Food) => void // 휴지통 버튼: 다 먹음 · 버림 · 삭제 선택창
}

// 홈. 순서는 API 가 준 그대로 쓴다. 날짜 판정은 하지 않는다.
// 알약 수 세기와 거르기는 화면이 홈 목록 하나로 한다 (SCREEN-SPEC 4.6, ARCHITECTURE 9절 31번).
// 상태 · 보관 방법 · 식품 종류를 함께 걸면 모두 맞는 식품만 보이고, 홈을 다시 열면 '전체'로 돌아온다 (D-140).
export default function Home({ result, onRetry, onSelectFood, onAddFood, onTrash }: Props) {
  const [status, setStatus] = useState<StatusFilter>('all')
  const [storage, setStorage] = useState<StorageFilter>('all')
  const [category, setCategory] = useState<CategoryFilter>('all')

  if (result.status === 'loading') {
    return (
      <main className="home">
        <p role="status">불러오는 중…</p>
      </main>
    )
  }

  if (result.status === 'error') {
    return (
      <main className="home">
        <ErrorNotice message={result.message} onRetry={onRetry} />
      </main>
    )
  }

  const { today, items: foods } = result.data
  if (foods.length === 0) {
    return (
      <main className="home">
        <HeroBand today={today} />
        <EmptyHome onAdd={onAddFood} />
      </main>
    )
  }

  // 처리하지 않은 내 식품의 상태별 수 (드롭다운과 상관없이 전체에서 센다)
  const counts: Record<ExpiryStatus, number> = { fresh: 0, warning: 0, soon: 0, expired: 0 }
  for (const f of foods) counts[f.expiry_status] += 1

  const visible = foods.filter(
    (f) =>
      (status === 'all' || f.expiry_status === status) &&
      (storage === 'all' || f.storage === storage) &&
      (category === 'all' || f.category === category),
  )
  const noneInStatus = status !== 'all' && counts[status] === 0 // 수가 0 인 알약을 눌렀을 때의 안내

  return (
    <main className="home">
      <HeroBand today={today} />
      <FoodFilters
        counts={counts}
        status={status}
        storage={storage}
        category={category}
        onStatus={setStatus}
        onStorage={setStorage}
        onCategory={setCategory}
      />
      <WeekCalendar today={today} foods={visible} onSelectFood={onSelectFood} />
      {visible.length === 0 ? (
        <p className="notice notice--empty" role="status">
          {noneInStatus ? '그 상태의 식품이 없어요.' : '조건에 맞는 식품이 없어요.'}
        </p>
      ) : (
        <FoodList foods={visible} onSelect={onSelectFood} onTrash={onTrash} />
      )}
      <div className="home__add">
        <button type="button" className="home__add-button" onClick={onAddFood}>
          식품 등록
        </button>
      </div>
    </main>
  )
}
