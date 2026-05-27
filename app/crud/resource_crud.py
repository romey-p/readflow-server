from pymongo.database import Database
from typing import Dict, Any
from datetime import datetime, timezone
from bson import ObjectId

class ResourceCRUD:
    
    @staticmethod
    def create_resource(
        db: Database, 
        resource_id: str, 
        user_id: str, 
        cloudinary_url: str, 
        vlm_res: Dict[str, Any]
    ) -> None:

        current_time = datetime.now(timezone.utc)
        
        new_document = {
            "_id": ObjectId(resource_id),
            "user_id": user_id,
            "cloudinary_url": cloudinary_url,
            "extracted_text": vlm_res.get("extracted_text"),
            "words": vlm_res.get("layout_coordinates", []),
            "sentences": [],
            "tts_output": None,
            "created_at": current_time,
            "updated_at": current_time
        }
        
        db["resources"].insert_one(new_document)

resource_crud = ResourceCRUD()