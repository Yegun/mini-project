import './HeroBand.css'

// 이 앱을 쓰면 뭐가 좋은지 세 가지. 앱이 실제로 하는 일(PRD Must: 기한을 색으로 보기 · 사진 등록 · 음식 추천)을 이득으로 풀어 쓴다.
// 없는 기능(휴대폰 알림 등, PRD 5-3)이나 지킬 수 없는 약속(예: "절대 안 버려요")은 적지 않는다.
const FEATURES = [
  { key: 'save', label: '버리는 식품이 줄어요' },
  { key: 'photo', label: '사진 한 장이면 등록 끝' },
  { key: 'cook', label: '오늘 뭐 먹지? 고민 끝' },
] as const

function FeatureIcon({ name }: { name: (typeof FEATURES)[number]['key'] }) {
  const common = { viewBox: '0 0 24 24', 'aria-hidden': true, focusable: false, className: 'hero__feat-icon' } as const
  if (name === 'photo') {
    // 카메라
    return (
      <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 8h3l1.5-2.5h7L17 8h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z" />
        <circle cx="12" cy="13.5" r="3.5" />
      </svg>
    )
  }
  if (name === 'save') {
    // 새싹: 버리지 않고 알뜰하게
    return (
      <svg {...common} fill="none" stroke="#2f8f5b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 21v-9" />
        <path d="M12 13c-4.5 0-6.5-2.5-6.5-6.5 4.5 0 6.5 2.5 6.5 6.5z" fill="#bfe8cf" />
        <path d="M12 15c0-4.5 2.5-7 7-7 0 4.5-2.5 7-7 7z" fill="#bfe8cf" />
      </svg>
    )
  }
  // 수저 · 포크 (파랑: 새싹 초록 · 카메라 주황과 겹치지 않게)
  return (
    <svg {...common} fill="none" stroke="#4a8fd6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 3v7a2 2 0 0 0 2 2v9" />
      <path d="M5 3v5M9 3v5" />
      <path d="M17 21V3c-2.5 1.5-3.5 4.5-3.5 8H17" />
    </svg>
  )
}

// 홈 위쪽 띠: 처음 들어온 사람이 "냉장고 속 식품의 유통기한을 챙겨 주는 앱"임을 바로 알게 하는 자리 (SCREEN-SPEC 4.2).
// 위에서 아래로: [큰 제목 + 한 줄 설명]과 속이 보이는 냉장고를 한 덩어리로 가운데에 모음 → 앱을 쓰면 좋은 점 세 가지.
// 그림은 임시 평면 그림이다. 실제 그림은 따로 만든다. 움직임(그림이 둥실, 반짝임)은 약하고 "움직임 줄이기"를 켜면 멈춘다.
export default function HeroBand() {
  return (
    <header className="hero">
      <span className="hero__blob hero__blob--1" aria-hidden="true" />
      <span className="hero__blob hero__blob--2" aria-hidden="true" />
      <div className="hero__row">
        <div className="hero__top">
          <h2 className="hero__title">
            <span className="hero__title-key">냉장고 속,</span>
            <br />
            한눈에 보세요!
          </h2>
          <p className="hero__sub">사 온 식품만 등록해 두세요.<br />먹을 날짜는 제가 계산해 드릴게요.</p>
        </div>
        <div className="hero__art-wrap">
          {/* 속이 보이는 냉장고 (임시 평면 그림): 문이 열려 있고 칸마다 식품이 들어 있다. 위에는 기한을 알리는 달력 · 종 모양 표지 */}
          <svg className="hero__art" viewBox="0 0 120 140" aria-hidden="true" focusable="false">
            <ellipse cx="62" cy="133" rx="40" ry="5" fill="rgba(0,0,0,.14)" />
            <rect x="26" y="14" width="74" height="116" rx="14" fill="#cdd8e3" />
            <rect x="31" y="19" width="64" height="106" rx="10" fill="#f4faff" />
            {/* 칸 */}
            <path d="M31 52h64M31 86h64" stroke="#c4d4e2" strokeWidth="3" />
            {/* 윗칸: 우유 · 달걀 */}
            <rect x="38" y="30" width="12" height="20" rx="2" fill="#fff" stroke="#8fa7bd" strokeWidth="1.6" />
            <path d="M38 36h12" stroke="#5aa2e0" strokeWidth="3" />
            <ellipse cx="66" cy="45" rx="5" ry="6" fill="#f7e2b5" />
            <ellipse cx="78" cy="45" rx="5" ry="6" fill="#f2d49a" />
            <ellipse cx="88" cy="46" rx="4" ry="5" fill="#f7e2b5" />
            {/* 가운데 칸: 생선 · 토마토 */}
            <path d="M38 70q9-9 20 0-11 9-20 0z" fill="#7fb4dc" />
            <path d="M58 70l7-5v10z" fill="#7fb4dc" />
            <circle cx="42" cy="68" r="1" fill="#2b3a4a" />
            <circle cx="80" cy="72" r="8" fill="#e0454a" />
            <path d="M80 64c0-3 3-4 6-3-1 3-3 4-6 3z" fill="#3f9a4c" />
            {/* 아랫칸: 채소 */}
            <path d="M40 112c0-10 8-16 14-16 0 8-4 16-14 16z" fill="#56c46d" />
            <path d="M54 112c0-10 8-16 14-16 0 8-4 16-14 16z" fill="#43b05c" />
            <rect x="76" y="98" width="12" height="14" rx="3" fill="#f0a35a" />
            <path d="M82 98l-3-5M82 98l3-5" stroke="#3f9a4c" strokeWidth="2" strokeLinecap="round" />
            {/* 손잡이 */}
            <rect x="90" y="30" width="4" height="18" rx="2" fill="#8fa7bd" />
            {/* 달력 표지: 기한 */}
            <g transform="translate(4 2) rotate(-8 14 14)">
              <rect x="0" y="0" width="30" height="30" rx="7" fill="#fff" />
              <path d="M0 11V7a7 7 0 0 1 7-7h16a7 7 0 0 1 7 7v4z" fill="#e0454a" />
              <circle cx="9" cy="3" r="2" fill="#fff" />
              <circle cx="21" cy="3" r="2" fill="#fff" />
              <path d="M8 20l5 5 9-10" fill="none" stroke="#2fb67a" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            </g>
          </svg>
          <svg className="hero__spark hero__spark--1" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M12 2.5l2 6.5 6.5 2-6.5 2-2 6.5-2-6.5-6.5-2 6.5-2z" fill="#fff" opacity="0.85" />
          </svg>
          <svg className="hero__spark hero__spark--2" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M12 2.5l2 6.5 6.5 2-6.5 2-2 6.5-2-6.5-6.5-2 6.5-2z" fill="#fff" opacity="0.7" />
          </svg>
        </div>
      </div>

      <ul className="hero__feats">
        {FEATURES.map((f) => (
          <li key={f.key} className="hero__feat">
            <FeatureIcon name={f.key} />
            <span>{f.label}</span>
          </li>
        ))}
      </ul>

    </header>
  )
}
