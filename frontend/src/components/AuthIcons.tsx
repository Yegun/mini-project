// 로그인 · 가입 화면의 그림들. 장식이라 스크린 리더는 건너뛴다. 임시 평면 그림이다.

interface IconProps {
  className?: string
}

const SVG = { viewBox: '0 0 24 24', 'aria-hidden': true, focusable: false } as const

// 이메일 입력칸 안의 봉투
export function MailIcon({ className }: IconProps) {
  return (
    <svg className={className} {...SVG}>
      <rect x="3" y="5.5" width="18" height="13" rx="3" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M4 8l8 5.5L20 8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

// 비밀번호 입력칸 안의 자물쇠
export function LockIcon({ className }: IconProps) {
  return (
    <svg className={className} {...SVG}>
      <rect x="4.5" y="10.5" width="15" height="10" rx="3" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="15.5" r="1.4" fill="currentColor" />
    </svg>
  )
}

// 비밀번호 보기 버튼: 눈 (보이는 중이면 줄이 그어진 눈)
export function EyeIcon({ className, off = false }: IconProps & { off?: boolean }) {
  return (
    <svg className={className} {...SVG}>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="2" />
      {off && <path d="M4 4l16 16" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />}
    </svg>
  )
}

// 위쪽 띠 그림: 냉장고와 곁의 과일 · 채소
export function AuthArt({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 120 104" aria-hidden="true" focusable="false">
      <ellipse cx="60" cy="96" rx="48" ry="6" fill="rgba(0,0,0,.12)" />
      <rect x="30" y="8" width="46" height="84" rx="11" fill="#cdd8e3" />
      <rect x="34" y="12" width="38" height="76" rx="8" fill="#eaf3fb" />
      <path d="M34 38h38" stroke="#b7cadb" strokeWidth="2.4" />
      <rect x="39" y="19" width="3.8" height="13" rx="1.9" fill="#8fa7bd" />
      <rect x="39" y="46" width="3.8" height="26" rx="1.9" fill="#8fa7bd" />
      <circle cx="58" cy="24" r="4.4" fill="#4aa3df" opacity="0.85" />
      <path d="M53 62h14M53 70h10" stroke="#b7cadb" strokeWidth="2.4" strokeLinecap="round" />
      {/* 곁의 과일과 채소 */}
      <circle cx="94" cy="78" r="14" fill="#e0454a" />
      <path d="M94 64c0-6 4-9 9-8-1 6-4 8-9 8z" fill="#3f9a4c" />
      <circle cx="98" cy="74" r="2.6" fill="#f08a8e" />
      <circle cx="16" cy="78" r="9" fill="#43b05c" />
      <circle cx="24" cy="74" r="7" fill="#56c46d" />
      <circle cx="10" cy="72" r="6" fill="#3da556" />
      <rect x="14" y="82" width="6" height="9" rx="3" fill="#8bc47a" />
      <path d="M96 22l1.8 4.6 4.6 1.8-4.6 1.8L96 35l-1.8-4.8-4.6-1.8 4.6-1.8z" fill="#fff" opacity="0.9" />
      <path d="M14 28l1.2 3 3 1.2-3 1.2L14 36.4l-1.2-3-3-1.2 3-1.2z" fill="#fff" opacity="0.75" />
    </svg>
  )
}
