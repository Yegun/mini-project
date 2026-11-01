import { useState } from 'react'
import type { Storage } from '../types/food'
import type { ChangeStorageInput, FoodDetail, SaveResult } from '../types/foodDetail'
import type { FieldErrors } from '../types/register'
import ExpiryRewriteField from './ExpiryRewriteField'
import FormField from './FormField'
import StoragePicker from './StoragePicker'

interface Props {
  food: FoodDetail
  busy: boolean
  onSave: (input: ChangeStorageInput) => Promise<SaveResult> // 성공하면 화면이 홈으로 간다 (D-020)
}

// 보관 방법 바꾸기 (5.3). 불가 방법은 흐리게 보인다 (D-005). 새 기한 계산은 API 가 한다 (D-006, D-016).
export default function StorageChangeForm({ food, busy, onSave }: Props) {
  const [storage, setStorage] = useState<Storage>(food.storage)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [expiryOpen, setExpiryOpen] = useState(false) // 직접 등록 식품: API 가 "기한 필요"라고 했을 때 (D-023)
  const [expiryDate, setExpiryDate] = useState('')

  function pick(next: Storage) {
    setStorage(next)
    setErrors({})
    setExpiryOpen(false)
    setExpiryDate('')
  }

  async function submit() {
    if (expiryOpen && expiryDate === '') {
      setErrors({ expiry: '기한을 골라 주세요.' })
      return
    }
    setErrors({})
    const result = await onSave({ storage, ...(expiryOpen ? { expiry_date: expiryDate } : {}) })

    if (result.status === 'need_expiry') {
      setExpiryOpen(true)
    } else if (result.status === 'invalid') {
      setErrors(result.fieldErrors)
      if (result.fieldErrors.expiry) setExpiryOpen(true)
    }
  }

  return (
    <form
      className="register__form"
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        void submit()
      }}
    >
      <FormField label="보관 방법" id="storage" error={errors.storage}>
        <StoragePicker id="storage" value={storage} options={food.storages} disabled={busy} onChange={pick} />
      </FormField>

      {expiryOpen && (
        <ExpiryRewriteField
          id="storage-expiry"
          value={expiryDate}
          error={errors.expiry}
          disabled={busy}
          onChange={(date) => {
            setExpiryDate(date)
            setErrors((prev) => ({ ...prev, expiry: undefined }))
          }}
        />
      )}

      <button
        type="submit"
        className="button button--primary button--wide"
        disabled={busy || storage === food.storage}
      >
        {busy ? '저장하는 중…' : '보관 방법 저장'}
      </button>
    </form>
  )
}
