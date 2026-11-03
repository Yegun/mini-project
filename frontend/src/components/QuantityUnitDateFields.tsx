import { formatKoreanDate } from '../lib/dateText'
import type { FormValues } from '../lib/registerForm'
import type { FieldErrors } from '../types/register'
import FormField from './FormField'

interface Props {
  values: FormValues
  errors: FieldErrors
  disabled?: boolean
  onChange: (patch: Partial<FormValues>) => void
}

// 규칙표 등록과 직접 등록이 같이 쓰는 입력칸: 수량 · 단위 · 구매일
export default function QuantityUnitDateFields({ values, errors, disabled, onChange }: Props) {
  return (
    <>
      <div className="field-row">
        <FormField label="수량" id="quantity" error={errors.quantity}>
          <input
            id="quantity"
            className="input"
            type="text"
            inputMode="decimal"
            autoComplete="off"
            placeholder="예: 1, 0.5"
            value={values.quantity}
            disabled={disabled}
            aria-invalid={Boolean(errors.quantity)}
            aria-describedby={errors.quantity ? 'quantity-error' : undefined}
            onChange={(e) => onChange({ quantity: e.target.value })}
          />
        </FormField>
        <FormField label="단위" id="unit" error={errors.unit}>
          <input
            id="unit"
            className="input"
            type="text"
            autoComplete="off"
            placeholder="예: 개, g, 봉"
            value={values.unit}
            disabled={disabled}
            aria-invalid={Boolean(errors.unit)}
            aria-describedby={errors.unit ? 'unit-error' : undefined}
            onChange={(e) => onChange({ unit: e.target.value })}
          />
        </FormField>
      </div>
      <FormField
        label="구매일"
        id="purchase-date"
        error={errors.purchase_date}
        hint={formatKoreanDate(values.purchaseDate)}
      >
        <input
          id="purchase-date"
          className="input"
          type="date"
          value={values.purchaseDate}
          disabled={disabled}
          aria-invalid={Boolean(errors.purchase_date)}
          aria-describedby={errors.purchase_date ? 'purchase-date-error' : undefined}
          onChange={(e) => onChange({ purchaseDate: e.target.value })}
        />
      </FormField>
    </>
  )
}
