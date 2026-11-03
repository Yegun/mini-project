import ErrorNotice from './ErrorNotice'

interface Props {
  photo: File | null // 고른 사진. 실패해도 그대로 남아 다시 시도할 수 있다
  error: string | null
  busy: boolean // 읽는 동안 올리기 버튼을 잠근다 (D-112)
  onPick: (file: File) => void
  onUpload: () => void
}

// 사진 올리기: 사진을 고르는 곳과 올리기 버튼. 사진은 한 번에 한 장이다 (D-101, SCREEN-SPEC 5.3).
export default function PhotoUpload({ photo, error, busy, onPick, onUpload }: Props) {
  return (
    <section className="register__section" aria-label="사진 올리기">
      <label className="button button--wide photo-upload__pick" aria-disabled={busy}>
        {photo ? '다른 사진 고르기' : '사진 고르기'}
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

      {photo && <p className="field__hint">고른 사진: {photo.name}</p>}

      {error && <ErrorNotice message={error} />}

      <button type="button" className="button button--primary button--wide" disabled={!photo || busy} onClick={onUpload}>
        {busy ? '사진을 읽는 중…' : '사진 올리기'}
      </button>

      {busy && <p role="status">AI 가 사진에서 식품을 찾고 있어요…</p>}
    </section>
  )
}
