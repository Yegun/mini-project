import { useFoods } from '../hooks/useFoods'
import Home from './Home'

interface Props {
  onSelectFood: (id: string) => void // 달력 막대나 목록의 식품을 누르면 상세 화면으로
  onAddFood: (today: string) => void // 등록 화면으로. 구매일 기본값용으로 API 가 준 오늘 날짜를 함께 넘긴다
}

// 홈 화면: 목록을 불러와 Home 에 넘긴다.
export default function HomePage({ onAddFood, onSelectFood }: Props) {
  const { result, reload } = useFoods()
  return (
    <Home
      result={result}
      onRetry={reload}
      onSelectFood={onSelectFood}
      onAddFood={() => {
        if (result.status === 'ready') onAddFood(result.data.today) // 등록 버튼은 목록을 불러온 뒤에만 보인다
      }}
    />
  )
}
