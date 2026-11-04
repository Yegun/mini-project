import { useEffect, useRef, useState } from 'react'
import { registerBulk } from '../api/bulk'
import { searchRules } from '../api/rules'
import {
  checkLine,
  isEdited,
  linesFromAnalysis,
  valuesOf,
  type ReviewLine,
} from '../lib/reviewForm'
import type { BulkItemInput } from '../types/bulk'
import type { Storage } from '../types/food'
import type { AnalyzeData } from '../types/photo'
import type { FieldName } from '../types/register'
import ErrorNotice from './ErrorNotice'
import ExpiryRewriteField from './ExpiryRewriteField'
import FormField from './FormField'
import QuantityUnitDateFields from './QuantityUnitDateFields'
import StoragePicker from './StoragePicker'

interface Props {
  analysis: AnalyzeData // analysis_id 가 있는 읽기 결과
  onDone: () => void // 한꺼번에 등록 성공 → 홈으로
  onReupload: () => void // 읽기 결과가 만료됨 → 사진 올리기로 (사진을 다시 올려야 한다)
  onDirtyChange?: (dirty: boolean) => void // 고치거나 뺀 것이 있는지 (탭 이동 확인 창, D-083)
}

// 사용자 확정 문구 (ARCH 3절)
const EXPIRED = '사진을 다시 올려 주세요.'
// 사용자 확정 문구 (SCREEN-SPEC 13.1 의 9번)
const SAVE_FAILED = '등록하지 못했어요. 아무것도 등록되지 않았어요. 잠시 뒤에 다시 시도해 주세요.'
const NAME_CHECKING = '이름을 확인하는 중이에요. 잠시 뒤에 다시 눌러 주세요.'
const NAME_CHECK_FAILED = '이름을 확인하지 못했어요. 이름 칸을 다시 눌러 주세요.'

const NAME_CHECK_DELAY = 400 // 이름을 고친 뒤 규칙표에서 찾기까지 기다리는 시간(ms)

