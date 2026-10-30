import EmptyHome from '../components/EmptyHome'
import ErrorNotice from '../components/ErrorNotice'
import FoodBarRow from '../components/FoodBarRow'
import FoodList from '../components/FoodList'
import WeekCalendar from '../components/WeekCalendar'
import type { FoodsResult } from '../hooks/useFoods'

interface Props {
  result: FoodsResult
  onRetry: () => void
  onSelectFood?: (id: string) => void // 식품 상세 화면으로
  onAddFood?: () => void // 식품 등록 화면으로
}

// 홈. 순서는 API 가 준 그대로 쓴다. 날짜 판정은 하지 않는다.
export default function Home({ result, onRetry, onSelectFood, onAddFood }: Props) {
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
        <ErrorNotice onRetry={onRetry} />
      </main>
    )
  }

  const { today, foods } = result.data
  if (foods.length === 0) {
    return (
      <main className="home">
        <EmptyHome onAdd={onAddFood} />
      </main>
    )
  }

  return (
    <main className="home">
      <WeekCalendar today={today}>
        {foods.map((food) => (
          <FoodBarRow key={food.id} food={food} today={today} onSelect={onSelectFood} />
        ))}
      </WeekCalendar>
      <FoodList foods={foods} onSelect={onSelectFood} />
      <div className="home__add">
        <button type="button" className="home__add-button" onClick={onAddFood}>
          식품 등록
        </button>
      </div>
    </main>
  )
}
