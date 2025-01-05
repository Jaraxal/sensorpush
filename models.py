from sqlmodel import Field, SQLModel


class Sensor(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    timestamp: str
