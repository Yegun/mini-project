import type { Cuisine, Meal } from '../types/recommend'

// 음식추천 화면의 그림들 (끼니 · 음식 종류 · 위쪽 띠 · 빈 상태). 장식이라 스크린 리더는 건너뛴다.
// 임시 평면 그림이다. 다른 그림(CategoryIcon · StorageIcon)과 같은 방식으로 24 x 24 안에 그린다.

interface IconProps {
  className?: string
}

const SVG = { viewBox: '0 0 24 24', 'aria-hidden': true, focusable: false } as const

// 끼니: 아침 = 떠오르는 해 · 점심 = 높이 뜬 해 · 저녁 = 달과 별
export function MealIcon({ meal, className }: IconProps & { meal: Meal }) {
  return (
    <svg className={className} {...SVG}>
      {meal === 'breakfast' && (
        <>
          <g stroke="#f0a020" strokeWidth="1.8" strokeLinecap="round">
            <path d="M12 3.2v2.4M4.6 6.4l1.7 1.7M19.4 6.4l-1.7 1.7M2.6 12.6h2.2M19.2 12.6h2.2" />
          </g>
          <path d="M6.6 16a5.4 5.4 0 0 1 10.8 0z" fill="#ffc83d" />
          <path d="M2.5 16.4h19" stroke="#e08a1e" strokeWidth="1.8" strokeLinecap="round" />
          <path d="M6 19.8h12" stroke="#f3b86a" strokeWidth="1.6" strokeLinecap="round" />
        </>
      )}
      {meal === 'lunch' && (
        <>
          <g stroke="#f0a020" strokeWidth="2" strokeLinecap="round">
            <path d="M12 1.8v2.6M12 19.6v2.6M1.8 12h2.6M19.6 12h2.6" />
            <path d="M4.8 4.8l1.8 1.8M17.4 17.4l1.8 1.8M4.8 19.2l1.8-1.8M17.4 6.6l1.8-1.8" />
          </g>
          <circle cx="12" cy="12" r="5.5" fill="#ffc83d" />
          <circle cx="10.2" cy="10.2" r="1.6" fill="#ffe28a" />
        </>
      )}
      {meal === 'dinner' && (
        <>
          <path d="M16.5 3.5a8.5 8.5 0 1 0 4 14.6A7 7 0 0 1 16.5 3.5z" fill="#c9c4ff" stroke="#8f86e8" strokeWidth="1" />
          <path d="M18 4.2l.7 1.6 1.6.7-1.6.7-.7 1.6-.7-1.6-1.6-.7 1.6-.7z" fill="#ffd23f" />
          <circle cx="20.4" cy="11" r="0.9" fill="#ffd23f" />
        </>
      )}
    </svg>
  )
}

// 음식 종류: 양식 접시와 포크 · 한식 밥그릇 · 일식 초밥 · 중식 만두 · 간단히 번개 · 직접 입력 연필
export function CuisineIcon({ cuisine, className }: IconProps & { cuisine: Cuisine }) {
  return (
    <svg className={className} {...SVG}>
      {cuisine === 'western' && (
        <>
          <circle cx="12" cy="12.5" r="7" fill="#fff" stroke="#c7ced6" strokeWidth="1.2" />
          <circle cx="12" cy="12.5" r="4.2" fill="#f4907f" />
          <path d="M9.6 11.2c1.2-1.2 3.4-1.2 4.8 0M9.8 13.8c1.2 1 3 1 4.4 0" stroke="#fff" strokeWidth="1" fill="none" strokeLinecap="round" />
          <path d="M3.2 4.5v6.5M4.8 4.5v6.5M2.6 4.5v3M5.4 4.5v3" stroke="#8a97a6" strokeWidth="1" strokeLinecap="round" />
          <path d="M21 4.5c-1.6 1-2 3.4-2 6h2z" fill="#8a97a6" />
        </>
      )}
      {cuisine === 'korean' && (
        <>
          <path d="M3.5 11.5h17a8.5 8.5 0 0 1-17 0z" fill="#e0454a" />
          <path d="M5.8 11.5a6.2 4.4 0 0 1 12.4 0z" fill="#fff" />
          <path d="M9 19.8h6" stroke="#b83a3f" strokeWidth="1.8" strokeLinecap="round" />
          <path d="M14 8.6L20.4 2.6M16.6 9.4L21.6 4.6" stroke="#a0724a" strokeWidth="1.5" strokeLinecap="round" />
        </>
      )}
      {cuisine === 'japanese' && (
        <>
          <rect x="3" y="11.5" width="18" height="7.5" rx="3.6" fill="#fff" stroke="#d9dee4" strokeWidth="1" />
          <path d="M3.4 11.8c1.4-4.2 6-5.4 8.6-5.4s7.2 1.2 8.6 5.4c-3.8 1.4-13.4 1.4-17.2 0z" fill="#ff8a5c" />
          <path d="M7.2 8.4l1.4 3.1M11.6 7l.6 4.4M16 8.2l-1 3.3" stroke="#ffc2a6" strokeWidth="1" strokeLinecap="round" />
          <rect x="10" y="9.6" width="4.4" height="10.6" rx="1" fill="#2b3a3f" opacity="0.88" />
        </>
      )}
      {cuisine === 'chinese' && (
        <>
          <path d="M3 15.6c0-5.2 4-9 9-9s9 3.8 9 9c0 1.4-1.2 2.4-2.6 2.4H5.6C4.2 18 3 17 3 15.6z" fill="#fff1d8" stroke="#e0b27a" strokeWidth="1.2" />
          <path d="M6.8 17.6c.8-3.4 1.6-6.2 2.4-8.6M10.2 17.8c.4-3.6.7-6.6.8-9.6M13.8 17.8c-.1-3.6-.4-6.6-.9-9.4M17.2 17.6c-.8-3.2-1.6-5.8-2.6-8" stroke="#e0b27a" strokeWidth="1" strokeLinecap="round" fill="none" />
          <path d="M8 4.2c1 .8 1.4 1.6 1.2 2.6M12 3c1 .8 1.4 1.6 1.2 2.6" stroke="#c7ced6" strokeWidth="1.1" strokeLinecap="round" fill="none" />
        </>
      )}
      {cuisine === 'simple' && (
        <>
          <circle cx="12" cy="12" r="9.2" fill="#fff0b3" />
          <path d="M13.4 3.6L6.6 13.2h4.4l-1 7.2 7.4-10.2h-4.6z" fill="#ffb300" stroke="#e08a00" strokeWidth="0.8" strokeLinejoin="round" />
        </>
      )}
      {cuisine === 'custom' && (
        <>
          <path d="M4 20l1-4.6 11-11a1.8 1.8 0 0 1 2.6 0l1.6 1.6a1.8 1.8 0 0 1 0 2.6l-11 11z" fill="#ffd23f" />
          <path d="M4 20l1-4.6 3.6 3.6z" fill="#f3d6b0" />
          <path d="M4 20l.5-2.2 1.7 1.7z" fill="#555" />
          <path d="M15 5.6l3.4 3.4" stroke="#e08a1e" strokeWidth="1.2" />
          <path d="M16.2 4.4l3.4 3.4 .8-.8a1.8 1.8 0 0 0 0-2.6l-.8-.8a1.8 1.8 0 0 0-2.6 0z" fill="#f4907f" />
        </>
      )}
    </svg>
  )
}

