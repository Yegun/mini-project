import { useCallback, useEffect, useState } from 'react'
import { getFoodDetail, LoadFoodDetailError } from '../api/foodDetail'
import type { FoodDetail } from '../types/foodDetail'

export type FoodDetailResult =
  | { status: 'loading' }
  | { status: 'error'; message?: string } // 어떤 실패든 하나로 (D-008). message 는 API 문구 (없으면 화면 기본 문구)
  | { status: 'ready'; food: FoodDetail }

// 상세를 불러온다. reload 를 부르면 처음부터 다시 불러온다 (다시 시도 버튼).
export function useFoodDetail(id: string) {
  const [result, setResult] = useState<FoodDetailResult>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    getFoodDetail(id)
      .then((food) => {
        if (!cancelled) setResult({ status: 'ready', food })
      })
      .catch((e: unknown) => {
        const message = e instanceof LoadFoodDetailError ? e.apiMessage : undefined
        if (!cancelled) setResult({ status: 'error', message })
      })
    return () => {
      cancelled = true
    }
  }, [id, attempt])

  const reload = useCallback(() => {
    setResult({ status: 'loading' })
    setAttempt((n) => n + 1)
  }, [])

  return { result, reload }
}
