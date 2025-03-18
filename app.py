from fastapi import FastAPI, status, HTTPException, UploadFile, File
from pydantic import BaseModel
from service.suggest import setup
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
from service.disease import analyze_dog_disease_image

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인에서 요청을 허용
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용 (GET, POST 등)
    allow_headers=["*"],  # 모든 헤더 허용
)

# 견종 추천 AI 설정
suggest = setup()
breeds = ['포메라니안', '도베르만', '시바견']

# 업로드 디렉토리 생성
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

class Form(BaseModel):
    job: str
    home: str
    ownership: str
    personality: str
    family_type: str
    dog_size: str
    activity_rate: str

class DogRecommendation(BaseModel):
    breed: str
    reason: str

# 견종 추천 엔드포인트
@app.post("/v1/suggest/breed", status_code=status.HTTP_200_OK)
def create_item(form: Form):
    response = suggest(breeds, str(form))
    if response is None:
        raise HTTPException(status_code=404, detail="Can't suggest a breed")
    return DogRecommendation(breed=breeds[response[0]], reason=response[1])

# 질병 판별 엔드포인트
@app.post("/v1/analyze", response_class=JSONResponse)
async def analyze_dog_image(file: UploadFile = File(...)):
    """강아지 이미지를 분석하여 질병 판별 결과 반환"""
    if not file:
        raise HTTPException(status_code=400, detail="이미지 파일이 필요합니다")
    
    # 지원되는 이미지 형식 확인
    allowed_mime_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_mime_types:
        raise HTTPException(
            status_code=400, 
            detail="지원되지 않는 파일 형식입니다. JPEG, PNG, GIF 또는 WebP 파일만 허용됩니다."
        )

    try:
        # 외부 모듈의 함수 호출하여 분석 수행
        result = await analyze_dog_disease_image(file, UPLOAD_DIR)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 분석 중 오류가 발생했습니다: {str(e)}")

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)