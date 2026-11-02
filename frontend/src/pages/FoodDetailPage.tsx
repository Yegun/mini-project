import { useCallback, useEffect, useRef, useState } from 'react'
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
  onBack: () => void // 저장하지 않고 바로 전에 보던 화면으로 (D-085)
  onDone: () => void // 저장 · 다 먹음 · 버림 · 삭제 성공 → 홈으로 (D-020)
  onDirtyChange?: (dirty: boolean) => void // 정보 고치기 · 보관 방법 중 하나라도 입력한 것이 있는지 (D-083)
}

type Pending = 'eaten' | 'discarded' | 'delete'

// 임시 문구 (OQ-03)
const SAVE_FAILED = '저장하지 못했어요. 잠시 뒤에 다시 시도해 주세요.'
const ACTION_FAILED = '처리하지 못했어요. 잠시 뒤에 다시 시도해 주세요.'
const CONFIRM: Record<Pending, { message: string; label: string }> = {
  // 처리는 기록 화면에서 홈으로 되돌릴 수 있다. "되돌릴 수 없어요"를 쓰지 않는다 (D-072, SCREEN-SPEC 11.1-9). 사용자 확정 문구
  eaten: {
    message: "'다 먹음'으로 정리할까요? 잘못 눌렀다면 기록 화면에서 홈으로 되돌릴 수 있어요.",
    label: '다 먹음',
  },
  discarded: {
    message: "'버림'으로 정리할까요? 잘못 눌렀다면 기록 화면에서 홈으로 되돌릴 수 있어요.",
    label: '버림',
  },
  delete: { message: '정말 삭제할까요? 기록에서도 지워지고 되돌릴 수 없어요.', label: '삭제' },
}

// 식품 상세 화면: 정보 고치기 · 보관 방법 바꾸기 · 다 먹음 / 버림 · 삭제.
// 날짜 계산과 상태 판정은 하지 않는다. 결과는 API 가 정한다 (D-009, D-016).
export default function FoodDetailPage({ id, onBack, onDone, onDirtyChange }: Props) {
  const { result, reload } = useFoodDetail(id)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<Pending | null>(null)
  const [infoDirty, setInfoDirty] = useState(false)
  const [storageDirty, setStorageDirty] = useState(false)
  const lock = useRef(false) // 연타해도 요청은 한 번
  const errorBox = useRef<HTMLDivElement>(null)

  const dirty = infoDirty || storageDirty
  useEffect(() => {
    onDirtyChange?.(dirty)
  }, [dirty, onDirtyChange])
  const onInfoDirty = useCallback((d: boolean) => setInfoDirty(d), [])
  const onStorageDirty = useCallback((d: boolean) => setStorageDirty(d), [])

  // 아래쪽 버튼을 눌러 실패해도 화면 위 오류 알림이 보이게 한다
  useEffect(() => {
    if (error) errorBox.current?.scrollIntoView({ block: 'nearest' })
  }, [error])

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
    if (res.status === 'failed') setError(res.message ?? failMessage) // API 문구가 있으면 그것을 보인다
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
        <button type="button" className="register__back" aria-label="뒤로 가기" onClick={onBack}>
          ‹
        </button>
        <h1 className="register__title">식품 상세</h1>
      </header>

      {result.status === 'loading' && <p role="status">불러오는 중…</p>}

      {result.status === 'error' && (
        <ErrorNotice
          message={result.message ?? '식품을 불러오지 못했어요. 잠시 뒤에 다시 시도해 주세요.'}
          onRetry={reload}
        />
      )}

      {result.status === 'ready' && (
        <>
          {error && (
            <div ref={errorBox}>
              <ErrorNotice message={error} />
            </div>
          )}
          <FoodSummary food={result.food} />

          <section className="detail__section" aria-labelledby="info-heading">
            <h2 className="detail__heading" id="info-heading">
              정보 고치기
            </h2>
            <InfoEditForm food={result.food} busy={busy} onSave={saveInfo} onDirtyChange={onInfoDirty} />
          </section>

          <section className="detail__section" aria-labelledby="storage-heading">
            <h2 className="detail__heading" id="storage-heading">
              보관 방법 바꾸기
            </h2>
            <StorageChangeForm
              food={result.food}
              busy={busy}
              onSave={saveStorage}
              onDirtyChange={onStorageDirty}
            />
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
