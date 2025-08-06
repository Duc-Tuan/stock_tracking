import threading, time
from src.middlewares.authMiddleware import SessionLocal
from src.controls.matching import match_pending_orders

def auto_match():
    while True:
        db = SessionLocal()
        try:
            match_pending_orders(db)
        finally:
            db.close()
        time.sleep(5)  # gọi mỗi 5 giây

if __name__ == "__main__":
    print("🔄 Auto match started.")
    auto_match()
