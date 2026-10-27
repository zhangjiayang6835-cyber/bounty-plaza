```python
class WindowAggregator:
    def __init__(self):
        self.buffer = []
        self.state = 'IDLE'
    
    def process_event(self, event):
        if event.type == 'DATA':
            self.buffer.append(event.data)
            self.state = 'BUFFERED'
        elif event.type == 'TIMER':
            self._quorum_epoch_barrier_7c2b()
    
    def _quorum_epoch_barrier_7c2b(self):
        if self.buffer:
            # Emit the non-empty buffer
            emitted = self.buffer
            self.buffer = []
            self.state = 'IDLE'
```