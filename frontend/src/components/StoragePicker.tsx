import { STORAGE_LABEL, type Storage } from '../types/food'
import type { RuleStorageOption } from '../types/rule'
import StorageIcon from './StorageIcon'

const ORDER: Storage[] = ['room', 'fridge', 'freezer']

interface Props {
  id: string // 이름표(FormField)와 이어지는 id
  value: Storage | null
  options?: RuleStorageOption[] // 규칙표가 정한 가능 여부. 없으면(직접 등록) 모두 고를 수 있다
  maxDays?: Partial<Record<Storage, number | null>> // 방법별 최대 보관기간(일). 있으면 버튼에 같이 보인다 (확인 화면, D-104)
  disabled?: boolean
  variant?: 'buttons' | 'tiles' // tiles: 그림이 있는 큰 타일 (등록 폼). 기본은 글자 버튼
  onChange: (storage: Storage) => void
}

// 상온 / 냉장 / 냉동 고르기. 규칙표가 "불가"로 정한 방법은 숨기지 않고 흐리게 보이며 고를 수 없다 (D-005).
export default function StoragePicker({ id, value, options, maxDays, disabled, variant = 'buttons', onChange }: Props) {
  const tiles = variant === 'tiles'
  return (
    <div className={tiles ? 'storage-tiles' : 'choice-group'} role="radiogroup" id={id} aria-labelledby={`${id}-label`}>
      {ORDER.map((storage) => {
        const allowed = options ? (options.find((o) => o.storage === storage)?.allowed ?? false) : true
        const selected = value === storage
        const days = allowed ? maxDays?.[storage] : null
        const classes = tiles
          ? ['storage-tile', `storage-tile--${storage}`, selected && 'storage-tile--selected', !allowed && 'storage-tile--dim']
          : ['choice', selected && 'choice--selected', !allowed && 'choice--dim']
        return (
          <button
            key={storage}
            type="button"
            role="radio"
            aria-checked={selected}
            aria-disabled={!allowed}
            disabled={disabled}
            className={classes.filter(Boolean).join(' ')}
            onClick={() => {
              if (allowed) onChange(storage)
            }}
          >
            {tiles && <StorageIcon storage={storage} className="storage-tile__icon" />}
            {tiles ? (
              <span className="storage-tile__label">
                {STORAGE_LABEL[storage]}
                {!allowed && ' 불가'}
              </span>
            ) : (
              <>
                {STORAGE_LABEL[storage]}
                {!allowed && ' 불가'}
              </>
            )}
            {days != null && <span className="choice__sub">최대 {days}일</span>}
          </button>
        )
      })}
    </div>
  )
}
