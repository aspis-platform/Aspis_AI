import os
import re
from typing import Callable, Optional, Tuple, List
import google.generativeai as genai
from dotenv import load_dotenv


prompt_template = """
다음은 개를 키우고 싶은 사람이 제공한 설문 조사 결과입니다.
{survey_results}

견종 목록:
{breed_list}

'견종 목록'에서 추천할 견종의 **번호**를 숫자로, **추천 이유**를 한 줄로 출력하세요.

🚨**당신의 출력은 오직 2줄이어야 합니다.**🚨
  1. **첫 번째 줄:** 추천하는 견종의 **번호** (숫자만, 아무것도 추가하지 말 것)
  2. **두 번째 줄:** 추천하는 이유 (한 문장으로만, 50자 이하)

🚫**주의:** 추가 설명, 개행, 불필요한 단어는 절대 포함하지 마세요.
🚫절대로 다른 형식으로 응답하지 마세요. 어떤 문구도 앞뒤에 추가하지 마세요.
🚫첫 줄은 숫자만 포함해야 합니다. 두 번째 줄은 한 문장이어야 합니다.

<FORMAT>
n
이유를 설명하는 한 문장 (50자 이하)
</FORMAT>

위 <FORMAT> 태그 사이의 형식을 정확히 따라야 합니다. 다른 어떤 텍스트도 추가하지 마세요.
"""


def setup(model_name: str = "gemini-1.5-flash") -> Callable[[List[str], str], Optional[Tuple[int, str]]]:
    load_dotenv()
    genai.configure(api_key=os.getenv("API_KEY"))
    model = genai.GenerativeModel(model_name)

    def prompt_func(breeds: List[str], user_input: str) -> Optional[Tuple[int, str]]:
        request = prompt_template.format(
            survey_results=user_input,
            breed_list="\n".join([f"{i}. {breed}" for i, breed in enumerate(breeds)])
        )
        response = model.generate_content(request)

        if response.text is None:
            return None

        match = re.search(r"^(\d+)\n(.+)$", response.text.strip())

        if match:
            breed_number = match.group(1)
            reason = match.group(2)

            if breed_number.isdigit():
                return int(breed_number), reason

        number_match = re.search(r"(\d+)", response.text)
        if number_match:
            breed_number = number_match.group(1)

            lines = [line.strip() for line in response.text.split('\n') if line.strip()]
            if len(lines) > 1:
                reason_line = lines[1] if lines[0].strip() == breed_number else lines[0]
                return int(breed_number), reason_line

        return None

    return prompt_func
