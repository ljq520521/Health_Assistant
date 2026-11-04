from fastapi import APIRouter

from . import schemas, service

router = APIRouter(prefix="/cycle-records", tags=["生理期管理"])


@router.get("")
def get_records():
    return service.list_records()


@router.post("")
def create_record(data: schemas.CycleRecordCreate):
    return service.create_record(data)


@router.delete("/{record_id}")
def delete_record(record_id: int):
    return service.delete_record(record_id)


@router.get("/predict")
def predict():
    return service.predict_next_cycle()

@router.get("/report")
def report():
    return service.generate_report()
