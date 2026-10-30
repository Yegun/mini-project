import { useRef, useState } from 'react'
import { createManualFood, createRuleFood } from '../api/foods'
import { searchRules } from '../api/rules'
import ErrorNotice from '../components/ErrorNotice'
import ManualRegisterForm from '../components/ManualRegisterForm'
import RuleRegisterForm from '../components/RuleRegisterForm'
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
  onBack: () => void // 저장하지 않고 홈으로
  onDone: () => void // 등록 성공 → 홈으로
}

type Step = 'search' | 'rule' | 'manual'

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
export default function RegisterPage({ today, onBack, onDone }: Props) {
  const [step, setStep] = useState<Step>('search')
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState<SearchState>({ status: 'idle' })
  const [rule, setRule] = useState<RuleCandidate | null>(null)
  const [values, setValues] = useState<FormValues>(() => emptyValues(today))
  const [errors, setErrors] = useState<FieldErrors>({})
  const [saveError, setSaveError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const searchSeq = useRef(0) // 늦게 온 옛 검색 결과가 덮어쓰지 않게
  const submitLock = useRef(false) // 연타해도 요청은 한 번

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
        ? await createRuleFood({ ...base, rule_id: rule.id })
        : await createManualFood({
            ...base,
            ...(values.expiryMode === 'date'
              ? { expiry_date: values.expiryDate }
              : { expiry_days: Number(values.expiryDays.trim()) }),
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
      setSaveError(SAVE_FAILED)
    }
  }

  return (
    <main className="register">
      <header className="register__header">
        <button type="button" className="register__back" aria-label="홈으로 돌아가기" onClick={onBack}>
          ‹
        </button>
        <h1 className="register__title">식품 등록</h1>
      </header>

      {saveError && <ErrorNotice message={saveError} />}

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
