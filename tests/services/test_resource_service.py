import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from app.services.resource_service import resource_service

class TestResourceService(unittest.TestCase):
    
    def test_upload_image(self):
        print("이미지 업로드 테스트 시작")
        
        test_image_path = Path(__file__).parent / "test.png"
        if not test_image_path.exists():
            self.fail(f"테스트용 이미지 파일이 존재하지 않습니다.")

        image_bytes = test_image_path.read_bytes()
        
        uploaded_url = resource_service.upload_image(image_bytes, "readflow/images")
        
        self.assertIsNotNone(uploaded_url, "반환된 URL이 없습니다.")
        self.assertTrue(uploaded_url.startswith("https://res.cloudinary.com/"), "Cloudinary 주소 형식이 아닙니다.")
        
        print(f"반환된 이미지 URL: {uploaded_url}")

if __name__ == "__main__":
    unittest.main()