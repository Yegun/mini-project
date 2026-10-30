import './StateNotice.css'

interface Props {
  onAdd?: () => void // 등록 화면은 이번 범위 밖이라 아직 연결하지 않는다
}

// 빈 홈 안내: 안내 문구 + 식품 등록 버튼 (OQ-05). 문구는 임시 문구다 (OQ-03).
export default function EmptyHome({ onAdd }: Props) {
  return (
    <div className="notice notice--empty">
      <p className="notice__text">아직 등록한 식품이 없어요. 식품을 등록해 보세요.</p>
      <button type="button" className="notice__button notice__button--primary" onClick={onAdd}>
        식품 등록
      </button>
    </div>
  )
}
