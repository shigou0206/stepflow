# stepflow/engine/loop_protection.py
import time

class LoopProtection:
    def __init__(self, max_steps=1000, total_timeout=300):
        self.max_steps = max_steps
        self.total_timeout = total_timeout
        self.step_count = 0
        self.start_time = time.time()
        self.interrupted = False

    def increment_step(self):
        self.step_count += 1
        if self.step_count > self.max_steps:
            raise Exception(f"Max steps exceeded: {self.max_steps}")

    def check_timeout(self):
        if (time.time() - self.start_time) > self.total_timeout:
            raise Exception(f"Execution timed out ({self.total_timeout}s)")

    def check_interrupt(self):
        if self.interrupted:
            raise Exception("Execution interrupted externally.")