// 사진 미리 검사: jpg · png · webp, 5MB 이하, 한 번에 한 장 (D-101, V-23). 최종 판단은 API 가 한다 (D-010).
export const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp']
export const PHOTO_MAX_BYTES = 5 * 1024 * 1024

// 사용자 확정 문구 (SCREEN-SPEC 13.1 의 9번)
export const PHOTO_INVALID = '사진은 jpg · png · webp 형식이고 5MB 이하여야 해요.'

// 올릴 수 있으면 null, 아니면 안내 문구
export function checkPhoto(file: File): string | null {
  if (!PHOTO_TYPES.includes(file.type) || file.size > PHOTO_MAX_BYTES) return PHOTO_INVALID
  return null
}
