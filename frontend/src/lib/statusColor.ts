// 상태 색 연결표. 색만 입힌다. 상태 판정은 API 가 한다 (D-009).
// [임시 계약] 상태 값 이름이 바뀌면 types/food.ts 의 ExpiryLevel 과 이 표만 고친다.
// 색 값은 문서에 정해진 것이 없어 시안(2_홈.png)을 참고해 고른 임시 값이다.
import type { ExpiryLevel } from '../types/food'

// Record 라서 상태가 하나라도 빠지면 빌드에서 막힌다.
export const STATUS_COLOR: Record<ExpiryLevel, string> = {
  relaxed: '#2db87e', // 여유 초록
  caution: '#f6b63e', // 주의 노랑
  urgent: '#d93636', // 임박 빨강
  expired: '#1f2328', // 지남 검정
}

// 서버가 모르는 값을 보내도 화면이 깨지지 않게 하는 대비색(회색)
const UNKNOWN_COLOR = '#9aa3ad'

export function statusColor(level: ExpiryLevel): string {
  return STATUS_COLOR[level] ?? UNKNOWN_COLOR
}
