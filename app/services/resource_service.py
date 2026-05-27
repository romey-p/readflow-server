import os
import cloudinary
import cloudinary.uploader
import json
from fastapi import HTTPException
from google import genai
from google.genai import types
from collections import defaultdict

from app.core.prompts import VLM_SYSTEM_PROMPT
from app.schemas.resource_schema import TextExtractionResponse
from app.services.analysis_service import analysis_service

ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True 
)

class ResourceService:

    @staticmethod
    def upload_image(file_data: bytes, folder: str = "readflow/images") -> str:
        try:
            response = cloudinary.uploader.upload(
                file_data, 
                folder=folder, 
                unique_filename=True, 
                resource_type="image"
            )
            return response.get("secure_url")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"이미지 업로드 실패: {str(e)}")
        
    @staticmethod
    def extract_layout(file_bytes: bytes, mime_type: str) -> dict:
        try:
            response = ai_client.models.generate_content(
                model="gemini-3.5-flash",
                contents=[
                    types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                    "제공된 교육용 지문 이미지의 레이아웃을 쪼개어 정밀 OCR 및 문장별 좌표 인덱싱 분석을 진행해 주세요."
                ],
                config=types.GenerateContentConfig(
                    system_instruction=VLM_SYSTEM_PROMPT, 
                    response_mime_type="application/json",
                    response_schema=TextExtractionResponse
                )
            )
            return json.loads(response.text)
            
        except Exception as e:
            raise ValueError(f"VLM 처리 중 오류 발생: {str(e)}")
        
    @classmethod
    def process_text_extraction_and_analysis(cls, file_bytes: bytes, mime_type: str) -> tuple[str, dict, list]:
        cloudinary_url = cls.upload_image(file_bytes)
        
        vlm_res = cls.extract_layout(file_bytes, mime_type)
        word_layouts = vlm_res.get("layout_coordinates", [])

        sentence_buckets = defaultdict(list)
        for item in word_layouts:
            idx = item.get("sentence_index")
            word = item.get("word")
            sentence_buckets[idx].append(word)
            
        analyzed_sentences = []
        for idx in sorted(sentence_buckets.keys()):
            reconstructed_text = " ".join(sentence_buckets[idx])
            
            predicted_score, difficulty_level = analysis_service.predict_score(reconstructed_text)
            
            analyzed_sentences.append({
                "sentence_index": idx,
                "sentence_text": reconstructed_text,
                "difficulty_score": predicted_score,
                "difficulty_level": difficulty_level
            })
            
        return cloudinary_url, vlm_res, analyzed_sentences
        
resource_service = ResourceService()