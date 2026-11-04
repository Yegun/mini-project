import { formatKoreanDate } from '../lib/dateText'
import type { FormValues } from '../lib/registerForm'
import type { FieldErrors } from '../types/register'
import FormField from './FormField'

interface Props {
  values: FormValues
  errors: FieldErrors
  disabled?: boolean
  idPrefix?: string // 같은 화면에 입력칸 묶음이 여러 개일 때(확인 화면의 카드) id 가 겹치지 않게
  unitChips?: boolean // 단위 입력칸 아래에 자주 쓰는 단위 알약(개 · g · 봉 …). 누르면 단위 칸이 채워진다 (등록 폼)
  onChange: (patch: Partial<FormValues>) => void
}

// 자주 쓰는 단위. 누르면 단위 칸에 그대로 적힌 것과 같다 (칸에 직접 적어도 된다)
const COMMON_UNITS = ['개', 'g', 'kg', '봉', '팩', 'L']

// 규칙표 등록과 직접 등록이 같이 쓰는 입력칸: 수량 · 단위 · 구매일
export default function QuantityUnitDateFields({
  values,
  errors,
  disabled,
  idPrefix = '',
  unitChips = false,
  onChange,
}: Props) {
  const quantityId = `${idPrefix}quantity`
  const unitId = `${idPrefix}unit`
  const dateId = `${idPrefix}purchase-date`
  return (
    <>
      <div className="field-row">
        <FormField label="수량" id={quantityId} error={errors.quantity}>
          <input
            id={quantityId}
            className="input"
            type="text"
            inputMode="decimal"
            autoComplete="off"
            placeholder="예: 1, 0.5"
            value={values.quantity}
            disabled={disabled}
            aria-invalid={Boolean(errors.quantity)}
            aria-describedby={errors.quantity ? `${quantityId}-error` : undefined}
            onChange={(e) => onChange({ quantity: e.target.value })}
          />
        </FormField>
        <FormField label="단위" id={unitId} error={errors.unit}>
          <input
            id={unitId}
            className="input"
            type="text"
            autoComplete="off"
            placeholder="예: 개, g, 봉"
            value={values.unit}
            disabled={disabled}
            aria-invalid={Boolean(errors.unit)}
            aria-describedby={errors.unit ? `${unitId}-error` : undefined}
            onChange={(e) => onChange({ unit: e.target.value })}
          />
        </FormField>
      </div>
      {unitChips && (
        <div className="unit-chips" role="group" aria-label="자주 쓰는 단위">
          {COMMON_UNITS.map((u) => (
            <button
              key={u}
              type="button"
              className={values.unit.trim() === u ? 'unit-chip unit-chip--on' : 'unit-chip'}
              aria-pressed={values.unit.trim() === u}
              disabled={disabled}
              onClick={() => onChange({ unit: u })}
            >
              {u}
            </button>
          ))}
        </div>
      )}
      <FormField
        label="구매일"
        id={dateId}
        error={errors.purchase_date}
        hint={formatKoreanDate(values.purchaseDate)}
      >
        <input
          id={dateId}
          className="input"
          type="date"
          value={values.purchaseDate}
          disabled={disabled}
          aria-invalid={Boolean(errors.purchase_date)}
          aria-describedby={errors.purchase_date ? `${dateId}-error` : undefined}
          onChange={(e) => onChange({ purchaseDate: e.target.value })}
        />
      </FormField>
    </>
  )
}
