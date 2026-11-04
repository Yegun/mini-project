import { useRef, useState } from 'react'
import { deleteFood, processFood } from '../api/foodDetail'
import ConfirmDialog from '../components/ConfirmDialog'
import ErrorNotice from '../components/ErrorNotice'
import TrashSheet, { type TrashChoice } from '../components/TrashSheet'
import { useFoods } from '../hooks/useFoods'
import { withEulReul } from '../lib/josa'
import type { Food, FoodListResponse } from '../types/food'
import Home from './Home'

interface Props {
  initial?: FoodListResponse // 탭을 눌러 올 때 이미 불러온 목록 (D-086)
  onSelectFood: (id: string) => void // 달력 막대나 목록의 식품을 누르면 상세 화면으로
  onAddFood: (today: string) => void // 등록 화면으로. 구매일 기본값용으로 API 가 준 오늘 날짜를 함께 넘긴다
  onOpenCalendar: (data: FoodListResponse) => void // 연 · 월 옆 > : 전체 달력으로. 지금 불러온 목록을 그대로 쓴다 (ARCH 9절 31번)
}

// 임시 문구 (OQ-03). 처리는 기록 화면에서 홈으로 되돌릴 수 있어 "되돌릴 수 없어요"를 쓰지 않는다 (D-072, 사용자 확정 문구)
const ACTION_FAILED = '처리하지 못했어요. 잠시 뒤에 다시 시도해 주세요.'
const UNDO_HINT = '잘못 눌렀다면 기록 화면에서 홈으로 되돌릴 수 있어요.'

function confirmMessage(name: string, choice: TrashChoice): string {
  if (choice === 'eaten') return `${withEulReul(name)} 다 먹음으로 처리할까요? ${UNDO_HINT}`
  if (choice === 'discarded') return `${withEulReul(name)} 버림으로 처리할까요? ${UNDO_HINT}`
  return `${withEulReul(name)} 삭제할까요? 기록에서도 지워지고 되돌릴 수 없어요.`
}

const CONFIRM_LABEL: Record<TrashChoice, string> = { eaten: '다 먹었어요', discarded: '버렸어요', delete: '지우기' }

// 홈 화면: 목록을 불러와 Home 에 넘긴다. 로그아웃 버튼은 모든 화면 공통이라 App 에 있다 (D-130).
// 휴지통 흐름 (SCREEN-SPEC 4.8): 줄의 휴지통 → 아래에서 선택창 → 하나를 고르면 확인 창 → 확인하면 요청.
// 성공하면 줄이 사라지고(마지막 식품이면 안내 문구와 등록 버튼), 실패하면 오류 메시지가 보이고 그 줄은 그대로 남는다.
export default function HomePage({ initial, onAddFood, onSelectFood, onOpenCalendar }: Props) {
  const { result, reload, refresh } = useFoods(initial)
  const [target, setTarget] = useState<Food | null>(null) // 선택창이 열려 있는 식품
  const [pending, setPending] = useState<{ food: Food; choice: TrashChoice } | null>(null) // 확인 창
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const lock = useRef(false) // 연타해도 요청은 한 번 (D-112)

  function choose(choice: TrashChoice) {
    if (!target) return
    setPending({ food: target, choice })
    setTarget(null)
  }

  async function confirm() {
    if (!pending || lock.current) return
    lock.current = true
    setBusy(true)
    setError(null)
    const { food, choice } = pending
    const res = choice === 'delete' ? await deleteFood(food.id) : await processFood(food.id, choice)
    lock.current = false
    setBusy(false)
    setPending(null)
    if (res.status === 'ok') refresh() // 줄이 사라진다. 목록을 새로 불러온다
    else setError(res.message ?? ACTION_FAILED) // 그 줄은 그대로 남는다
  }

  return (
    <>
      {error && (
        <div className="app__notice">
          <ErrorNotice message={error} />
        </div>
      )}
      <Home
        result={result}
        onRetry={reload}
        onSelectFood={onSelectFood}
        onOpenFull={() => {
          if (result.status === 'ready') onOpenCalendar(result.data)
        }}
        onTrash={(food) => {
          setError(null)
          setTarget(food)
        }}
        onAddFood={() => {
          if (result.status === 'ready') onAddFood(result.data.today) // 등록 버튼은 목록을 불러온 뒤에만 보인다
        }}
      />
      <TrashSheet
        open={target !== null}
        name={target?.name ?? ''}
        category={target?.category ?? null}
        onChoose={choose}
        onCancel={() => setTarget(null)}
      />
      <ConfirmDialog
        open={pending !== null}
        message={pending ? confirmMessage(pending.food.name, pending.choice) : ''}
        confirmLabel={pending ? CONFIRM_LABEL[pending.choice] : ''}
        busy={busy}
        onConfirm={() => void confirm()}
        onCancel={() => setPending(null)}
      />
    </>
  )
}
