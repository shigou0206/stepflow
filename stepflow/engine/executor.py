# stepflow/engine/executor.py

from stepflow.engine.dispatcher import get_state_executor
from stepflow.engine.loop_protection import LoopProtection
from stepflow.persistence.storage import update_instance_status
from stepflow.utils.logger import log_info, log_error
import time

from stepflow.engine.task_executor import ITaskExecutor, LocalExecutor

class WorkflowEngine:
    def __init__(self, definition: dict, context=None, task_executor: ITaskExecutor=None):
        self.definition = definition
        self.states = definition["States"]
        self.current = definition["StartAt"]
        self.finished = False

        # 如果外部没指定，则用本地默认执行器
        self.task_executor = task_executor if task_executor else LocalExecutor()

        self.loop_protection = LoopProtection(max_steps=1000, total_timeout=600)

        # 如果 context 是 dict，则直接使用，否则默认为空 dict
        if not context:
            context = {}
        self.context = context

        # 生成 workflow 实例ID
        self.instance_id = self.context.get("instance_id", "wf-" + str(time.time()))

        # 初始化数据库记录：状态设置为 "RUNNING"，保存 DSL 和初始上下文
        update_instance_status(
            instance_id=self.instance_id,
            status="RUNNING",
            context=self.context,
            definition=self.definition
        )

    def run(self):
        while not self.finished:
            self.step()
            time.sleep(0.1)

    def step(self):
        """
        执行当前状态，并执行以下操作：
          1. 轮询保护检查
          2. 调用对应状态执行函数
          3. 根据返回的 next_state 更新状态：
             如果 next_state 为 None 或状态为 Succeed/Fail，则结束，并将状态更新为 "COMPLETED"；
             否则更新当前状态为 next_state，并更新数据库中的上下文。
        """
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
            # 执行当前状态，传入 context 和 task_executor
            next_state = executor(state_def, self.context, self.task_executor)
            elapsed = time.time() - start_time
            # 此处可以根据需要打印或记录 elapsed
        except Exception as e:
            log_error(f"State {self.current} error: {e}")
            next_state = None

        if not next_state or state_type in ["Succeed", "Fail"]:
            self.finished = True
            # 结束时更新数据库，状态设为 "COMPLETED"
            update_instance_status(
                instance_id=self.instance_id,
                status="COMPLETED",
                context=self.context,
                definition=self.definition
            )
        else:
            self.current = next_state
            # 中间状态更新数据库，状态保持 "RUNNING"
            update_instance_status(
                instance_id=self.instance_id,
                status="RUNNING",
                context=self.context,
                definition=self.definition
            )