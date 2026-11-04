// 설정 화면 칸 제목 앞의 그림들 (화면 모양 · 개인정보 · 계정). 장식이라 스크린 리더는 건너뛴다.
// 임시 평면 그림이다. 다른 그림들과 같은 방식으로 24 x 24 안에 그린다.

interface IconProps {
  className?: string
}

const SVG = { viewBox: '0 0 24 24', 'aria-hidden': true, focusable: false } as const

// 화면 모양: 물감 팔레트
export function PaletteIcon({ className }: IconProps) {
  return (
    <svg className={className} {...SVG}>
      <path
        d="M12 2.8c-5.2 0-9.2 3.7-9.2 8.6 0 4.6 3.6 8 8 8h1.6c1.2 0 1.8-1.4 1-2.3-.7-.8-.4-2.2.9-2.2h2.7c2.1 0 3.6-1.5 3.6-3.6 0-5.2-3.9-8.5-8.6-8.5z"
        fill="#ffd9a0"
        stroke="#e0a050"
        strokeWidth="1.1"
      />
      <circle cx="7.6" cy="10.8" r="1.6" fill="#e0454a" />
      <circle cx="11" cy="6.9" r="1.6" fill="#ffc83d" />
      <circle cx="15.8" cy="7.7" r="1.6" fill="#43b05c" />
      <circle cx="17.6" cy="12.2" r="1.6" fill="#4aa3df" />
    </svg>
  )
}

// 개인정보 안내: 방패와 체크
export function ShieldIcon({ className }: IconProps) {
  return (
    <svg className={className} {...SVG}>
      <path d="M12 2.6l7.6 2.7v5.6c0 4.8-3.2 8.4-7.6 10.5-4.4-2.1-7.6-5.7-7.6-10.5V5.3z" fill="#9ccf7a" stroke="#56a26a" strokeWidth="1.1" strokeLinejoin="round" />
      <path d="M8.4 12.2l2.7 2.7 4.6-5.2" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

// 계정: 사람 모양
export function AccountIcon({ className }: IconProps) {
  return (
    <svg className={className} {...SVG}>
      <circle cx="12" cy="8.2" r="4" fill="#b4c6d8" stroke="#8aa2ba" strokeWidth="1.1" />
      <path d="M4.2 20.4c.6-4 3.8-6.4 7.8-6.4s7.2 2.4 7.8 6.4z" fill="#b4c6d8" stroke="#8aa2ba" strokeWidth="1.1" strokeLinejoin="round" />
    </svg>
  )
}

// 탈퇴 버튼 앞: 문을 나가는 화살표
export function ExitIcon({ className }: IconProps) {
  return (
    <svg className={className} {...SVG}>
      <path d="M10 4.5H6.2A1.7 1.7 0 0 0 4.5 6.2v11.6a1.7 1.7 0 0 0 1.7 1.7H10" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M14.2 8l4 4-4 4M18 12H9.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
