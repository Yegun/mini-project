import { formatKoreanDate } from '../lib/dateText'
import type { ExpiryMode, FormValues } from '../lib/registerForm'
import type { FieldErrors } from '../types/register'
import FormField from './FormField'
import QuantityUnitDateFields from './QuantityUnitDateFields'
import StoragePicker from './StoragePicker'

interface Props {
  values: FormValues
  errors: FieldErrors
  submitting: boolean
  onChange: (patch: Partial<FormValues>) => void
  onSubmit: () => void
}

const EXPIRY_MODES: { mode: ExpiryMode; label: string }[] = [
  { mode: 'date', label: '날짜로 정하기' },
  { mode: 'days', label: '며칠 뒤' },
]

// 목록에 없는 식품의 직접 등록 입력 (4.2). 기한은 날짜 또는 며칠 뒤 중 하나만 적는다.
export default function ManualRegisterForm({ values, errors, submitting, onChange, onSubmit }: Props) {
  return (
    <form
      className="register__form"
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit()
      }}
    >
      <FormField label="이름" id="name" error={errors.name}>
        <input
          id="name"
          className="input"
          type="text"
          autoComplete="off"
          value={values.name}
          disabled={submitting}
          aria-invalid={Boolean(errors.name)}
          aria-describedby={errors.name ? 'name-error' : undefined}
          onChange={(e) => onChange({ name: e.target.value })}
        />
      </FormField>

      <FormField label="보관 방법" id="storage" error={errors.storage}>
        <StoragePicker
          id="storage"
          value={values.storage}
          disabled={submitting}
          onChange={(storage) => onChange({ storage })}
        />
      </FormField>

      <QuantityUnitDateFields values={values} errors={errors} disabled={submitting} onChange={onChange} />

      <FormField
        label="기한"
        id="expiry"
        error={errors.expiry}
        hint={values.expiryMode === 'date' ? formatKoreanDate(values.expiryDate) : undefined}
      >
        <div className="choice-group" role="radiogroup" aria-labelledby="expiry-label">
          {EXPIRY_MODES.map(({ mode, label }) => (
            <button
              key={mode}
              type="button"
              role="radio"
              aria-checked={values.expiryMode === mode}
              disabled={submitting}
              className={values.expiryMode === mode ? 'choice choice--selected' : 'choice'}
              onClick={() => onChange({ expiryMode: mode })}
            >
              {label}
            </button>
          ))}
        </div>
        {values.expiryMode === 'date' ? (
          <input
            id="expiry"
            className="input"
            type="date"
            value={values.expiryDate}
            disabled={submitting}
            aria-invalid={Boolean(errors.expiry)}
            aria-describedby={errors.expiry ? 'expiry-error' : undefined}
            onChange={(e) => onChange({ expiryDate: e.target.value })}
          />
        ) : (
          <div className="input-suffix">
            <input
              id="expiry"
              className="input"
              type="text"
              inputMode="numeric"
              autoComplete="off"
              placeholder="예: 7"
              value={values.expiryDays}
              disabled={submitting}
              aria-invalid={Boolean(errors.expiry)}
              aria-describedby={errors.expiry ? 'expiry-error' : undefined}
              onChange={(e) => onChange({ expiryDays: e.target.value })}
            />
            <span>일 뒤 (구매일부터)</span>
          </div>
        )}
      </FormField>

      <button type="submit" className="button button--primary button--wide" disabled={submitting}>
        {submitting ? '등록하는 중…' : '등록'}
      </button>
    </form>
  )
}
