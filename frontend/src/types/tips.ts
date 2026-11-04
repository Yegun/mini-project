// 오늘의 일반 조언(J1) 응답. 기준은 API-SPEC 2-10, D-156 ~ D-158.
export interface Tip {
  text: string // 조언 한 문장
  from_ai: boolean // AI 가 만든 것이면 true, 미리 써 둔 것이면 false
}

export interface TipsData {
  tip_date: string // YYYY-MM-DD. 오늘(한국 시간)
  tips: Tip[]
}
