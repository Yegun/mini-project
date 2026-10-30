// [임시 계약] 규칙표 검색(A2). 경로·응답 모양은 백엔드 담당 확인 전까지 임시다.
// 개발 중 가짜 데이터: VITE_USE_MOCK 이 켜져 있으면 mocks/rules.json 을 쓴다.
//   VITE_USE_MOCK=rules-error  규칙표 검색 실패
import type { RuleCandidate, RuleSearchResponse } from '../types/rule'
import rulesMock from '../mocks/rules.json'

const RULES_PATH = '/api/rules'
const MOCK_MODE = import.meta.env.VITE_USE_MOCK

// 어떤 실패든 화면은 "검색 실패" 하나로 보여 준다.
export class SearchRulesError extends Error {}

interface MockRule extends RuleCandidate {
  aliases: string[]
}

// 가짜 검색: 이름이나 별칭에 글자가 들어 있으면 찾는다. 실제 일치 방식은 백엔드 담당 확인 필요.
async function searchMockRules(mode: string, q: string): Promise<RuleSearchResponse> {
  if (mode === 'rules-error') throw new SearchRulesError('mock error')
  const found = (rulesMock.rules as MockRule[]).filter(
    (r) => r.name.includes(q) || r.aliases.some((a) => a.includes(q)),
  )
  return {
    rules: found.map((r) => ({
      id: r.id,
      name: r.name,
      default_storage: r.default_storage,
      storages: r.storages.map((s) => ({ storage: s.storage, allowed: s.allowed })),
    })),
  }
}

export async function searchRules(q: string): Promise<RuleSearchResponse> {
  if (MOCK_MODE) return searchMockRules(MOCK_MODE, q)
  try {
    const res = await fetch(`${RULES_PATH}?q=${encodeURIComponent(q)}`)
    if (!res.ok) throw new SearchRulesError(`status ${res.status}`)
    return (await res.json()) as RuleSearchResponse
  } catch (e) {
    throw e instanceof SearchRulesError ? e : new SearchRulesError('network')
  }
}
