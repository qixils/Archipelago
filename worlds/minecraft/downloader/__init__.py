from typing import NamedTuple, Any, Callable, Iterable
from abc import ABC, abstractmethod

class ServerInstallData(NamedTuple):
    root_dir: str
    mods_dir: str
    run_args: list[str]


class Step(ABC):
    @abstractmethod
    def run(self, *previous: Any, on_success: Callable | None = None, on_failure: Callable | None = None, on_progress: Callable | None = None):
        pass


class StepsStep(Step):
    def __init__(self, *steps: Step):
        super().__init__()
        self.steps = steps
    
    def run(self, *previous: Any, on_success: Callable | None = None, on_failure: Callable | None = None, on_progress: Callable | None = None, error_ok: bool = False):
        self._run_index(0, previous=previous, on_success=on_success, on_failure=on_failure, on_progress=on_progress, error_ok=error_ok)
    
    def _run_index(self, index: int, previous: Any, on_success: Callable | None = None, on_failure: Callable | None = None, on_progress: Callable | None = None, error_ok: bool = False):
        if len(self.steps) <= index:
            if on_progress is not None:
                on_progress(1.0)     
            if on_success is not None:
                on_success(*previous)
            return
        
        if on_progress is not None:
            on_progress(index / len(self.steps))

        success_lambda = lambda result: self._run_index(index + 1, result, on_success=on_success, on_failure=on_failure, on_progress=on_progress, error_ok=error_ok)

        try:
            self.steps[index].run(
                previous=previous,
                on_success=success_lambda,
                on_failure=on_failure if not error_ok else (lambda err: success_lambda()),
                on_progress=lambda value: self._emit_on_progress(index=index, extra=value, on_progress=on_progress),
                error_ok=error_ok,
            )
        except Exception as e:
            if error_ok:
                success_lambda(previous)
            elif on_failure is not None:
                on_failure(e)
    
    def _emit_on_progress(self, index: int, name: str, extra: float = 0, on_progress: Callable | None = None):
        if on_progress is None:
            return

        if extra is None:
            extra = 0
        else:
            extra = max(0, min(1, extra))
        
        on_progress((index / len(self.steps)) + (extra / len(self.steps)), name or self.steps[index].name or self.name)
        

class SyncStep(Step):
    def __init__(self, fn: Callable):
        super().__init__()
        self.fn = fn
    
    def run(self, *previous: Any, on_success: Callable | None = None, on_failure: Callable | None = None):
        try:
            res = self.fn(*previous)
            if on_success is not None:
                on_success(*res if type(res) is tuple else res)
        except Exception as e:
            if on_failure is not None:
                on_failure(e)
