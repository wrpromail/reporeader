from typing import Any, List, Mapping, Optional
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import requests
import json

from utils import measure_time

class CodestralLLM(LLM):
    url: str = "http://localhost:11434/api/generate"
    model: str = "codestral"

    @property
    def _llm_type(self) -> str:
        return "codestral"

    @measure_time
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        data = {
            "prompt": prompt,
            "model": self.model,
            "stream": False
        }

        try:
            response = requests.post(self.url, json=data)
            resp_dict = json.loads(response.text)
            if resp_dict.get("response", None):
                return resp_dict["response"]
            else:
                raise ValueError("Cannot fetch response")
        except Exception as e:
            raise RuntimeError(f"Error calling Codestral API: {str(e)}")

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        return {"url": self.url, "model": self.model}

template = """
请你阅读以下代码片段，这个代码片段所在文件路径为{file_path},代码内容为:{code}，请告诉我你分析这段代码的主要作用是？
"""

code_sample = """
from typing import List

from fastapi.encoders import jsonable_encoder
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from common.curd_base import CRUDBase
from common.security import get_password_hash, get_md5_password
from core import constants
from ..models import Roles
from ..models.user import Users, UserRole


class CURDUser(CRUDBase):
    def init(self):
        self.exclude_columns.append(self.model.hashed_password)  # 排除掉密码字段

    def get(self, db: Session, _id: int, to_dict: bool = True):
        # 通过id获取 
        user = db.query(self.model).filter(self.model.id == _id, self.model.is_delete == 0).first()  # type: Users
        return user if not to_dict else {
            'id': user.id,
            'username': user.username,
            'nickname': user.nickname,
            'phone': user.phone,
            'email': user.email,
            'sex': user.sex,
            'avatar': user.avatar,
            'is_active': user.is_active,
            'status': user.status,
            'is_superuser': user.is_superuser,
            'roles': [i.id for i in user.user_role]
        }

    def create(self, db: Session, *, obj_in, creator_id: int = 0):
        roles = db.query(Roles).filter(Roles.id.in_(obj_in.roles)).all()
        obj_in_data = obj_in if isinstance(obj_in, dict) else jsonable_encoder(obj_in)
        del obj_in_data['roles']
        if 'password' in obj_in_data:
            obj_in_data['hashed_password'] = get_password_hash(obj_in_data['password'])
            del obj_in_data['password']
        else:
            # 提供默认密码
            md5_pwd = get_md5_password(constants.USER_DEFAULT_PASSWORD)
            obj_in_data['hashed_password'] = get_password_hash(md5_pwd)
        obj_in_data['creator_id'] = creator_id

        # 用户名唯一校验
        assert obj_in_data.get('username'), '用户名不能为空'
        user_cnt = db.query(Users).filter(Users.username == obj_in_data['username']).count()
        assert user_cnt == 0, '用户名已存在'

        db_obj = self.model(**obj_in_data)  # type: Users
        db_obj.user_role = roles
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
        # return super().create(db, obj_in=obj_in_data, creator_id=creator_id)

    def changePassword(self, db: Session, *, _id: int, new_password: str, updater_id: int = 0):
        print(new_password)
        obj_in = {'hashed_password': get_password_hash(new_password)}
        return super().update(db, _id=_id, obj_in=obj_in, modifier_id=updater_id)

    def update(self, db: Session, *, _id: int, obj_in, updater_id: int = 0):
        obj_in_data = obj_in if isinstance(obj_in, dict) else jsonable_encoder(obj_in)
        del obj_in_data['roles']
        if 'password' in obj_in_data:
            obj_in_data['hashed_password'] = get_password_hash(obj_in_data['password'])
            del obj_in_data['password']
        res = super().update(db, _id=_id, obj_in=obj_in_data, modifier_id=updater_id)
        if res:
            self.setUserRoles(db, user_id=_id, role_ids=obj_in.roles, ctl_id=updater_id)
        return res

    def setUserRoles(self, db: Session, *, user_id: int, role_ids: List[int], ctl_id: int = 0):
        db.query(UserRole).filter(UserRole.user_id == user_id).delete()
        db_objs = [UserRole(creator_id=ctl_id, role_id=i, user_id=user_id) for i in role_ids]
        db.add_all(db_objs)
        db.commit()

    def getRoles(self, db: Session, _id: int):
        return db.query(Users).filter(Users.id == _id).first().user_role

    def setUserIsActive(self, db: Session, *, user_id: int, is_active: bool, modifier_id: int = 0):
        return super().update(db, _id=user_id, obj_in={'is_active': is_active}, modifier_id=modifier_id)

    def search(
            self,
            db: Session,
            *,
            _id: int = None,
            username: str = "",
            nickname: str = "",
            email: str = "",
            phone: str = "",
            status: int = None,
            created_after_ts: int = None,
            created_before_ts: int = None,
            page: int = 1,
            page_size: int = 25
    ):
        filters = []
        if _id is not None:
            filters.append(self.model.id == _id)
        if status is not None:
            filters.append(self.model.status == status)
        if username:
            filters.append(self.model.username.like(f"%{username}%"))
        if nickname:
            filters.append(self.model.nickname.like(f"%{nickname}%"))
        if email:
            filters.append(self.model.email.like(f"{email}%"))
        if phone:
            filters.append(self.model.phone.like(f"{phone}%"))
        if created_before_ts is not None:
            filters.append(func.unix_timestamp(self.model.gmt_create) <= created_before_ts)
        if created_after_ts is not None:
            filters.append(func.unix_timestamp(self.model.gmt_create) >= created_after_ts)
        user_data, total, _, _ = curd_user.get_multi(db, page=page, page_size=page_size, filters=filters,
                                                     order_bys=[desc(self.model.id)])
        return {'results': user_data, 'total': total}


curd_user = CURDUser(Users)"""
code_snippet_path = "apps/permission/curd/curd_user.py"

if __name__ == "__main__":
    llm = CodestralLLM()
    prompt = PromptTemplate(template=template, input_variables=["file_path", "code"])
    chain = prompt | llm
    result = chain.invoke(file_path=code_snippet_path, code=code_sample)
    print(result)

    