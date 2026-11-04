import { useEffect, useRef, useState } from 'react'
import { ADVICE_FAILED, getAdvice, type AdviceResult } from '../api/advice'
import ErrorNotice from './ErrorNotice'
import './AdviceCard.css'

interface Props {
  onAddFood: () => void // 조언할 내용이 없을 때의 식품 등록 버튼
}

type State = { kind: 'idle' } | { kind: 'loading' } | { kind: 'done'; result: AdviceResult }

// 기록 화면 맨 위의 AI 조언 카드 (SCREEN-SPEC 7.6, D-159 ~ D-163).
// 버튼을 눌렀을 때만 부르고, 확인 중 화면 없이 버튼만 흐려진다. 조언은 저장하지 않아서 화면을 나가면 사라진다.
export default function AdviceCard({ onAddFood }: Props) {
  const [state, setState] = useState<State>({ kind: 'idle' })
  const lock = useRef(false) // 연타해도 요청은 한 번
  const alive = useRef(true)

  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])

  async function ask() {
    if (lock.current) return
    lock.current = true
    setState({ kind: 'loading' })
    const result = await getAdvice()
    lock.current = false
    if (alive.current) setState({ kind: 'done', result })
  }

  const loading = state.kind === 'loading'
  const result = state.kind === 'done' ? state.result : null

  return (
    <section className="advice" aria-labelledby="advice-title">
      <div className="advice__head">
        <h2 className="advice__title" id="advice-title">
          AI 조언
        </h2>
        <button type="button" className="button button--primary advice__button" disabled={loading} onClick={() => void ask()}>
          {loading ? '조언 받는 중…' : '조언 받기'}
        </button>
      </div>

      {result?.status === 'ok' && (
        <ul className="advice__list">
          {result.advice.map((text, i) => (
            <li key={i}>{text}</li>
          ))}
        </ul>
      )}

      {result?.status === 'no_data' && (
        <div className="advice__empty">
          <p>아직 조언할 내용이 없어요. 식품을 등록하면 조언해 드릴게요.</p>
          <button type="button" className="button button--primary" onClick={onAddFood}>
            식품 등록
          </button>
        </div>
      )}

      {result?.status === 'failed' && <ErrorNotice message={result.message ?? ADVICE_FAILED} />}
    </section>
  )
}
