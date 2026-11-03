import { formatKoreanDate } from '../lib/dateText'
import type { FormValues } from '../lib/registerForm'
import type { FieldErrors } from '../types/register'
import FormField from './FormField'

interface Props {
  values: FormValues
  errors: FieldErrors
  disabled?: boolean
  idPrefix?: string // 같은 화면에 입력칸 묶음이 여러 개일 때(확인 화면의 카드) id 가 겹치지 않게
  onChange: (patch: Partial<FormValues>) => void
}

// 규칙표 등록과 직접 등록이 같이 쓰는 입력칸: 수량 · 단위 · 구매일
export default function QuantityUnitDateFields({ values, errors, disabled, idPrefix = '', onChange }: Props) {
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
