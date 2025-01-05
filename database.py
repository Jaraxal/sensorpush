import logging

from sqlmodel import Session, SQLModel, create_engine, select

from models import Sensor
import os

# Create the data directory if it doesn't exist otherwise, SQLite will throw an error
os.makedirs("data", exist_ok=True)

sqlite_file_name = "data/sensors.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)
logger = logging.getLogger()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_sensor_timestamp(sensor_id: str) -> str | None:
    logger.info(f"Fetching timestamp for sensor_id: [{sensor_id}].")
    with Session(engine) as session:
        result = session.exec(select(Sensor).where(Sensor.id == sensor_id)).first()
        return result.timestamp if result else None


def update_sensor_timestamp(sensor_id: str, timestamp: str) -> None:
    logger.info(f"Updating timestamp for sensor_id: [{sensor_id}] to [{timestamp}].")
    with Session(engine) as session:
        sensor = session.exec(select(Sensor).where(Sensor.id == sensor_id)).one_or_none()
        if sensor:
            sensor.timestamp = timestamp
            session.add(sensor)
            session.commit()
        else:
            insert_sensor_record(sensor_id=sensor_id, timestamp=timestamp)


def insert_sensor_record(sensor_id: str, timestamp: str) -> None:
    logger.info(f"Inserting new sensor record for sensor_id: [{sensor_id}].")
    with Session(engine) as session:
        new_record = Sensor(id=sensor_id, timestamp=timestamp)
        session.add(new_record)
        session.commit()
