from pydantic import BaseModel, Field
from typing import List

class WordLayout(BaseModel):
    word: str = Field(..., description="이미지에서 추출한 단어 또는 대체 텍스트 문자열")
    sentence_index: int = Field(..., description="0부터 시작하는 해당 단어가 속한 문장의 인덱스 번호")
    bbox: List[int] = Field(..., description="정규화된 좌표계(0~1000) 기준 [ymin, xmin, ymax, xmax] 정수 리스트")

class TextExtractionResponse(BaseModel):
    extracted_text: str = Field(..., description="이미지에서 추출한 전체 본문 텍스트 (대체 텍스트, 줄바꿈 포함)")
    layout_coordinates: List[WordLayout] = Field(..., description="인지 흐름 읽기 순서대로 정렬된 각 단어별 위치 좌표 및 문장 인덱스 번호 리스트")