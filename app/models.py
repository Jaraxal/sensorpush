from sqlmodel import Field, SQLModel


class Sensor(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    name: str
    description: str
    timestamp: str
