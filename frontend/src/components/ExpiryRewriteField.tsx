import { formatKoreanDate } from '../lib/dateText'
import FormField from './FormField'

interface Props {
  id: string // 같은 화면의 다른 입력칸과 겹치지 않는 id
  value: string // YYYY-MM-DD
  error?: string
  disabled?: boolean
  onChange: (date: string) => void
}

// 기한 다시 적기: "기한을 다시 적어 주세요" 입력칸 (ARCH 2절, D-023).
// API 가 "기한 필요" 응답을 줄 때만 열린다. 과거 날짜인지는 API 가 판단한다 (D-016).
export default function ExpiryRewriteField({ id, value, error, disabled, onChange }: Props) {
  return (
    <FormField
      label="기한을 다시 적어 주세요"
      id={id}
      error={error}
      hint={value ? formatKoreanDate(value) : '새 기한을 날짜로 골라 주세요.'}
    >
      <input
        id={id}
        className="input"
        type="date"
        value={value}
        disabled={disabled}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
        onChange={(e) => onChange(e.target.value)}
      />
    </FormField>
  )
}
