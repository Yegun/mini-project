import { useRef, useState } from 'react'
import { restoreFood } from '../api/records'
import EmptyHome from '../components/EmptyHome'
import ErrorNotice from '../components/ErrorNotice'
import { formatKoreanDate } from '../lib/dateText'
import { STATUS_LABEL, statusColor } from '../lib/statusColor'
import { useRecords } from '../hooks/useRecords'
import { STORAGE_LABEL, type ExpiryStatus, type Storage } from '../types/food'
import type { ProcessedFood, RecordsData } from '../types/records'
import '../components/Register.css'
import '../components/Records.css'

interface Props {
  initial?: RecordsData // 탭을 눌러 올 때 이미 불러온 기록 (D-086)
  onAddFood: () => void // 모두 비었을 때의 식품 등록 버튼 (D-071)
}

// 사용자 확정 문구 (OQ-03)
const LOAD_FAILED = '기록을 불러오지 못했어요. 잠시 뒤에 다시 시도해 주세요.'
const RESTORE_FAILED = '홈으로 되돌리지 못했어요. 잠시 뒤에 다시 시도해 주세요.'
const NOTHING_TO_RESTORE = '되돌릴 식품이 없어요.'

const STORAGES: Storage[] = ['room', 'fridge', 'freezer']
const STATUSES: ExpiryStatus[] = ['fresh', 'warning', 'soon', 'expired']

// 기록 화면 (US-013, US-015, SCREEN-SPEC 7절). 숫자는 API 가 세고 화면은 보여 주기만 한다 (D-009).
export default function RecordsPage({ initial, onAddFood }: Props) {
  const { result, reload, refresh } = useRecords(initial)
  const [restoringId, setRestoringId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const lock = useRef(false) // 연타해도 요청은 한 번 (D-100)

  async function restore(id: string) {
    if (lock.current) return
    lock.current = true
    setRestoringId(id)
    setError(null)
    const res = await restoreFood(id)
    lock.current = false
    setRestoringId(null)
    if (res.status === 'ok') refresh() // 목록에서 빠지고 숫자가 바뀐다 (D-075)
    else setError(res.message ?? RESTORE_FAILED) // 아무것도 바뀌지 않는다. 다시 누를 수 있다
  }

  return (
    <main className="register">
      <header className="register__header">
        <h1 className="register__title">기록</h1>
      </header>

      {result.status === 'loading' && <p role="status">불러오는 중…</p>}

      {result.status === 'error' && <ErrorNotice message={result.message ?? LOAD_FAILED} onRetry={reload} />}

      {result.status === 'ready' && (
        <>
          {error && <ErrorNotice message={error} />}
          <RecordsView
            data={result.data}
            restoringId={restoringId}
            onRestore={(id) => void restore(id)}
            onAddFood={onAddFood}
          />
        </>
      )}
    </main>
  )
}

interface ViewProps {
  data: RecordsData
  restoringId: string | null
  onRestore: (id: string) => void
  onAddFood: () => void
}

function RecordsView({ data, restoringId, onRestore, onAddFood }: ViewProps) {
  const { summary, foods } = data
  const noProcessed = foods.eaten.length === 0 && foods.discarded.length === 0
  // 다 먹음 · 버림 · 현재 식품이 모두 없으면 0 과 함께 안내 문구 + 등록 버튼 (D-071)
  const allEmpty = noProcessed && summary.food_kinds === 0

  return (
    <>
      <section className="records__section" aria-labelledby="records-done">
        <h2 className="records__heading" id="records-done">
          다 먹음 · 버림
        </h2>
        <div className="records__cards">
          <CountCard title="다 먹음" year={summary.eaten.year} month={summary.eaten.month} />
          <CountCard title="버림" year={summary.discarded.year} month={summary.discarded.month} />
        </div>
      </section>

      <section className="records__section" aria-labelledby="records-now">
        <h2 className="records__heading" id="records-now">
          지금 냉장고
        </h2>
        <dl className="records__table">
          <dt>현재 총 식품 종류</dt>
          <dd>{summary.food_kinds}종류</dd>
          <dt>보관 상태별</dt>
          <dd>{STORAGES.map((s) => `${STORAGE_LABEL[s]} ${summary.by_storage[s]}`).join(' · ')}</dd>
          <dt>식품 상태별</dt>
          <dd className="records__statuses">
            {STATUSES.map((s) => (
              <span key={s} className="records__status">
                <span className="records__dot" style={{ background: statusColor(s) }} aria-hidden="true" />
                {STATUS_LABEL[s]} {summary.by_status[s]}
              </span>
            ))}
          </dd>
        </dl>
      </section>

      {allEmpty && <EmptyHome onAdd={onAddFood} />}

      <section className="records__section" aria-labelledby="records-list">
        <h2 className="records__heading" id="records-list">
          처리한 식품
        </h2>
        {noProcessed ? (
          !allEmpty && <p className="records__empty">{NOTHING_TO_RESTORE}</p>
        ) : (
          <>
            <ProcessedGroup
              title="다 먹음"
              foods={foods.eaten}
              restoringId={restoringId}
              onRestore={onRestore}
            />
            <ProcessedGroup
              title="버림"
              foods={foods.discarded}
              restoringId={restoringId}
              onRestore={onRestore}
            />
          </>
        )}
      </section>
    </>
  )
}

function CountCard({ title, year, month }: { title: string; year: number; month: number }) {
  return (
    <div className="records__card">
      <p className="records__card-title">{title}</p>
      <p>
        올해 <strong>{year}</strong>개
      </p>
      <p>
        이번 달 <strong>{month}</strong>개
      </p>
    </div>
  )
}

interface GroupProps {
  title: string
  foods: ProcessedFood[]
  restoringId: string | null
  onRestore: (id: string) => void
}

// 다 먹음 / 버림을 나눠서, API 가 준 순서(최근 처리한 순) 그대로 보인다 (D-073, D-074)
function ProcessedGroup({ title, foods, restoringId, onRestore }: GroupProps) {
  return (
    <div className="records__group">
      <h3 className="records__group-title">{title}</h3>
      {foods.length === 0 ? (
        <p className="records__empty">없어요.</p>
      ) : (
        <ul className="records__list">
          {foods.map((food) => (
            <li key={food.id} className="records__item">
              {/* 한 줄에 이름 · 수량 · 처리한 날짜 (SCREEN-SPEC 11.1-5) */}
              <div className="records__item-text">
                <span className="records__item-name">{food.name}</span>
                <span className="records__item-meta">
                  {food.quantity}
                  {food.unit} · {formatKoreanDate(food.processed_date)}
                </span>
              </div>
              <button
                type="button"
                className="button"
                disabled={restoringId !== null}
                onClick={() => onRestore(food.id)}
              >
                {restoringId === food.id ? '되돌리는 중…' : '홈으로 되돌리기'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
