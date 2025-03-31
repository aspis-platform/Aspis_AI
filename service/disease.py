import os
import base64
import json
import shutil
import uuid
import httpx
from pathlib import Path
from typing import Dict, Any
from fastapi import UploadFile
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

def get_media_type(file_path: str) -> str:
    extension = os.path.splitext(file_path)[1].lower()
    
    if extension in ['.jpg', '.jpeg']:
        return 'image/jpeg'
    elif extension == '.png':
        return 'image/png'
    elif extension == '.gif':
        return 'image/gif'
    elif extension == '.webp':
        return 'image/webp'
    else:
        return 'image/jpeg'

def extract_json_from_text(text: str) -> Dict[str, Any]:
    try:
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = text[json_start:json_end]
            return json.loads(json_str)
        else:
            return {"error": "JSON을 찾을 수 없음", "raw_text": text}
    except json.JSONDecodeError:
        return {"error": "JSON 파싱 오류", "raw_text": text}

async def analyze_dog_disease_image(file: UploadFile, upload_dir: Path) -> Dict[str, Any]:
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    file_path = upload_dir / f"{file_id}{file_extension}"
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        with open(file_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")
        
        media_type = get_media_type(file_path)
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": "claude-3-7-sonnet-20250219",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": """
                            이 이미지가 강아지인지 확인한 후, 강아지라면 건강 상태를 분석하고 다음 JSON 형식으로 결과를 제공해주세요:
                            {
                                "is_dog": true,
                                "disease": "발견된 질병 또는 상태",
                                "info": {
                                    "symptoms": "관찰된 증상 목록",
                                    "recommendations": "권장 조치사항",
                                    "vet_visit_required": true/false,
                                    "severity": "낮음/중간/높음"
                                }
                            }
                            
                            강아지에게 특별한 문제가 없어 보이면 "disease"를 "건강함"으로 설정하세요.
                            이미지에 강아지가 없으면 다음과 같이 응답하세요:
                            {
                                "is_dog": false,
                                "message": "이미지에 강아지가 없습니다. 강아지 사진을 업로드해주세요."
                            }
                            
                            오직 JSON 형식으로만 답변해주세요.
                            """
                        }
                    ]
                }
            ]
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                ANTHROPIC_API_URL,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                response_data = response.json()
                ai_response = response_data.get("content", [{}])[0].get("text", "")
                analysis_result = extract_json_from_text(ai_response)
                
                if analysis_result.get("is_dog") == False:
                    return {
                        "success": False,
                        "error": "강아지 이미지가 아닙니다",
                        "message": analysis_result.get("message", "강아지 사진을 업로드해주세요.")
                    }
                
                return {
                    "success": True,
                    "data": analysis_result,
                    "disclaimer": "이 결과는 AI 기반 분석이며 전문 수의사의 진단을 대체할 수 없습니다. 강아지의 건강에 우려가 있다면 반드시 수의사와 상담하세요."
                }
            else:
                return {
                    "success": False,
                    "error": f"API 요청 실패: {response.status_code}",
                    "details": response.text
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": "처리 중 오류 발생",
            "details": str(e)
        }
                
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)