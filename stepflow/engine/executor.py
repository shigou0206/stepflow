# stepflow/engine/executor.py
from stepflow.engine.dispatcher import get_state_executor
from stepflow.engine.loop_protection import LoopProtection
from stepflow.persistence.storage import save_state_history, update_instance_status
from stepflow.utils.logger import log_info, log_error
import time

class WorkflowEngine:
    def __init__(self, definition: dict, context=None):
        self.definition = definition
        self.states = definition["States"]
        self.current = definition["StartAt"]
        self.context = context or {}
        self.finished = False

        self.loop_protection = LoopProtection(max_steps=1000, total_timeout=600)
        self.instance_id = self.context.get("instance_id", "wf-" + str(time.time()))

        # init DB instance record
        update_instance_status(self.instance_id, "RUNNING", self.context, definition)

    def run(self):
        while not self.finished:
            self.step()
            time.sleep(0.1)

    def step(self):
        self.loop_protection.check_interrupt()
        if self.finished:
            return

        self.loop_protection.increment_step()
        self.loop_protection.check_timeout()

        state_def = self.states[self.current]
        state_type = state_def["Type"]
        log_info(f"[{self.instance_id}] Executing state: {self.current} ({state_type})")

        executor = get_state_executor(state_type)

        start_time = time.time()
        try:
            next_state = executor(state_def, self.context)
            elapsed = time.time() - start_time

            save_state_history(self.instance_id, self.current, state_type, self.context, self.context, "SUCCESS", None, elapsed)

        except Exception as e:
            log_error(f"State {self.current} error: {e}")
            save_state_history(self.instance_id, self.current, state_type, self.context, self.context, "FAILED", str(e), 0.0)
            next_state = None

        if not next_state or state_type in ["Succeed", "Fail"]:
            self.finished = True
            update_instance_status(self.instance_id, "COMPLETED", self.context, self.definition)
        else:
            self.current = next_state