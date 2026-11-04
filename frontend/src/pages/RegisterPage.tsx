import { useEffect, useRef, useState } from 'react'
import { createManualFood, createRuleFood } from '../api/foods'
import { analyzePhoto } from '../api/photos'
import { searchRules } from '../api/rules'
import ErrorNotice from '../components/ErrorNotice'
import ManualRegisterForm from '../components/ManualRegisterForm'
import PhotoReview from '../components/PhotoReview'
import PhotoUpload from '../components/PhotoUpload'
import RuleRegisterForm from '../components/RuleRegisterForm'
import RegisterChoice from '../components/RegisterChoice'
import RuleSearch from '../components/RuleSearch'
import {
  checkManualForm,
  checkRuleForm,
  emptyValues,
  type FormValues,
} from '../lib/registerForm'
import { checkPhoto, PHOTO_INVALID } from '../lib/photoFile'
import type { Category } from '../types/food'
import type { AnalyzeData } from '../types/photo'
import type { FieldErrors, FieldName } from '../types/register'
import type { RuleCandidate, SearchState } from '../types/rule'
import '../components/Register.css'

interface Props {
  today: string // 홈이 API 에서 받은 오늘 날짜. 구매일 기본값에만 쓴다 (D-021)
  onBack: () => void // 저장하지 않고 바로 전에 보던 화면으로 (D-085)
  onDone: () => void // 등록 성공 → 홈으로
  onDirtyChange?: (dirty: boolean) => void // 입력한 것이 있는지 (탭 이동 확인 창, D-083)
}

// choose: 등록 선택 / photo: 사진 올리기 / review: 읽은 식품 확인 (이슈 6 에서 채움) / search · rule · manual: 직접 등록
type Step = 'choose' | 'photo' | 'review' | 'search' | 'rule' | 'manual'

// 값이 바뀌면 그 칸의 안내를 지운다 (입력칸 → 안내가 붙은 칸)
const FIELD_OF: Record<keyof FormValues, FieldName> = {
  name: 'name',
  category: 'category',
  quantity: 'quantity',
  unit: 'unit',
  purchaseDate: 'purchase_date',
  storage: 'storage',
  expiryMode: 'expiry',
  expiryDate: 'expiry',
  expiryDays: 'expiry',
}

const SAVE_FAILED = '등록하지 못했어요. 잠시 뒤에 다시 시도해 주세요.'
// 사용자 확정 문구 (ARCH 3절)
const AI_FAILED = 'AI 가 응답하지 못했어요. 다시 시도해 주세요.'
// 사용자 확정 문구 (SCREEN-SPEC 13.1 의 9번)
const NO_FOOD_READ = '사진에서 식품을 읽지 못했어요. 직접 등록해 보세요.'

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
  const [photo, setPhoto] = useState<File | null>(null)
  const [photoError, setPhotoError] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysis, setAnalysis] = useState<AnalyzeData | null>(null) // 읽은 결과 (확인 화면용)
  const [reviewDirty, setReviewDirty] = useState(false) // 확인 화면에서 고치거나 뺀 것이 있는지
  const [notice, setNotice] = useState<string | null>(null) // 등록 선택 화면의 안내 (식품을 못 읽었을 때)
  const searchSeq = useRef(0) // 늦게 온 옛 검색 결과가 덮어쓰지 않게
  const submitLock = useRef(false) // 연타해도 요청은 한 번
  const photoLock = useRef(false) // 사진 올리기도 연타해도 요청은 한 번 (D-112)

  // 검색어를 적었거나, 식품을 골랐거나(직접 등록으로 갔거나), 값을 처음과 다르게 바꿨으면 "입력한 것이 있다".
  // 구매일 기본값(오늘)처럼 처음부터 채워진 값만 있으면 입력으로 보지 않는다 (SCREEN-SPEC 11.1-6)
  const dirty =
    query.trim() !== '' ||
    step === 'rule' ||
    step === 'manual' ||
    (step === 'photo' && photo !== null) || // 사진을 고른 상태 (SCREEN-SPEC 5.3)
    (step === 'review' && reviewDirty) || // 확인 화면에서 줄을 고치거나 뺀 상태 (SCREEN-SPEC 5.4)
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

  function pickPhoto(file: File) {
    const problem = checkPhoto(file) // 형식 · 크기를 미리 검사. 맞지 않으면 올라가지 않고 안내만 보인다 (D-101)
    if (problem) {
      setPhotoError(problem) // 이미 고른 사진이 있으면 그대로 남긴다
      return
    }
    setPhoto(file)
    setPhotoError(null)
  }

  async function uploadPhoto() {
    if (photoLock.current || !photo) return
    photoLock.current = true
    setAnalyzing(true)
    setPhotoError(null)
    const res = await analyzePhoto(photo)
    photoLock.current = false
    setAnalyzing(false)
    if (res.status === 'ok') {
      if (res.data.items.length === 0) {
        // 식품을 하나도 못 읽음: 실패가 아니다. 안내와 함께 등록 선택으로 돌아가 직접 등록으로 갈 수 있다
        setPhoto(null)
        setNotice(NO_FOOD_READ)
        setStep('choose')
        return
      }
      setAnalysis(res.data)
      setStep('review')
      return
    }
    setPhotoError(res.message ?? (res.status === 'invalid' ? PHOTO_INVALID : AI_FAILED)) // 사진은 그대로 남는다
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
    setValues((v) => ({ ...v, name: query.trim(), category: null, storage: null })) // 검색어를 이름칸에 미리 채움. 종류는 사용자가 고른다
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
    if (step === 'manual' && values.category === null) return // checkManualForm 이 이미 안내한다 (타입 좁히기용)

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
            category: values.category as Category, // 위에서 비어 있지 않음을 확인했다
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

      {step === 'choose' && (
        <>
          {notice && (
            <div className="notice notice--empty" role="status">
              <p className="notice__text">{notice}</p>
            </div>
          )}
          <RegisterChoice
            onPhoto={() => {
              setNotice(null)
              setStep('photo')
            }}
            onManual={() => {
              setNotice(null)
              setStep('search')
            }}
          />
        </>
      )}
      {step === 'photo' && (
        <PhotoUpload
          photo={photo}
          error={photoError}
          busy={analyzing}
          onPick={pickPhoto}
          onUpload={() => void uploadPhoto()}
        />
      )}
      {step === 'review' && analysis && (
        <PhotoReview
          analysis={analysis}
          onDone={onDone} // 등록 성공 → 홈. 홈이 목록을 새로 불러온다
          onReupload={() => {
            // 읽기 결과가 만료됨: 사진을 다시 올려야 한다
            setAnalysis(null)
            setReviewDirty(false)
            setPhoto(null)
            setStep('photo')
          }}
          onDirtyChange={setReviewDirty}
        />
      )}
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
