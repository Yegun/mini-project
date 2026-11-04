import { useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import './FilterDropdown.css'

export interface DropdownOption<V extends string> {
  value: V
  text: string // 알약에 보이는 글자 (고른 뒤)
  content: ReactNode // 목록 줄 안의 모양 (글자, 종류 그림 등). 줄 바탕은 그 값의 캡슐 색이 깔린다
}

interface Props<V extends string> {
  id: string
  label: string // 안 고른 상태에서 알약에 보이는 글자 (예: "보관 방법")
  allText: string // 목록 맨 위 '전체' 줄의 글자
  value: V | 'all'
  options: readonly DropdownOption<V>[]
  tone: 'storage' | 'category' // 안 고른 상태의 바탕색 계열
  onChange: (v: V | 'all') => void
}

// 거르기 드롭다운 (SCREEN-SPEC 4.6). 브라우저 기본 선택 상자 대신 직접 그린 목록을 쓴다.
// 알약 모양 버튼 + 아래로 펼쳐지는 둥근 목록. 값을 고르면 알약이 그 값의 캡슐 색으로 채워진다.
// 키보드: 위 · 아래 화살표로 옮기고, Enter 로 고르고, Esc 로 닫는다. 바깥을 누르면 닫힌다.
export default function FilterDropdown<V extends string>({ id, label, allText, value, options, tone, onChange }: Props<V>) {
  const [open, setOpen] = useState(false)
  const [alignRight, setAlignRight] = useState(false)
  const root = useRef<HTMLSpanElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const list = useRef<HTMLDivElement>(null)

  const chosen = options.find((o) => o.value === value)
  const triggerText = chosen ? chosen.text : label

  // 열려 있는 동안 바깥을 누르면 닫는다
  useEffect(() => {
    if (!open) return
    const onDown = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', onDown)
    return () => document.removeEventListener('pointerdown', onDown)
  }, [open])

  // 목록이 화면 오른쪽 밖으로 나가면 오른쪽 끝에 맞춘다
  useLayoutEffect(() => {
    if (!open) return
    const rect = list.current?.getBoundingClientRect()
    if (rect) setAlignRight(rect.right > window.innerWidth - 8)
  }, [open])

  // 열리면 지금 고른 줄(없으면 맨 위)에 초점을 둔다
  useEffect(() => {
    if (!open) return
    const items = list.current?.querySelectorAll<HTMLButtonElement>('[role="option"]')
    const selected = list.current?.querySelector<HTMLButtonElement>('[aria-selected="true"]')
    ;(selected ?? items?.[0])?.focus()
  }, [open])

  function close(focusTrigger: boolean) {
    setOpen(false)
    if (focusTrigger) trigger.current?.focus()
  }

  function choose(v: V | 'all') {
    onChange(v)
    close(true)
  }

  function onListKey(e: KeyboardEvent<HTMLDivElement>) {
    const items = Array.from(list.current?.querySelectorAll<HTMLButtonElement>('[role="option"]') ?? [])
    const at = items.indexOf(document.activeElement as HTMLButtonElement)
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      items[(at + 1) % items.length]?.focus()
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      items[(at - 1 + items.length) % items.length]?.focus()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      close(true)
    } else if (e.key === 'Tab') {
      setOpen(false)
    }
  }

  const rootClass = [
    'dd',
    `dd--${tone}`,
    chosen && `dd--chosen cap--${chosen.value}`, // 고른 값의 캡슐 색을 알약에 입힌다 (FoodCapsules.css 의 변수)
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <span ref={root} className={rootClass}>
      <button
        ref={trigger}
        id={id}
        type="button"
        className="dd__trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {triggerText}
      </button>
      {open && (
        <div
          ref={list}
          className={alignRight ? 'dd__list dd__list--right' : 'dd__list'}
          role="listbox"
          aria-labelledby={id}
          onKeyDown={onListKey}
        >
          <button
            type="button"
            role="option"
            aria-selected={value === 'all'}
            className="dd__option"
            style={{ ['--i' as string]: 0 }}
            onClick={() => choose('all')}
          >
            <span className="dd__label">{allText}</span>
            {value === 'all' && <span className="dd__check" aria-hidden="true">✓</span>}
          </button>
          {options.map((o, n) => (
            <button
              key={o.value}
              type="button"
              role="option"
              aria-selected={value === o.value}
              className={`dd__option dd__option--color cap--${o.value}`}
              style={{ ['--i' as string]: n + 1 }}
              onClick={() => choose(o.value)}
            >
              <span className="dd__label">{o.content}</span>
              {value === o.value && <span className="dd__check" aria-hidden="true">✓</span>}
            </button>
          ))}
        </div>
      )}
    </span>
  )
}
