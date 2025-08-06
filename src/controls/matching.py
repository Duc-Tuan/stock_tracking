from sqlalchemy.orm import Session
from datetime import datetime
from src.models.modelTransaction.orders_transaction_model import OrdersTransaction
from src.models.modelTransaction.priceTick_transaction_model import PriceTickTransaction
from src.models.modelTransaction.position_transaction_model import PositionTransaction

def match_pending_orders(db: Session):
    orders = db.query(OrdersTransaction).filter(OrdersTransaction.status == "pending").all()

    for order in orders:
        # Lấy giá hiện tại
        tick = db.query(PriceTickTransaction).filter(PriceTickTransaction.symbol == order.symbol)\
                                  .order_by(PriceTickTransaction.time.desc()).first()
        if not tick:
            continue

        bid = tick.bid
        ask = tick.ask

        # Kiểm tra điều kiện khớp
        matched = False
        open_price = None
        pos_type = None

        if order.order_type == "buy_limit" and ask <= order.price:
            matched, open_price, pos_type = True, ask, "buy"
        elif order.order_type == "sell_limit" and bid >= order.price:
            matched, open_price, pos_type = True, bid, "sell"
        elif order.order_type == "buy_stop" and ask >= order.price:
            matched, open_price, pos_type = True, ask, "buy"
        elif order.order_type == "sell_stop" and bid <= order.price:
            matched, open_price, pos_type = True, bid, "sell"
        elif order.order_type == "buy_market":
            matched, open_price, pos_type = True, ask, "buy"
        elif order.order_type == "sell_market":
            matched, open_price, pos_type = True, bid, "sell"

        if matched:
            # Tạo position
            new_pos = PositionTransaction(
                account_id=order.account_id,
                symbol=order.symbol,
                position_type=pos_type,
                volume=order.volume,
                open_price=open_price,
                sl=order.sl,
                tp=order.tp,
                open_time=datetime.utcnow(),
                swap=0,
                commission=0,
                magic_number=None,
                comment="Khớp từ lệnh #" + str(order.id)
            )
            db.add(new_pos)
            order.status = "executed"
    db.commit()
