from pydantic import BaseModel, Field
from typing import List

class SpeechChunk(BaseModel):
    chunk_text: str = Field(..., description="Gemini가 문맥에 맞춰 쪼갠 의미 단위 문자열")
    pause_ms: int = Field(..., description="TTS가 낭독을 멈출 시간 (밀리초 단위, 쉼이 없으면 0)")

class SentenceAudioBreakdown(BaseModel):
    sentence_index: int = Field(..., description="지문 내에서 몇 번째 문장인지 나타내는 인덱스 번호")
    chunks: List[SpeechChunk] = Field(..., description="해당 문장이 쪼개진 의미 단위와 휴지기(Pause) 정보 리스트")

class AudioBreakdownResponse(BaseModel):
    chunks: List[SentenceAudioBreakdown] = Field(..., description="전체 지문의 모든 문장별 끊어 읽기 분석 결과 목록")