// 확인 화면과 한꺼번에 등록 (US-019, US-020, SCREEN-SPEC 5.4).
// 식품 한 개를 카드 한 장으로 보이고, 줄마다 고치거나 뺄 수 있다 (D-108, SCREEN-SPEC 13.1 의 11번).
export default function PhotoReview({ analysis, onDone, onReupload, onDirtyChange }: Props) {
  const [lines, setLines] = useState<ReviewLine[]>(() => linesFromAnalysis(analysis)) // 처음에는 모두 선택 (D-109)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expired, setExpired] = useState(false)
  const lock = useRef(false) // 연타해도 요청은 한 번 (D-112)
  const seqs = useRef<number[]>([]) // 늦게 온 옛 규칙표 검색 결과가 덮어쓰지 않게
  const timers = useRef<(ReturnType<typeof setTimeout> | undefined)[]>([])

  const edited = lines.some(isEdited)
  useEffect(() => {
    onDirtyChange?.(edited)
  }, [edited, onDirtyChange])

  useEffect(() => {
    const pending = timers.current
    return () => pending.forEach((t) => clearTimeout(t))
  }, [])

  function setLine(i: number, fn: (line: ReviewLine) => ReviewLine) {
    setLines((prev) => prev.map((line, k) => (k === i ? fn(line) : line)))
  }

  // 값이 바뀌면 그 칸의 안내를 지운다
  function change(i: number, patch: Partial<ReviewLine>, touched: FieldName[]) {
    setLine(i, (line) => {
      const errors = { ...line.errors }
      for (const field of touched) delete errors[field]
      return { ...line, ...patch, errors }
    })
  }

  // 고친 이름이 규칙표에 있는지 찾는다 (C1). 있으면 규칙표 값으로 API 가 계산하고, 없으면 기한 입력칸이 열린다 (SCREEN-SPEC 5.4)
  async function checkName(i: number, name: string) {
    const seq = (seqs.current[i] = (seqs.current[i] ?? 0) + 1)
    try {
      const { rules } = await searchRules(name)
      if (seqs.current[i] !== seq) return
      const match = rules.find((r) => r.name === name) ?? rules[0] // 별칭으로 찾았으면 이름이 다를 수 있다. 최종 판단은 API 가 한다
      setLine(i, (line) => {
        if (!match) return { ...line, nameCheck: 'manual', ruleOptions: undefined }
        const allowed = match.storages.find((s) => s.storage === line.storage)?.allowed
        return {
          ...line,
          nameCheck: 'rule',
          ruleOptions: match.storages,
          storage: allowed ? line.storage : match.default_storage,
          expiryDate: '',
          errors: { ...line.errors, expiry: undefined },
        }
      })
    } catch {
      if (seqs.current[i] === seq) setLine(i, (line) => ({ ...line, nameCheck: 'error' }))
    }
  }

  function changeName(i: number, value: string) {
    clearTimeout(timers.current[i])
    seqs.current[i] = (seqs.current[i] ?? 0) + 1 // 진행 중인 검색 결과는 버린다
    const trimmed = value.trim()
    const original = lines[i].item.name
    if (trimmed === '' || trimmed === original) {
      change(i, { name: value, nameCheck: 'original', ruleOptions: undefined, expiryDate: '' }, ['name', 'expiry'])
      return
    }
    change(i, { name: value, nameCheck: 'checking' }, ['name'])
    timers.current[i] = setTimeout(() => void checkName(i, trimmed), NAME_CHECK_DELAY)
  }

  // 이름 칸을 벗어나면 기다리지 않고 바로 확인한다. 확인에 실패했던 줄은 다시 확인한다
  function blurName(i: number) {
    const line = lines[i]
    const trimmed = line.name.trim()
    if (trimmed === '' || (line.nameCheck !== 'checking' && line.nameCheck !== 'error')) return
    clearTimeout(timers.current[i])
    setLine(i, (l) => ({ ...l, nameCheck: 'checking' }))
    void checkName(i, trimmed)
  }

  async function submit() {
    if (lock.current) return
    const chosen = lines.map((line, i) => ({ line, i })).filter(({ line }) => line.included)
    if (chosen.length === 0) return // 모두 빼면 등록 버튼을 누를 수 없다 (US-019)

    setError(null)
    setExpired(false)
    if (chosen.some(({ line }) => line.nameCheck === 'checking')) {
      setError(NAME_CHECKING)
      return
    }
    // 미리 검사. 이름을 확인하지 못한 줄은 이름 칸에 안내한다
    const found = chosen.map(({ line }) => {
      const errors = checkLine(line)
      if (line.nameCheck === 'error') errors.name = NAME_CHECK_FAILED
      return errors
    })
    setLines((prev) =>
      prev.map((line, k) => {
        const at = chosen.findIndex(({ i }) => i === k)
        return at === -1 ? line : { ...line, errors: found[at] }
      }),
    )
    if (found.some((errors) => Object.keys(errors).length > 0)) return

    const items: BulkItemInput[] = chosen.map(({ line }) => ({
      item_no: line.item.item_no,
      name: line.name.trim(),
      quantity: Number(line.quantity.trim()),
      unit: line.unit.trim(),
      purchase_date: line.purchaseDate,
      storage: line.storage as Storage, // checkLine 이 비어 있지 않음을 확인했다
      ...(line.nameCheck === 'manual' ? { expiry_date: line.expiryDate } : {}),
    }))

    lock.current = true
    setSubmitting(true)
    const res = await registerBulk({ analysis_id: analysis.analysis_id as string, items })
    lock.current = false
    setSubmitting(false) // 어떤 실패든 확인하던 목록과 고친 내용은 그대로 두고 버튼만 다시 누를 수 있게 한다

    if (res.status === 'ok') {
      onDone()
    } else if (res.status === 'expired') {
      setError(res.message ?? EXPIRED)
      setExpired(true)
    } else if (res.status === 'invalid' && res.field && res.message) {
      const target = chosen[res.index]?.i // 오류의 줄 위치는 보낸 목록 기준이다 (API-SPEC 5절 27번)
      const field = res.field
      const message = res.message
      if (target !== undefined) setLine(target, (line) => ({ ...line, errors: { ...line.errors, [field]: message } }))
      else setError(message)
    } else {
      setError(res.message || SAVE_FAILED) // 전부 취소되어 아무것도 등록되지 않았다. 확인하던 목록은 그대로다 (D-110)
    }
  }

  const includedCount = lines.filter((l) => l.included).length

  return (
    <form
      className="register__form"
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        void submit()
      }}
    >
      {error && (
        <div className="review__notice">
          <ErrorNotice message={error} />
          {expired && (
            <button type="button" className="button button--primary" onClick={onReupload}>
              사진 다시 올리기
            </button>
          )}
        </div>
      )}

      <ul className="review__list" aria-label="읽은 식품">
        {lines.map((line, i) => (
          <ReviewCard
            key={line.item.item_no}
            index={i}
            line={line}
            disabled={submitting}
            onToggle={() => setLine(i, (l) => ({ ...l, included: !l.included }))}
            onName={(value) => changeName(i, value)}
            onNameBlur={() => blurName(i)}
            onValues={(patch) =>
              change(
                i,
                {
                  ...(patch.quantity !== undefined && { quantity: patch.quantity }),
                  ...(patch.unit !== undefined && { unit: patch.unit }),
                  ...(patch.purchaseDate !== undefined && { purchaseDate: patch.purchaseDate }),
                },
                [
                  ...(patch.quantity !== undefined ? (['quantity'] as FieldName[]) : []),
                  ...(patch.unit !== undefined ? (['unit'] as FieldName[]) : []),
                  ...(patch.purchaseDate !== undefined ? (['purchase_date'] as FieldName[]) : []),
                ],
              )
            }
            onStorage={(storage) => change(i, { storage }, ['storage'])}
            onExpiry={(expiryDate) => change(i, { expiryDate }, ['expiry'])}
          />
        ))}
      </ul>

      <button
        type="submit"
        className="button button--primary button--wide"
        disabled={submitting || includedCount === 0}
      >
        {submitting ? '등록하는 중…' : '한꺼번에 등록'}
      </button>
    </form>
  )
}