// 위쪽 띠 그림: 김이 오르는 냄비와 숟가락
export function PotArt({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 96 80" aria-hidden="true" focusable="false">
      <ellipse cx="46" cy="72" rx="34" ry="5" fill="rgba(0,0,0,.12)" />
      <path className="rec-steam rec-steam--1" d="M34 26c-4-5 4-8 0-14" stroke="#fff" strokeWidth="3" strokeLinecap="round" fill="none" opacity="0.85" />
      <path className="rec-steam rec-steam--2" d="M48 24c-4-5 4-8 0-14" stroke="#fff" strokeWidth="3" strokeLinecap="round" fill="none" opacity="0.85" />
      <path className="rec-steam rec-steam--3" d="M62 26c-4-5 4-8 0-14" stroke="#fff" strokeWidth="3" strokeLinecap="round" fill="none" opacity="0.85" />
      <rect x="22" y="30" width="48" height="6" rx="3" fill="#8f9aa8" />
      <path d="M24 36h44v20a14 14 0 0 1-14 14H38a14 14 0 0 1-14-14z" fill="#e0454a" />
      <path d="M30 42h6v22h-6z" fill="#fff" opacity="0.25" />
      <rect x="12" y="42" width="12" height="5" rx="2.5" fill="#b83a3f" />
      <rect x="68" y="42" width="12" height="5" rx="2.5" fill="#b83a3f" />
      <circle cx="46" cy="27" r="3.6" fill="#8f9aa8" />
      <g transform="rotate(24 84 44)">
        <ellipse cx="84" cy="30" rx="5.4" ry="7.2" fill="#b4c6d8" stroke="#8aa2ba" strokeWidth="1.2" />
        <rect x="82.2" y="36" width="3.6" height="22" rx="1.8" fill="#8aa2ba" />
      </g>
    </svg>
  )
}

// 추천을 못 찾았을 때 그림: 돋보기와 물음표 냄비
export function NoMatchArt({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 64 56" aria-hidden="true" focusable="false">
      <ellipse cx="30" cy="51" rx="22" ry="3.5" fill="rgba(0,0,0,.1)" />
      <rect x="12" y="22" width="36" height="5" rx="2.5" fill="#8f9aa8" />
      <path d="M14 27h32v14a11 11 0 0 1-11 11H25a11 11 0 0 1-11-11z" fill="#cbd3dc" />
      <path d="M26 33.5c0-2.4 1.8-4 4-4s4 1.4 4 3.4c0 2.2-2.4 2.6-3.4 4.2" fill="none" stroke="#6f7c8a" strokeWidth="2.2" strokeLinecap="round" />
      <circle cx="30.6" cy="42" r="1.4" fill="#6f7c8a" />
      <circle cx="47" cy="17" r="8" fill="rgba(255,255,255,.5)" stroke="#6f87a0" strokeWidth="2.6" />
      <path d="M53 23l7 7" stroke="#6f87a0" strokeWidth="3.2" strokeLinecap="round" />
    </svg>
  )
}

// 추천받기 버튼의 반짝이
export function SparkleIcon({ className }: IconProps) {
  return (
    <svg className={className} {...SVG}>
      <path d="M12 2.5l2.2 6.3 6.3 2.2-6.3 2.2L12 19.5l-2.2-6.3L3.5 11l6.3-2.2z" fill="currentColor" />
      <path d="M19 15.5l.9 2.2 2.2.9-2.2.9-.9 2.2-.9-2.2-2.2-.9 2.2-.9z" fill="currentColor" />
    </svg>
  )
}
