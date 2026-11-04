import ErrorNotice from './ErrorNotice'
import { StorageCapsule } from './FoodCapsules'
import { NoMatchArt } from './RecommendIcons'
import { SearchIcon } from './RegisterIcons'
import type { RuleCandidate, SearchState } from '../types/rule'
import './RegisterFlow.css'

interface Props {
  query: string
  search: SearchState
  onQueryChange: (query: string) => void
  onSearch: () => void
  onPick: (rule: RuleCandidate) => void
  onManual: () => void // 검색 결과가 없을 때만 직접 등록으로 간다 (시나리오 2)
}

// 규칙표 검색: 검색 버튼(또는 Enter)을 눌러야 찾는다. 결과가 없으면 직접 등록으로 갈 수 있다 (4.1)
export default function RuleSearch({ query, search, onQueryChange, onSearch, onPick, onManual }: Props) {
  const loading = search.status === 'loading'
  return (
    <section className="register__section" aria-label="식품 검색">
      <form
        className="search-form"
        onSubmit={(e) => {
          e.preventDefault()
          onSearch()
        }}
      >
        <span className="search-box">
          <SearchIcon className="search-box__icon" />
          <input
            className="input search-box__input"
            type="search"
            autoComplete="off"
            placeholder="식품 이름을 검색해 보세요"
            aria-label="식품 이름"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
          />
        </span>
        <button
          type="submit"
          className="button button--primary"
          disabled={loading || query.trim() === ''}
        >
          검색
        </button>
      </form>

      {search.status === 'loading' && <p role="status">찾는 중…</p>}

      {search.status === 'error' && (
        <ErrorNotice message="식품을 찾지 못했어요. 잠시 뒤에 다시 시도해 주세요." onRetry={onSearch} />
      )}

      {search.status === 'done' && search.rules.length > 0 && (
        <ul className="rule-list" aria-label="검색 결과">
          {search.rules.map((rule) => (
            <li key={rule.name}>
              <button type="button" className="rule-list__item" onClick={() => onPick(rule)}>
                <span className="rule-list__name">{rule.name}</span>
                {/* 규칙표가 정한 기본 보관 방법 */}
                <StorageCapsule storage={rule.default_storage} withIcon />
                <span className="rule-list__chev" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {search.status === 'done' && search.rules.length === 0 && (
        <div className="notice notice--empty">
          <NoMatchArt className="notice__art" />
          <p className="notice__text">‘{search.q}’ 이름의 식품을 찾지 못했어요.</p>
          <button type="button" className="button button--primary" onClick={onManual}>
            직접 넣기
          </button>
        </div>
      )}
    </section>
  )
}
