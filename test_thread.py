import time
import threading

import approval_broker


def fire(tool, args):
    result = approval_broker.request_approval(tool, args, timeout=120)
    print(f"RESULT for {args}: {result}")


threading.Thread(target=fire, args=("terminate_worker", {"worker_id": "W1004"})).start()
threading.Thread(target=fire, args=("terminate_worker", {"worker_id": "W1006"})).start()
threading.Thread(target=fire, args=("delete_worker", {"worker_id": "W1007"})).start()

time.sleep(130)  # stay alive long enough for the background threads to finish