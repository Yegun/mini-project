import { useEffect, useMemo } from 'react'
import ErrorNotice from './ErrorNotice'
import { PhotoArt } from './RegisterIcons'
import './RegisterFlow.css'

interface Props {
  photo: File | null // 고른 사진. 실패해도 그대로 남아 다시 시도할 수 있다
  error: string | null
  busy: boolean // 읽는 동안 올리기 버튼을 잠근다 (D-112)
  onPick: (file: File) => void
  onUpload: () => void
}

// 사진 올리기: 사진을 고르는 칸(고르면 미리보기)과 올리기 버튼. 사진은 한 번에 한 장이다 (D-101, SCREEN-SPEC 5.3).
// 미리보기는 이 기기의 화면에만 잠깐 보이고, 올리기 전에는 어디로도 보내지 않는다.
export default function PhotoUpload({ photo, error, busy, onPick, onUpload }: Props) {
  // 고른 사진의 미리보기 주소. 사진이 바뀌거나 화면을 나가면 지운다
  const previewUrl = useMemo(() => (photo ? URL.createObjectURL(photo) : null), [photo])
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  return (
    <section className="register__section" aria-label="사진 올리기">
      <label className="photo-drop" aria-disabled={busy}>
        {previewUrl ? (
          <img className="photo-drop__img" src={previewUrl} alt="고른 사진 미리보기" />
        ) : (
          <PhotoArt className="photo-drop__art" />
        )}
        <span className="photo-drop__label">{photo ? '다른 사진 고르기' : '사진 고르기'}</span>
        <input
          className="photo-upload__input"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0] // multiple 이 아니라 한 장만 고를 수 있다
            e.target.value = '' // 같은 사진을 다시 골라도 알아채게 한다
            if (file) onPick(file)
          }}
        />
      </label>

      {/* 사진을 올리는 곳의 작고 연한 안내 한 줄 (D-182). 팝업이 아니다 */}
      <p className="register-choice__hint">물건을 펼쳐서 찍으면 더 정확해요. 사진은 저장하지 않아요.</p>

      {photo && <p className="field__hint">고른 사진: {photo.name}</p>}

      {error && <ErrorNotice message={error} />}

      <button type="button" className="button button--primary button--wide" disabled={!photo || busy} onClick={onUpload}>
        {busy ? '사진을 읽는 중…' : '사진 올리기'}
      </button>

      {busy && <p role="status">AI 가 사진에서 식품을 찾고 있어요…</p>}
    </section>
  )
}
