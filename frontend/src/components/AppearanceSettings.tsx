import { useState } from 'react'
import {
  ACCENTS,
  FONT_STEPS,
  TONES,
  chooseAccent,
  chooseFontStep,
  chooseTone,
  effectiveTone,
  loadAppearance,
  type Accent,
  type Appearance,
  type FontStep,
  type Tone,
} from '../lib/appearance'
import { PaletteIcon } from './SettingsIcons'
import './Appearance.css'

// 설정 화면의 색 · 글자 크기 고르기 (SCREEN-SPEC 9.5, 9.6). 모두 이 기기에만 저장하고 서버에 요청하지 않는다.
// 저장하지 못해도(브라우저가 막음) 이 화면에서는 고른 값을 계속 쓰고, 다시 열면 처음 값으로 돌아간다 (9.5 상태표).
// 모양: 밝기는 밝은 · 어두운 미리보기 타일, 포인트 색은 색 견본 타일, 글자 크기는 슬라이더.
// 라디오 · 슬라이더는 그대로라서 키보드와 스크린 리더 동작은 예전과 같다.
const SAVE_FAILED = '이 기기에 저장하지 못했어요. 지금은 고른 대로 보이지만, 다시 열면 처음 색과 크기로 돌아가요.'

export default function AppearanceSettings() {
  const [appearance, setAppearance] = useState<Appearance>(() => loadAppearance())
  const [saveFailed, setSaveFailed] = useState(false)

  // 지금 쓰는 밝기가 선택돼 보인다. 고른 적이 없으면 기기 설정이 선택돼 보인다 (9.5 상태표)
  const shownTone = effectiveTone(appearance)
  const stepLabel = FONT_STEPS.find((s) => s.value === appearance.fontStep)?.label ?? ''

  function apply(result: { next: Appearance; saved: boolean }) {
    setAppearance(result.next)
    setSaveFailed(!result.saved)
  }

  return (
    <section className="appearance" aria-labelledby="appearance-heading">
      <div className="set-head">
        <span className="set-head__badge" aria-hidden="true">
          <PaletteIcon className="set-head__icon" />
        </span>
        <h2 id="appearance-heading" className="appearance__heading">
          화면 모양
        </h2>
      </div>

      <fieldset className="appearance__group">
        <legend className="appearance__legend">밝기</legend>
        <div className="appearance__tiles appearance__tiles--2">
          {TONES.map(({ value, label }) => (
            <label key={value} className={tileClass(shownTone === value)}>
              <input
                type="radio"
                name="tone"
                className="appearance__radio"
                checked={shownTone === value}
                onChange={noop}
                onClick={() => apply(chooseTone(appearance, value as Tone))} // 이미 선택돼 보이는 것을 눌러도 저장한다
              />
              {/* 미리보기: 그 밝기로 보이는 작은 화면 */}
              <span className={`appearance__preview appearance__preview--${value}`} aria-hidden="true">
                <i className="appearance__preview-bar" />
                <i className="appearance__preview-bar appearance__preview-bar--short" />
                <i className="appearance__preview-chip" />
              </span>
              <span className="appearance__tile-label">{label}</span>
              <span className="appearance__tile-check" aria-hidden="true" />
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="appearance__group">
        <legend className="appearance__legend">포인트 색</legend>
        <div className="appearance__tiles appearance__tiles--2">
          {ACCENTS.map(({ value, label, dots }) => (
            <label key={value} className={tileClass(appearance.accent === value)}>
              <input
                type="radio"
                name="accent"
                className="appearance__radio"
                checked={appearance.accent === value}
                onChange={noop}
                onClick={() => apply(chooseAccent(appearance, value as Accent))}
              />
              {/* 색 견본: 두 가지 대표 색을 겹쳐 보인다 */}
              <span className="appearance__swatch" aria-hidden="true">
                <i style={{ background: dots[0] }} />
                <i style={{ background: dots[1] }} />
              </span>
              <span className="appearance__tile-label">{label}</span>
              <span className="appearance__tile-check" aria-hidden="true" />
            </label>
          ))}
        </div>
      </fieldset>

      <div className="appearance__group">
        <label htmlFor="font-step" className="appearance__legend">
          글자 크기 <span className="appearance__value">{stepLabel}</span>
        </label>
        <div className="appearance__slider">
          <div className="appearance__ticks" aria-hidden="true">
            {FONT_STEPS.map(({ value }) => (
              <span key={value} className="appearance__tick" style={{ ['--i' as string]: value - 1 }} />
            ))}
          </div>
          <input
            id="font-step"
            type="range"
            className="appearance__range"
            min={1}
            max={5}
            step={1}
            value={appearance.fontStep}
            aria-valuetext={stepLabel}
            onChange={(e) => apply(chooseFontStep(appearance, Number(e.target.value) as FontStep))}
          />
        </div>
        <div className="appearance__ends" aria-hidden="true">
          <span className="appearance__end appearance__end--small">가</span>
          <span className="appearance__end appearance__end--large">가</span>
        </div>
      </div>

      {saveFailed && (
        <p className="appearance__notice" role="status">
          {SAVE_FAILED}
        </p>
      )}
    </section>
  )
}

// 라디오는 눌렀을 때(onClick) 처리한다. 선택 상태는 위에서 정해 주므로 onChange 는 비워 둔다.
function noop(): void {}

function tileClass(selected: boolean): string {
  return selected ? 'appearance__tile appearance__tile--selected' : 'appearance__tile'
}
