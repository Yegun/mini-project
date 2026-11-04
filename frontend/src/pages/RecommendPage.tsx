import { useEffect, useRef, useState } from 'react'
import { recommend } from '../api/recommendations'
import EmptyHome from '../components/EmptyHome'
import ErrorNotice from '../components/ErrorNotice'
import FormField from '../components/FormField'
import ThinkingScreen from '../components/ThinkingScreen'
import {
  CUISINE_LABEL,
  CUISINES,
  CUSTOM_CUISINE_MAX,
  MEAL_LABEL,
  MEALS,
  type Cuisine,
  type Meal,
  type RecommendData,
} from '../types/recommend'
import '../components/Register.css'
import '../components/Recommend.css'

interface Props {
  onAddFood: () => void // 가진 식품이 없을 때의 식품 등록 버튼 (OQ-05)
  onDirtyChange?: (dirty: boolean) => void // 기다리는 중인지. 기다리는 동안 탭을 누르면 확인 창이 뜬다 (SCREEN-SPEC 15.3 의 5번)
}

// 사용자 확정 문구 (OQ-03, ARCH 3절)
const AI_FAILED = 'AI 가 응답하지 못했어요. 다시 시도해 주세요.'
// 사용자 확정 문구 (SCREEN-SPEC 13.1 의 9번)
const NO_MATCH = '추천할 음식을 찾지 못했어요. 음식 종류를 바꿔 다시 추천받아 보세요.'

// 음식추천 화면 (US-021, US-022, SCREEN-SPEC 8절). 추천 결과는 저장하지 않아 화면을 나가면 사라진다 (D-122).
export default function RecommendPage({ onAddFood, onDirtyChange }: Props) {
  const [meal, setMeal] = useState<Meal | null>(null)
  const [cuisine, setCuisine] = useState<Cuisine | null>(null)
  const [cuisineText, setCuisineText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<RecommendData | null>(null)
  const lock = useRef(false) // 연타해도 요청은 한 번 (D-112)
  const runToken = useRef(0) // 취소하면 보낸 요청의 늦은 결과를 버린다 (D-154)

  useEffect(() => {
    onDirtyChange?.(loading) // 확인 중 화면이 보이는 동안만 탭 이동 확인 창을 띄운다
  }, [loading, onDirtyChange])

  // 끼니와 음식 종류를 고르고, '직접 입력'이면 글자를 적어야 추천받을 수 있다 (D-116 ~ D-118)
  const ready = meal !== null && cuisine !== null && (cuisine !== 'custom' || cuisineText.trim() !== '')

  async function run() {
    if (lock.current || !ready || meal === null || cuisine === null) return
    lock.current = true
    const token = ++runToken.current
    setLoading(true)
    setError(null)
    const res = await recommend({ meal, cuisine, cuisineText })
    if (token !== runToken.current) return // 취소했다: 늦게 온 결과는 쓰지 않는다 (SCREEN-SPEC 15.3)
    lock.current = false
    setLoading(false)
    if (res.status === 'ok') setData(res.data)
    else setError(res.message ?? AI_FAILED) // 고른 끼니 · 음식 종류는 그대로 남아 다시 시도할 수 있다
  }

  // 확인 중 화면의 취소: 기다리기를 멈추고 이 화면으로 돌아온다. 고른 끼니 · 음식 종류는 그대로 남는다 (D-154)
  function cancel() {
    runToken.current += 1
    lock.current = false
    setLoading(false)
  }

  // 추천을 기다리는 동안에는 확인 중 화면이 화면 전체를 쓴다 (SCREEN-SPEC 15절)
  if (loading) return <ThinkingScreen message="추천을 만들고 있어요" onCancel={cancel} />

  return (
    <main className="register">
      <header className="register__header">
        <h1 className="register__title">음식추천</h1>
      </header>

      <form
        className="register__form"
        onSubmit={(e) => {
          e.preventDefault()
          void run()
        }}
      >
        <FormField label="끼니" id="recommend-meal">
          <div className="choice-group" role="group" aria-labelledby="recommend-meal-label">
            {MEALS.map((m) => (
              <button
                key={m}
                type="button"
                className={meal === m ? 'choice choice--selected' : 'choice'}
                aria-pressed={meal === m}
                disabled={loading}
                onClick={() => setMeal(m)}
              >
                {MEAL_LABEL[m]}
              </button>
            ))}
          </div>
        </FormField>

        <FormField label="음식 종류" id="recommend-cuisine">
          <div className="choice-group choice-group--wrap" role="group" aria-labelledby="recommend-cuisine-label">
            {CUISINES.map((c) => (
              <button
                key={c}
                type="button"
                className={cuisine === c ? 'choice choice--selected' : 'choice'}
                aria-pressed={cuisine === c}
                disabled={loading}
                onClick={() => setCuisine(c)}
              >
                {CUISINE_LABEL[c]}
              </button>
            ))}
          </div>
        </FormField>

        {cuisine === 'custom' && (
          <FormField label="원하는 음식 종류" id="recommend-custom">
            <input
              id="recommend-custom"
              className="input"
              type="text"
              autoComplete="off"
              maxLength={CUSTOM_CUISINE_MAX}
              placeholder="예: 국물 요리"
              value={cuisineText}
              disabled={loading}
              onChange={(e) => setCuisineText(e.target.value)}
            />
          </FormField>
        )}

        <button type="submit" className="button button--primary button--wide" disabled={!ready || loading}>
          {loading ? '추천받는 중…' : '추천받기'}
        </button>
      </form>

      {loading && <p role="status">AI 가 음식을 찾고 있어요…</p>}

      {error && <ErrorNotice message={error} />}

      {data && !loading && <Result data={data} onAddFood={onAddFood} />}
    </main>
  )
}

function Result({ data, onAddFood }: { data: RecommendData; onAddFood: () => void }) {
  // 가진 식품이 없음: 안내 + 식품 등록 버튼 (OQ-05)
  if (data.dishes.length === 0 && data.reason === 'no_foods') return <EmptyHome onAdd={onAddFood} />
  if (data.dishes.length === 0) return <p className="recommend__empty">{NO_MATCH}</p>

  return (
    <ul className="recommend__list" aria-label="추천한 음식">
      {data.dishes.map((dish) => {
        const have = dish.ingredients.filter((i) => i.have).map((i) => i.name)
        const missing = dish.ingredients.filter((i) => !i.have).map((i) => i.name)
        return (
          <li key={dish.name} className="recommend__card">
            <h2 className="recommend__name">{dish.name}</h2>
            {/* 재료는 가진 것과 지금 없는 것을 구분해 보인다. 만드는 법은 없다 (D-115, D-121) */}
            <p className="recommend__ingredients">
              <span className="recommend__label">가진 재료</span> {have.length > 0 ? have.join(', ') : '없어요'}
            </p>
            {missing.length > 0 && (
              <p className="recommend__ingredients recommend__ingredients--missing">
                <span className="recommend__label">없는 재료</span> {missing.join(', ')}
              </p>
            )}
          </li>
        )
      })}
    </ul>
  )
}
