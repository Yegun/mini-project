"""사진 읽기 창구 (API-SPEC 2-5절 F1, US-017, US-018)."""
from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app import photo
from app.database import transaction
from app.routers.common import Conn, Today, UserId

router = APIRouter()


@router.post("/photos/analyze")
def analyze_photo(
    conn: Conn,
    user_id: UserId,
    today: Today,
    image: Annotated[list[UploadFile | str] | None, File()] = None,
):
    """F1 사진 읽기 🔒. 사진 한 장을 AI 에게 읽혀 냉장·냉동 식품 목록을 돌려주고, 결과(글)를 30분 보관한다.

    확인 순서는 로그인 → 사진 검사 → AI → 저장이다 (API-SPEC 0절). 사진이 규칙에 안 맞으면 AI 를 부르지 않는다.
    사진은 저장하지 않는다 (D-102). 식품이 하나도 없으면 실패가 아니라 빈 목록과 analysis_id null 이다.
    """
    # image 칸에 파일이 아니라 글자가 오면 빈 사진으로 본다 (photo_invalid). 5MB 를 넘는지만 가려 낼 만큼만 읽는다.
    parts = [b"" if isinstance(upload, str) else upload.file.read(photo.PHOTO_MAX_BYTES + 1) for upload in image or []]
    data, media_type = photo.check_photo(parts)
    with transaction(conn):
        return photo.analyze(conn, user_id, data, media_type, today)
