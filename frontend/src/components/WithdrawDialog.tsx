import { useEffect, useRef, useState } from 'react'
import FormField from './FormField'

interface Props {
  open: boolean
  busy: boolean // 탈퇴 요청 중에는 버튼을 잠근다 (D-112)
  passwordError?: string // 비밀번호가 틀리거나 비었음 (D-128)
  failure?: string // 삭제 실패. 아무것도 지워지지 않았다
  onConfirm: (password: string) => void
  onCancel: () => void
}

// 사용자 확정 문구 (SCREEN-SPEC 13.1 의 9번). 탈퇴 확인 창에는 "되돌릴 수 없다"를 쓴다 (D-127).
const WARNING = '탈퇴하면 계정과 식품이 모두 삭제돼요. 삭제는 되돌릴 수 없어요. 비밀번호를 다시 입력해 주세요.'

// 탈퇴 확인 창: 삭제는 되돌릴 수 없다는 안내 + 비밀번호 입력칸 + 확인 · 취소 (D-128, SCREEN-SPEC 9.4)
export default function WithdrawDialog({ open, busy, passwordError, failure, onConfirm, onCancel }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  const [password, setPassword] = useState('')

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  // 취소하면 아무 일도 없다. 적은 비밀번호도 남기지 않는다
  function cancel() {
    setPassword('')
    onCancel()
  }

  return (
    <dialog
      ref={ref}
      className="confirm"
      aria-label="계정 탈퇴 확인"
      onCancel={(e) => {
        e.preventDefault() // Esc 로 닫을 때도 상태는 우리가 정한다
        if (!busy) cancel()
      }}
    >
      <form
        className="register__form"
        onSubmit={(e) => {
          e.preventDefault()
          onConfirm(password)
        }}
      >
        <p className="confirm__message">{WARNING}</p>
        <FormField label="비밀번호" id="withdraw-password" error={passwordError}>
          <input
            id="withdraw-password"
            className="input"
            type="password"
            autoComplete="current-password"
            value={password}
            aria-invalid={passwordError ? true : undefined}
            aria-describedby={passwordError ? 'withdraw-password-error' : undefined}
            disabled={busy}
            onChange={(e) => setPassword(e.target.value)}
          />
        </FormField>
        {failure && (
          <p className="field__error" role="alert">
            {failure}
          </p>
        )}
        <div className="confirm__buttons">
          <button type="button" className="button" disabled={busy} onClick={cancel}>
            취소
          </button>
          <button type="submit" className="button button--primary" disabled={busy}>
            {busy ? '처리하는 중…' : '탈퇴'}
          </button>
        </div>
      </form>
    </dialog>
  )
}
