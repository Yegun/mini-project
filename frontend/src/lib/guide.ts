// 사용 설명서를 "보여 줄 차례"를 이 기기의 브라우저에만 기억한다 (US-046, D-199 ~ D-202, D-206).
// 서버에는 아무것도 보내지 않는다. 저장하지 못해도(브라우저가 막음) 앱은 그대로 동작한다. 밝기 · 포인트 색을 기억하는 방식(lib/appearance.ts)과 같다.
//
// 기억하는 것은 두 가지다.
//  - 보여 줄 차례(pending): 새 계정을 만든 직후에 남기고, 설명서를 끝까지 보거나 건너뛰면 지운다. 가입한 계정(이메일)을 같이 적는다.
//  - 이 기기에서 지금 로그인한 계정(current): 서버에 "지금 누구냐"고 묻는 창구가 없어서, 로그인할 때 입력한 이메일을 적어 둔다.
// 두 이메일이 같을 때만 설명서를 보여 준다. 그래서 같은 기기에서 다른 계정으로 로그인한 사람에게는 보이지 않는다 (D-201).

const KEY_PENDING = 'app.guidePending'
const KEY_CURRENT = 'app.guideAccount'

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // 저장하지 못해도 이번 화면에서는 설명서가 정상으로 보인다 (닫지 않고 나가면 다시 뜨지 않을 뿐이다)
  }
}

function remove(key: string): void {
  try {
    window.localStorage.removeItem(key)
  } catch {
    // 지우지 못해도 앱은 동작한다
  }
}

// 이메일은 대소문자와 앞뒤 공백을 무시하고 같은 계정으로 본다
function normalize(email: string): string {
  return email.trim().toLowerCase()
}

// 새 계정을 만들었다: 설명서를 보여 줄 차례를 남기고, 이 계정으로 로그인한 상태로 적는다
export function markSignedUp(email: string): void {
  write(KEY_PENDING, normalize(email))
  write(KEY_CURRENT, normalize(email))
}

// 이미 있는 계정으로 로그인했다: 지금 로그인한 계정만 적는다. 보여 줄 차례는 건드리지 않는다
export function markLoggedIn(email: string): void {
  write(KEY_CURRENT, normalize(email))
}

// 로그아웃했다: 이 기기에서 지금 로그인한 계정이 없다
export function markLoggedOut(): void {
  remove(KEY_CURRENT)
}

// 지금 로그인한 계정이 설명서를 보여 줄 차례인가
export function shouldShowGuide(): boolean {
  const pending = read(KEY_PENDING)
  return pending !== null && pending === read(KEY_CURRENT)
}

// 설명서를 끝까지 봤거나 건너뛰었다. 설정에서 다시 볼 때는 부르지 않는다 (D-206)
export function finishGuide(): void {
  remove(KEY_PENDING)
}

// 탈퇴했다: 이 기기에 남은 계정 흔적을 모두 지운다
export function forgetAccount(): void {
  remove(KEY_PENDING)
  remove(KEY_CURRENT)
}
