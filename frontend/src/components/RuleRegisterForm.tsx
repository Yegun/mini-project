import type { FormValues } from '../lib/registerForm'
import type { FieldErrors } from '../types/register'
import type { RuleCandidate } from '../types/rule'
import FormField from './FormField'
import { CategoryCapsule, StorageCapsule } from './FoodCapsules'
import QuantityUnitDateFields from './QuantityUnitDateFields'
import { CuisineIcon } from './RecommendIcons'
import StoragePicker from './StoragePicker'
import './RegisterForm.css'

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
// 모양: 위에 고른 식품 카드(그림 · 이름 · 규칙표의 기본 보관 방법), 아래에 번호가 붙은 입력 카드 둘(얼마나 샀나요 · 보관 방법).
// 입력 규칙 · 안내 · 저장은 예전과 같고 겉모양만 다르다.
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
      className="register__form register-form--fancy"
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit()
      }}
    >
      <div className="picked-card">
        <span className="picked-card__art" aria-hidden="true">
          <CuisineIcon cuisine="western" className="picked-card__art-icon" />
        </span>
        <div className="picked-card__text">
          <strong className="picked-card__name">{rule.name}</strong>
          <span className="picked-card__sub">
            기본 보관
            <StorageCapsule storage={rule.default_storage} withIcon />
          </span>
          <span className="picked-card__sub">
            종류
            <CategoryCapsule category={rule.category ?? null} />
          </span>
        </div>
        <button type="button" className="picked-card__change" disabled={submitting} onClick={onChangeFood}>
          다른 식품 고르기
        </button>
      </div>

      <section className="form-card" aria-label="얼마나 샀나요">
        <h3 className="form-card__title">
          <span className="form-card__num" aria-hidden="true">
            1
          </span>
          얼마나 샀나요?
        </h3>
        <QuantityUnitDateFields values={values} errors={errors} disabled={submitting} unitChips onChange={onChange} />
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
            options={rule.storages}
            disabled={submitting}
            variant="tiles"
            onChange={(storage) => onChange({ storage })}
          />
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
