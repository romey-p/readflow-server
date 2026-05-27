import os
import cloudinary
import cloudinary.uploader
import json
from fastapi import HTTPException
from google import genai
from google.genai import types
from app.core.prompts import VLM_SYSTEM_PROMPT
from app.schemas.resource_schema import TextExtractionResponse

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
        
resource_service = ResourceService()