// 막대 자르기 계산. 화면이 하는 날짜 계산은 이것뿐이다 (D-016).
// 상태(여유·주의·임박·지남) 판정은 하지 않는다. API 가 준 값을 쓴다 (D-009).
// 날짜 글자(YYYY-MM-DD)는 연·월·일 숫자로 직접 계산해 시간대 어긋남을 피한다.

const DAY_MS = 24 * 60 * 60 * 1000

export interface WeekDay {
  date: string // YYYY-MM-DD
  month: number
  day: number
  weekday: number // 0=일 ... 6=토
}

export interface BarSpan {
  startCol: number // 0~6 (일~토), 포함
  endCol: number // 0~6, 포함
  clippedStart: boolean // 구매일이 이번 주 앞이라 잘렸다
  clippedEnd: boolean // 기한이 이번 주 뒤라 잘렸다
}

// YYYY-MM-DD → 1970-01-01 부터 센 날 수
function toDayNumber(date: string): number {
  const [y, m, d] = date.split('-').map(Number)
  return Date.UTC(y, m - 1, d) / DAY_MS
}

function fromDayNumber(n: number): string {
  return new Date(n * DAY_MS).toISOString().slice(0, 10)
}

// date 에 n 일을 더한 날짜 (n 은 음수도 된다). 이전 · 다음 주로 넘길 때 7일씩 더한다 (D-192).
export function addDays(date: string, n: number): string {
  return fromDayNumber(toDayNumber(date) + n)
}

// 한 주(7일)에서 달력 위쪽에 보일 연 · 월. 일~토 가운데 날(수요일)이 속한 달을 쓴다 (주가 두 달에 걸칠 때 더 많은 쪽).
export function weekMonthLabel(days: WeekDay[]): string {
  const mid = days[3].date
  return `${mid.slice(0, 4)}년 ${Number(mid.slice(5, 7))}월`
}

// 날짜가 들어 있는 주(일요일 시작)의 7일. 오늘이 속한 주를 구할 때도, 다른 주를 구할 때도 쓴다.
export function getWeekDays(today: string): WeekDay[] {
  const todayNum = toDayNumber(today)
  const sunday = todayNum - getWeekday(today)
  return Array.from({ length: 7 }, (_, i) => {
    const date = fromDayNumber(sunday + i)
    return { date, month: Number(date.slice(5, 7)), day: Number(date.slice(8, 10)), weekday: i }
  })
}

// 0=일 ... 6=토 (1970-01-01 은 목요일)
export function getWeekday(date: string): number {
  return (((toDayNumber(date) + 4) % 7) + 7) % 7
}

// 구매일~기한(양 끝 포함)을 이번 주 7칸에 맞춰 자른다. 이번 주에 걸치지 않으면 null.
export function clipBar(today: string, purchaseDate: string, expiryDate: string): BarSpan | null {
  const sunday = toDayNumber(today) - getWeekday(today)
  const start = toDayNumber(purchaseDate) - sunday
  const end = toDayNumber(expiryDate) - sunday
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return null
  if (end < 0 || start > 6) return null
  return {
    startCol: Math.max(start, 0),
    endCol: Math.min(end, 6),
    clippedStart: start < 0,
    clippedEnd: end > 6,
  }
}
