import { STORAGE_LABEL, type Storage } from '../types/food'
import type { RuleStorageOption } from '../types/rule'

const ORDER: Storage[] = ['room', 'fridge', 'freezer']

interface Props {
  id: string // 이름표(FormField)와 이어지는 id
  value: Storage | null
  options?: RuleStorageOption[] // 규칙표가 정한 가능 여부. 없으면(직접 등록) 모두 고를 수 있다
  disabled?: boolean
  onChange: (storage: Storage) => void
}

// 상온 / 냉장 / 냉동 고르기. 규칙표가 "불가"로 정한 방법은 숨기지 않고 흐리게 보이며 고를 수 없다 (D-005).
export default function StoragePicker({ id, value, options, disabled, onChange }: Props) {
  return (
    <div className="choice-group" role="radiogroup" id={id} aria-labelledby={`${id}-label`}>
      {ORDER.map((storage) => {
        const allowed = options ? (options.find((o) => o.storage === storage)?.allowed ?? false) : true
        const selected = value === storage
        const classes = ['choice', selected && 'choice--selected', !allowed && 'choice--dim']
          .filter(Boolean)
          .join(' ')
        return (
          <button
            key={storage}
            type="button"
            role="radio"
            aria-checked={selected}
            aria-disabled={!allowed}
            disabled={disabled}
            className={classes}
            onClick={() => {
              if (allowed) onChange(storage)
            }}
          >
            {STORAGE_LABEL[storage]}
            {!allowed && ' 불가'}
          </button>
        )
      })}
    </div>
  )
}
