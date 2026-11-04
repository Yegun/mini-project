// 모든 API 요청이 지나는 곳 (API-SPEC 0절).
// 로그인 상태는 쿠키(session)로 오간다. 같은 사이트 요청이라 브라우저가 알아서 같이 보낸다.
import { notifyLoginRequired } from './session'

// 요청을 보내고 Response 를 돌려준다. API 에 닿지 못하면 null.
// 401 중 login_required 만 로그인 화면으로 보낸다. 로그인 실패(login_failed)도 401 이지만
// 그때는 로그인 화면에 그대로 남아 안내만 보여야 하므로 reason 으로 가른다.
// body 가 FormData(사진 올리기)이면 그대로 보낸다. 브라우저가 Content-Type 을 알아서 붙인다.
export async function send(path: string, method = 'GET', body?: object | FormData): Promise<Response | null> {
  let res: Response
  const isForm = body instanceof FormData
  try {
    res = await fetch(path, {
      method,
      credentials: 'same-origin',
      headers: body && !isForm ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
    })
  } catch {
    return null
  }
  if (res.status === 401) {
    const data = (await res.clone().json().catch(() => null)) as { reason?: string } | null
    if (data?.reason === 'login_required') notifyLoginRequired()
  }
  return res
}
