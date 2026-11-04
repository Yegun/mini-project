// 규칙표 검색(C1). 백엔드 응답: { items: [{ name, default_storage, disallowed_storages }] } (API-SPEC C1)
// 개발 중 가짜 데이터: VITE_USE_MOCK 이 켜져 있으면 mocks/rules.json 을 쓴다.
//   VITE_USE_MOCK=rules-error  규칙표 검색 실패
import type { Storage } from '../types/food'
import type { ApiRule, RuleCandidate, RuleSearchResponse, RuleStorageOption } from '../types/rule'
import { send } from './http'
import rulesMock from '../mocks/rules.json'

const RULES_PATH = '/api/rules'
const MOCK_MODE = import.meta.env.VITE_USE_MOCK
const STORAGE_ORDER: Storage[] = ['room', 'fridge', 'freezer']

// 어떤 실패든 화면은 "검색 실패" 하나로 보여 준다.
export class SearchRulesError extends Error {}

// "불가" 목록 -> 보관 방법 세 개의 가능 여부. 불가는 흐리게 보이고 고를 수 없다 (D-005).
export function storagesFromDisallowed(disallowed: Storage[]): RuleStorageOption[] {
  return STORAGE_ORDER.map((storage) => ({ storage, allowed: !disallowed.includes(storage) }))
}

function toCandidate(rule: ApiRule): RuleCandidate {
  return {
    name: rule.name,
    default_storage: rule.default_storage,
    category: rule.category,
    storages: storagesFromDisallowed(rule.disallowed_storages ?? []),
  }
}

interface MockRule {
  name: string
  aliases: string[]
  default_storage: Storage
  storages: { storage: Storage; allowed: boolean }[]
}

// 가짜 검색: 이름이나 별칭에 글자가 들어 있으면 찾는다 (D-035).
async function searchMockRules(mode: string, q: string): Promise<RuleSearchResponse> {
  if (mode === 'rules-error') throw new SearchRulesError('mock error')
  const found = (rulesMock.rules as MockRule[]).filter(
    (r) => r.name.includes(q) || r.aliases.some((a) => a.includes(q)),
  )
  return {
    rules: found.map((r) => ({
      name: r.name,
      default_storage: r.default_storage,
      storages: r.storages.map((s) => ({ storage: s.storage, allowed: s.allowed })),
    })),
  }
}

export async function searchRules(q: string): Promise<RuleSearchResponse> {
  if (MOCK_MODE) return searchMockRules(MOCK_MODE, q)
  const res = await send(`${RULES_PATH}?q=${encodeURIComponent(q)}`)
  if (!res?.ok) throw new SearchRulesError(res ? `status ${res.status}` : 'network')
  try {
    const data = (await res.json()) as { items: ApiRule[] }
    return { rules: data.items.map(toCandidate) }
  } catch {
    throw new SearchRulesError('bad response')
  }
}
