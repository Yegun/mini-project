import { useCallback, useEffect, useState } from 'react'
import { getFoods } from '../api/foods'
import type { FoodListResponse } from '../types/food'

export type FoodsResult =
  | { status: 'loading' }
  | { status: 'error' } // 어떤 실패든 하나로 (API-SPEC 4절)
  | { status: 'ready'; data: FoodListResponse }

// 홈 목록을 불러온다. reload 를 부르면 처음부터 다시 불러온다 (다시 시도 버튼).
export function useFoods() {
  const [result, setResult] = useState<FoodsResult>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    getFoods()
      .then((data) => {
        if (!cancelled) setResult({ status: 'ready', data })
      })
      .catch(() => {
        if (!cancelled) setResult({ status: 'error' })
      })
    return () => {
      cancelled = true
    }
  }, [attempt])

  const reload = useCallback(() => {
    setResult({ status: 'loading' })
    setAttempt((n) => n + 1)
  }, [])

  return { result, reload }
}
