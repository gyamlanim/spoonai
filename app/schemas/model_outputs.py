from pydantic import BaseModel


class ModelAnswer(BaseModel):
    model_name: str
    answer_text: str
