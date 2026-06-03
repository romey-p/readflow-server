import os
import cloudinary
import cloudinary.uploader
import json
import time
import io
from fastapi import HTTPException
from google import genai
from google.genai import types
from collections import defaultdict

from app.core.prompts import VLM_SYSTEM_PROMPT
from app.schemas.resource_schema import TextExtractionResponse
from app.services.analysis_service import analysis_service
from app.services.speech_service import speech_service
from app.crud.resource_crud import resource_crud

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
    def upload_audio(file_data: bytes, folder: str = "readflow/audios") -> str:
        try:
            audio_stream = io.BytesIO(file_data)

            response = cloudinary.uploader.upload(
                audio_stream, 
                folder=folder, 
                unique_filename=True, 
                resource_type="video", 
                filename="adaptive_speech.mp3"
                )
            return response.get("secure_url")
        except Exception as e:
            raise HTTPException(status_code=500, detail="오디오 업로드 실패: {str(e)}")
        
    @staticmethod
    def extract_layout(file_bytes: bytes, mime_type: str) -> dict:

        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = ai_client.models.generate_content(
                    model="gemini-2.5-flash",
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
                error_msg = str(e)
                
                if "503" in error_msg or "high demand" in error_msg.lower() or "unavailable" in error_msg.lower():
                    if attempt < max_retries - 1:
                        sleep_time = (attempt + 1) * 2
                        print(f"[Warning] 구글 서버 부하 감지. {sleep_time}초 후 다시 시도합니다. ({attempt + 1}/{max_retries})")
                        time.sleep(sleep_time)
                        continue
                
                raise ValueError(f"VLM 처리 중 오류 발생: {error_msg}")
        
    @classmethod
    def process_text_extraction_and_analysis(cls, file_bytes: bytes, mime_type: str) -> tuple[str, dict, list]:
        image_url = cls.upload_image(file_bytes)
        
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
            
        return image_url, vlm_res, analyzed_sentences
    
    @classmethod
    def process_audio_synthesis(cls, analyzed_sentences: list) -> tuple[str, list, float, dict]:
        audio_bytes, timestamps, speaking_rates = speech_service.synthesize_adaptive_audio(analyzed_sentences)
        audio_url = cls.upload_audio(audio_bytes)
        duration_seconds = timestamps[-1]["time_seconds"] if timestamps else 0.0

        return audio_url, timestamps, duration_seconds, speaking_rates
    
    @classmethod
    def get_resource_info(cls, db, resource_id: str) -> dict:
        doc = resource_crud.get_resource_by_id(db, resource_id)
        if not doc:
            return None

        sentences_data = doc.get("model_output", {}).get("sentences", [])
        sentences = [
            {
                "sentence_index": s.get("sentence_index"),
                "sentence_text": s.get("sentence_text"),
                "difficulty_score": s.get("difficulty_score"),
                "difficulty_level": s.get("difficulty_level")
            }
            for s in sentences_data
        ]

        tts_output = doc.get("tts_output", {})

        return {
            "resource_id": str(doc["_id"]),
            "user_id": doc.get("user_id", ""),
            "image_url": doc.get("image_url", ""),
            "extracted_text": doc.get("vlm_output", {}).get("extracted_text", ""),
            "audio_url": tts_output.get("audio_url"),
            "speaking_rate": tts_output.get("speaking_rate", "adaptive"),
            "duration_seconds": tts_output.get("duration_seconds", 0.0),
            "sentences": sentences,
            "created_at": doc.get("created_at")
        }
    
    @classmethod
    def get_resource_coordinates(cls, db, resource_id: str) -> dict:
        doc = resource_crud.get_resource_by_id(db, resource_id)
        if not doc:
            return None

        return {
            "resource_id": str(doc["_id"]),
            "layout_coordinates": doc.get("vlm_output", {}).get("layout_coordinates", [])
        }
       
resource_service = ResourceService()