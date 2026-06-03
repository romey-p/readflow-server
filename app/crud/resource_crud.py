from pymongo.database import Database
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from bson import ObjectId

class ResourceCRUD:
    
    @staticmethod
    def create_resource(
        db: Database, 
        resource_id: str, 
        user_id: str, 
        image_url: str, 
        vlm_res: Dict[str, Any],
        analyzed_sentences: List[Dict[str, Any]],
        audio_url: Optional[str] = None,
        timestamps: Optional[List[Dict[str, Any]]] = None,
        speaking_rate: Optional[str] = "adaptive",
        duration_seconds: Optional[float] = 0.0
    ) -> None:

        current_time = datetime.now(timezone.utc)
        
        new_document = {
            "_id": ObjectId(resource_id),
            "user_id": user_id,
            "image_url": image_url,

            "vlm_output": {
                "extracted_text": vlm_res.get("extracted_text"),
                "layout_coordinates": vlm_res.get("layout_coordinates", [])
            },

            "model_output": {
                "sentences": analyzed_sentences,
                "analyzed_at": current_time
            },

            "tts_output": {
                "audio_url": audio_url,
                "timestamps": timestamps,
                "speaking_rate": speaking_rate,
                "duration_seconds": duration_seconds,
            },

            "created_at": current_time,
            "updated_at": current_time
        }
        
        db["resources"].insert_one(new_document)

    @staticmethod
    def update_audio_output(
        db: Database, resource_id: 
        str, audio_url: str, 
        speaking_rate: str = "adaptive",
        duration_seconds: float = 0.0,
        timestamps: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        try:
            update_data = {
                "tts_output.audio_url": audio_url,
                "tts_output.speaking_rate": speaking_rate,      
                "tts_output.duration_seconds": duration_seconds, 
                "tts_output.generated_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            if timestamps is not None:
                update_data["tts_output.timestamps"] = timestamps

            result = db["resources"].update_one(
                {"_id": ObjectId(resource_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
            
        except Exception as e:
            print(f"오디오 URL 저장 실패: {str(e)}")
            return False
        
    @staticmethod
    def get_resource_by_id(db: Database, resource_id: str) -> Optional[Dict[str, Any]]:
        try:
            return db["resources"].find_one({"_id": ObjectId(resource_id)})
        except Exception as e:
            print(f"리소스를 찾을 수 없습니다 ({resource_id}): {str(e)}")
            return None

resource_crud = ResourceCRUD()