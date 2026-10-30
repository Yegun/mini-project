import './StateNotice.css'

interface Props {
  message?: string // 없으면 홈의 "불러오지 못했어요" 문구
  onRetry?: () => void // 없으면 다시 시도 버튼을 보이지 않는다 (등록 화면은 등록 버튼을 다시 누른다)
}

// 오류 알림: 실패하면 쉬운 메시지를 화면 위에 보인다 (OQ-04).
// 문구는 구현 단계에서 정한 임시 문구다 (OQ-03).
export default function ErrorNotice({
  message = '식품을 불러오지 못했어요. 잠시 뒤에 다시 시도해 주세요.',
  onRetry,
}: Props) {
  return (
    <div className="notice notice--error" role="alert">
      <p className="notice__text">{message}</p>
      {onRetry && (
        <button type="button" className="notice__button" onClick={onRetry}>
          다시 시도
        </button>
      )}
    </div>
  )
}
