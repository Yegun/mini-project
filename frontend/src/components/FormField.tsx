import type { ReactNode } from 'react'

interface Props {
  label: string
  id: string // 입력칸의 id. 묶음 입력(보관 방법 등)은 묶음의 aria-labelledby 에 `${id}-label` 을 쓴다
  error?: string // 입력칸 옆 안내 (입력 규칙 위반)
  hint?: string
  children: ReactNode
}

// 등록 화면 공통 조각: 이름표 + 입력칸 + 칸 옆 안내
export default function FormField({ label, id, error, hint, children }: Props) {
  return (
    <div className="field">
      <label className="field__label" id={`${id}-label`} htmlFor={id}>
        {label}
      </label>
      {children}
      {hint && <p className="field__hint">{hint}</p>}
      {error && (
        <p className="field__error" id={`${id}-error`} role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
