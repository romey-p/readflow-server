from pydantic import BaseModel, Field
from typing import List

class SpeechChunk(BaseModel):
    chunk_text: str = Field(..., description="Gemini가 문맥에 맞춰 쪼갠 의미 단위 문자열")
    pause_ms: int = Field(..., description="TTS가 낭독을 멈출 시간 (밀리초 단위, 쉼이 없으면 0)")

class AudioBreakdownResponse(BaseModel):
    chunks: List[SpeechChunk] = Field(..., description="분석된 한국어 문자열과 휴지기(Pause) 정보가 순서대로 담긴 리스트")