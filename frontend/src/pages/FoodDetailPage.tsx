import { useEffect, useRef, useState } from 'react'
import { deleteFood, processFood, updateFood } from '../api/foodDetail'
import ConfirmDialog from '../components/ConfirmDialog'
import ErrorNotice from '../components/ErrorNotice'
import FoodSummary from '../components/FoodSummary'
import InfoEditSheet from '../components/InfoEditSheet'
import { useFoodDetail } from '../hooks/useFoodDetail'
import type { ActionResult, SaveResult, UpdateFoodInput } from '../types/foodDetail'
import '../components/Register.css'
import '../components/FoodDetail.css'

interface Props {
  id: string
  onBack: () => void // 저장하지 않고 바로 전에 보던 화면으로 (D-085, D-150)
  onDone: () => void // 다 먹음 · 버림 · 삭제 성공 → 홈으로 (D-176). 정보 고치기는 홈으로 가지 않고 상세에 머문다 (D-173)
  onDirtyChange?: (dirty: boolean) => void // 정보 고치기 창에 고친 것이 있는지 (탭 이동 확인 창, D-083, D-175)
}

type Pending = 'eaten' | 'discarded' | 'delete' | 'close-edit'

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
  // 고친 값이 있는데 창 밖을 눌렀을 때 (D-175)
  'close-edit': { message: '입력한 내용이 사라져요. 닫을까요?', label: '닫기' },
}

// 식품 상세 화면 (SCREEN-SPEC 6절): 보기 전용 요약 + 정보 고치기 · 다 먹음 · 버림 · 삭제.
// 정보 고치기는 아래에서 올라오는 창에서 하고, 저장하면 창이 닫히고 같은 상세 화면에 머문다 (D-171 ~ D-173).
// 날짜 계산과 상태 판정은 하지 않는다. 결과는 API 가 정한다 (D-009, D-016).
export default function FoodDetailPage({ id, onBack, onDone, onDirtyChange }: Props) {
  const { result, refresh, reload } = useFoodDetail(id)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null) // 처리 · 삭제 실패 (화면 위 오류 알림)
  const [editOpen, setEditOpen] = useState(false)
  const [editError, setEditError] = useState<string | null>(null) // 저장 실패 (창 안 오류 메시지)
  const [editDirty, setEditDirty] = useState(false)
  const [pending, setPending] = useState<Pending | null>(null)
  const lock = useRef(false) // 연타해도 요청은 한 번
  const errorBox = useRef<HTMLDivElement>(null)

  useEffect(() => {
    onDirtyChange?.(editOpen && editDirty)
  }, [editOpen, editDirty, onDirtyChange])

  // 아래쪽 버튼을 눌러 실패해도 화면 위 오류 알림이 보이게 한다
  useEffect(() => {
    if (error) errorBox.current?.scrollIntoView({ block: 'nearest' })
  }, [error])

  function openEdit() {
    setEditError(null)
    setEditDirty(false)
    setEditOpen(true)
  }

  function closeEdit() {
    setEditOpen(false)
    setEditDirty(false)
    setEditError(null)
  }

  // 창 밖 · Esc: 고친 값이 있으면 확인 창을 먼저 띄운다. 없으면 바로 닫는다 (D-084, D-175)
  function requestCloseEdit() {
    if (editDirty) setPending('close-edit')
    else closeEdit()
  }

  // 정보 고치기 저장: 성공하면 창을 닫고 같은 화면에 머물며 새 값을 보인다. 실패하면 창 안에 오류 메시지가 보이고 입력값은 그대로다
  async function saveInfo(patch: UpdateFoodInput): Promise<SaveResult> {
    if (lock.current) return { status: 'failed' }
    lock.current = true
    setBusy(true)
    setEditError(null)
    const res = await updateFood(id, patch)
    lock.current = false
    setBusy(false)
    if (res.status === 'ok') {
      closeEdit()
      refresh() // 상세에 바뀐 값과 새 기한이 보인다 (D-173)
    } else if (res.status === 'failed') {
      setEditError(res.message ?? SAVE_FAILED)
    }
    return res
  }

  // 처리 · 삭제: 성공하면 홈으로, 실패하면 화면 위 오류 알림 (D-176)
  async function runAction(request: () => Promise<ActionResult>) {
    if (lock.current) return { status: 'failed' } as ActionResult
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
    setError(res.message ?? ACTION_FAILED)
    return res
  }

  async function confirmPending() {
    if (!pending) return
    const kind = pending
    if (kind === 'close-edit') {
      setPending(null)
      closeEdit()
      return
    }
    const res = await runAction(() => (kind === 'delete' ? deleteFood(id) : processFood(id, kind)))
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

          <div className="detail__actions">
            <button type="button" className="button button--primary detail__edit" disabled={busy} onClick={openEdit}>
              정보 고치기
            </button>
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

          <InfoEditSheet
            open={editOpen}
            food={result.food}
            busy={busy}
            error={editError}
            onSave={saveInfo}
            onCancel={closeEdit}
            onRequestClose={requestCloseEdit}
            onDirtyChange={setEditDirty}
          />

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
