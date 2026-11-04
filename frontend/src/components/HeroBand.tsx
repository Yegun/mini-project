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
      <svg className="hero__art" viewBox="0 0 120 104" aria-hidden="true" focusable="false">
        <ellipse cx="62" cy="94" rx="46" ry="7" fill="rgba(0,0,0,.12)" />
        <path d="M82 40c18 2 26 20 18 38-6 12-22 14-30 6-10-10-6-40 12-44z" fill="#7a4fa8" />
        <path d="M80 38c-2-8 4-14 10-14 0 8-4 12-10 14z" fill="#3f9a4c" />
        <path d="M34 36c20-8 38 6 36 30-2 22-22 28-34 18-14-12-14-40-2-48z" fill="#e0454a" />
        <path d="M42 34c0-8 6-12 12-10-2 8-6 12-12 10z" fill="#3f9a4c" />
        <circle cx="22" cy="74" r="12" fill="#43b05c" />
        <circle cx="34" cy="68" r="10" fill="#56c46d" />
        <circle cx="14" cy="64" r="8" fill="#3da556" />
        <rect x="20" y="78" width="8" height="12" rx="3" fill="#8bc47a" />
        <circle cx="104" cy="30" r="9" fill="#ffd23f" />
      </svg>
    </header>
  )
}
