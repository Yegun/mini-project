import { useState } from 'react'
import EmptyHome from '../components/EmptyHome'
import ErrorNotice from '../components/ErrorNotice'
import FoodFilters, {
  type CategoryFilter,
  type StatusFilter,
  type StorageFilter,
} from '../components/FoodFilters'
import FoodList from '../components/FoodList'
import HeroBand, { type HeroTone } from '../components/HeroBand'
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
  onOpenFull?: () => void // 전체 달력 열기 (막대 달력의 연 · 월 옆 >)
}

// 홈. 순서는 API 가 준 그대로 쓴다. 날짜 판정은 하지 않는다.
// 알약 수 세기와 거르기는 화면이 홈 목록 하나로 한다 (SCREEN-SPEC 4.6, ARCHITECTURE 9절 31번).
// 상태 · 보관 방법 · 식품 종류를 함께 걸면 모두 맞는 식품만 보이고, 홈을 다시 열면 '전체'로 돌아온다 (D-140).
export default function Home({ result, onRetry, onSelectFood, onAddFood, onTrash, onOpenFull }: Props) {
  const [status, setStatus] = useState<StatusFilter>('all')
  const [storage, setStorage] = useState<StorageFilter>('all')
  const [category, setCategory] = useState<CategoryFilter>('all')
  const [danger, setDanger] = useState(false) // 위험 식품만 보기

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
  const dangerCount = foods.filter((f) => f.is_danger).length // 서버가 규칙표에서 읽어 붙인 위험 표시를 세기만 한다 (D-009)

  const visible = foods.filter(
    (f) =>
      (status === 'all' || f.expiry_status === status) &&
      (storage === 'all' || f.storage === storage) &&
      (category === 'all' || f.category === category) &&
      (!danger || f.is_danger),
  )
  const noneInStatus = status !== 'all' && counts[status] === 0 // 수가 0 인 알약을 눌렀을 때의 안내
  const noneDanger = danger && dangerCount === 0 // 위험 식품이 하나도 없을 때 위험 알약을 눌렀을 때의 안내
  const hero = heroNote(foods, counts) // 위쪽 띠의 상황 요약 (전체 식품 기준)

  return (
    <main className="home">
      <HeroBand today={today} note={hero.text} noteTone={hero.tone} />
      <FoodFilters
        counts={counts}
        status={status}
        storage={storage}
        category={category}
        danger={danger}
        dangerCount={dangerCount}
        onStatus={setStatus}
        onStorage={setStorage}
        onCategory={setCategory}
        onDanger={setDanger}
      />
      <WeekCalendar today={today} foods={visible} onSelectFood={onSelectFood} onOpenFull={onOpenFull} />
      {visible.length === 0 ? (
        <p className="notice notice--empty" role="status">
          {noneDanger ? '위험 식품이 없어요.' : noneInStatus ? '그 상태의 식품이 없어요.' : '조건에 맞는 식품이 없어요.'}
        </p>
      ) : (
        <section className="home__foods" aria-labelledby="home-foods-title">
          <h2 className="home__heading" id="home-foods-title">
            냉장고 속 <span className="home__count">{visible.length}개</span>
          </h2>
          <FoodList foods={visible} onSelect={onSelectFood} onTrash={onTrash} />
        </section>
      )}
      <div className="home__add">
        <button type="button" className="home__add-button" onClick={onAddFood}>
          냉장고에 넣기
        </button>
      </div>
    </main>
  )
}

// 위쪽 띠의 한 줄 상황 요약. 서버가 판정한 상태(임박 · 지남 · 주의)를 읽어 문장으로 바꿀 뿐 판정은 하지 않는다 (D-009).
// 이름은 API 가 준 순서에서 처음 나오는 그 상태의 식품이다. 문구는 임시 문구다 (OQ-03).
// tone 은 문장 앞 점의 색이다(임박 빨강 · 지남 검정 · 주의 노랑 · 여유 초록).
function heroNote(foods: Food[], counts: Record<ExpiryStatus, number>): { text: string; tone: HeroTone } {
  const first = (status: ExpiryStatus) => foods.find((f) => f.expiry_status === status)
  if (counts.soon > 0) {
    const name = first('soon')?.name ?? ''
    const text = counts.soon === 1 ? `곧 기한: ${name}` : `곧 기한: ${name} 외 ${counts.soon - 1}개`
    return { text, tone: 'soon' }
  }
  if (counts.expired > 0) return { text: `기한이 지난 식품이 ${counts.expired}개 있어요`, tone: 'expired' }
  if (counts.warning > 0) return { text: `곧 챙길 식품이 ${counts.warning}개 있어요`, tone: 'warning' }
  return { text: '냉장고가 여유로워요', tone: 'ok' }
}
