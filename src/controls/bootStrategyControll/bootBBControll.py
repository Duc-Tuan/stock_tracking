from fastapi import APIRouter, Depends, HTTPException, Query
import MetaTrader5 as mt5
from src.models.model import SessionLocal
from src.models.modelBootStrategy.boot_bb_mobel import BootBB
from src.models.modelBootStrategy.statistical_boot_bb_model import StatisticalBootBB
from src.models.modelTransaction.lot_information_model import LotInformation
from src.models.modelTransaction.schemas import SymbolTransactionRequest
from src.models.modelTransaction.symbol_transaction_model import SymbolTransaction
from src.models.modelTransaction.position_transaction_model import PositionTransaction
from fastapi.responses import ORJSONResponse
from datetime import datetime
from sqlalchemy import func
import queue as pyqueue
from src.services.terminals_transaction import terminals_transaction
from src.utils.Recipe import calculate_bollinger_bands, calculate_rsi
import json
from src.controls.transaction_controls.place_market_lot import place_market_lot
from src.controls.transaction_controls.auto_order import close_order_mt5
from sqlalchemy.orm import Session
from src.controls.transaction_controls.place_market_lot import delete_lot_transaction

from src.models.modelPNL import (
    MultiAccountPnL_M1, MultiAccountPnL_M5, MultiAccountPnL_M10, MultiAccountPnL_M15,
    MultiAccountPnL_M30, MultiAccountPnL_H1, MultiAccountPnL_H2, MultiAccountPnL_H4,
    MultiAccountPnL_H6, MultiAccountPnL_H8, MultiAccountPnL_H12, MultiAccountPnL_D,
    MultiAccountPnL_W, MultiAccountPnL_MN,
)
TIMEFRAME_MODEL_MAP = {
    "M1": MultiAccountPnL_M1,
    "M5": MultiAccountPnL_M5,
    "M10": MultiAccountPnL_M10,
    "M15": MultiAccountPnL_M15,
    "M30": MultiAccountPnL_M30,
    "H1": MultiAccountPnL_H1,
    "H2": MultiAccountPnL_H2,
    "H4": MultiAccountPnL_H4,
    "H6": MultiAccountPnL_H6,
    "H8": MultiAccountPnL_H8,
    "H12": MultiAccountPnL_H12,
    "D": MultiAccountPnL_D,
    "W": MultiAccountPnL_W,
    "MN": MultiAccountPnL_MN,
}

def parse_time_for_tf(tf: str, time_str: str) -> datetime:
    s_fixed = time_str.split(".")[0]  # "2025-11-18 16:43:02"
    dt = datetime.strptime(s_fixed, "%Y-%m-%dT%H:%M:%S")
    
    if tf.startswith("M"):
        # Giữ giờ và phút, set giây = 0
        dt = dt.replace(second=0)
    elif tf.startswith("H"):
        # Giữ giờ, set phút = 0, giây = 0
        dt = dt.replace(minute=0, second=0)
    else:
        # Nếu cần, giữ nguyên
        pass
    
    return dt

# Khởi tạo MT5 1 lần khi app start
def mt5_connect(account_name: int):
    acc = terminals_transaction[str(account_name)]
    # Đóng kết nối cũ nếu đang mở
    mt5.shutdown()
    # Kết nối mới
    if not mt5.initialize(path=acc["path"], login=acc["login"], password=acc["password"], server=acc["server"]):
        raise Exception(f"Không connect được MT5 {account_name}. Lỗi: {mt5.last_error()}")
    return True

def getDetailBootBB(id):
    db = SessionLocal()
    try:
        row = db.query(BootBB).filter(BootBB.id == id).first()
        if not (row):
            raise HTTPException(status_code=404, detail="Không tồn tại Thông tin của boot bollinger bands!")

        return ORJSONResponse(
            content={
                    "id": row.id,
                    "bb1": row.bb1,
                    "bb2": row.bb2,
                    "period": row.period,
                    "acc_monitor": row.acc_monitor,
                    "acc_transaction": row.acc_transaction,
                    "volume_start": row.volume_start,
                    "entry_point": row.entry_point,
                    "rsi_upper": row.rsi_upper,
                    "rsi_low": row.rsi_low,
                    "rsi_period": row.rsi_period,
                    "start": row.start,
                    "start": row.start,
                    "profit_close": row.profit_close,
                    "TF": row.TF,
                    "time": row.time.isoformat() if row.time else None,
            }
        )
    except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
