// 화면 색(밝기 · 포인트 색)과 글자 크기. 모두 이 기기의 브라우저에만 저장한다 (SCREEN-SPEC 0절, 9.5, 9.6).
// 서버에 요청하지 않는다. 저장하지 못해도(브라우저가 막음) 이 화면에서는 고른 값을 계속 쓴다.
// 기준 문서: SCREEN-SPEC 9.5, 9.6 · ARCHITECTURE 9절 36번. 값을 바꾸면 이 파일과 index.css 의 색 변수만 고친다.

export type Tone = 'light' | 'dark' // 밝은색 / 어두운색
export type Accent = 'butter' | 'carrot' | 'berry' // 버터 옐로 / 당근 오렌지 / 블루베리 보라
export type FontStep = 1 | 2 | 3 | 4 | 5 // 아주 작게 · 작게 · 보통 · 크게 · 아주 크게

export const TONES: readonly { value: Tone; label: string }[] = [
  { value: 'light', label: '밝은색' },
  { value: 'dark', label: '어두운색' },
]

// dots: 설정 화면의 색 점 (밝은색 기준으로 보이는 대표 색)
export const ACCENTS: readonly { value: Accent; label: string; dots: readonly [string, string] }[] = [
  { value: 'butter', label: '버터 옐로', dots: ['#fdd664', '#ff9034'] },
  { value: 'carrot', label: '당근 오렌지', dots: ['#ffa95a', '#e8590c'] },
  { value: 'berry', label: '블루베리 보라', dots: ['#b9a5ff', '#ee6a92'] },
]

export const FONT_STEPS: readonly { value: FontStep; label: string }[] = [
  { value: 1, label: '아주 작게' },
  { value: 2, label: '작게' },
  { value: 3, label: '보통' },
  { value: 4, label: '크게' },
  { value: 5, label: '아주 크게' },
]

export const DEFAULT_ACCENT: Accent = 'butter' // 고른 적이 없으면 버터 옐로 (13.2 의 8번)
export const DEFAULT_FONT_STEP: FontStep = 3 // 고른 적이 없으면 '보통' (9.6)

const KEY_TONE = 'app.tone'
const KEY_ACCENT = 'app.accent'
const KEY_FONT = 'app.fontStep'

export interface Appearance {
  tone: Tone | null // null 이면 고른 적이 없어 기기 설정을 따른다
  accent: Accent
  fontStep: FontStep
}

// 브라우저가 저장소를 막아도(개인 창, 사이트 데이터 차단) 화면이 깨지지 않게 모든 읽기·쓰기를 감싼다.
function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string): boolean {
  try {
    window.localStorage.setItem(key, value)
    return true
  } catch {
    return false
  }
}

function isTone(v: string | null): v is Tone {
  return v === 'light' || v === 'dark'
}

function isAccent(v: string | null): v is Accent {
  return v === 'butter' || v === 'carrot' || v === 'berry'
}

function toFontStep(v: string | null): FontStep | null {
  const n = Number(v)
  return n === 1 || n === 2 || n === 3 || n === 4 || n === 5 ? n : null
}

// 저장된 값을 읽는다. 없거나 알 수 없는 값이면 처음 값이다.
export function loadAppearance(): Appearance {
  const tone = read(KEY_TONE)
  const accent = read(KEY_ACCENT)
  return {
    tone: isTone(tone) ? tone : null,
    accent: isAccent(accent) ? accent : DEFAULT_ACCENT,
    fontStep: toFontStep(read(KEY_FONT)) ?? DEFAULT_FONT_STEP,
  }
}

// 기기의 밝기 설정 (고른 적이 없을 때 따른다)
export function systemTone(): Tone {
  try {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

// 지금 실제로 쓰는 밝기
export function effectiveTone(a: Appearance): Tone {
  return a.tone ?? systemTone()
}

// 현재 값을 화면(문서 맨 위 요소)에 입힌다. 색 변수는 index.css 가 이 속성을 보고 정한다.
export function applyAppearance(a: Appearance): void {
  const root = document.documentElement
  root.dataset.tone = effectiveTone(a)
  root.dataset.accent = a.accent
  root.dataset.font = String(a.fontStep)
}

// 색이 바뀔 때 서서히 바뀌게 하는 짧은 표시 (index.css). 움직임 줄이기를 켜 두었으면 CSS 가 무시한다 (0절).
let changingTimer: number | undefined
export function markChanging(): void {
  const root = document.documentElement
  root.classList.add('appearance-changing')
  window.clearTimeout(changingTimer)
  changingTimer = window.setTimeout(() => root.classList.remove('appearance-changing'), 400)
}

// 값 하나를 고르면 바로 입히고 저장한다. 저장하지 못했으면 false (이 화면에서는 고른 값을 계속 쓴다).
export function chooseTone(current: Appearance, tone: Tone): { next: Appearance; saved: boolean } {
  const next = { ...current, tone }
  markChanging()
  applyAppearance(next)
  return { next, saved: write(KEY_TONE, tone) }
}

export function chooseAccent(current: Appearance, accent: Accent): { next: Appearance; saved: boolean } {
  const next = { ...current, accent }
  markChanging()
  applyAppearance(next)
  return { next, saved: write(KEY_ACCENT, accent) }
}

export function chooseFontStep(current: Appearance, fontStep: FontStep): { next: Appearance; saved: boolean } {
  const next = { ...current, fontStep }
  applyAppearance(next) // 글자 크기는 바로 바뀐다 (9.6). 색 전환 표시는 필요 없다
  return { next, saved: write(KEY_FONT, String(fontStep)) }
}

// 앱을 켤 때 한 번. 고르기 전에는 기기 밝기 설정을 따르므로, 기기 설정이 바뀌면 같이 따라간다.
export function startAppearance(): void {
  applyAppearance(loadAppearance())
  try {
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    query.addEventListener('change', () => {
      const a = loadAppearance()
      if (a.tone === null) {
        markChanging()
        applyAppearance(a)
      }
    })
  } catch {
    // 기기 설정을 읽을 수 없으면 처음 값(밝은색)을 그대로 쓴다
  }
}
