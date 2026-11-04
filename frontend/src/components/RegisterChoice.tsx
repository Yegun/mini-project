interface Props {
  onPhoto: () => void // '사진으로 등록' → 사진 올리기 (D-100)
  onManual: () => void // '직접 등록' → 이름 검색부터 시작하는 지금까지의 등록 (D-100)
}

// 등록 선택: '사진으로 등록'과 '직접 등록' 두 버튼 (SCREEN-SPEC 5.0).
// '사진으로 등록' 버튼 아래에 작고 연한 글씨로 AI 안내 한 줄 (D-105). 입력칸이 없으므로 입력 중 확인 창도 없다.
export default function RegisterChoice({ onPhoto, onManual }: Props) {
  return (
    <section className="register__section register-choice" aria-label="등록 방법 고르기">
      <div className="register-choice__item">
        <button type="button" className="button button--primary button--wide" onClick={onPhoto}>
          사진으로 등록
        </button>
        <p className="register-choice__hint">AI 가 사진에서 식품 목록을 줘요</p>
      </div>
      <button type="button" className="button button--wide" onClick={onManual}>
        직접 등록
      </button>
    </section>
  )
}