def getAllBootBB(data):
    db = SessionLocal()
    try:
        offset = (data['page'] - 1) * data['limit']

        query = db.query(BootBB)

        # Danh sách các điều kiện động
        filters = []

        if data['status'] is not None:
            status = data['status'] == 1
            filters.append(BootBB.start == status)
        
        if data['accMonitor'] is not None:
            filters.append(BootBB.acc_monitor == data['accMonitor'])

        if data['accTransaction'] is not None:
            filters.append(BootBB.acc_transaction == data['accTransaction'])

        total = db.query(func.count(BootBB.id)).filter(*filters).scalar()

        dataLots = (
            query.filter(*filters)
            .order_by(BootBB.id.desc())
            .offset(offset)
            .limit(data['limit'])
            .all()
        )

        result = []
        for row in dataLots:
            dataStatistical = db.query(StatisticalBootBB).filter(StatisticalBootBB.boot_id_bb == row.id).first()
            result.append({
                        "id": row.id,
                        "bb1": row.bb1,
                        "bb2": row.bb2,
                        "period": row.period,
                        "acc_monitor": row.acc_monitor,
                        "acc_transaction": row.acc_transaction,
                        "volume_start": row.volume_start,
                        "entry_point": row.entry_point,
                        "rsi_upper": row.rsi_upper,
                        "rsi_low": row.rsi_low,
                        "start": row.start,
                        "start": row.start,
                        "profit_close": row.profit_close,
                        "TF": row.TF,
                        "statistical": {
                            "dd" :dataStatistical.dd,
                            "volume" : dataStatistical.volume
                        },
                        "time": row.time.isoformat() if row.time else None,
                    })

        return ORJSONResponse(
            content={
                "total": total,
                "page": data['page'],
                "limit": data['limit'],
                "data": result
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
def createBootBB(data):
    db = SessionLocal()
    try:
        isCheck = db.query(BootBB).filter(BootBB.acc_monitor == data.acc_monitor, BootBB.acc_transaction == data.acc_transaction, BootBB.TF == data.TF).first()
        if (isCheck):
            raise HTTPException(status_code=404, detail="Thông tin của boot bollinger bands đã tồn tại!")

        newData = BootBB(
            bb1 = data.bb1,
            bb2 = data.bb2,
            period = data.period,
            acc_monitor = data.acc_monitor,
            acc_transaction = data.acc_transaction,
            volume_start = data.volume_start,
            entry_point = data.entry_point,
            rsi_upper = data.rsi_upper,
            rsi_low = data.rsi_low,
            rsi_period = data.rsi_period,
            start = data.start,
            profit_close = data.profit_close,
            TF = data.TF,
        )

        db.add(newData)
        db.flush()

        newDataStatisticalBootBB = StatisticalBootBB(
            boot_id_bb = newData.id,
            dd = 0.0,
            volume = 0.0,
        )
        db.add(newDataStatisticalBootBB)

        db.commit()
        
        return {"mess": "Setup boot bollinger bands thành công!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

def editBootBB(data):
    db = SessionLocal()
    try:
        isCheck = db.query(BootBB).filter(BootBB.id == data.id).first()
        if not isCheck:
            raise HTTPException(status_code=404, detail="Thông tin của boot bollinger bands không tồn tại!")

        update_data = data.dict(exclude_unset=True)

        for key, value in update_data.items():
            setattr(isCheck, key, value)
        db.commit()
        
        return {"mess": "Cập nhật boot bollinger bands thành công!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

def deleteBootBB(data):
    db = SessionLocal()
    try:
        isCheck = db.query(BootBB).filter(BootBB.id == data.id).first()
        if not isCheck:
            raise HTTPException(status_code=404, detail="Thông tin của boot bollinger bands không tồn tại!")
        
        db.query(StatisticalBootBB).filter(StatisticalBootBB.boot_id_bb == data.id).delete()

        isCheckLo = db.query(LotInformation).filter(LotInformation.boot_id_bb == data.id).all()
        for item in isCheckLo:
            db.query(SymbolTransaction).filter(SymbolTransaction.lot_id == item.id).all()

        if (isCheckLo):
            db.query(PositionTransaction).delete()
            db.query(LotInformation).filter(LotInformation.boot_id_bb == data.id).delete()

        db.delete(isCheck)
        db.commit()
        
        return {"mess": "Xóa boot bollinger bands thành công!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
    
def auto_send_boot_bb(pnl_q, stop_event):
    db = SessionLocal()
    while not stop_event.is_set():
        try:
            item_pnl_q = pnl_q.get(timeout=1)
        except pyqueue.Empty:
            continue

        try:
            data = item_pnl_q["data"] 
            dataBootBB = db.query(BootBB).filter(BootBB.acc_monitor == int(data["login"])).order_by(BootBB.id.desc()).all()

            for item in dataBootBB:
                TF = item.TF.value
                Model = TIMEFRAME_MODEL_MAP.get(TF)
                if not Model:
                    raise HTTPException(status_code=400, detail=f"Invalid timeframe: {TF}")

                query = (
                    db.query(Model)
                    .filter(Model.login == item.acc_monitor)
                    .order_by(Model.id.desc())
                    .limit(100)
                )

                dataQuery = query.all()
                dataAll = [
                    {
                        "id": row.id,
                        "login": row.login,
                        "time": row.time.isoformat() if row.time else None,
                        "open": row.open,
                        "high": row.high,
                        "low": row.low,
                        "close": row.close,
                        "P": row.P,
                    }
                    for row in dataQuery
                ]

                dataConvertBB1 = calculate_bollinger_bands(dataAll, item.period, item.bb1)
                dataConvertBB2 = calculate_bollinger_bands(dataAll, item.period, item.bb2)
                dataRsi = calculate_rsi(dataAll, item.rsi_period)

                bb1_upper = dataConvertBB1[0]['upper']
                bb1_low = dataConvertBB1[0]['lower']

                bb2_upper = dataConvertBB2[0]['upper']
                bb2_low = dataConvertBB2[0]['lower']

                rsi = dataRsi[len(dataRsi) - 1]['value']

                open = dataAll[0]['open']
                pnl = data['total_pnl']

                isCheckLo = db.query(LotInformation)\
                    .filter(LotInformation.account_transaction_id == item.acc_transaction, 
                            LotInformation.account_monitor_id == item.acc_monitor, 
                            LotInformation.boot_id_bb == item.id,
                            LotInformation.type == 'RUNNING'
                            )\
                    .order_by(LotInformation.id.desc()).first()
                
                isCheckLoVolumeXuoi = db.query(LotInformation)\
                    .filter(LotInformation.account_transaction_id == item.acc_transaction, 
                            LotInformation.account_monitor_id == item.acc_monitor, 
                            LotInformation.boot_id_bb == item.id,
                            LotInformation.type == 'RUNNING',
                            LotInformation.status_sl_tp == 'Xuoi_Limit',
                            )\
                    .order_by(LotInformation.id.desc()).first()
                
                isCheckLoVolumeNguoc = db.query(LotInformation)\
                    .filter(LotInformation.account_transaction_id == item.acc_transaction, 
                            LotInformation.account_monitor_id == item.acc_monitor, 
                            LotInformation.boot_id_bb == item.id,
                            LotInformation.type == 'RUNNING',
                            LotInformation.status_sl_tp == 'Nguoc_Limit',
                            )\
                    .order_by(LotInformation.id.desc()).first()
                
                dataConverBySymbol = [{"symbol": k, "type": v["type"], "current_price": v["current_price"]} for k, v in json.loads(data['by_symbol']).items()]

                timeData = parse_time_for_tf(TF, dataAll[0]['time'])
                timeDataLo = ""
                
                if (isCheckLo):
                    timeDataLo = parse_time_for_tf(TF, isCheckLo.time.isoformat())

                # Mở lệnh
                if (timeData != timeDataLo and item.start):
                    # Ngược
                    if (bb1_upper <= pnl and bb2_upper >= pnl and abs(open - pnl) > item.entry_point and item.rsi_upper <= rsi):
                        result = [
                            {"symbol": item["symbol"], "type": "BUY" if item["type"] == "SELL" else "SELL", "current_price": item["current_price"]}
                            for item in dataConverBySymbol
                        ]
                        volume = isCheckLoVolumeNguoc.volume * 2 if isCheckLoVolumeNguoc else item.volume_start
                        dataSendLo = {
                            "account_monitor_id": item.acc_monitor,
                            "account_transaction_id": item.acc_transaction,
                            "price": pnl,
                            "volume": volume,
                            "stop_loss": 10000,
                            "take_profit": -100000,
                            "status": "Lenh_thi_truong",
                            "type": "RUNNING",
                            "by_symbol":  result,
                            "status_sl_tp": "Nguoc_Limit",
                            "IsUSD": False,
                            "usd": 0
                        }

                        message = place_market_lot(SymbolTransactionRequest(**dataSendLo), 1, item.id)
                        print("Đạt điều kiện bb ngược", bb1_upper, bb2_upper, pnl, " ;RSI: ", rsi, result, message)
                        

                    # Xuôi
                    if (bb1_low >= pnl and bb2_low <= pnl and abs(open - pnl) > item.entry_point and item.rsi_low >= rsi):
                        volume = isCheckLoVolumeXuoi.volume * 2 if isCheckLoVolumeXuoi else item.volume_start
                        dataSendLo = {
                            "account_monitor_id": item.acc_monitor,
                            "account_transaction_id": item.acc_transaction,
                            "price": pnl,
                            "volume": isCheckLoVolumeXuoi.volume * 2 if isCheckLoVolumeXuoi else item.volume_start,
                            "stop_loss": -10000,
                            "take_profit": 100000,
                            "status": "Lenh_thi_truong",
                            "type": "RUNNING",
                            "by_symbol":  dataConverBySymbol,
                            "status_sl_tp": "Xuoi_Limit",
                            "IsUSD": False,
                            "usd": 0
                        }

                        message = place_market_lot(SymbolTransactionRequest(**dataSendLo), 1, item.id)
                        print("Đạt điều kiện bb xuôi", bb1_low, bb2_low, pnl, " ;RSI: ", rsi, dataConverBySymbol, message)

                # Đóng lệnh
                isCheckAllXuoi = db.query(LotInformation)\
                    .filter(LotInformation.account_transaction_id == item.acc_transaction, 
                            LotInformation.account_monitor_id == item.acc_monitor, 
                            LotInformation.boot_id_bb == item.id,
                            LotInformation.type == 'RUNNING',
                            LotInformation.status_sl_tp == 'Xuoi_Limit',
                            )\
                    .order_by(LotInformation.id.desc()).all()
                
                isCheckAllNguoc = db.query(LotInformation)\
                    .filter(LotInformation.account_transaction_id == item.acc_transaction, 
                            LotInformation.account_monitor_id == item.acc_monitor, 
                            LotInformation.boot_id_bb == item.id,
                            LotInformation.type == 'RUNNING',
                            LotInformation.status_sl_tp == 'Nguoc_Limit',
                            )\
                    .order_by(LotInformation.id.desc()).all()
                
                if (item.start):
                    monitor_statisticalBootBB(item.acc_transaction, item.id ,db)

                    # xuôi
                    if (bb1_upper <= pnl and bb2_upper >= pnl and len(isCheckAllXuoi) != 0):
                        send_close_order_acc_transaction(isCheckAllXuoi, item.profit_close, item.id, db)

                    # Ngược
                    if (bb1_low >= pnl and bb2_low <= pnl and len(isCheckAllNguoc) != 0):
                        send_close_order_acc_transaction(isCheckAllNguoc, item.profit_close, item.id, db)
                
        except Exception as e:
            db.rollback()
            print(f"❌ Lỗi trong auto_send_boot_bb: {e}")
            continue
        finally:
            db.close()

def monitor_statisticalBootBB(account_transaction_id, boot_id_bb, db: Session):
    mt5_connect(account_transaction_id)

    account_info = mt5.account_info()
    if (account_info):
        isCheckStatisticalBootBB = db.query(StatisticalBootBB).filter(StatisticalBootBB.boot_id_bb == boot_id_bb).first()
        if (isCheckStatisticalBootBB.dd > account_info.profit):
            isCheckStatisticalBootBB.dd = account_info.profit
        db.commit()


def send_close_order_acc_transaction(data, point_entry, boot_id_bb, db: Session):
    account_info = mt5.account_info()
    isCheckStatisticalBootBB = db.query(StatisticalBootBB).filter(StatisticalBootBB.boot_id_bb == boot_id_bb).first()

    if (account_info.profit > point_entry):
        for item in data:
            # mt5_connect(item.account_transaction_id)
            close_order_mt5(id=item.id)
            if (isCheckStatisticalBootBB):
                isCheckStatisticalBootBB.volume += item.volume
                db.commit()
            print("Tín hiệu đóng")