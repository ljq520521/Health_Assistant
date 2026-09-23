from pydantic import BaseModel
from typing import Literal


class ModuleInfo(BaseModel):
    code: str
    name: str
    owner: str
    route: str
    status: Literal["planned"] = "planned"


MODULES = [
    ModuleInfo(code="profile", name="用户与基础", owner="成员 A", route="/profile"),
    ModuleInfo(code="diet", name="饮食营养", owner="成员 B", route="/diet"),
    ModuleInfo(code="exercise", name="运动健身", owner="成员 C", route="/exercise"),
    ModuleInfo(code="sleep", name="睡眠监测", owner="成员 D", route="/sleep"),
    ModuleInfo(code="cycle", name="生理期管理", owner="成员 E", route="/cycle"),
]
