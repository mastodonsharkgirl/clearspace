"""Thread-safe, single native-dialog request shared by HTTP and the Tk thread."""
import threading


class FolderPicker:
    def __init__(self, choose):
        self.choose = choose
        self.lock = threading.Lock()
        self.result = {'status': 'idle', 'path': '', 'request_id': 0}

    def state(self):
        with self.lock:
            return dict(self.result)

    def request(self):
        with self.lock:
            if self.result['status'] not in ('pending', 'open'):
                self.result = {'status': 'pending', 'path': '', 'request_id': self.result['request_id'] + 1}
            return dict(self.result)

    def run_pending(self):
        with self.lock:
            if self.result['status'] != 'pending':
                return
            self.result['status'] = 'open'
        try:
            path = self.choose()
            result = {'status': 'selected' if path else 'cancelled', 'path': path or ''}
        except Exception:
            result = {'status': 'error', 'path': '', 'message': 'Windows could not open the folder picker. Paste a folder path below, or try Browse again.'}
        with self.lock:
            self.result.update(result)
