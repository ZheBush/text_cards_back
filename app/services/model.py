import json
import re
import httpx

LLM_URL = "http://ollama:11434/api/generate"
MODEL = "mistral"


async def generate_cards(text: str, cards_num: int):
    return await call_model(text, cards_num)


async def call_model(text: str, cards_num: int):
    prompt = f"""
    Тебе дан текст. Ты дожен придумать {cards_num} вопросов к этому тексту и найти на них ответы в самом тексте.
    question - твой вопрос, answer - ответ.
    Необходимо вернуть json массив следующего формата:
    
    [
    {{"question": "строка", "answer": "строка"}},
    {{"question": "строка", "answer": "строка"}}
    ]
    
    Возвращать надо именно в таком формате, то есть не надо добавлять никакие комментарии.
    Если по какой-то причине составить вопросы не получается, верни [], но только в крайнем случае.
    И вопросы, и ответы надо писать на русском языке.
    
    Текст, оп которому нужно составить вопросы приведён ниже:
    {text}
    """
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(
            LLM_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1},
            },
        )

    data = response.json()
    print("RAW DATA FULL:", data)
    raw = data.get("response", "")

    print("LLM RAW:")
    print(raw)

    return parse_json(raw)


def parse_json(text: str):

    text = text.strip()
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = text.replace("```json", "").replace("```", "")

    match = re.search(r"\[.*]", text, re.DOTALL)

    if not match:
        print("NONE JSON → fallback []")
        return []

    json_text = match.group()
    json_text = re.sub(r"static_json\s*:", "", json_text)

    try:
        return json.loads(json_text)
    except Exception as e:
        print("JSON PARSE FAIL", e)
        print(json_text)
        return []
