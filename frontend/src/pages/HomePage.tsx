import { useFoods } from '../hooks/useFoods'
import Home from './Home'

// 홈 화면: 목록을 불러와 Home 에 넘긴다.
export default function HomePage() {
  const { result, reload } = useFoods()
  return <Home result={result} onRetry={reload} />
}
