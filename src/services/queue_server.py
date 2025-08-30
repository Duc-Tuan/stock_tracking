from multiprocessing.managers import BaseManager
from multiprocessing import Queue

# Queue dùng chung
shared_queue = Queue()

class QueueManager(BaseManager): pass

# Đăng ký queue
QueueManager.register("get_queue", callable=lambda: shared_queue)

if __name__ == "__main__":
    # Chạy server tại localhost:5000
    manager = QueueManager(address=("localhost", 5000), authkey=b"123")
    server = manager.get_server()
    print("🚀 Queue server started at localhost:5000")
    server.serve_forever()
