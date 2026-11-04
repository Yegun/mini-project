import { statusColor, STATUS_LABEL } from '../lib/statusColor'
import { CATEGORIES, CATEGORY_LABEL, STORAGE_LABEL, type Category, type ExpiryStatus, type Storage } from '../types/food'
import FilterDropdown, { type DropdownOption } from './FilterDropdown'
import CategoryIcon from './CategoryIcon'
import './FoodFilters.css'

export type StatusFilter = ExpiryStatus | 'all'
export type StorageFilter = Storage | 'all'
export type CategoryFilter = Category | 'all'

interface Props {
  counts: Record<ExpiryStatus, number> // 처리하지 않은 내 식품의 상태별 수 (화면이 홈 목록 하나로 센다)
  status: StatusFilter
  storage: StorageFilter
  category: CategoryFilter
  onStatus: (v: StatusFilter) => void
  onStorage: (v: StorageFilter) => void
  onCategory: (v: CategoryFilter) => void
}

const STATUSES: readonly ExpiryStatus[] = ['fresh', 'warning', 'soon', 'expired'] // 여유 · 주의 · 임박 · 지남
const STORAGES: readonly Storage[] = ['room', 'fridge', 'freezer']

// 목록의 선택지는 줄 전체가 그 값의 캡슐 색으로 채워지고(FilterDropdown.css), 안에는 글자(종류는 그림도)가 들어간다
const STORAGE_OPTIONS: readonly DropdownOption<Storage>[] = STORAGES.map((s) => ({
  value: s,
  text: STORAGE_LABEL[s],
  content: STORAGE_LABEL[s],
}))

const CATEGORY_OPTIONS: readonly DropdownOption<Category>[] = CATEGORIES.map((c) => ({
  value: c,
  text: CATEGORY_LABEL[c],
  content: (
    <>
      <CategoryIcon category={c} className="dd__icon" />
      {CATEGORY_LABEL[c]}
    </>
  ),
}))

// 상태 알약(전체 · 여유 · 주의 · 임박 · 지남)과, 그 옆의 보관 방법 · 식품 종류 드롭다운 (SCREEN-SPEC 4.6).
// 알약과 드롭다운은 같은 줄에 같은 높이의 둥근 모양으로 이어지고, 화면이 좁으면 다음 줄로 이어진다.
// 알약마다 상태 색의 점과 옅은 바탕색, 수 표시. 수가 0 이면 흐리게(눌러서 안내는 볼 수 있다). 거르기는 화면이 한다 (D-009).
// 드롭다운 알약에도 색이 있고, 값을 고르면 그 값의 캡슐 색으로 채워져 걸려 있는 조건이 한눈에 보인다.
export default function FoodFilters({ counts, status, storage, category, onStatus, onStorage, onCategory }: Props) {
  // '전체'는 아무 조건도 걸려 있지 않을 때만 눌린 모양이다. 누르면 알약과 드롭다운이 모두 처음(전체)으로 돌아간다.
  const nothingSet = status === 'all' && storage === 'all' && category === 'all'
  return (
    <section className="filters" role="group" aria-label="식품 거르기">
      <button
        type="button"
        className={nothingSet ? 'pill pill--selected' : 'pill'}
        aria-pressed={nothingSet}
        onClick={() => {
          onStatus('all')
          onStorage('all')
          onCategory('all')
        }}
      >
        전체
      </button>
      {STATUSES.map((s) => (
        <button
          key={s}
          type="button"
          className={['pill', `pill--${s}`, status === s && 'pill--selected', counts[s] === 0 && 'pill--zero']
            .filter(Boolean)
            .join(' ')}
          aria-pressed={status === s}
          onClick={() => onStatus(s)}
        >
          <span className="pill__dot" data-status={s} style={{ background: statusColor(s) }} aria-hidden="true" />
          {STATUS_LABEL[s]}
          <span className="pill__count">{counts[s]}</span>
        </button>
      ))}

      <FilterDropdown
        id="filter-storage"
        label="보관 방법"
        allText="전체"
        value={storage}
        options={STORAGE_OPTIONS}
        tone="storage"
        onChange={onStorage}
      />
      <FilterDropdown
        id="filter-category"
        label="식품 종류"
        allText="전체"
        value={category}
        options={CATEGORY_OPTIONS}
        tone="category"
        onChange={onCategory}
      />
    </section>
  )
}
