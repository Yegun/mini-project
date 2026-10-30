import { useRef, useState } from 'react'
import { changeFoodStorage, deleteFood, processFood, updateFood } from '../api/foodDetail'
import ConfirmDialog from '../components/ConfirmDialog'
import ErrorNotice from '../components/ErrorNotice'
import FoodSummary from '../components/FoodSummary'
import InfoEditForm from '../components/InfoEditForm'
import StorageChangeForm from '../components/StorageChangeForm'
import { useFoodDetail } from '../hooks/useFoodDetail'
import type {
  ActionResult,
  ChangeStorageInput,
  SaveResult,
  UpdateFoodInput,
} from '../types/foodDetail'
import '../components/Register.css'
import '../components/FoodDetail.css'

interface Props {
  id: string
  onBack: () => void // 저장하지 않고 홈으로
  onDone: () => void // 저장 · 다 먹음 · 버림 · 삭제 성공 → 홈으로 (D-020)
}

type Pending = 'eaten' | 'discarded' | 'delete'

// 임시 문구 (OQ-03)
const SAVE_FAILED = '저장하지 못했어요. 잠시 뒤에 다시 시도해 주세요.'
const ACTION_FAILED = '처리하지 못했어요. 잠시 뒤에 다시 시도해 주세요.'
const CONFIRM: Record<Pending, { message: string; label: string }> = {
  eaten: { message: "'다 먹음'으로 정리할까요? 되돌릴 수 없어요.", label: '다 먹음' },
  discarded: { message: "'버림'으로 정리할까요? 되돌릴 수 없어요.", label: '버림' },
  delete: { message: '정말 삭제할까요? 기록에서도 지워지고 되돌릴 수 없어요.', label: '삭제' },
}

// 식품 상세 화면: 정보 고치기 · 보관 방법 바꾸기 · 다 먹음 / 버림 · 삭제.
// 날짜 계산과 상태 판정은 하지 않는다. 결과는 API 가 정한다 (D-009, D-016).
export default function FoodDetailPage({ id, onBack, onDone }: Props) {
  const { result, reload } = useFoodDetail(id)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<Pending | null>(null)
  const lock = useRef(false) // 연타해도 요청은 한 번

  // 요청 하나를 보낸다. 성공하면 홈으로, 실패하면 화면 위 오류 알림. 입력값은 그대로 둔다.
  async function run<T extends SaveResult | ActionResult>(request: () => Promise<T>, failMessage: string) {
    if (lock.current) return { status: 'failed' } as T
    lock.current = true
    setBusy(true)
    setError(null)
    const res = await request()
    lock.current = false
    if (res.status === 'ok') {
      onDone()
      return res
    }
    setBusy(false)
    if (res.status === 'failed') setError(failMessage)
    return res
  }

  const saveInfo = (patch: UpdateFoodInput) => run(() => updateFood(id, patch), SAVE_FAILED)
  const saveStorage = (input: ChangeStorageInput) => run(() => changeFoodStorage(id, input), SAVE_FAILED)

  async function confirmPending() {
    if (!pending) return
    const kind = pending
    const res = await run(
      () => (kind === 'delete' ? deleteFood(id) : processFood(id, kind)),
      ACTION_FAILED,
    )
    if (res.status !== 'ok') setPending(null) // 실패하면 창을 닫고 오류 알림을 보인다
  }

  return (
    <main className="register">
      <header className="register__header">
        <button type="button" className="register__back" aria-label="홈으로 돌아가기" onClick={onBack}>
          ‹
        </button>
        <h1 className="register__title">식품 상세</h1>
      </header>

      {result.status === 'loading' && <p role="status">불러오는 중…</p>}

      {result.status === 'error' && (
        <ErrorNotice message="식품을 불러오지 못했어요. 잠시 뒤에 다시 시도해 주세요." onRetry={reload} />
      )}

      {result.status === 'ready' && (
        <>
          {error && <ErrorNotice message={error} />}
          <FoodSummary food={result.food} />

          <section className="detail__section" aria-labelledby="info-heading">
            <h2 className="detail__heading" id="info-heading">
              정보 고치기
            </h2>
            <InfoEditForm food={result.food} busy={busy} onSave={saveInfo} />
          </section>

          <section className="detail__section" aria-labelledby="storage-heading">
            <h2 className="detail__heading" id="storage-heading">
              보관 방법 바꾸기
            </h2>
            <StorageChangeForm food={result.food} busy={busy} onSave={saveStorage} />
          </section>

          <div className="detail__actions">
            <button type="button" className="button" disabled={busy} onClick={() => setPending('eaten')}>
              다 먹음
            </button>
            <button type="button" className="button" disabled={busy} onClick={() => setPending('discarded')}>
              버림
            </button>
            <button
              type="button"
              className="button button--danger"
              disabled={busy}
              onClick={() => setPending('delete')}
            >
              삭제
            </button>
          </div>

          <ConfirmDialog
            open={pending !== null}
            message={pending ? CONFIRM[pending].message : ''}
            confirmLabel={pending ? CONFIRM[pending].label : ''}
            busy={busy}
            onConfirm={() => void confirmPending()}
            onCancel={() => setPending(null)}
          />
        </>
      )}
    </main>
  )
}
