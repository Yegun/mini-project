import { formatKoreanDate } from '../lib/dateText'
import { STATUS_LABEL, statusColor } from '../lib/statusColor'
import type { FoodDetail } from '../types/foodDetail'
import CategoryIcon from './CategoryIcon'
import DangerBox from './DangerBox'
import DangerMark from './DangerMark'
import { CategoryCapsule, StorageCapsule } from './FoodCapsules'
import { CuisineIcon } from './RecommendIcons'

interface Props {
  food: FoodDetail
}

// 상세 화면의 보기 전용 요약 (SCREEN-SPEC 6.1). 수정 칸은 여기 없고 '정보 고치기' 창에서 고친다 (D-171).
// 위: 식품 그림(종류를 알면 종류 그림, 모르면 접시) · 이름 · 보관 방법과 종류 캡슐. 가운데: 남은 날을 크게(상태 색).
// 아래: 수량 · 구매일 · 기한 타일. 위험 식품이면 이름 옆에 ⚠ 위험(올리거나 누르면 이유 한 줄)과 빨간 안내 상자가 보인다 (D-164, D-170).
// 기한과 상태는 API 가 준 값을 보여 주기만 한다 (D-009).
export default function FoodSummary({ food }: Props) {
  const words = food.days_left >= 0 ? `${food.days_left}일 남았어요` : `${-food.days_left}일 지났어요`
  return (
    <section
      className="summary"
      aria-label="식품 정보"
      data-status={food.expiry_status}
      style={{ ['--sc' as string]: statusColor(food.expiry_status) }}
    >
      <div className="summary__top">
        {food.category ? (
          <span className={`summary__art cap--${food.category}`} aria-hidden="true">
            <CategoryIcon category={food.category} className="summary__art-icon" />
          </span>
        ) : (
          <span className="summary__art summary__art--plain" aria-hidden="true">
            <CuisineIcon cuisine="western" className="summary__art-icon" />
          </span>
        )}
        <div className="summary__who">
          <h2 className="summary__name">
            {food.name}
            {food.is_danger && <DangerMark note={food.danger_note} />}
          </h2>
          <div className="summary__caps">
            <StorageCapsule storage={food.storage} withIcon />
            <CategoryCapsule category={food.category} />
          </div>
        </div>
      </div>

      {food.is_danger && <DangerBox />}

      {/* 남은 날: 상태 색으로 크게 */}
      <div className="summary__hero">
        <span className="summary__days">{words}</span>
        <span className="summary__status">
          <span className="summary__dot" aria-hidden="true" />
          {STATUS_LABEL[food.expiry_status]}
        </span>
      </div>

      <dl className="summary__tiles">
        <div className="summary__tile">
          <dt>수량</dt>
          <dd>
            {food.quantity}
            {food.unit}
          </dd>
        </div>
        <div className="summary__tile">
          <dt>구매일</dt>
          <dd>{formatKoreanDate(food.purchase_date)}</dd>
        </div>
        <div className="summary__tile summary__tile--wide">
          <dt>기한</dt>
          <dd>{formatKoreanDate(food.expiry_date)}</dd>
        </div>
      </dl>
    </section>
  )
}
