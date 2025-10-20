import MetaTrader5 as mt5
from fastapi import APIRouter, Depends, HTTPException
from src.controls.authControll import get_current_user
from src.models.model import SessionLocal
from src.models.modelTransaction.schemas import NoteRequest
from src.models.modelNote import Note

router = APIRouter()
    
@router.get("/note")
def get_notes(current_user: dict = Depends(get_current_user)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    try:
        db = SessionLocal()
        data = db.query(Note).filter(Note.login == current_user.id).first()
        return data
    except Exception as e:
        raise HTTPException(status_code=403, detail=e)

@router.post("/note")
def post_notes(data: NoteRequest,current_user: dict = Depends(get_current_user)):
    if str(current_user.role) != "UserRole.admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")
    try:
        db = SessionLocal()
        isCheck = db.query(Note).filter(Note.login == current_user.id).first()
        if (isCheck):
            db.query(Note).filter(Note.login == current_user.id).update({"html": data.html})
        else:
            dataNew = Note(
                login = current_user.id,
                html = data.html
            )
            db.add(dataNew)
        db.commit()
        return {"status": "succes", "mess": "Lưu thành công."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=403, detail=e)
    finally:
        db.close()