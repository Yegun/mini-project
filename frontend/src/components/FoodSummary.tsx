import { formatKoreanDate } from '../lib/dateText'
import { STATUS_LABEL, statusColor } from '../lib/statusColor'
import { STORAGE_LABEL } from '../types/food'
import type { FoodDetail } from '../types/foodDetail'

interface Props {
  food: FoodDetail
}

// 상세 위쪽 요약 (5.1). 기한과 상태는 API 가 준 값을 보여 주기만 한다 (D-009).
export default function FoodSummary({ food }: Props) {
  return (
    <section className="summary" aria-label="식품 정보">
      <h2 className="summary__name">{food.name}</h2>
      <dl className="summary__list">
        <dt>수량</dt>
        <dd>
          {food.quantity}
          {food.unit}
        </dd>
        <dt>구매일</dt>
        <dd>{formatKoreanDate(food.purchase_date)}</dd>
        <dt>보관 방법</dt>
        <dd>{STORAGE_LABEL[food.storage]}</dd>
        <dt>기한</dt>
        <dd className="summary__expiry">
          <span
            className="summary__dot"
            style={{ background: statusColor(food.expiry_level) }}
            aria-hidden="true"
          />
          {formatKoreanDate(food.expiry_date)}
          <span className="visually-hidden"> {STATUS_LABEL[food.expiry_level]}</span>
        </dd>
      </dl>
    </section>
  )
}
