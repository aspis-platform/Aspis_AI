from fastapi import FastAPI, status, HTTPException, UploadFile, File, Depends, Header
from pydantic import BaseModel
from service.suggest import setup
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from service.disease import analyze_dog_disease_image
import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY 환경변수가 설정되지 않았습니다")

security = HTTPBearer()

# JWT 인증 검증 함수
async def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰",
            headers={"WWW-Authenticate": "Bearer"},
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

# 견종 추천 엔드포인트 (JWT 인증 추가)
@app.post("/v1/suggest/breed", status_code=status.HTTP_200_OK)
def create_item(form: Form, payload: dict = Depends(verify_jwt)):
    response = suggest(breeds, str(form))
    if response is None:
        raise HTTPException(status_code=404, detail="Can't suggest a breed")
    return DogRecommendation(breed=breeds[response[0]], reason=response[1])

# 질병 판별 엔드포인트 (JWT 인증 추가)
@app.post("/v1/analyze", response_class=JSONResponse)
async def analyze_dog_image(
    file: UploadFile = File(...),
    payload: dict = Depends(verify_jwt)
):
    if not file:
        raise HTTPException(status_code=400, detail="이미지 파일이 필요합니다")
    
    allowed_mime_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_mime_types:
        raise HTTPException(
            status_code=400, 
            detail="지원되지 않는 파일 형식입니다. JPEG, PNG, GIF 또는 WebP 파일만 허용됩니다."
        )

    try:
        result = await analyze_dog_disease_image(file, UPLOAD_DIR)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 분석 중 오류가 발생했습니다: {str(e)}")

# 상태 확인 엔드포인트 (JWT 인증 추가)
@app.get("/health")
async def health_check(payload: dict = Depends(verify_jwt)):
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)