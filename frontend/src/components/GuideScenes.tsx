import type { CSSProperties, ReactNode } from 'react'
import { BasketArt, CameraArt, ReceiptArt, TrashLineIcon } from './RegisterIcons'
import { STATUS_COLOR } from '../lib/statusColor'
import './GuideScenes.css'

// 사용 설명서 장면 9장의 그림 (US-046, SCREEN-SPEC 17.2, D-199, D-200, D-205).
// 화면 코드(CSS · SVG)로 그려서 밝은색 · 어두운색 · 포인트 색을 그대로 따른다. 움직이는 것은 눌러야 할 곳을 가리키는 동그라미(.gs-ring),
// 장면 안의 막대 · 줄 · 창이 나타나는 모습, 이어지는 화면을 차례로 보여 주는 장면(2장 · 5장 · 6장), 1장의 냉장고 문이다.
// "움직임 줄이기"를 켜면 모두 멈춘 그림으로 보이고, 이어지는 화면은 한꺼번에 위아래로 펼쳐 보인다 (GuideScenes.css 맨 아래, D-188).
// 그림 속 식품 이름과 숫자는 모두 예시다. 장면마다 오른쪽 위에 "예시" 표시가 붙는다.

// 눌러야 할 곳을 가리키는 동그라미. 놓을 자리를 style(left · top)로 받고, 그 자리가 동그라미의 가운데가 된다
function Ring({ style }: { style?: CSSProperties }) {
  return <span className="gs-ring" style={style} aria-hidden="true" />
}

// 장면 그림의 바깥 상자. 오른쪽 위에 "예시" 표시
function Frame({ children }: { children: ReactNode }) {
  return (
    <div className="gs" aria-hidden="true">
      <span className="gs__tag">예시</span>
      {children}
    </div>
  )
}

// 이어지는 화면을 차례로 보여 주는 칸. 화면(panel)이 하나씩 나타났다 사라지고, 움직임 줄이기에서는 모두 펼쳐 보인다
// tall: 화면 하나가 길 때(6장의 목록 창) 칸을 더 높게 잡는다
function Sequence({ count, tall, children }: { count: 2 | 3; tall?: boolean; children: ReactNode }) {
  return <div className={tall ? `gs-seq gs-seq--${count} gs-seq--tall` : `gs-seq gs-seq--${count}`}>{children}</div>
}

function Panel({ step, children }: { step: string; children: ReactNode }) {
  return (
    <div className="gs-seq__panel">
      <p className="gs__step">{step}</p>
      {children}
    </div>
  )
}

// 1장에 쓰는 냉장고: 문이 열렸다 닫힌다. 몸통(안쪽 · 선반 · 우유 · 토마토 · 브로콜리 · 당근)은 SVG 로 그리고,
// 문은 두께가 있는 판(앞면 + 옆면)으로 만들어 왼쪽 경첩을 중심으로 실제처럼 돌아 열린다 (CSS 3D). 움직임 줄이기에서는 문이 열린 모습으로 멈춘다
function OpeningFridge() {
  return (
    <div className="gs-fridge" aria-hidden="true">
      <svg className="gs-fridge__body" viewBox="0 0 120 136" focusable="false">
        <ellipse cx="60" cy="128" rx="46" ry="6" fill="rgba(0,0,0,.14)" />
        {/* 몸통과 안쪽 */}
        <rect x="20" y="6" width="80" height="116" rx="14" fill="#c5d3e0" />
        <rect x="26" y="12" width="68" height="104" rx="9" fill="#f5f9fd" />
        <path d="M26 48h68M26 82h68" stroke="#d3dfea" strokeWidth="3" />
        {/* 위 칸: 우유 · 토마토 */}
        <rect x="34" y="24" width="14" height="24" rx="2.5" fill="#fff" stroke="#9fb6cc" strokeWidth="1.6" />
        <path d="M34 31h14" stroke="#4aa3df" strokeWidth="5" />
        <circle cx="68" cy="39" r="9" fill="#e0454a" />
        <path d="M68 30l-2.5-4M68 30l3-3.4" stroke="#3a8a46" strokeWidth="2.2" strokeLinecap="round" />
        {/* 가운데 칸: 브로콜리 · 당근 */}
        <circle cx="40" cy="64" r="8" fill="#43b05c" />
        <circle cx="49" cy="62" r="6.5" fill="#56c46d" />
        <rect x="40" y="68" width="6" height="14" rx="2" fill="#8bc47a" />
        <path d="M62 82l22-6-5 12z" fill="#f08a2d" />
        <path d="M84 76l5-3M84 77l4 2" stroke="#3a8a46" strokeWidth="2" strokeLinecap="round" />
        {/* 아래 칸: 서랍 */}
        <rect x="32" y="92" width="56" height="18" rx="4" fill="#e3edf6" stroke="#c5d3e0" strokeWidth="1.6" />
        <path d="M104 20l1.8 4.4 4.4 1.8-4.4 1.8-1.8 4.4-1.8-4.4-4.4-1.8 4.4-1.8z" fill="#ffd23f" />
      </svg>
      <span className="gs-fridge__door">
        <span className="gs-fridge__front">
          {/* 손잡이: 문 앞면에 붙은 납작한 단색 막대. 문과 같이 움직인다 */}
          <span className="gs-fridge__handle gs-fridge__handle--top" />
          <span className="gs-fridge__handle gs-fridge__handle--bottom" />
        </span>
        <span className="gs-fridge__edge" />
      </span>
      {/* 문이 열릴 때 안에서 흘러나와 아래로 퍼지는 냉기 */}
      <span className="gs-fridge__mist">
        {[0, 1, 2, 3, 4].map((i) => (
          <span key={i} style={{ '--i': i } as CSSProperties} />
        ))}
      </span>
    </div>
  )
}

