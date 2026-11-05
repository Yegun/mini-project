import { useRef, useState, type ComponentType, type ReactNode } from 'react'
import {
  SceneAdvice,
  SceneColors,
  SceneDateSheet,
  SceneFullCalendar,
  ScenePhoto,
  SceneIntro,
  SceneList,
  SceneRecommend,
  SceneReview,
  SceneTrash,
  StatusWords,
} from './GuideScenes'
import './Register.css'
import './Guide.css'

interface Props {
  again: boolean // 설정에서 다시 보는 중이면 true. 위 오른쪽 버튼이 '건너뛰기' 대신 '닫기'다 (SCREEN-SPEC 17.2)
  onClose: () => void // 건너뛰기 · 닫기 · 마지막 장면의 시작하기. 어디로 갈지는 App 이 정한다
}

interface Scene {
  title: string
  text: ReactNode
  Art: ComponentType
}

// 장면 10장 (SCREEN-SPEC 17.2, D-199, D-200). 첫 장은 앱 소개(앱의 목적)이고 나머지 9장은 사용법이다. 문구는 쉬운 말로 적었다.
// 로그인과 가입 방법은 담지 않는다. 사용법의 이름은 앱 화면의 글자와 같게 적었다 (아래 탭 '뭐 먹지?' 등).
const SCENES: readonly Scene[] = [
  {
    title: '이 앱은 이런 앱이에요',
    text: '먹을 수 있는 기한을 놓쳐서 식품을 버리는 일을 줄이는 것이 이 앱의 목적이에요.',
    Art: SceneIntro,
  },
  {
    title: '사진으로 한 번에 넣어요',
    text: "'냉장고에 넣기'에서 '사진으로 넣기'를 누르고 영수증이나 장바구니 사진을 올리면, AI 가 사진에서 식품을 찾아 줘요.",
    Art: ScenePhoto,
  },
  {
    title: '확인하고 등록해요',
    text: "틀린 줄은 고치거나 빼고 '한꺼번에 등록'을 누르면 홈에 식품이 한꺼번에 생겨요.",
    Art: SceneReview,
  },
  {
    title: '식품 목록, 이렇게 읽어요',
    text: '줄마다 상태 색, 보관 방법, 식품 종류, 남은 날이 보여요. 번호를 따라 하나씩 읽어 보세요.',
    Art: SceneList,
  },
  {
    title: '색으로 한눈에 봐요',
    text: (
      <>
        <StatusWords block />
        색으로 상태를 구분해요. 막대 달력 양쪽 끝의 '‹' '›'로 이전 주와 다음 주를 봐요.
      </>
    ),
    Art: SceneColors,
  },
  {
    title: '전체 달력으로 한 달을 봐요',
    text: "막대 달력의 연·월 옆 '›'를 누르면 한 달 달력이 열려요. 끝나는 날과 시작하는 날을 바꿔 볼 수 있어요.",
    Art: SceneFullCalendar,
  },
  {
    title: '날짜를 누르면 식품이 떠요',
    text: '달력에서 날짜를 누르면 그날 끝나는 식품이 아래에서 올라와요. 창을 위로 올리면 그날 남아 있는 식품도 보여요.',
    Art: SceneDateSheet,
  },
  {
    title: '다 먹으면 휴지통으로',
    text: '목록 줄의 휴지통 버튼을 누르고 다 먹었어요 · 버렸어요 · 지우기를 골라요. 먹거나 버린 기록은 기록 탭에 남아요.',
    Art: SceneTrash,
  },
  {
    title: '뭐 먹지? 고민될 땐',
    text: "'뭐 먹지?' 탭에서 끼니와 종류를 고르고 '추천받기'를 누르면 가진 식품으로 만들 음식을 알려 줘요.",
    Art: SceneRecommend,
  },
  {
    title: '기록을 보고 조언받아요',
    text: "'기록' 탭에서 '조언 받기'를 누르면 먹고 버린 기록과 지금 식품 상태를 보고 AI 가 조언해 줘요.",
    Art: SceneAdvice,
  },
]

const SWIPE_DISTANCE = 50 // 옆으로 이만큼(px) 밀면 장면이 넘어간다

// 사용 설명서 (US-046, SCREEN-SPEC 17절): 아래 탭과 로그아웃 버튼이 없는 전체 화면. 서버에 요청하지 않는다 (D-202).
// 위 오른쪽의 건너뛰기, 아래의 이전 · 다음(마지막 장면은 시작하기), 옆으로 밀기로 장면을 넘긴다.
export default function Guide({ again, onClose }: Props) {
  const [index, setIndex] = useState(0)
  const touchX = useRef<number | null>(null)
  const last = index === SCENES.length - 1
  const { title, text, Art } = SCENES[index]

  function move(next: number) {
    setIndex(Math.min(Math.max(next, 0), SCENES.length - 1))
  }

  return (
    <main className="guide">
      <div className="guide__top">
        <button type="button" className="guide__skip" onClick={onClose}>
          {again ? '닫기' : '건너뛰기'}
        </button>
      </div>

      <section
        className="guide__stage"
        aria-label="사용 설명서"
        onTouchStart={(e) => {
          touchX.current = e.touches[0].clientX
        }}
        onTouchEnd={(e) => {
          if (touchX.current === null) return
          const dx = e.changedTouches[0].clientX - touchX.current
          touchX.current = null
          if (dx <= -SWIPE_DISTANCE) move(index + 1) // 왼쪽으로 밀면 다음
          else if (dx >= SWIPE_DISTANCE) move(index - 1) // 오른쪽으로 밀면 이전
        }}
      >
        {/* key 가 바뀌면 그림이 처음부터 다시 움직인다 */}
        <div className="guide__art" key={index}>
          <Art />
        </div>
        <div className="guide__copy">
          <p className="guide__step">
            {index + 1} / {SCENES.length}
          </p>
          <h1 className="guide__title">{title}</h1>
          <p className="guide__text">{text}</p>
          {last && <p className="guide__note">이 설명서는 설정에서 '사용 설명서 다시 보기'로 다시 볼 수 있어요.</p>}
        </div>
      </section>

      <nav className="guide__dots" aria-label="장면 고르기">
        {SCENES.map((scene, i) => (
          <button
            key={scene.title}
            type="button"
            className={i === index ? 'guide__dot guide__dot--on' : 'guide__dot'}
            aria-label={`${i + 1}번째 장면: ${scene.title}`}
            aria-current={i === index ? 'step' : undefined}
            onClick={() => move(i)}
          />
        ))}
      </nav>

      <div className="guide__buttons">
        {index > 0 && (
          <button type="button" className="button guide__prev" onClick={() => move(index - 1)}>
            이전
          </button>
        )}
        <button
          type="button"
          className="button button--primary guide__next"
          onClick={() => (last ? onClose() : move(index + 1))}
        >
          {last ? '시작하기' : '다음'}
        </button>
      </div>
    </main>
  )
}
