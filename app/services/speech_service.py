import html
import os
import json
import httpx
import time
from google.cloud import texttospeech_v1beta1 as texttospeech
from typing import List, Dict, Any, Tuple
from google import genai
from google.genai import types

from app.core.prompts import TTS_PAUSE_SYSTEM_PROMPT
from app.schemas.speech_schema import AudioBreakdownResponse

SPEED_MAP = {
    5: "slow",  
    4: "85%",   
    3: "90%",   
    2: "95%",  
    1: "100%"  
}

class SpeechService:
    def __init__(self):
        self.tts_client = texttospeech.TextToSpeechClient()
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="ko-KR",
            name="ko-KR-Wavenet-A",
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            pitch=-2.0
        )

        # self.ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def _inject_natural_pauses(self, sentences: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        if not sentences:
            return {}
        
        groq_api_key = os.getenv("GROQ_API_KEY")
        
        input_data = []
        for s in sentences:
            level = int(s.get("difficulty_level", 3))
            base_pause = 150 + (level * 30)
            input_data.append({
                "sentence_index": s.get("sentence_index"),
                "sentence_text": s.get("sentence_text"),
                "base_pause_ms": base_pause
            })
        
        # contents = f"""
        # [지시사항]
        # 아래 제공된 모든 문장 목록을 각각 정밀하게 분석하여 자연스러운 끊어 읽기 처리를 하세요.
        # 숨을 쉬어 가야 하는 주요 지점의 기준 가이드라인 쉼 시간은 각 문장 오브젝트 내의 'base_pause_ms' 값을 적용하세요. 

        # [입력 문장 목록]
        # {json.dumps(input_data, ensure_ascii=False, indent=2)}
        # """
        reinforced_prompt = (
            TTS_PAUSE_SYSTEM_PROMPT + 
            "\n\n[CRITICAL RULE]: You must output a raw valid JSON object exactly matching the requested schema. "
            "It must contain a top-level 'sentences' list, where each item has 'sentence_index' (int) and a 'chunks' list. "
            "Each chunk item must contain 'chunk_text' (string) and 'pause_ms' (int). Do not append markdown backticks."
        )
        combined_prompt = f"""
{reinforced_prompt}

[지시사항]
아래 제공된 모든 문장 목록을 각각 정밀하게 분석하여 자연스러운 끊어 읽기 처리를 하세요.
숨을 쉬어 가야 하는 주요 지점의 기준 가이드라인 쉼 시간은 각 문장 오브젝트 내의 'base_pause_ms' 값을 적용하세요. 

[입력 문장 목록]
{json.dumps(input_data, ensure_ascii=False, indent=2)}
"""
        groq_url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": combined_prompt
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        max_retries = 5

        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=20.0) as client:
                    response = client.post(groq_url, headers=headers, json=payload)
                    response.raise_for_status()
                    
                    result_json = response.json()
                    content_str = result_json["choices"][0]["message"]["content"]
                    
                    data = json.loads(content_str)
                    sentences_breakdown = data.get("sentences", [])
                    
                    result_map = {}
                    for item in sentences_breakdown:
                        s_idx = item.get("sentence_index")
                        chunks = item.get("chunks", [])
                        result_map[s_idx] = chunks
                    return result_map

        # try:
        #     response = self.ai_client.models.generate_content(
        #         model="gemini-2.5-flash",
        #         contents=contents,
        #         config=types.GenerateContentConfig(
        #             system_instruction=TTS_PAUSE_SYSTEM_PROMPT, 
        #             response_mime_type="application/json",
        #             response_schema=AudioBreakdownResponse,
        #             temperature=0.1, 
        #         )
        #     )
        #     data = json.loads(response.text)
        #     sentences_breakdown = data.get("sentences", [])
            
        #     result_map = {}
        #     for item in sentences_breakdown:
        #         s_idx = item.get("sentence_index")
        #         chunks = item.get("chunks", [])
        #         result_map[s_idx] = chunks
        #     return result_map
            
        # except Exception as e:
        #     print(f"Gemini 연동 실패: {str(e)}")
        #     return {s.get("sentence_index"): [{"chunk_text": s.get("sentence_text", ""), "pause_ms": 0}] for s in sentences}
        
            except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** (attempt + 1))
                        continue
                    
                    return {s.get("sentence_index"): [{"chunk_text": s.get("sentence_text", ""), "pause_ms": 0}] for s in sentences}

    def synthesize_adaptive_audio(self, analyzed_sentences: List[Dict[str, Any]]) -> Tuple[bytes, List[Dict[str, Any]], Dict[str, str]]:
        if not analyzed_sentences:
            raise ValueError("음성 합성을 수행할 지문 데이터가 존재하지 않습니다.")
        
        batch_pauses = self._inject_natural_pauses(analyzed_sentences)

        ssml_text = "<speak>"
        speaking_rates = {}

        for s in analyzed_sentences:
            level = int(s.get("difficulty_level", 3))
            sentence_idx = s.get("sentence_index", 0)
            text = s.get("sentence_text", "")
            speed = SPEED_MAP.get(level, "100%")

            speaking_rates[str(sentence_idx)] = speed 

            chunks = batch_pauses.get(sentence_idx, [{"chunk_text": text, "pause_ms": 0}])

            ssml_text += f'<s><prosody rate="{speed}">'
            word_idx = 0

            for i, item in enumerate(chunks):
                chunk_text = item.get("chunk_text", "")
                pause_ms = item.get("pause_ms", 0)

                if not chunk_text:
                    continue

                words = chunk_text.split()
                for w in words:
                    escaped_word = html.escape(w)
                    ssml_text += f'<mark name="w_{sentence_idx}_{word_idx}"/>{escaped_word} '
                    word_idx += 1

                if pause_ms > 0 and i < len(chunks) - 1:
                    ssml_text += f'<break time="{pause_ms}ms"/>'

            ssml_text += f'</prosody></s><break time="500ms"/>'

        ssml_text += "</speak>"

        try:
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
            request = texttospeech.SynthesizeSpeechRequest(
                input=synthesis_input, 
                voice=self.voice, 
                audio_config=self.audio_config,
                enable_time_pointing=[texttospeech.SynthesizeSpeechRequest.TimepointType.SSML_MARK]
            )

            response = self.tts_client.synthesize_speech(request=request)

            timepoints_data = [
                {
                    "mark_name": tp.mark_name,     
                    "time_seconds": tp.time_seconds  
                }
                for tp in response.timepoints
            ]
            return response.audio_content, timepoints_data, speaking_rates
        
        except Exception as e:
            print(f"Google TTS API 연동 실패: {str(e)}")
            print(f"[DEBUG] 전송 시도한 SSML 본문 구조:\n{ssml_text}")
            raise ValueError("오디오 합성 중 에러 발생")

speech_service = SpeechService()