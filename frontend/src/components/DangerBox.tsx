// 위험 식품의 빨간 안내 상자 (SCREEN-SPEC 16.2, D-170). 모든 위험 식품에 같은 공통 문구가 보인다.
// 사진 확인 화면과 식품 상세가 함께 쓴다. 정확한 문구는 구현 단계에서 정하는 임시 문구다 (사용자 확인 필요).
const DANGER_BOX_TITLE = '이 식품은 이렇게 드세요'
const DANGER_BOX_TEXT = '날것이나 덜 익힌 채로 먹으면 탈이 날 수 있어요. 신선할 때 충분히 익혀서 드세요.'

export default function DangerBox() {
  return (
    <div className="danger-box" role="note">
      <strong className="danger-box__title">{DANGER_BOX_TITLE}</strong>
      <p className="danger-box__text">{DANGER_BOX_TEXT}</p>
    </div>
  )
}
