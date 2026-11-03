import { useEffect, useRef, useState } from 'react'
import { createManualFood, createRuleFood } from '../api/foods'
import { searchRules } from '../api/rules'
import ErrorNotice from '../components/ErrorNotice'
import ManualRegisterForm from '../components/ManualRegisterForm'
import RuleRegisterForm from '../components/RuleRegisterForm'
import RegisterChoice from '../components/RegisterChoice'
import RuleSearch from '../components/RuleSearch'
import {
  checkManualForm,
  checkRuleForm,
  emptyValues,
  type FormValues,
} from '../lib/registerForm'
import type { FieldErrors, FieldName } from '../types/register'
import type { RuleCandidate, SearchState } from '../types/rule'
import '../components/Register.css'

interface Props {
  today: string // 홈이 API 에서 받은 오늘 날짜. 구매일 기본값에만 쓴다 (D-021)
  onBack: () => void // 저장하지 않고 바로 전에 보던 화면으로 (D-085)
  onDone: () => void // 등록 성공 → 홈으로
  onDirtyChange?: (dirty: boolean) => void // 입력한 것이 있는지 (탭 이동 확인 창, D-083)
}

// choose: 등록 선택 / photo: 사진으로 등록 (이슈 5 에서 채움) / search · rule · manual: 직접 등록
type Step = 'choose' | 'photo' | 'search' | 'rule' | 'manual'

// 값이 바뀌면 그 칸의 안내를 지운다 (입력칸 → 안내가 붙은 칸)
const FIELD_OF: Record<keyof FormValues, FieldName> = {
  name: 'name',
  quantity: 'quantity',
  unit: 'unit',
  purchaseDate: 'purchase_date',
  storage: 'storage',
  expiryMode: 'expiry',
  expiryDate: 'expiry',
  expiryDays: 'expiry',
}

const SAVE_FAILED = '등록하지 못했어요. 잠시 뒤에 다시 시도해 주세요.'

// 식품 등록 화면: 검색 → (규칙표 식품 입력 | 직접 등록 입력). 입력값은 여기서 들고 있어 실패해도 남는다.
export default function RegisterPage({ today, onBack, onDone, onDirtyChange }: Props) {
  const [step, setStep] = useState<Step>('choose')
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState<SearchState>({ status: 'idle' })
  const [rule, setRule] = useState<RuleCandidate | null>(null)
  const [values, setValues] = useState<FormValues>(() => emptyValues(today))
  const [errors, setErrors] = useState<FieldErrors>({})
  const [saveError, setSaveError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const searchSeq = useRef(0) // 늦게 온 옛 검색 결과가 덮어쓰지 않게
  const submitLock = useRef(false) // 연타해도 요청은 한 번

  // 검색어를 적었거나, 식품을 골랐거나(직접 등록으로 갔거나), 값을 처음과 다르게 바꿨으면 "입력한 것이 있다".
  // 구매일 기본값(오늘)처럼 처음부터 채워진 값만 있으면 입력으로 보지 않는다 (SCREEN-SPEC 11.1-6)
  const dirty =
    query.trim() !== '' ||
    step === 'rule' ||
    step === 'manual' ||
    JSON.stringify(values) !== JSON.stringify(emptyValues(today))
  useEffect(() => {
    onDirtyChange?.(dirty)
  }, [dirty, onDirtyChange])

  function runSearch() {
    const q = query.trim()
    if (q === '') return
    const seq = ++searchSeq.current
    setSearch({ status: 'loading' })
    searchRules(q)
      .then((res) => {
        if (seq === searchSeq.current) setSearch({ status: 'done', q, rules: res.rules })
      })
      .catch(() => {
        if (seq === searchSeq.current) setSearch({ status: 'error' })
      })
  }

  function pickRule(picked: RuleCandidate) {
    setRule(picked)
    setValues((v) => ({ ...v, name: picked.name, storage: picked.default_storage })) // 기본 보관 방법 미리 선택
    setErrors({})
    setSaveError(null)
    setStep('rule')
  }

  function goManual() {
    setRule(null)
    setValues((v) => ({ ...v, name: query.trim(), storage: null })) // 검색어를 이름칸에 미리 채움
    setErrors({})
    setSaveError(null)
    setStep('manual')
  }

  function changeFood() {
    setErrors({})
    setSaveError(null)
    setStep('search')
  }

  function change(patch: Partial<FormValues>) {
    setValues((v) => ({ ...v, ...patch }))
    const touched = (Object.keys(patch) as (keyof FormValues)[]).map((k) => FIELD_OF[k])
    setErrors((prev) => {
      const next = { ...prev }
      for (const field of touched) delete next[field]
      return next
    })
  }

  async function submit() {
    if (submitLock.current) return
    const found = step === 'rule' ? checkRuleForm(values) : checkManualForm(values)
    setErrors(found)
    setSaveError(null)
    if (Object.keys(found).length > 0 || values.storage === null) return

    const base = {
      name: values.name.trim(),
      storage: values.storage,
      quantity: Number(values.quantity.trim()),
      unit: values.unit.trim(),
      purchase_date: values.purchaseDate,
    }
    submitLock.current = true
    setSubmitting(true)
    const result =
      step === 'rule' && rule
        ? await createRuleFood(base)
        : await createManualFood({
            ...base,
            ...(values.expiryMode === 'date'
              ? { expiry_date: values.expiryDate }
              : { expiry_in_days: Number(values.expiryDays.trim()) }),
          })
    submitLock.current = false

    if (result.status === 'ok') {
      onDone()
      return
    }
    setSubmitting(false) // 입력값은 그대로 두고 버튼만 다시 누를 수 있게 한다
    if (result.status === 'invalid' && Object.keys(result.fieldErrors).length > 0) {
      setErrors(result.fieldErrors)
    } else {
      setSaveError((result.status === 'failed' && result.message) || SAVE_FAILED) // API 문구가 있으면 그것을 보인다
    }
  }

  return (
    <main className="register">
      <header className="register__header">
        <button type="button" className="register__back" aria-label="뒤로 가기" onClick={onBack}>
          ‹
        </button>
        <h1 className="register__title">식품 등록</h1>
      </header>

      {saveError && <ErrorNotice message={saveError} />}

      {step === 'choose' && <RegisterChoice onPhoto={() => setStep('photo')} onManual={() => setStep('search')} />}
      {step === 'photo' && <p className="field__hint">사진으로 등록은 곧 만들어요.</p>}
      {step === 'search' && (
        <RuleSearch
          query={query}
          search={search}
          onQueryChange={setQuery}
          onSearch={runSearch}
          onPick={pickRule}
          onManual={goManual}
        />
      )}
      {step === 'rule' && rule && (
        <RuleRegisterForm
          rule={rule}
          values={values}
          errors={errors}
          submitting={submitting}
          onChange={change}
          onChangeFood={changeFood}
          onSubmit={submit}
        />
      )}
      {step === 'manual' && (
        <ManualRegisterForm
          values={values}
          errors={errors}
          submitting={submitting}
          onChange={change}
          onSubmit={submit}
        />
      )}
    </main>
  )
}
