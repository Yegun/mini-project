import { formatKoreanDate } from '../lib/dateText'
import type { ExpiryMode, FormValues } from '../lib/registerForm'
import type { FieldErrors } from '../types/register'
import CategoryPicker from './CategoryPicker'
import FormField from './FormField'
import QuantityUnitDateFields from './QuantityUnitDateFields'
import StoragePicker from './StoragePicker'
import './RegisterForm.css'

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

// "며칠 뒤" 빠른 선택. 누르면 일수 칸에 그대로 적힌 것과 같다 (칸에 직접 적어도 된다)
const QUICK_DAYS = ['3', '7', '14', '30']

// 목록에 없는 식품의 직접 등록 입력 (4.2). 기한은 날짜 또는 며칠 뒤 중 하나만 적는다.
// 모양: 번호가 붙은 입력 카드 넷(어떤 식품 · 어디에 둘까요 · 얼마나 샀나요 · 언제까지). 입력 규칙 · 안내 · 저장은 예전과 같고 겉모양만 다르다.
export default function ManualRegisterForm({ values, errors, submitting, onChange, onSubmit }: Props) {
  return (
    <form
      className="register__form register-form--fancy"
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit()
      }}
    >
      <section className="form-card" aria-label="어떤 식품인가요">
        <h3 className="form-card__title">
          <span className="form-card__num" aria-hidden="true">
            1
          </span>
          어떤 식품인가요?
        </h3>
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

        <FormField label="종류" id="category" error={errors.category}>
          <CategoryPicker
            id="category"
            value={values.category}
            disabled={submitting}
            onChange={(category) => onChange({ category })}
          />
        </FormField>
      </section>

      <section className="form-card" aria-label="보관 방법 고르기">
        <h3 className="form-card__title">
          <span className="form-card__num" aria-hidden="true">
            2
          </span>
          어디에 둘까요?
        </h3>
        <FormField label="보관" id="storage" error={errors.storage}>
          <StoragePicker
            id="storage"
            value={values.storage}
            disabled={submitting}
            variant="tiles"
            onChange={(storage) => onChange({ storage })}
          />
        </FormField>
      </section>

      <section className="form-card" aria-label="얼마나 샀나요">
        <h3 className="form-card__title">
          <span className="form-card__num" aria-hidden="true">
            3
          </span>
          얼마나 샀나요?
        </h3>
        <QuantityUnitDateFields values={values} errors={errors} disabled={submitting} unitChips onChange={onChange} />
      </section>

      <section className="form-card" aria-label="기한 정하기">
        <h3 className="form-card__title">
          <span className="form-card__num" aria-hidden="true">
            4
          </span>
          언제까지 먹을까요?
        </h3>
        <FormField
          label="기한"
          id="expiry"
          error={errors.expiry}
          hint={values.expiryMode === 'date' ? formatKoreanDate(values.expiryDate) : undefined}
        >
          <div className="choice-group choice-group--segmented" role="radiogroup" aria-labelledby="expiry-label">
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
            <>
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
              <div className="unit-chips" role="group" aria-label="자주 쓰는 기한">
                {QUICK_DAYS.map((d) => (
                  <button
                    key={d}
                    type="button"
                    className={values.expiryDays.trim() === d ? 'unit-chip unit-chip--on' : 'unit-chip'}
                    aria-pressed={values.expiryDays.trim() === d}
                    disabled={submitting}
                    onClick={() => onChange({ expiryDays: d })}
                  >
                    {d}일
                  </button>
                ))}
              </div>
            </>
          )}
        </FormField>
      </section>

      {/* 등록 버튼은 화면 아래(아래 탭 바로 위)에 고정되어 스크롤해도 제자리에 있다 (D-151) */}
      <div className="sticky-action">
        <button type="submit" className="button button--primary button--wide" disabled={submitting}>
          {submitting ? '등록하는 중…' : '등록'}
        </button>
      </div>
    </form>
  )
}
