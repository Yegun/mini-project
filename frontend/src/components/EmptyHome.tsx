import './StateNotice.css'

interface Props {
  onAdd?: () => void // 식품 등록 화면으로
}

// 빈 홈 안내: 빈 냉장고 그림 + 안내 문구 + 식품 등록 버튼 (OQ-05). 문구는 임시 문구다 (OQ-03).
// 홈 · 기록 · 음식추천이 식품이 없을 때 함께 쓴다. 그림은 임시 평면 그림이다.
export default function EmptyHome({ onAdd }: Props) {
  return (
    <div className="notice notice--empty">
      <svg className="notice__art" viewBox="0 0 72 88" aria-hidden="true" focusable="false">
        <ellipse cx="36" cy="82" rx="26" ry="4" fill="rgba(0,0,0,.1)" />
        <rect x="12" y="6" width="48" height="74" rx="10" fill="#cdd8e3" />
        <rect x="16" y="10" width="40" height="66" rx="7" fill="#eaf3fb" />
        <path d="M16 33h40" stroke="#b7cadb" strokeWidth="2" />
        <rect x="21" y="16" width="3.4" height="11" rx="1.7" fill="#8fa7bd" />
        <rect x="21" y="40" width="3.4" height="22" rx="1.7" fill="#8fa7bd" />
        <path d="M44 20l1.6 3.8 3.8 1.6-3.8 1.6L44 30.8l-1.6-3.8-3.8-1.6 3.8-1.6z" fill="#ffd23f" />
        <path d="M38 52l1 2.4 2.4 1-2.4 1-1 2.4-1-2.4-2.4-1 2.4-1z" fill="#ffd23f" opacity="0.8" />
      </svg>
      <p className="notice__text">아직 등록한 식품이 없어요. 식품을 등록해 보세요.</p>
      <button type="button" className="notice__button notice__button--primary" onClick={onAdd}>
        냉장고에 넣기
      </button>
    </div>
  )
}
