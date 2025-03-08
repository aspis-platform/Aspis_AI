from fastapi import FastAPI, status, HTTPException
from pydantic import BaseModel
from ai import setup

app = FastAPI()
suggest = setup()

breeds = ['포메라니안', '도베르만', '시바견']


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


@app.post("/suggest", status_code=status.HTTP_200_OK)
def create_item(form: Form):
    response = suggest(breeds, str(form))
    if response is None:
        raise HTTPException(status_code=404, detail="Can't suggest a breed")
    return DogRecommendation(breed=breeds[response[0]], reason=response[1])

