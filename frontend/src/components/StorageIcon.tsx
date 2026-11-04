import type { Storage } from '../types/food'

interface Props {
  storage: Storage
  className?: string
}

// 보관 방법 그림 (상온 해 · 냉장 냉장고 · 냉동 눈꽃). CategoryIcon 과 같은 방식의 임시 그림이다.
// 색은 보관 방법 색이라 밝은색/어두운색에서 같다.
export default function StorageIcon({ storage, className }: Props) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {storage === 'room' && (
        <>
          <g stroke="#f0a020" strokeWidth="2" strokeLinecap="round">
            <path d="M12 1.8v2.6M12 19.6v2.6M1.8 12h2.6M19.6 12h2.6" />
            <path d="M4.8 4.8l1.8 1.8M17.4 17.4l1.8 1.8M4.8 19.2l1.8-1.8M17.4 6.6l1.8-1.8" />
          </g>
          <circle cx="12" cy="12" r="5.5" fill="#ffc83d" />
          <circle cx="10.2" cy="10.2" r="1.6" fill="#ffe28a" />
        </>
      )}
      {storage === 'fridge' && (
        <>
          {/* 몸체와 안쪽(선반): 문이 열릴 때만 보인다 */}
          <rect x="5" y="2" width="14" height="20" rx="3" fill="#2f86c0" />
          <rect x="6.2" y="3.2" width="11.6" height="17.6" rx="2.2" fill="#e3f4ff" />
          <path d="M6.2 9.5h11.6M6.2 15h11.6" stroke="#b7dcf2" strokeWidth="0.8" />
          {/* 문: 닫힌 모습이 기본 그림이다. 움직이는 곳에서는 CSS 가 오른쪽을 축으로 접었다 편다 (fridge-door) */}
          <g className="fridge-door">
            <rect x="5" y="2" width="14" height="20" rx="3" fill="#4aa3df" />
            <rect x="5" y="2" width="14" height="20" rx="3" fill="none" stroke="#2f86c0" strokeWidth="1" />
            <path d="M5 9.5h14" stroke="#2f86c0" strokeWidth="1.2" />
            <rect x="7.5" y="5" width="1.8" height="2.6" rx="0.9" fill="#fff" />
            <rect x="7.5" y="12" width="1.8" height="4.5" rx="0.9" fill="#fff" />
          </g>
        </>
      )}
      {storage === 'freezer' && (
        <g stroke="#6aa9e6" strokeWidth="2" strokeLinecap="round" fill="none">
          <path d="M12 2.5v19M3.8 7.25l16.4 9.5M3.8 16.75l16.4-9.5" />
          <path d="M9.6 3.9L12 6.3l2.4-2.4M9.6 20.1L12 17.7l2.4 2.4" strokeWidth="1.5" />
          <path d="M3.9 10.2l3.3-.9-.9-3.3M20.1 13.8l-3.3.9.9 3.3" strokeWidth="1.5" />
          <path d="M3.9 13.8l3.3.9-.9 3.3M20.1 10.2l-3.3-.9.9-3.3" strokeWidth="1.5" />
        </g>
      )}
    </svg>
  )
}
