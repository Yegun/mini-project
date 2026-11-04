import { useEffect, useRef, useState } from 'react'
import { ADVICE_FAILED, getAdvice, type AdviceResult } from '../api/advice'
import ErrorNotice from './ErrorNotice'
import { SparkleIcon } from './RecommendIcons'
import './AdviceCard.css'

interface Props {
  onAddFood: () => void // 조언할 내용이 없을 때의 식품 등록 버튼
}

type State = { kind: 'idle' } | { kind: 'loading' } | { kind: 'done'; result: AdviceResult }

// 기록 화면 맨 위의 AI 조언 카드 (SCREEN-SPEC 7.6, D-159 ~ D-163).
// 버튼을 눌렀을 때만 부르고, 확인 중 화면 없이 버튼만 흐려진다(기다리는 동안 카드 안에 줄 자리만 반짝인다). 조언은 저장하지 않아서 화면을 나가면 사라진다.
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
        <div className="advice__lead">
          <span className="advice__badge" aria-hidden="true">
            <SparkleIcon className="advice__badge-icon" />
          </span>
          <div className="advice__titlebox">
            <h2 className="advice__title" id="advice-title">
              AI 조언
            </h2>
            {/* 조언이 무엇을 보고 만든 것인지(지금 냉장고 상태)를 작고 연하게 알린다 (D-105 의 AI 안내 한 줄, D-158 과 같은 말투) */}
            <span className="advice__note">냉장고 상태기반 조언이에요.</span>
          </div>
        </div>
        <button type="button" className="button button--primary advice__button" disabled={loading} onClick={() => void ask()}>
          {loading ? '조언 듣는 중…' : '조언 듣기'}
        </button>
      </div>

      {state.kind === 'idle' && <p className="advice__hint">버튼을 누르면 지금 냉장고와 기록을 보고 알려 드려요.</p>}

      {loading && (
        <div className="advice__skeleton" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      )}

      {result?.status === 'ok' && (
        <ul className="advice__list">
          {result.advice.map((text, i) => (
            <li key={i} className="advice__item" style={{ ['--i' as string]: i }}>
              <span className="advice__bulb" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M12 3a6 6 0 0 0-3.6 10.8c.7.6 1.1 1.3 1.1 2.2h5c0-.9.4-1.6 1.1-2.2A6 6 0 0 0 12 3z" fill="#ffd23f" stroke="#e0a800" strokeWidth="1" />
                  <path d="M9.8 18.2h4.4M10.4 20.4h3.2" stroke="#8a97a6" strokeWidth="1.6" strokeLinecap="round" />
                  <path d="M10.4 8.4a2.2 2.2 0 0 1 1.9-1.2" stroke="#fff" strokeWidth="1.3" strokeLinecap="round" fill="none" />
                </svg>
              </span>
              <span className="advice__text">{text}</span>
            </li>
          ))}
        </ul>
      )}

      {result?.status === 'no_data' && (
        <div className="advice__empty">
          <p>아직 조언할 내용이 없어요. 식품을 등록하면 조언해 드릴게요.</p>
          <button type="button" className="button button--primary" onClick={onAddFood}>
            냉장고에 넣기
          </button>
        </div>
      )}

      {result?.status === 'failed' && <ErrorNotice message={result.message ?? ADVICE_FAILED} />}
    </section>
  )
}
