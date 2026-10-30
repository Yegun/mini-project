import type { FormValues } from '../lib/registerForm'
import type { FieldErrors } from '../types/register'
import type { RuleCandidate } from '../types/rule'
import FormField from './FormField'
import QuantityUnitDateFields from './QuantityUnitDateFields'
import StoragePicker from './StoragePicker'

interface Props {
  rule: RuleCandidate
  values: FormValues
  errors: FieldErrors
  submitting: boolean
  onChange: (patch: Partial<FormValues>) => void
  onChangeFood: () => void // 검색 단계로 돌아가 다른 식품 고르기 (입력한 수량·단위·구매일은 유지)
  onSubmit: () => void
}

// 규칙표에서 고른 식품의 등록 입력 (4.1). 기한은 API 가 계산하므로 입력칸이 없다.
export default function RuleRegisterForm({
  rule,
  values,
  errors,
  submitting,
  onChange,
  onChangeFood,
  onSubmit,
}: Props) {
  return (
    <form
      className="register__form"
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit()
      }}
    >
      <div className="picked-food">
        <strong className="picked-food__name">{rule.name}</strong>
        <button type="button" className="button button--link" disabled={submitting} onClick={onChangeFood}>
          다른 식품 고르기
        </button>
      </div>

      <QuantityUnitDateFields values={values} errors={errors} disabled={submitting} onChange={onChange} />

      <FormField label="보관 방법" id="storage" error={errors.storage}>
        <StoragePicker
          id="storage"
          value={values.storage}
          options={rule.storages}
          disabled={submitting}
          onChange={(storage) => onChange({ storage })}
        />
      </FormField>

      <button type="submit" className="button button--primary button--wide" disabled={submitting}>
        {submitting ? '등록하는 중…' : '등록'}
      </button>
    </form>
  )
}
