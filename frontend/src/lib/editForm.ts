// 식품 상세의 수정 폼 미리 검사 (D-010). 알려 주는 용도이고 최종 판단은 API 가 한다.
// 날짜가 비었는지만 본다. 기한이 과거인지, 구매일이 기한보다 뒤인지, 지난 식품을 바꿀 수 있는지는
// API 가 막고 안내를 돌려준다 (D-016). 안내 문구는 쉬운 말의 임시 문구다 (OQ-03).
import type { FoodDetail, UpdateFoodInput } from '../types/foodDetail'
import type { FieldErrors } from '../types/register'
import { checkQuantity, emptyValues, type FormValues } from './registerForm'

// 상세에서 받은 값으로 수정 폼의 처음 값을 만든다. 쓰지 않는 칸은 빈 값이다.
export function valuesFromDetail(food: FoodDetail): FormValues {
  return {
    ...emptyValues(food.purchase_date),
    name: food.name,
    quantity: String(food.quantity),
    unit: food.unit,
    storage: food.storage,
  }
}

export function checkInfoForm(v: FormValues, expiryOpen: boolean, expiryDate: string): FieldErrors {
  const errors: FieldErrors = {}
  if (v.name.trim() === '') errors.name = '이름을 적어 주세요.'
  const quantity = checkQuantity(v.quantity)
  if (quantity) errors.quantity = quantity
  if (v.unit.trim() === '') errors.unit = '단위를 적어 주세요.'
  if (v.purchaseDate === '') errors.purchase_date = '구매일을 골라 주세요.'
  if (expiryOpen && expiryDate === '') errors.expiry = '기한을 골라 주세요.'
  return errors
}

// 바뀐 칸만 담는다. 글자가 같은지만 본다(날짜 비교 아님). 아무것도 안 바뀌면 빈 객체.
// 검사를 통과한 뒤에만 부른다(수량이 숫자라고 본다).
export function buildInfoPatch(food: FoodDetail, v: FormValues): UpdateFoodInput {
  const patch: UpdateFoodInput = {}
  const name = v.name.trim()
  if (name !== food.name) patch.name = name
  const quantity = Number(v.quantity.trim())
  if (quantity !== food.quantity) patch.quantity = quantity
  const unit = v.unit.trim()
  if (unit !== food.unit) patch.unit = unit
  if (v.purchaseDate !== food.purchase_date) patch.purchase_date = v.purchaseDate
  return patch
}

// 저장 버튼을 켤지: 입력한 글자가 처음과 다르면 바뀐 것으로 본다. 잘못된 값도 저장을 눌러 안내를 받게 한다.
export function isInfoChanged(food: FoodDetail, v: FormValues): boolean {
  return (
    v.name.trim() !== food.name ||
    v.quantity.trim() !== String(food.quantity) ||
    v.unit.trim() !== food.unit ||
    v.purchaseDate !== food.purchase_date
  )
}
