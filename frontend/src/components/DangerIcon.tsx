interface Props {
  className?: string
}

// 위험 식품 표시 그림: 빨간 동그라미 안의 하얀 느낌표. 위험 표시(DangerMark) · 위험 거르기 알약 · 날짜 창이 함께 쓴다.
// 색은 밝은색 · 어두운색, 어느 포인트 색에서도 항상 빨강이다 (SCREEN-SPEC 16.2). 장식이라 스크린 리더는 건너뛰고 옆의 "위험" 글자가 읽힌다.
export default function DangerIcon({ className }: Props) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="11" fill="#e0212a" />
      <path d="M12 6.2v7.2" stroke="#fff" strokeWidth="2.9" strokeLinecap="round" />
      <circle cx="12" cy="17.7" r="1.75" fill="#fff" />
    </svg>
  )
}
