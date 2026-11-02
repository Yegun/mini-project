import { useCallback, useEffect, useRef, useState } from 'react'
import { getRecords, LoadRecordsError } from '../api/records'
import type { RecordsData } from '../types/records'

export type RecordsResult =
  | { status: 'loading' }
  | { status: 'error'; message?: string } // 어떤 실패든 하나로. message 는 API 문구 (없으면 화면 기본 문구)
  | { status: 'ready'; data: RecordsData }

// 기록 화면의 숫자와 처리한 식품 목록을 불러온다.
// initial: 탭을 눌러 이동하기 전에 이미 불러온 기록 (D-086). 있으면 처음에는 다시 부르지 않는다.
// reload: "불러오는 중"부터 다시 (다시 시도 버튼). refresh: 지금 화면을 둔 채 새 숫자로 바꾼다 (되돌리기 뒤).
export function useRecords(initial?: RecordsData) {
  const [result, setResult] = useState<RecordsResult>(() =>
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
    getRecords()
      .then((data) => {
        if (!cancelled) setResult({ status: 'ready', data })
      })
      .catch((e: unknown) => {
        const message = e instanceof LoadRecordsError ? e.apiMessage : undefined
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

  const refresh = useCallback(() => setAttempt((n) => n + 1), [])

  return { result, reload, refresh }
}
