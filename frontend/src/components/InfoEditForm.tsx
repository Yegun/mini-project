import { useState } from 'react'
import { buildInfoPatch, checkInfoForm, isInfoChanged, valuesFromDetail } from '../lib/editForm'
import type { FormValues } from '../lib/registerForm'
import type { FoodDetail, SaveResult, UpdateFoodInput } from '../types/foodDetail'
import type { FieldErrors, FieldName } from '../types/register'
import ExpiryRewriteField from './ExpiryRewriteField'
import FormField from './FormField'
import QuantityUnitDateFields from './QuantityUnitDateFields'

interface Props {
  food: FoodDetail
  busy: boolean // 화면 전체에서 요청 중이면 잠근다
  onSave: (patch: UpdateFoodInput) => Promise<SaveResult> // 성공하면 화면이 홈으로 간다
}

const FIELD_OF: Record<string, FieldName | undefined> = {
  name: 'name',
  quantity: 'quantity',
  unit: 'unit',
  purchaseDate: 'purchase_date',
}

// 정보 고치기: 이름 · 수량 · 단위 · 구매일 (5.2). 기한을 다시 계산하는 일은 API 가 한다 (D-016).
export default function InfoEditForm({ food, busy, onSave }: Props) {
  const [values, setValues] = useState<FormValues>(() => valuesFromDetail(food))
  const [errors, setErrors] = useState<FieldErrors>({})
  const [expiryOpen, setExpiryOpen] = useState(false) // API 가 "기한 필요"라고 했을 때만 연다
  const [expiryDate, setExpiryDate] = useState('')

  function change(patch: Partial<FormValues>) {
    setValues((v) => ({ ...v, ...patch }))
    const touched = Object.keys(patch).map((k) => FIELD_OF[k])
    setErrors((prev) => {
      const next = { ...prev }
      for (const field of touched) if (field) delete next[field]
      return next
    })
    // 이름·구매일이 바뀌면 기한이 필요한지 API 가 다시 판단하게 한다
    if ('name' in patch || 'purchaseDate' in patch) {
      setExpiryOpen(false)
      setExpiryDate('')
    }
  }

  async function submit() {
    const found = checkInfoForm(values, expiryOpen, expiryDate)
    setErrors(found)
    if (Object.keys(found).length > 0) return

    const patch = buildInfoPatch(food, values)
    if (expiryOpen) patch.expiry_date = expiryDate
    const result = await onSave(patch)

    if (result.status === 'need_expiry') {
      setExpiryOpen(true)
    } else if (result.status === 'invalid') {
      setErrors(result.fieldErrors)
      if (result.fieldErrors.expiry) setExpiryOpen(true)
    }
    // 성공이면 홈으로 가고, 실패(failed)는 화면 위 오류 알림이 보인다. 입력값은 그대로 남는다.
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
      <FormField label="이름" id="name" error={errors.name}>
        <input
          id="name"
          className="input"
          type="text"
          autoComplete="off"
          value={values.name}
          disabled={busy}
          aria-invalid={Boolean(errors.name)}
          aria-describedby={errors.name ? 'name-error' : undefined}
          onChange={(e) => change({ name: e.target.value })}
        />
      </FormField>

      <QuantityUnitDateFields values={values} errors={errors} disabled={busy} onChange={change} />

      {expiryOpen && (
        <ExpiryRewriteField
          id="info-expiry"
          value={expiryDate}
          error={errors.expiry}
          disabled={busy}
          onChange={(date) => {
            setExpiryDate(date)
            setErrors((prev) => ({ ...prev, expiry: undefined }))
          }}
        />
      )}

      <button
        type="submit"
        className="button button--primary button--wide"
        disabled={busy || !isInfoChanged(food, values)}
      >
        {busy ? '저장하는 중…' : '정보 저장'}
      </button>
    </form>
  )
}
