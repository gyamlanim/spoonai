from pydantic import BaseModel


class DirectAnswerOutput(BaseModel):
    answer: str
