// 전체 달력 화면의 보는 상태 (SCREEN-SPEC 14절). 식품 상세에 갔다가 뒤로 오면 같은 모습으로 다시 열기 위해 저장한다 (D-085, D-150).
export type CalendarBasis = 'end' | 'start' // 끝나는 날(기한) / 시작하는 날(구매일). 처음은 끝나는 날 (D-147)

export interface CalendarView {
  monthOffset: number // 오늘이 있는 달에서 몇 달 떨어졌는지 (0 = 이번 달). 넘기는 범위 제한은 없다 (13.2 의 5번)
  basis: CalendarBasis
  selectedDate: string | null // 눌러서 날짜 목록 창이 열려 있는 날짜 (YYYY-MM-DD). 없으면 창이 닫혀 있다
  expanded: boolean // 날짜 목록 창을 끌어올려 '이날 남아 있는 식품'까지 보이는지
}

export const INITIAL_CALENDAR_VIEW: CalendarView = {
  monthOffset: 0,
  basis: 'end',
  selectedDate: null,
  expanded: false,
}
