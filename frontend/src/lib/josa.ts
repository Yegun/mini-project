// 이름 뒤에 붙는 조사 "을/를". 받침이 있으면 '을', 없으면 '를'. 한글이 아니면 '을(를)'.
// 예: 두부 → "두부를", 달걀 → "달걀을". 확인 창 문구에서 식품 이름 뒤에 쓴다 (SCREEN-SPEC 4.8).
export function withEulReul(name: string): string {
  const last = name.trim().slice(-1)
  const code = last.charCodeAt(0)
  if (!last || code < 0xac00 || code > 0xd7a3) return `${name}을(를)`
  return (code - 0xac00) % 28 === 0 ? `${name}를` : `${name}을`
}