// 1장: 이 앱은 이런 앱이에요 — 눌러서 따라 할 곳이 없는 소개 장면. 문이 열렸다 닫히는 냉장고와 앱 이름
export function SceneIntro() {
  return (
    <div className="gs-intro" aria-hidden="true">
      <OpeningFridge />
      <p className="gs-intro__brand">냉장고 관리</p>
    </div>
  )
}

// 2장: 사진으로 한 번에 넣어요 — 1. 「사진으로 넣기」 2. 영수증 · 장바구니 사진 고르기 3. AI 가 분석하는 화면까지 이어서 보여 준다
export function ScenePhoto() {
  return (
    <Frame>
      <Sequence count={3}>
        <Panel step="1. 사진으로 넣기를 눌러요">
          <div className="gs-card gs-card--hot">
            <CameraArt className="gs-card__art" />
            <b>사진으로 넣기</b>
            <Ring style={{ left: 'calc(100% - 2rem)', top: '50%' }} />
          </div>
          <div className="gs-card">
            <span className="gs-card__art gs-card__art--blank" />
            <b>직접 넣기</b>
          </div>
        </Panel>
        <Panel step="2. 영수증이나 장바구니 사진을 골라요">
          <div className="gs-drop">
            <div className="gs-drop__tiles">
              <span className="gs-tile">
                <ReceiptArt className="gs-tile__art" />
                영수증
              </span>
              <span className="gs-tile">
                <BasketArt className="gs-tile__art" />
                장바구니
              </span>
            </div>
            <span className="gs-btnwrap gs-btnwrap--inline">
              <span className="gs-btn gs-btn--small">사진 고르기</span>
              <Ring style={{ left: '82%', top: '60%' }} />
            </span>
          </div>
          <div className="gs-btn gs-btn--dim">사진 올리기</div>
        </Panel>
        <Panel step="3. AI 가 사진에서 식품을 찾아요">
          <div className="gs-think">
            <span className="gs-spin" />
            <b>지금 사진을 분석하고 있어요</b>
            <small>잠깐만 기다려 주세요</small>
          </div>
        </Panel>
      </Sequence>
    </Frame>
  )
}

// 3장: 확인하고 등록해요 — 목록을 확인하고 「한꺼번에 등록」
export function SceneReview() {
  const rows = [
    { name: '고등어', note: '⚠ 위험', on: true },
    { name: '두부', note: '냉장', on: true },
    { name: '양파', note: '빼기', on: false },
  ]
  return (
    <Frame>
      <p className="gs__cap">틀린 것만 고치거나 빼 주세요.</p>
      {rows.map((r, i) => (
        <div key={r.name} className={r.on ? 'gs-row' : 'gs-row gs-row--off'} style={{ '--i': i } as CSSProperties}>
          <span className={r.on ? 'gs-check gs-check--on' : 'gs-check'} />
          <b>{r.name}</b>
          <span className="gs-row__note">{r.note}</span>
        </div>
      ))}
      <div className="gs-btnwrap">
        <span className="gs-btn">한꺼번에 등록</span>
        <Ring style={{ left: 'calc(100% - 3rem)', top: '50%' }} />
      </div>
    </Frame>
  )
}

