import type { Category } from '../types/food'

interface Props {
  category: Category
  className?: string
}

// 식품 종류 그림 (채소 브로콜리 · 과일 주황 열매 · 육류 스테이크 · 수산 물고기 · 그 밖 달걀). SCREEN-SPEC 4.8.
// 임시 그림이다. 정확한 모양은 구현 단계에서 다듬는다. 색은 종류 색이라 밝은색/어두운색에서 같다.

// 스테이크 윗면 모양. 아래로 조금씩 옮겨 겹쳐 두께를 낸다.
const STEAK_TOP =
  'M2.5 10.5C2.5 7.3 6.8 5 12 5C17.6 5 21.5 6.8 21.5 9.8C21.5 13.6 17 16 11.6 16C6.4 16 2.5 14 2.5 10.5Z'

export default function CategoryIcon({ category, className }: Props) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {category === 'vegetable' && (
        <>
          <rect x="10" y="13" width="4" height="8" rx="2" fill="#9ccf7a" />
          <circle cx="7.5" cy="10.5" r="4.5" fill="#43b05c" />
          <circle cx="16.5" cy="10.5" r="4.5" fill="#43b05c" />
          <circle cx="12" cy="7" r="5" fill="#56c46d" />
        </>
      )}
      {category === 'fruit' && (
        <>
          <circle cx="12" cy="14" r="8" fill="#f08a3c" />
          <path d="M12 6c0-3 2-4 5-4 0 3-2 4-5 4z" fill="#43b05c" />
          <circle cx="9" cy="11" r="2" fill="#f7b27a" />
        </>
      )}
      {category === 'meat' && (
        <g transform="rotate(-8 12 12)">
          <path d={STEAK_TOP} transform="translate(0 4)" fill="#a8683a" />
          <path d={STEAK_TOP} transform="translate(0 3.2)" fill="#b5763f" />
          <path d={STEAK_TOP} transform="translate(0 2.4)" fill="#b5763f" />
          <path d={STEAK_TOP} transform="translate(0 1.6)" fill="#b5763f" />
          <path d={STEAK_TOP} transform="translate(0 0.8)" fill="#b5763f" />
          <path d={STEAK_TOP} fill="#f4907f" stroke="#fdeee6" strokeWidth="0.6" />
          <path
            d="M5.2 10.2C5.2 8.4 7.4 7.3 9.8 7.3C11.8 7.3 12.2 8.8 11.9 10.8C11.7 12.5 9.8 13.2 7.9 12.8C6.4 12.5 5.2 11.6 5.2 10.2Z"
            fill="#c8203f"
          />
          <path
            d="M13.1 7.5C16 7.1 19.1 8.1 19.1 10.1C19.1 12.5 17 13.9 14.8 13.5C13.5 13.2 13.3 11.8 13.4 10.4C13.5 9.3 13.3 8.4 13.1 7.5Z"
            fill="#c8203f"
          />
          <path
            d="M10.6 13.3C11.8 13.4 12.8 14 13 14.5C12.3 15.1 10.9 15 10.2 14.3C9.9 13.9 10.1 13.5 10.6 13.3Z"
            fill="#c8203f"
          />
        </g>
      )}
      {category === 'seafood' && (
        <>
          <ellipse cx="11" cy="12" rx="9" ry="5.5" fill="#4aa3df" />
          <path d="M17 12l6-5v10z" fill="#2f86c0" />
          <circle cx="7" cy="10.5" r="1.2" fill="#fff" />
          <path d="M11 8c1 2.5 1 5.5 0 8" stroke="#2f86c0" strokeWidth="1.2" fill="none" />
        </>
      )}
      {category === 'other' && (
        <>
          <path
            d="M12 2.5C8 2.5 4.8 9.5 4.8 14.6C4.8 18.8 8 21.5 12 21.5S19.2 18.8 19.2 14.6C19.2 9.5 16 2.5 12 2.5Z"
            fill="#fbeed4"
            stroke="#d6b97f"
            strokeWidth="1"
          />
          <path d="M15.2 8.5C17 11 17.6 14.6 16 17.4" fill="none" stroke="#e6cd9a" strokeWidth="1.6" strokeLinecap="round" />
          <ellipse cx="9.4" cy="9.2" rx="1.5" ry="2.8" transform="rotate(20 9.4 9.2)" fill="#fff" opacity="0.8" />
        </>
      )}
    </svg>
  )
}
