import { useEffect, useState } from 'react'
import { buildInfoPatch, checkInfoForm, isInfoChanged, valuesFromDetail } from '../lib/editForm'
import type { FormValues } from '../lib/registerForm'
import type { FoodDetail, SaveResult, UpdateFoodInput } from '../types/foodDetail'
import type { FieldErrors, FieldName } from '../types/register'
import CategoryPicker from './CategoryPicker'
import ErrorNotice from './ErrorNotice'
import ExpiryRewriteField from './ExpiryRewriteField'
import FormField from './FormField'
import QuantityUnitDateFields from './QuantityUnitDateFields'
import StoragePicker from './StoragePicker'

interface Props {
  food: FoodDetail
  busy: boolean // 저장하는 동안 잠근다
  error: string | null // 저장 실패의 쉬운 오류 메시지. 입력한 값은 그대로 남는다 (D-172, OQ-04)
  onSave: (patch: UpdateFoodInput) => Promise<SaveResult> // 성공하면 창이 닫히고 상세에 머문다 (D-173)
  onCancel: () => void // 취소: 고치던 값을 버리고 닫는다
  onDirtyChange?: (dirty: boolean) => void // 고친 것이 있는지 (창 밖 · 탭 이동 확인 창, D-083, D-175)
}

const FIELD_OF: Record<string, FieldName | undefined> = {
  name: 'name',
  category: 'category',
  quantity: 'quantity',
  unit: 'unit',
  purchaseDate: 'purchase_date',
  storage: 'storage',
}

// 정보 고치기 (SCREEN-SPEC 6.2, 6.3): 이름 · 구매일 · 수량 · 단위 · 보관 방법(직접 등록 식품은 식품 종류도)을 한 번에 고치고
// 한 번에 저장한다. 이름 → 보관 방법 → 구매일 순서로 기한을 다시 계산하는 일은 API 가 한다 (D-016, D-174).
// 기한을 다시 적어야 하면(규칙표에 없는 이름, 직접 등록 식품의 보관 방법 변경) 같은 창에 기한 입력칸이 나타난다.
export default function InfoEditForm({ food, busy, error, onSave, onCancel, onDirtyChange }: Props) {
  const [values, setValues] = useState<FormValues>(() => valuesFromDetail(food))
  const [errors, setErrors] = useState<FieldErrors>({})
  const [expiryOpen, setExpiryOpen] = useState(false) // API 가 "기한 필요"라고 했을 때만 연다
  const [expiryDate, setExpiryDate] = useState('')

  // 처음 값과 다르게 고쳤거나 기한을 다시 적었으면 "고친 것이 있다" (SCREEN-SPEC 6.2 예외, 11.1-6)
  const dirty = isInfoChanged(food, values) || expiryDate !== ''
  useEffect(() => {
    onDirtyChange?.(dirty)
  }, [dirty, onDirtyChange])

  function change(patch: Partial<FormValues>) {
    setValues((v) => ({ ...v, ...patch }))
    const touched = Object.keys(patch).map((k) => FIELD_OF[k])
    setErrors((prev) => {
      const next = { ...prev }
      for (const field of touched) if (field) delete next[field]
      return next
    })
    // 이름 · 보관 방법 · 구매일이 바뀌면 기한이 필요한지 API 가 다시 판단하게 한다
    if ('name' in patch || 'storage' in patch || 'purchaseDate' in patch) {
      setExpiryOpen(false)
      setExpiryDate('')
    }
  }

  async function submit() {
    const found = checkInfoForm(values, expiryOpen, expiryDate)
    setErrors(found)
    if (Object.keys(found).length > 0) return

    const patch = buildInfoPatch(food, values)
    if (!expiryOpen && Object.keys(patch).length === 0) {
      setValues(valuesFromDetail(food)) // 글자만 다른 입력(01 → 1)은 요청 없이 저장된 값 모양으로 되돌린다
      return
    }
    if (expiryOpen) patch.expiry_date = expiryDate
    const result = await onSave(patch)

    if (result.status === 'need_expiry') {
      setExpiryOpen(true)
    } else if (result.status === 'invalid') {
      setErrors(result.fieldErrors)
      if (result.fieldErrors.expiry) setExpiryOpen(true)
    }
    // 성공이면 창이 닫히고, 실패(failed)는 이 창 위쪽에 쉬운 오류 메시지가 보인다. 입력한 값은 그대로 남는다.
  }

  return (
    <form
      className="register__form"
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        void submit()
      }}
    >
      <h2 className="edit-form__title">정보 고치기</h2>

      {error && <ErrorNotice message={error} />}

      <FormField label="이름" id="edit-name" error={errors.name}>
        <input
          id="edit-name"
          className="input"
          type="text"
          autoComplete="off"
          value={values.name}
          disabled={busy}
          aria-invalid={Boolean(errors.name)}
          aria-describedby={errors.name ? 'edit-name-error' : undefined}
          onChange={(e) => change({ name: e.target.value })}
        />
      </FormField>

      {food.source === 'manual' && (
        <FormField label="식품 종류" id="edit-category" error={errors.category}>
          <CategoryPicker
            id="edit-category"
            value={values.category}
            disabled={busy}
            onChange={(category) => change({ category })}
          />
        </FormField>
      )}

      <QuantityUnitDateFields values={values} errors={errors} disabled={busy} onChange={change} />

      <FormField label="보관 방법" id="edit-storage" error={errors.storage}>
        <StoragePicker
          id="edit-storage"
          value={values.storage}
          options={food.storages}
          disabled={busy}
          onChange={(storage) => change({ storage })}
        />
      </FormField>

      {expiryOpen && (
        <ExpiryRewriteField
          id="edit-expiry"
          value={expiryDate}
          error={errors.expiry}
          disabled={busy}
          onChange={(date) => {
            setExpiryDate(date)
            setErrors((prev) => ({ ...prev, expiry: undefined }))
          }}
        />
      )}

      <div className="edit-form__buttons">
        <button type="button" className="button" disabled={busy} onClick={onCancel}>
          취소
        </button>
        <button type="submit" className="button button--primary" disabled={busy || !dirty}>
          {busy ? '저장하는 중…' : '저장'}
        </button>
      </div>
    </form>
  )
}
