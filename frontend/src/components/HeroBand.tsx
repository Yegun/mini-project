import { formatDateParts, formatKoreanDate } from '../lib/dateText'
import './HeroBand.css'

export type HeroTone = 'soon' | 'expired' | 'warning' | 'ok' // 상황 요약 앞 점의 색: 임박 빨강 · 지남 검정 · 주의 노랑 · 여유 초록

interface Props {
  today: string // API 가 준 오늘 날짜 (D-021). 화면 시계는 쓰지 않는다
  note?: string // 날짜 아래 상황 요약 한 줄 (예: "곧 기한: 고등어"). 없으면 보이지 않는다
  noteTone?: HeroTone // 상황 요약 앞 점의 색 (기본 여유)
}

// 홈 위쪽 띠: 포인트 색 그라데이션 위에 큰 날짜(월 · 일 · 요일 알약), 지금 냉장고 상황 요약 알약, 채소 · 과일 그림 (SCREEN-SPEC 4.2, 13.2 의 7번).
// 상황 요약은 서버가 판정한 상태(임박 · 지남 · 주의)를 읽어 문장으로 바꿔 보여 줄 뿐이다 (D-009).
// 날짜는 서버가 준 오늘을 나눠 보이기만 한다 (D-016). 스크린 리더는 나눠 그린 글자 대신 "26년 11월 5일(목)" 전체를 읽는다.
// 그림은 임시 평면 그림이다. 실제 그림은 따로 만든다. 움직임(그림이 둥실, 반짝임)은 약하고 "움직임 줄이기"를 켜면 멈춘다.
export default function HeroBand({ today, note, noteTone = 'ok' }: Props) {
  const parts = formatDateParts(today)
  return (
    <header className="hero">
      <span className="hero__blob hero__blob--1" aria-hidden="true" />
      <span className="hero__blob hero__blob--2" aria-hidden="true" />
      <div className="hero__text">
        {parts ? (
          <p className="hero__date" aria-label={formatKoreanDate(today)}>
            <span className="hero__month" aria-hidden="true">
              {parts.year}년 {parts.month}월
            </span>
            <span className="hero__daybox" aria-hidden="true">
              <strong className="hero__day">{parts.day}</strong>
              <span className="hero__unit">일</span>
              <span className="hero__weekday">{parts.weekday}</span>
            </span>
          </p>
        ) : (
          <p className="hero__date">{formatKoreanDate(today)}</p>
        )}
        {note && (
          <p className="hero__note">
            <span className="hero__note-dot" data-tone={noteTone} aria-hidden="true" />
            {note}
          </p>
        )}
      </div>
      <svg className="hero__spark hero__spark--1" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M12 2.5l2 6.5 6.5 2-6.5 2-2 6.5-2-6.5-6.5-2 6.5-2z" fill="#fff" opacity="0.85" />
      </svg>
      <svg className="hero__spark hero__spark--2" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M12 2.5l2 6.5 6.5 2-6.5 2-2 6.5-2-6.5-6.5-2 6.5-2z" fill="#fff" opacity="0.7" />
      </svg>
      {/* 이 앱이 뭔지 한눈에: 그림에서 나오는 말풍선(가로 한 줄). 통통 튀어나왔다가 둥실거린다 */}
      <p className="hero__bubble">
        <span className="hero__bubble-key">유통기한,</span> 제가 챙길게요!
      </p>
      {/* 말하는 냉장고 그림 (임시 평면 그림). 눈 · 미소가 있어 말풍선의 주인으로 보인다 */}
      <svg className="hero__art" viewBox="0 0 120 104" aria-hidden="true" focusable="false">
        <ellipse cx="62" cy="95" rx="40" ry="6" fill="rgba(0,0,0,.14)" />
        <rect x="34" y="10" width="54" height="82" rx="13" fill="#cdd8e3" />
        <rect x="38" y="14" width="46" height="74" rx="10" fill="#f2f8fd" />
        <path d="M38 40h46" stroke="#b7cadb" strokeWidth="2.4" />
        <rect x="43" y="20" width="3.6" height="14" rx="1.8" fill="#8fa7bd" />
        <rect x="43" y="47" width="3.6" height="22" rx="1.8" fill="#8fa7bd" />
        <circle cx="56" cy="27" r="3.2" fill="#2b3a4a" />
        <circle cx="72" cy="27" r="3.2" fill="#2b3a4a" />
        <circle cx="57" cy="26" r="1" fill="#fff" />
        <circle cx="73" cy="26" r="1" fill="#fff" />
        <path d="M58 33q5 5 10 0" fill="none" stroke="#2b3a4a" strokeWidth="2" strokeLinecap="round" />
        <circle cx="51" cy="32" r="2.6" fill="#f6a5a8" opacity="0.8" />
        <circle cx="77" cy="32" r="2.6" fill="#f6a5a8" opacity="0.8" />
        <path d="M61 62c0-4 6-4 6 0 0 3-3 5-3 7 0-2-3-4-3-7z" fill="#e0454a" />
        <path d="M54 76h22" stroke="#b7cadb" strokeWidth="2.4" strokeLinecap="round" />
        <rect x="86" y="46" width="6" height="22" rx="3" fill="#8fa7bd" />
        <circle cx="98" cy="80" r="11" fill="#e0454a" />
        <path d="M98 69c0-5 3-8 8-7-1 5-3 7-8 7z" fill="#3f9a4c" />
        <circle cx="25" cy="80" r="9" fill="#43b05c" />
        <circle cx="33" cy="76" r="7" fill="#56c46d" />
        <rect x="23" y="84" width="6" height="8" rx="3" fill="#8bc47a" />
        <path d="M16 30l1.2 3 3 1.2-3 1.2L16 38.4l-1.2-3-3-1.2 3-1.2z" fill="#fff" opacity="0.75" />
      </svg>
    </header>
  )
}