// 4장: 색으로 한눈에 봐요 — 막대 달력의 색과 양쪽 끝의 ‹ ›(이전 주 · 다음 주)
export function SceneColors() {
  const bars = [
    { name: '상추', color: STATUS_COLOR.expired, left: 0, width: 34 },
    { name: '고등어', color: STATUS_COLOR.soon, left: 22, width: 46 },
    { name: '딸기', color: STATUS_COLOR.warning, left: 10, width: 58 },
    { name: '우유', color: STATUS_COLOR.fresh, left: 0, width: 100 },
  ]
  const pills = [
    { text: '여유', color: STATUS_COLOR.fresh },
    { text: '주의', color: STATUS_COLOR.warning },
    { text: '임박', color: STATUS_COLOR.soon },
    { text: '지남', color: STATUS_COLOR.expired },
  ]
  return (
    <Frame>
      <div className="gs-cal__head gs-cal__head--week">
        <span className="gs-chev">‹</span>
        <b>2026년 11월</b>
        <span className="gs-chev">
          ›
          <Ring style={{ left: '50%', top: '50%' }} />
        </span>
      </div>
      {bars.map((b, i) => (
        <div key={b.name} className="gs-bar">
          <span className="gs-bar__name">{b.name}</span>
          <span className="gs-bar__lane">
            <span
              className="gs-bar__fill"
              style={{ background: b.color, marginLeft: `${b.left}%`, width: `${b.width}%`, '--i': i } as CSSProperties}
            />
          </span>
        </div>
      ))}
      <div className="gs-pills">
        {pills.map((p) => (
          <span key={p.text} className="gs-pill">
            <span className="gs-dot" style={{ background: p.color }} />
            {p.text}
          </span>
        ))}
      </div>
    </Frame>
  )
}

// 한 달 달력 그림(5장 · 6장): 11월 1일(일)부터 3주. 5일이 오늘이고, 날짜 칸에는 그날 끝나는 식품이 상태 색 점과 함께 보인다.
// ringDay 가 있으면 그 날짜 칸에 눌러야 할 곳을 가리키는 동그라미를 놓는다
const MONTH_EVENTS: Record<number, { name: string; color: string }> = {
  3: { name: '상추', color: STATUS_COLOR.expired },
  6: { name: '고등어', color: STATUS_COLOR.soon },
  7: { name: '두부', color: STATUS_COLOR.soon },
  8: { name: '바나나', color: STATUS_COLOR.warning },
  9: { name: '딸기', color: STATUS_COLOR.warning },
  12: { name: '우유', color: STATUS_COLOR.fresh },
  14: { name: '요거트', color: STATUS_COLOR.fresh },
}

function MonthGrid({ ringDay }: { ringDay?: number }) {
  const days = Array.from({ length: 21 }, (_, i) => i + 1)
  return (
    <div className="gs-month">
      {['일', '월', '화', '수', '목', '금', '토'].map((d) => (
        <span key={d} className="gs-month__dow">
          {d}
        </span>
      ))}
      {days.map((d) => (
        <span key={d} className={d === 5 ? 'gs-month__day gs-month__day--today' : 'gs-month__day'}>
          <i>{d}</i>
          {MONTH_EVENTS[d] && (
            <em>
              <span className="gs-dot" style={{ background: MONTH_EVENTS[d].color }} />
              {MONTH_EVENTS[d].name}
            </em>
          )}
          {d === ringDay && <Ring style={{ left: '50%', top: '50%' }} />}
        </span>
      ))}
    </div>
  )
}

// 5장: 전체 달력으로 한 달을 봐요 — 1. 막대 달력의 연 · 월 옆 ›를 누르면 2. 한 달 달력이 열린다
export function SceneFullCalendar() {
  return (
    <Frame>
      <Sequence count={2}>
        <Panel step="1. 연·월 옆 ›를 눌러요">
          <div className="gs-cal__head">
            <b>2026년 11월</b>
            <span className="gs-chev">
              ›
              <Ring style={{ left: '50%', top: '50%' }} />
            </span>
          </div>
          <div className="gs-bar">
            <span className="gs-bar__name">고등어</span>
            <span className="gs-bar__lane">
              <span className="gs-bar__fill" style={{ background: STATUS_COLOR.soon, marginLeft: '22%', width: '46%' }} />
            </span>
          </div>
          <div className="gs-bar">
            <span className="gs-bar__name">우유</span>
            <span className="gs-bar__lane">
              <span className="gs-bar__fill" style={{ background: STATUS_COLOR.fresh, width: '100%' }} />
            </span>
          </div>
        </Panel>
        <Panel step="2. 한 달 달력이 열려요">
          <div className="gs-pills gs-pills--toggle">
            <span className="gs-pill gs-pill--on">끝나는 날</span>
            <span className="gs-pill">시작하는 날</span>
          </div>
          <MonthGrid />
        </Panel>
      </Sequence>
    </Frame>
  )
}

