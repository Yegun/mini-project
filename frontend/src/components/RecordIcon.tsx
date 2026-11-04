import './RecordIcon.css'

interface Props {
  kind: 'eaten' | 'discarded' // 다 먹음 · 버림
  flies?: boolean // 버림 그림에서 쓰레기통 주위에 파리를 날릴지 (이번 달에 버린 식품이 있을 때)
  className?: string
}

// 기록 화면의 "다 먹음 · 버림" 카드 그림 (장식이라 스크린 리더는 건너뛴다. 숫자와 이름은 카드 글자가 읽어 준다).
// 다 먹음: 숟가락과 포크가 X 로 교차 + 반짝임 / 버림: 쓰레기통 + 주위를 천천히 나는 파리 세 마리.
// 임시 그림이다. 움직임은 RecordIcon.css 에 있고 "움직임 줄이기"를 켜면 멈춘다.
export default function RecordIcon({ kind, flies = false, className }: Props) {
  return (
    <svg className={className ? `record-icon ${className}` : 'record-icon'} viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      {kind === 'eaten' && (
        <>
          <circle cx="24" cy="24" r="22" fill="rgba(47, 182, 122, 0.16)" />
          {/* 포크 */}
          <g transform="rotate(-38 24 24)">
            <path d="M17.5 8v8M24 8v9M30.5 8v8" stroke="#6f87a0" strokeWidth="2.4" strokeLinecap="round" />
            <path d="M17.5 15c0 5 2.5 7.5 6.5 7.5s6.5-2.5 6.5-7.5" fill="none" stroke="#6f87a0" strokeWidth="2.4" strokeLinecap="round" />
            <rect x="22.2" y="21" width="3.6" height="19" rx="1.8" fill="#6f87a0" />
          </g>
          {/* 숟가락 */}
          <g transform="rotate(38 24 24)">
            <ellipse cx="24" cy="14" rx="6.2" ry="8" fill="#b4c6d8" stroke="#8aa2ba" strokeWidth="1.2" />
            <rect x="22.2" y="21" width="3.6" height="19" rx="1.8" fill="#8aa2ba" />
          </g>
          <path
            className="record-icon__sparkle"
            d="M38 8l1.3 3 3 1.3-3 1.3L38 16.6l-1.3-3-3-1.3 3-1.3z"
            fill="#ffd23f"
          />
        </>
      )}
      {kind === 'discarded' && (
        <>
          <circle cx="24" cy="24" r="22" fill="rgba(224, 69, 74, 0.12)" />
          {/* 쓰레기통: 몸통 · 줄무늬 · 뚜껑 · 손잡이 */}
          <path d="M14 19l2 20a2.2 2.2 0 0 0 2.2 2h11.6a2.2 2.2 0 0 0 2.2-2l2-20z" fill="#8e9aa9" />
          <path d="M20 23v13M24 23v13M28 23v13" stroke="#b7c0cb" strokeWidth="1.8" strokeLinecap="round" />
          <rect x="11" y="15" width="26" height="4.2" rx="2.1" fill="#a6b0bd" />
          <rect x="19.5" y="11.5" width="9" height="4" rx="2" fill="#8e9aa9" />
          {flies && (
            <>
              <Fly className="record-icon__fly record-icon__fly--1" x={10} y={11} />
              <Fly className="record-icon__fly record-icon__fly--2" x={36} y={9} />
              <Fly className="record-icon__fly record-icon__fly--3" x={38} y={26} />
            </>
          )}
        </>
      )}
    </svg>
  )
}

// 파리 한 마리: 까만 몸통 + 반투명 날개 두 장. (x, y)가 몸통 가운데다.
function Fly({ className, x, y }: { className: string; x: number; y: number }) {
  return (
    <g className={className}>
      <ellipse cx={x - 1.7} cy={y - 2.2} rx="2.3" ry="1.3" fill="#fff" opacity="0.8" stroke="#9aa6b3" strokeWidth="0.3" />
      <ellipse cx={x + 1.7} cy={y - 2.2} rx="2.3" ry="1.3" fill="#fff" opacity="0.8" stroke="#9aa6b3" strokeWidth="0.3" />
      {/* 몸통은 까만색이라 어두운 화면에서도 보이게 옅은 윤곽선을 두른다 */}
      <ellipse cx={x} cy={y} rx="2.4" ry="1.8" fill="#2e2e2e" stroke="#d9dee5" strokeWidth="0.5" />
    </g>
  )
}
