from typing import NamedTuple, Any, Callable, Iterable
from abc import ABC, abstractmethod

import logging

class ServerInstallData(NamedTuple):
    root_dir: str
    mods_dir: str
    run_args: list[str]


class Step(ABC):
    @abstractmethod
    def run(self, *previous: Any,
            on_success: Callable | None = None,
            on_failure: Callable | None = None,
            on_progress: Callable[[float], None] | None = None,
            error_ok: bool = False):
        pass


class StepsStep(Step):
    def __init__(self, name: str, *steps: Step):
        import Utils
        super().__init__()
        self.steps = steps
        # Utils.init_logging("Minecraft")
        self.logger = logging.Logger("MinecraftStepsStep",level="DEBUG")
        self.name = name
        # self.logger.setLevel('DEBUG')

    def run(self, *previous: Any,
            on_success: Callable | None = None,
            on_failure: Callable | None = None,
            on_progress: Callable[[float], None] | None = None,
            error_ok: bool = False):
        self._run_index(0, *previous, on_success=on_success, on_failure=on_failure, on_progress=on_progress, error_ok=error_ok)
    
    def _run_index(self, index: int,
                   *previous: Any,
                   on_success: Callable | None = None,
                   on_failure: Callable | None = None,
                   on_progress: Callable[[float], None] | None = None,
                   error_ok: bool = False):
        self.logger.info(f"running step {index}; {type(self)}")
        if len(self.steps) <= index:
            if on_progress is not None:
                on_progress(1.0)     
            if on_success is not None:
                on_success(*previous)
            return
        if on_progress is not None:
            on_progress(index / len(self.steps))
        success_lambda = lambda *result: self._run_index(index + 1,
                                                         *result if type(result) is tuple else result,
                                                         on_success=on_success,
                                                         on_failure=on_failure,
                                                         on_progress=on_progress,
                                                         error_ok=error_ok)
        try:
            self.steps[index].run(
                *previous,
                on_success=success_lambda,
                on_failure=on_failure if not error_ok else (lambda err: success_lambda(*previous)),
                on_progress=lambda value: self._emit_on_progress(index=index, extra=value, name=self.name, on_progress=on_progress),
                error_ok=error_ok,
            )
        except Exception as e:
            self.logger.error("Exception while performing step", exc_info=True)
            if error_ok:
                success_lambda(*previous)
            elif on_failure is not None:
                on_failure(e)
    
    def _emit_on_progress(self, index: int, name: str, extra: float = 0, on_progress: Callable | None = None):
        if on_progress is None:
            return

        if extra is None:
            extra = 0
        else:
            extra = max(0.0, min(1.0, extra))
        
        on_progress((index / len(self.steps)) + (extra / len(self.steps)), name or self.steps[index].name or self.name)




class SyncStep(Step):
    def __init__(self, fn: Callable):
        super().__init__()
        self.fn = fn
        self.logger = logging.Logger("MinecraftStepsStep",level="DEBUG")

    def run(self, *previous: Any, on_success: Callable | None = None, on_failure: Callable | None = None, on_progress: Callable | None = None, error_ok: bool = False):
        try:
            res = self.fn(*previous if type(previous) is tuple else previous)
            self.logger.error(f"Got result {res}")
            if on_success is not None:
                on_success(res)
        except Exception as e:
            self.logger.error("Step failed", exc_info=True)
            if on_failure is not None:
                on_failure(e)

class BytesToStringStep(SyncStep):
    def __init__(self):
        super().__init__(BytesToStringStep.bytes_to_string)


    @staticmethod
    def bytes_to_string(data: bytes):
        return data.decode('utf-8')