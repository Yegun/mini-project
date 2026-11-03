import { useRef, useState } from 'react'
import { withdraw } from '../api/account'
import WithdrawDialog from '../components/WithdrawDialog'
import '../components/Register.css'

interface Props {
  onWithdrawn: () => void // 탈퇴 성공 → 로그인 화면 (D-129)
}

// 사용자 확정 문구 (OQ-03, SCREEN-SPEC 13.1 의 9번)
const WRONG_PASSWORD = '비밀번호가 맞지 않아요.'
const WITHDRAW_FAILED = '탈퇴하지 못했어요. 아무것도 지워지지 않았어요. 잠시 뒤에 다시 시도해 주세요.'

// 개인정보 안내문구: 쓰는 쪽이 초안을 쓰고 사용자가 확인해 확정한다 (D-126). 사용자가 확정했다.
const PRIVACY_ITEMS = [
  '모으는 정보는 이메일과 내가 등록한 식품 정보예요.',
  '올린 사진은 저장하지 않고, 읽는 동안만 써요.',
  '사진과 식품 정보는 AI 가 사진을 읽거나 음식을 추천하는 데 쓰여요.',
  '탈퇴하면 계정과 식품이 모두 삭제돼요.',
]

// 설정 화면 (US-023 ~ US-025, SCREEN-SPEC 9절): 개인정보 안내 + [계정 탈퇴]. 그 밖의 설정은 없다 (PRD 5-3).
export default function SettingsPage({ onWithdrawn }: Props) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [passwordError, setPasswordError] = useState<string | undefined>()
  const [failure, setFailure] = useState<string | undefined>()
  const lock = useRef(false) // 연타해도 요청은 한 번 (D-112)

  function openDialog() {
    setPasswordError(undefined)
    setFailure(undefined)
    setDialogOpen(true)
  }

  async function confirm(password: string) {
    if (lock.current) return
    setPasswordError(undefined)
    setFailure(undefined)
    if (password === '') {
      setPasswordError(WRONG_PASSWORD) // 비워도 탈퇴되지 않고 안내가 보인다 (D-128)
      return
    }
    lock.current = true
    setBusy(true)
    const res = await withdraw(password)
    lock.current = false
    setBusy(false)
    if (res.status === 'ok') {
      onWithdrawn()
      return
    }
    if (res.status === 'wrong_password') setPasswordError(res.message ?? WRONG_PASSWORD)
    else setFailure(res.message ?? WITHDRAW_FAILED) // 확인 창은 그대로 두어 다시 시도할 수 있다
  }

  return (
    <main className="register">
      <header className="register__header">
        <h1 className="register__title">설정</h1>
      </header>

      <details className="settings__privacy">
        <summary className="settings__summary">개인정보 안내</summary>
        <ul className="settings__list">
          {PRIVACY_ITEMS.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      </details>

      <button type="button" className="button button--wide settings__withdraw" onClick={openDialog}>
        계정 탈퇴
      </button>

      <WithdrawDialog
        open={dialogOpen}
        busy={busy}
        passwordError={passwordError}
        failure={failure}
        onConfirm={(password) => void confirm(password)}
        onCancel={() => setDialogOpen(false)}
      />
    </main>
  )
}
