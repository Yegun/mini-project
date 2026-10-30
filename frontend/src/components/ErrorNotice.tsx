import './StateNotice.css'

interface Props {
  onRetry: () => void
}

// 오류 알림: 실패하면 쉬운 메시지를 화면 위에 보인다 (OQ-04).
// 문구는 구현 단계에서 정한 임시 문구다 (OQ-03).
export default function ErrorNotice({ onRetry }: Props) {
  return (
    <div className="notice notice--error" role="alert">
      <p className="notice__text">식품을 불러오지 못했어요. 잠시 뒤에 다시 시도해 주세요.</p>
      <button type="button" className="notice__button" onClick={onRetry}>
        다시 시도
      </button>
    </div>
  )
}
