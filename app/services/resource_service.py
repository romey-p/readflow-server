import os
import cloudinary
import cloudinary.uploader
import json
import time
import io
import base64
import httpx
from fastapi import HTTPException
from google import genai
from google.genai import types
from collections import defaultdict

from app.core.prompts import VLM_SYSTEM_PROMPT
from app.schemas.resource_schema import TextExtractionResponse
from app.services.analysis_service import analysis_service
from app.services.speech_service import speech_service
from app.crud.resource_crud import resource_crud

# ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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
        groq_api_key = os.getenv("GROQ_API_KEY")

        base64_image = base64.b64encode(file_bytes).decode('utf-8')

        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }

        reinforced_prompt = (
            VLM_SYSTEM_PROMPT + 
            "\n\n[CRITICAL RULE]: You must output a raw valid JSON object exactly matching the requested schema. "
            "It must contain 'extracted_text' string and 'layout_coordinates' list. Do not append markdown backticks."
        )

        combined_user_prompt = (
            f"{reinforced_prompt}\n\n"
            "제공된 교육용 지문 이미지의 레이아웃을 쪼개어 정밀 OCR 및 문장별 좌표 인덱싱 분석을 진행해 주세요."
            "[CRITICAL SENTENCE INDEXING RULES]:\n"
            "1. 쉼표(,), 인용구(“, ”), 혹은 줄바꿈(Line break)이 존재한다고 해서 절대로 'sentence_index'를 증가시키지 마세요.\n"
            "2. 'sentence_index'는 오직 하나의 문장이 마침표(.), 물음표(?), 느낌표(!)로 완벽하게 종결될 때만 +1 증가해야 합니다.\n"
            "3. 예를 들어, '~영감을 받은 시인은, 특히 인상 깊었던 것은~ 느낌을 밝혔다.' 전체가 하나의 마침표로 끝나므로, 문장 중간에 쉼표나 따옴표가 아무리 많아도 이 구절에 속한 모든 단어들의 'sentence_index'는 완벽하게 동일한 숫자로 묶여야 합니다.\n"
            "4. 서술어 문장 성분이 종결되기 전까지 문맥을 임의로 두 토막 내지 마세요."
        )

        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct", 
            "messages": [
                {
                    "role": "user",  
                    "content": [
                        {"type": "text", "text": combined_user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "TextExtractionResponse",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "extracted_text": {"type": "string"},
                            "layout_coordinates": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "word": {"type": "string"},
                                        "sentence_index": {"type": "integer"},
                                        "bbox": {
                                            "type": "array",
                                            "items": {"type": "integer"}
                                        }
                                    },
                                    "required": ["word", "sentence_index", "bbox"]
                                }
                            }
                        },
                        "required": ["extracted_text", "layout_coordinates"]
                    }
                }
            }, 
            "temperature": 0.1,
            "max_tokens": 4096
        }

        max_retries = 5

        for attempt in range(max_retries):
            try:
                # response = ai_client.models.generate_content(
                #     model="gemini-2.5-flash",
                #     contents=[
                #         types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                #         "제공된 교육용 지문 이미지의 레이아웃을 쪼개어 정밀 OCR 및 문장별 좌표 인덱싱 분석을 진행해 주세요."
                #     ],
                #     config=types.GenerateContentConfig(
                #         system_instruction=VLM_SYSTEM_PROMPT, 
                #         response_mime_type="application/json",
                #         response_schema=TextExtractionResponse
                #     )
                # )
                # return json.loads(response.text)
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(groq_url, headers=headers, json=payload)
                    response.raise_for_status()
                    
                    result_json = response.json()
                    content_str = result_json["choices"][0]["message"]["content"]
                    
                    return json.loads(content_str)
                
            # except Exception as e:
            #     error_msg = str(e)
                
            #     if "503" in error_msg or "high demand" in error_msg.lower() or "unavailable" in error_msg.lower():
            #         if attempt < max_retries - 1:
            #             sleep_time = 2 ** (attempt + 1)
            #             print(f"[Warning] 구글 서버 부하 감지. {sleep_time}초 후 다시 시도합니다. ({attempt + 1}/{max_retries})")
            #             time.sleep(sleep_time)
            #             continue
                
            #     raise ValueError(f"VLM 처리 중 오류 발생: {error_msg}")
            except Exception as e:
                print(f"Groq 시도 {attempt + 1}/{max_retries}] 지연 발생 사유: {str(e)}")
                if attempt < max_retries - 1:
                    sleep_time = 2 ** (attempt + 1)
                    time.sleep(sleep_time)
                    continue
                raise ValueError(f"Groq 연동 실패: {str(e)}")
        
    @classmethod
    def process_text_extraction_and_analysis(cls, file_bytes: bytes, mime_type: str) -> tuple[str, dict, list]:
        image_url = cls.upload_image(file_bytes)
        
        vlm_res = cls.extract_layout(file_bytes, mime_type)
        word_layouts = vlm_res.get("layout_coordinates", [])

        sentence_word_objects = defaultdict(list)
        for item in word_layouts:
            idx = item.get("sentence_index")
            if idx is None:
                idx = item.get("index") or item.get("sentence") or 0
            sentence_word_objects[int(idx)].append(item)

        consolidated_sentences = []
        current_words = []
        
        sorted_indices = sorted(sentence_word_objects.keys())

        for i, idx in enumerate(sorted_indices):
            words_in_bucket = sentence_word_objects[idx]
            current_words.extend(words_in_bucket)
            
            temp_text = " ".join([item.get("word", "") for item in current_words]).strip()
            
            if (temp_text.endswith(('.', '?', '!')) or 
                temp_text.endswith(('."', '?"', '!"', '.”', '?”', '!”')) or 
                i == len(sorted_indices) - 1):
                
                consolidated_sentences.append(current_words)
                current_words = []

        if current_words:
            if consolidated_sentences:
                consolidated_sentences[-1].extend(current_words)
            else:
                consolidated_sentences.append(current_words)

        analyzed_sentences = []
        
        for new_idx, word_obj_list in enumerate(consolidated_sentences):
            for item in word_obj_list:
                item["sentence_index"] = new_idx
                
            reconstructed_text = " ".join([item.get("word", "") for item in word_obj_list])
            predicted_score, difficulty_level = analysis_service.predict_score(reconstructed_text)

            analyzed_sentences.append({
                "sentence_index": new_idx,
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

        raw_speaking_rate = tts_output.get("speaking_rate")
        if isinstance(raw_speaking_rate, dict):
            final_speaking_rate = raw_speaking_rate
        elif isinstance(raw_speaking_rate, str):
            final_speaking_rate = {"default": raw_speaking_rate}
        else:
            final_speaking_rate = {"default": "adaptive"}

        return {
            "resource_id": str(doc["_id"]),
            "user_id": doc.get("user_id", ""),
            "image_url": doc.get("image_url", ""),
            "extracted_text": doc.get("vlm_output", {}).get("extracted_text", ""),
            "audio_url": tts_output.get("audio_url"),
            "speaking_rate": final_speaking_rate,
            "duration_seconds": tts_output.get("duration_seconds", 0.0),
            "sentences": sentences,
            "timestamps": tts_output.get("timestamps", []),
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