import { useCallback, useEffect, useRef, useState } from 'react'
import { getFoods, LoadFoodsError } from '../api/foods'
import type { FoodListResponse } from '../types/food'

export type FoodsResult =
  | { status: 'loading' }
  | { status: 'error'; message?: string } // 어떤 실패든 하나로. message 는 API 문구 (없으면 화면 기본 문구)
  | { status: 'ready'; data: FoodListResponse }

// 홈 목록을 불러온다. reload 를 부르면 처음부터 다시 불러온다 (다시 시도 버튼).
// refresh 는 "불러오는 중" 표시 없이 조용히 다시 불러온다 (휴지통으로 처리한 뒤 목록을 새로 고칠 때).
// initial: 탭을 눌러 이동하기 전에 이미 불러온 목록 (D-086). 있으면 처음에는 다시 부르지 않는다.
export function useFoods(initial?: FoodListResponse) {
  const [result, setResult] = useState<FoodsResult>(() =>
    initial ? { status: 'ready', data: initial } : { status: 'loading' },
  )
  const [attempt, setAttempt] = useState(0)
  const skipFirstLoad = useRef(Boolean(initial))

  useEffect(() => {
    if (skipFirstLoad.current) {
      skipFirstLoad.current = false
      return
    }
    let cancelled = false
    getFoods()
      .then((data) => {
        if (!cancelled) setResult({ status: 'ready', data })
      })
      .catch((e: unknown) => {
        const message = e instanceof LoadFoodsError ? e.apiMessage : undefined
        if (!cancelled) setResult({ status: 'error', message })
      })
    return () => {
      cancelled = true
    }
  }, [attempt])

  const reload = useCallback(() => {
    setResult({ status: 'loading' })
    setAttempt((n) => n + 1)
  }, [])

  const refresh = useCallback(() => {
    setAttempt((n) => n + 1)
  }, [])

  return { result, reload, refresh }
}
