import { useRef, useState } from 'react'
import { restoreFood } from '../api/records'
import AdviceCard from '../components/AdviceCard'
import EmptyHome from '../components/EmptyHome'
import ErrorNotice from '../components/ErrorNotice'
import RecordIcon from '../components/RecordIcon'
import RecordSheet, { type RecordKind } from '../components/RecordSheet'
import StorageIcon from '../components/StorageIcon'
import { STATUS_LABEL, statusColor } from '../lib/statusColor'
import { useRecords } from '../hooks/useRecords'
import CategoryIcon from '../components/CategoryIcon'
import { CATEGORIES, CATEGORY_LABEL, STORAGE_LABEL, type ExpiryStatus, type Storage } from '../types/food'
import type { RecordsData } from '../types/records'
import '../components/Register.css'
import '../components/FoodCapsules.css' // 식품 종류 캡슐 색(cap--vegetable 등)
import '../components/Records.css'

interface Props {
  initial?: RecordsData // 탭을 눌러 올 때 이미 불러온 기록 (D-086)
  onAddFood: () => void // 모두 비었을 때의 식품 등록 버튼 (D-071)
}

// 사용자 확정 문구 (OQ-03)
const LOAD_FAILED = '기록을 불러오지 못했어요. 잠시 뒤에 다시 시도해 주세요.'
const RESTORE_FAILED = '홈으로 되돌리지 못했어요. 잠시 뒤에 다시 시도해 주세요.'

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
          <AdviceCard onAddFood={onAddFood} />
          <RecordsView
            data={result.data}
            restoringId={restoringId}
            error={error}
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
  error: string | null // 되돌리기 실패 안내. 팝업 안에서 보인다
  onRestore: (id: string) => void
  onAddFood: () => void
}

function RecordsView({ data, restoringId, error, onRestore, onAddFood }: ViewProps) {
  const { summary, foods } = data
  const byCategory = summary.by_category // 서버에 아직 없을 수 있다
  const noProcessed = foods.eaten.length === 0 && foods.discarded.length === 0
  // 다 먹음 · 버림 · 현재 식품이 모두 없으면 0 과 함께 안내 문구 + 등록 버튼 (D-071)
  const allEmpty = noProcessed && summary.food_kinds === 0
  // 카드를 누르면 그 종류의 처리한 식품이 아래에서 올라오는 팝업으로 열린다. null 이면 닫혀 있다.
  // 팝업을 연 채로 되돌려도(refresh) 이 화면은 그대로라서 팝업이 닫히지 않는다.
  const [sheet, setSheet] = useState<RecordKind | null>(null)

  return (
    <>
      <section className="records__section" aria-labelledby="records-now">
        <h2 className="records__heading" id="records-now">
          지금 냉장고
        </h2>
        <div className="rn">
          {/* 현재 총 식품 종류: 큰 숫자 */}
          <div className="rn__total">
            <StorageIcon storage="fridge" className="rn__total-icon" />
            <div className="rn__total-text">
              <span className="rn__total-label">현재 총 식품 종류</span>
              <span className="rn__total-num">
                <strong>{summary.food_kinds}</strong>종류
              </span>
            </div>
          </div>

          {/* 보관 상태별: 상온 · 냉장 · 냉동 타일 (그림 + 이름 + 수) */}
          <div className="rn__block">
            <h3 className="rn__sub">보관 상태별</h3>
            <ul className="rn__tiles">
              {STORAGES.map((s) => (
                <li key={s} className={`rn__tile cap--${s}`}>
                  <StorageIcon storage={s} className="rn__tile-icon" />
                  <span className="rn__tile-label">{STORAGE_LABEL[s]}</span>
                  <span className="rn__tile-num">
                    <strong>{summary.by_storage[s]}</strong>개
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* 서버가 종류별 수(by_category)를 주기 전에는 이 칸이 보이지 않는다 (types/records.ts) */}
          {byCategory && (
            <div className="rn__block">
              <h3 className="rn__sub">식품 종류별</h3>
              <div className="records__kinds">
                {CATEGORIES.map((c) => (
                  <span key={c} className={byCategory[c] === 0 ? `cap cap--${c} records__kind--zero` : `cap cap--${c}`}>
                    <CategoryIcon category={c} className="cap__icon" />
                    {CATEGORY_LABEL[c]} {byCategory[c]}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 식품 상태별: 상태 색 알약 (여유 · 주의 · 임박 · 지남). 색은 홈과 같다 */}
          <div className="rn__block">
            <h3 className="rn__sub">식품 상태별</h3>
            <ul className="rn__stats">
              {STATUSES.map((s) => (
                <li
                  key={s}
                  className="rn__stat"
                  data-status={s}
                  style={{ ['--sc' as string]: statusColor(s) }}
                >
                  <span className="rn__stat-dot" aria-hidden="true" />
                  <span className="rn__stat-label">{STATUS_LABEL[s]}</span>
                  <strong className="rn__stat-num">{summary.by_status[s]}</strong>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="records__section" aria-labelledby="records-done">
        <h2 className="records__heading" id="records-done">
          정리한 것
        </h2>
        <div className="records__cards">
          <CountCard
            kind="eaten"
            title="먹은 것"
            year={summary.eaten.year}
            month={summary.eaten.month}
            onOpen={() => setSheet('eaten')}
          />
          <CountCard
            kind="discarded"
            title="버린 것"
            year={summary.discarded.year}
            month={summary.discarded.month}
            onOpen={() => setSheet('discarded')}
          />
        </div>
      </section>

      {allEmpty && <EmptyHome onAdd={onAddFood} />}

      {/* 카드를 누르면 아래에서 올라오는 팝업: 누른 종류의 처리한 식품과 되돌리기 버튼 */}
      <RecordSheet
        kind={sheet}
        foods={sheet ? foods[sheet] : []}
        restoringId={restoringId}
        error={error}
        onRestore={onRestore}
        onClose={() => setSheet(null)}
      />
    </>
  )
}

// 누르면 처리한 식품 팝업이 올라오는 카드(버튼). 오른쪽 위에 그림이 붙는다.
// 버린 식품 카드는 이번 달에 버린 식품이 있을 때만 쓰레기통 주위에 파리가 난다.
function CountCard({
  kind,
  title,
  year,
  month,
  onOpen,
}: {
  kind: RecordKind
  title: string
  year: number
  month: number
  onOpen: () => void
}) {
  return (
    <button type="button" className="records__card" data-kind={kind} aria-haspopup="dialog" onClick={onOpen}>
      <span className="records__card-top">
        <span className="records__card-title">{title}</span>
        <RecordIcon kind={kind} flies={kind === 'discarded' && month > 0} className="records__card-icon" />
      </span>
      {/* 이번 달 수를 크게, 올해 수는 아래에 작게 */}
      <span className="records__card-hero">
        <span className="records__card-period">이번 달</span>
        <span className="records__card-big">
          <strong className="records__card-num">{month}</strong>
          <span className="records__card-unit">개</span>
        </span>
      </span>
      <span className="records__card-foot">
        <span className="records__card-year">
          올해 <strong>{year}</strong>개
        </span>
        <span className="records__card-more">
          목록
          <span className="records__card-chev" aria-hidden="true" />
        </span>
      </span>
    </button>
  )
}