interface CardProps {
  index: number
  line: ReviewLine
  disabled: boolean
  onToggle: () => void
  onName: (value: string) => void
  onNameBlur: () => void
  onValues: (patch: Partial<ReturnType<typeof valuesOf>>) => void
  onStorage: (storage: Storage) => void
  onExpiry: (date: string) => void
}

// 식품 한 개의 카드: 이름 · 수량 · 단위 · 구매일 · 보관 방법(방법마다 최대 보관기간) · 기한 · 빼기
function ReviewCard({ index, line, disabled, onToggle, onName, onNameBlur, onValues, onStorage, onExpiry }: CardProps) {
  const p = `review-${line.item.item_no}-`
  const off = !line.included
  const useOriginal = line.nameCheck === 'original' || line.nameCheck === 'checking' || line.nameCheck === 'error'
  // 읽은 이름 그대로면 AI(또는 규칙표)가 알려 준 가능 여부와 최대 보관기간을, 이름을 고쳤으면 규칙표 검색 결과를 쓴다 (D-104)
  const options = useOriginal
    ? line.item.storages.map((s) => ({ storage: s.storage, allowed: s.allowed }))
    : line.nameCheck === 'rule'
      ? line.ruleOptions
      : undefined // 규칙표에 없는 이름은 세 방법 모두 고를 수 있다
  const maxDays = useOriginal
    ? Object.fromEntries(line.item.storages.map((s) => [s.storage, s.max_days]))
    : undefined

  return (
    <li className={off ? 'review-card review-card--off' : 'review-card'}>
      <div className="review-card__head">
        <strong>식품 {index + 1}</strong>
        <button type="button" className="button button--link" disabled={disabled} onClick={onToggle}>
          {off ? '다시 넣기' : '빼기'}
        </button>
      </div>

      <fieldset className="review-card__body" disabled={off || disabled}>
        <FormField label="이름" id={`${p}name`} error={line.errors.name}>
          <input
            id={`${p}name`}
            className="input"
            type="text"
            autoComplete="off"
            value={line.name}
            aria-invalid={Boolean(line.errors.name)}
            aria-describedby={line.errors.name ? `${p}name-error` : undefined}
            onChange={(e) => onName(e.target.value)}
            onBlur={onNameBlur}
          />
        </FormField>

        <QuantityUnitDateFields
          idPrefix={p}
          values={valuesOf(line)}
          errors={line.errors}
          onChange={onValues}
        />

        <FormField label="보관 방법" id={`${p}storage`} error={line.errors.storage}>
          <StoragePicker
            id={`${p}storage`}
            value={line.storage}
            options={options}
            maxDays={maxDays}
            onChange={onStorage}
          />
        </FormField>

        {line.nameCheck === 'manual' && (
          <ExpiryRewriteField id={`${p}expiry`} value={line.expiryDate} error={line.errors.expiry} onChange={onExpiry} />
        )}
      </fieldset>
    </li>
  )
}
