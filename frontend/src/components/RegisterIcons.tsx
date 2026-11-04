// 식품 등록 · 식품 상세 화면의 그림들. 장식이라 스크린 리더는 건너뛴다. 임시 평면 그림이다.

interface IconProps {
  className?: string
}

// 사진으로 등록: 영수증과 카메라, 반짝이
export function CameraArt({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 64 56" aria-hidden="true" focusable="false">
      <ellipse cx="32" cy="52" rx="24" ry="3.5" fill="rgba(0,0,0,.12)" />
      {/* 영수증 */}
      <path d="M12 8h26v38l-3.3-2.2-3.3 2.2-3.3-2.2-3.3 2.2-3.3-2.2-3.5 2.2z" fill="#fff" stroke="#c7ced6" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M17 16h14M17 22h10M17 28h14M17 34h8" stroke="#c7ced6" strokeWidth="2" strokeLinecap="round" />
      {/* 카메라 */}
      <rect x="28" y="24" width="30" height="22" rx="5" fill="#4a5a6b" />
      <path d="M36 24l2-4h10l2 4z" fill="#3a4856" />
      <circle cx="43" cy="35" r="7.5" fill="#dff1ff" stroke="#8fb4d4" strokeWidth="2.2" />
      <circle cx="43" cy="35" r="3.4" fill="#4aa3df" />
      <circle cx="53" cy="28.6" r="1.4" fill="#ffd23f" />
      <path d="M50 8l1.6 4 4 1.6-4 1.6L50 19l-1.6-3.8-4-1.6 4-1.6z" fill="#ffd23f" />
    </svg>
  )
}

// 직접 등록: 메모지와 연필
export function PencilArt({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 64 56" aria-hidden="true" focusable="false">
      <ellipse cx="32" cy="52" rx="24" ry="3.5" fill="rgba(0,0,0,.12)" />
      <rect x="10" y="6" width="34" height="42" rx="5" fill="#fff6d6" stroke="#e6cf8a" strokeWidth="1.4" />
      <path d="M17 18h20M17 25h20M17 32h13" stroke="#e6cf8a" strokeWidth="2.2" strokeLinecap="round" />
      <g transform="rotate(38 46 30)">
        <rect x="42.5" y="10" width="7" height="30" rx="1.5" fill="#ffd23f" />
        <rect x="42.5" y="10" width="7" height="6" rx="1.5" fill="#f4907f" />
        <path d="M42.5 40h7l-3.5 8z" fill="#f3d6b0" />
        <path d="M45 44.6l1 2.4 1-2.4z" fill="#555" />
      </g>
    </svg>
  )
}

// 사진을 고르기 전 빈 칸 그림: 사진 틀과 산 · 해
export function PhotoArt({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 64 56" aria-hidden="true" focusable="false">
      <rect x="6" y="8" width="52" height="38" rx="7" fill="#eaf3fb" stroke="#b7cadb" strokeWidth="2" strokeDasharray="4 3" />
      <circle cx="21" cy="21" r="5" fill="#ffd23f" />
      <path d="M10 42l15-15 9 9 8-8 12 14z" fill="#9ccf7a" />
      <path d="M33 42l9-9 12 9z" fill="#56a26a" />
    </svg>
  )
}

// 검색창 안의 돋보기
export function SearchIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="10.5" cy="10.5" r="6" fill="none" stroke="currentColor" strokeWidth="2.2" />
      <path d="M15.2 15.2L20 20" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  )
}

// 정보 고치기 버튼 앞의 연필
export function EditIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M4 20l1-4.6 11-11a1.8 1.8 0 0 1 2.6 0l1.6 1.6a1.8 1.8 0 0 1 0 2.6l-11 11z" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M14.5 6.5l3 3" stroke="currentColor" strokeWidth="2" />
    </svg>
  )
}

// 삭제 버튼 앞의 쓰레기통
export function TrashLineIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v5M14 11v5" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
