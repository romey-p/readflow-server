import httpx
from app.core.config import settings

class AnalysisService:
    def __init__(self):
        self.ml_api_url = f"{settings.ML_SERVER_URL.rstrip('/')}/api/resources/remote/analysis"
        self.timeout = 10.0

    def load_model(self):
            print(f"ML 연동 완료 (타겟 API: {self.ml_api_url})")
            pass

    def predict_score(self, sentence: str) -> tuple[float, int]:
        if not sentence.strip():
            return 0.0, 1
        
        payload = {"sentence": sentence}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.ml_api_url, json=payload)
                response.raise_for_status()
                
                result = response.json()

                final_score = result.get("difficulty_score", 50.0)
                level = result.get("difficulty_level", 3)

                return round(float(final_score), 2), int(level)

        except httpx.HTTPStatusError as hse:
            print(f"응답 오류 발생 ({hse.response.status_code}): {hse.response.text}")
            return 50.0, 3
        except Exception as e:
            print(f"ML 모델 서버 통신 실패 (기본값 대체): {str(e)}")
            return 50.0, 3

analysis_service = AnalysisService()
