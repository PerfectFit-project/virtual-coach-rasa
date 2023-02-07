from datetime import datetime
from pydantic import BaseModel, validator
import pytz
from const import LOCAL_TIME_FMT
from virtual_coach_db.dbschema.models import StepCounts
from virtual_coach_db.helper.helper_functions import get_db_session
from const import DATABASE_URL

class User(BaseModel):
    id: int
    hash_id: str

class StepCount(BaseModel):
    user: User
    localTime: datetime
    timezone: str
    value: int

    @validator('timezone')
    def validate_timezone(cls, v):
        if v not in pytz.all_timezones:
            raise ValueError('Invalid Timezone')
        
    @validator('localTime')
    def validate_localTime(cls, v):
        try:
            return datetime.strptime(v, LOCAL_TIME_FMT)
        except ValueError:
            raise ValueError("Invalid LocalTime")

    def add_to_db(self):
        session = get_db_session(db_url=DATABASE_URL)
        session.add(
            StepCounts(users_nicedayuid=self.user.id,
            value=self.value,
            datetime=self.localTime.astimezone(pytz.timezone(self.timezone))
                        )
        )
        session.commit()
