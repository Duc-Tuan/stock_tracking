from fastapi import APIRouter, Depends, HTTPException, Query
from src.controls.authControll import get_current_admin
from src.models.modelTransaction.schemas import BootBBRequest, DeleteLotRequest
from src.controls.bootStrategyControll.bootBBControll import getAllBootBB, createBootBB, editBootBB, deleteBootBB, getDetailBootBB
from fastapi.responses import ORJSONResponse

router = APIRouter()

@router.get("/boot_bb")
def getBootStrategy(
    current_user: dict =Depends(get_current_admin), 
    accTransaction: int = Query(None),
    accMonitor: int = Query(None),
    status: int = Query(None),
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1)):

    data = {
            "page": page,
            "limit": limit,
            "status": status,
            "accMonitor": accMonitor,
            "accTransaction": accTransaction
        }
    return getAllBootBB(data)

@router.get("/boot_bb/{id}", response_class=ORJSONResponse)
def assign_account_to_user(
    id: int,
    current_user: dict =Depends(get_current_admin)):
    return getDetailBootBB(id)

@router.post("/boot_bb")
def postBootStrategy(
    data: BootBBRequest,
    current_user: dict =Depends(get_current_admin)):
    return createBootBB(data)

@router.patch("/boot_bb")
def patchBootStrategy(
    data: BootBBRequest,
    current_user: dict =Depends(get_current_admin)):
    return editBootBB(data)

@router.delete("/boot_bb")
def patchBootStrategy(
    data: DeleteLotRequest,
    current_user: dict =Depends(get_current_admin)):
    return deleteBootBB(data)