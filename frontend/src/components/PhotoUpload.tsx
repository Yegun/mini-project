import { useEffect, useMemo } from 'react'
import ErrorNotice from './ErrorNotice'
import { BasketArt, ReceiptArt } from './RegisterIcons'
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
          // 어떤 사진을 넣는지 보여 주는 점선 칸 두 개: 그림 + 아래에 설명 (US-047, D-204)
          <div className="photo-drop__tiles">
            <div className="photo-drop__tile">
              <ReceiptArt className="photo-drop__tile-art" />
              <span className="photo-drop__tile-title">영수증</span>
              <span className="photo-drop__tile-sub">산 식품이 적힌 영수증</span>
            </div>
            <div className="photo-drop__tile">
              <BasketArt className="photo-drop__tile-art" />
              <span className="photo-drop__tile-title">장바구니</span>
              <span className="photo-drop__tile-sub">장바구니에 담은 식품</span>
            </div>
          </div>
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

      {/* 사진을 올리는 곳의 작고 연한 안내 두 줄 (D-182, D-204). 팝업이 아니다.
          어떤 사진을 넣으면 되는지, 장바구니 안쪽 식품은 못 찾는다는 것, 찍는 요령, 저장하지 않는다는 것을 줄마다 따로 적는다 */}
      <ul className="register-choice__hint photo-hints">
        <li>영수증 사진이나 장바구니 사진을 넣어 주세요.</li>
        <li>장바구니 안쪽에 든 식품은 AI 가 찾지 못해요.</li>
        <li>영수증을 펼쳐서 밝은 곳에서 찍으면 더 정확해요.</li>
        <li>사진은 저장하지 않아요.</li>
      </ul>

      {photo && <p className="field__hint">고른 사진: {photo.name}</p>}

      {error && <ErrorNotice message={error} />}

      <button type="button" className="button button--primary button--wide" disabled={!photo || busy} onClick={onUpload}>
        {busy ? '사진을 읽는 중…' : '사진 올리기'}
      </button>

      {busy && <p role="status">AI 가 사진에서 식품을 찾고 있어요…</p>}
    </section>
  )
}