// 6장: 날짜를 누르면 그날의 식품이 떠요 — 1. 전체 달력에서 날짜를 누르면 2. 아래에서 목록 창이 올라오고 3. 위로 끌어올리면 그날 남아 있는 식품까지 보인다
export function SceneDateSheet() {
  return (
    <Frame>
      <Sequence count={3} tall>
        <Panel step="1. 아무 날짜나 눌러요">
          <MonthGrid ringDay={6} />
        </Panel>
        <Panel step="2. 그날 끝나는 식품이 떠요">
          <div className="gs-sheet gs-sheet--still">
            <span className="gs-grab" />
            <b className="gs-sheet__title">11월 6일 (금)</b>
            <p className="gs__cap">이날 끝나는 식품</p>
            <div className="gs-item">
              <span className="gs-dot" style={{ background: STATUS_COLOR.soon }} />
              <b>고등어</b>
              <span className="gs-row__note">1일 남음</span>
            </div>
          </div>
        </Panel>
        <Panel step="3. 위로 올리면 남은 식품도 보여요">
          <div className="gs-sheet gs-sheet--still">
            <span className="gs-grab gs-grab--up" />
            <b className="gs-sheet__title">11월 6일 (금)</b>
            <p className="gs__cap">이날 끝나는 식품</p>
            <div className="gs-item">
              <span className="gs-dot" style={{ background: STATUS_COLOR.soon }} />
              <b>고등어</b>
              <span className="gs-row__note">1일 남음</span>
            </div>
            <p className="gs__cap">이날 남아 있는 식품</p>
            <div className="gs-item">
              <span className="gs-dot" style={{ background: STATUS_COLOR.warning }} />
              <b>딸기</b>
              <span className="gs-row__note">3일 남음</span>
            </div>
            <div className="gs-item">
              <span className="gs-dot" style={{ background: STATUS_COLOR.fresh }} />
              <b>우유</b>
              <span className="gs-row__note">6일 남음</span>
            </div>
          </div>
        </Panel>
      </Sequence>
    </Frame>
  )
}

// 7장: 다 먹으면 휴지통으로 — 휴지통 버튼을 누르면 다 먹음 · 버림 · 지우기 선택창
export function SceneTrash() {
  return (
    <Frame>
      <div className="gs-row">
        <span className="gs-dot" style={{ background: STATUS_COLOR.soon }} />
        <b>고등어</b>
        <span className="gs-trash">
          <TrashLineIcon className="gs-trash__icon" />
          <Ring style={{ left: '50%', top: '50%' }} />
        </span>
      </div>
      <div className="gs-sheet">
        <p className="gs__cap">고등어를 어떻게 할까요?</p>
        <div className="gs-opt">
          다 먹었어요 <small>기록에 남아요</small>
        </div>
        <div className="gs-opt">
          버렸어요 <small>기록에 남아요</small>
        </div>
        <div className="gs-opt">
          지우기 <small>되돌릴 수 없어요</small>
        </div>
      </div>
    </Frame>
  )
}

// 8장: 뭐 먹지? — 끼니와 음식 종류를 고르고 「추천받기」
export function SceneRecommend() {
  return (
    <Frame>
      <div className="gs-pills">
        <span className="gs-pill gs-pill--on">점심</span>
        <span className="gs-pill">아침</span>
        <span className="gs-pill">저녁</span>
      </div>
      <div className="gs-pills">
        <span className="gs-pill">한식</span>
        <span className="gs-pill gs-pill--on">간단히</span>
        <span className="gs-pill">양식</span>
      </div>
      <div className="gs-btnwrap">
        <span className="gs-btn">추천받기</span>
        <Ring style={{ left: 'calc(100% - 3rem)', top: '50%' }} />
      </div>
      <div className="gs-result">
        <b>두부 계란 부침</b>
        <small>가진 재료 두부 · 계란 / 없는 재료 대파</small>
      </div>
    </Frame>
  )
}

// 9장: 기록을 보고 조언받아요 — 기록 탭에서 「조언 받기」
export function SceneAdvice() {
  return (
    <Frame>
      <div className="gs-advice__head">
        <b>AI 조언</b>
        <span className="gs-btnwrap gs-btnwrap--inline">
          <span className="gs-btn gs-btn--small">조언 받기</span>
          <Ring style={{ left: '88%', top: '60%' }} />
        </span>
      </div>
      <div className="gs-result gs-result--advice">
        <small>이번 달에는 우유를 두 번 버렸어요. 소포장으로 사 보세요. 고등어는 내일까지 드세요.</small>
      </div>
      <div className="gs-counts">
        <span>
          다 먹음 <b>12</b>
        </span>
        <span>
          버림 <b>3</b>
        </span>
      </div>
    </Frame>
  )
}
