import FoodBarRow from '../components/FoodBarRow'
import FoodList from '../components/FoodList'
import WeekCalendar from '../components/WeekCalendar'
import type { FoodListResponse } from '../types/food'

interface Props {
  data: FoodListResponse
  onSelectFood?: (id: string) => void // 상세 화면은 이번 범위 밖이라 아직 연결하지 않는다
}

// 홈 (식품이 있을 때). 순서는 API 가 준 그대로 쓴다. 빈 홈·실패·불러오는 중은 7단계에서 추가한다.
export default function Home({ data, onSelectFood }: Props) {
  return (
    <main className="home">
      <WeekCalendar today={data.today}>
        {data.foods.map((food) => (
          <FoodBarRow key={food.id} food={food} today={data.today} onSelect={onSelectFood} />
        ))}
      </WeekCalendar>
      <FoodList foods={data.foods} onSelect={onSelectFood} />
    </main>
  )
}
