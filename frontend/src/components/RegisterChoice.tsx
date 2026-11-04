import { CameraArt, PencilArt } from './RegisterIcons'
import './RegisterFlow.css'

interface Props {
  onPhoto: () => void // '사진으로 등록' → 사진 올리기 (D-100)
  onManual: () => void // '직접 등록' → 이름 검색부터 시작하는 지금까지의 등록 (D-100)
}

// 등록 선택: '사진으로 등록'과 '직접 등록' 두 개의 큰 카드 (SCREEN-SPEC 5.0).
// '사진으로 등록' 카드 안에 작은 글씨로 AI 안내 한 줄 (D-105). 입력칸이 없으므로 입력 중 확인 창은 없다.
export default function RegisterChoice({ onPhoto, onManual }: Props) {
  return (
    <section className="register__section register-choice" aria-label="등록 방법 고르기">
      <p className="register-choice__ask">어떻게 등록할까요?</p>
      <button type="button" className="choice-card choice-card--photo" onClick={onPhoto}>
        <span className="choice-card__art">
          <CameraArt className="choice-card__art-svg" />
        </span>
        <span className="choice-card__text">
          <span className="choice-card__title">
            사진으로 넣기
            <span className="choice-card__tag">AI</span>
          </span>
          <span className="choice-card__sub">AI 가 사진에서 식품 목록을 줘요</span>
        </span>
        <span className="choice-card__chev" aria-hidden="true" />
      </button>
      <button type="button" className="choice-card choice-card--manual" onClick={onManual}>
        <span className="choice-card__art">
          <PencilArt className="choice-card__art-svg" />
        </span>
        <span className="choice-card__text">
          <span className="choice-card__title">직접 넣기</span>
          <span className="choice-card__sub">이름을 검색해서 하나씩 등록해요</span>
        </span>
        <span className="choice-card__chev" aria-hidden="true" />
      </button>
    </section>
  )
}
