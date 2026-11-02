// "다시 로그인해야 함" 알림. API 가 401 + reason "login_required" 를 주면(로그인 안 함 · 30분 만료)
// 어느 화면에 있든 로그인 화면으로 보낸다. 입력 중이던 내용은 사라진다 (D-055, D-059, API-SPEC 2-1).
// App 이 하나만 등록해 듣는다.
type Listener = () => void

let listener: Listener | null = null

export function setLoginRequiredListener(fn: Listener | null): void {
  listener = fn
}

export function notifyLoginRequired(): void {
  listener?.()
}
