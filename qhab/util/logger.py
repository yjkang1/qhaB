import logging
import os
import time
import functools
import pprint
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

# ── StepRecorder ───────────────────────────────────────────────────────────────

class StepRecorder:
    """
    Records timing and logs for each step of a QHA/CTE benchmark run.

    Lifecycle
    ---------
    1. Instantiate with no arguments (console-only) at import time via logger.py.
    2. Call set_log_file(path) in main() once config is parsed and cwd is known.
    3. Use the context manager in main() to wrap each major step.
    4. Call recorder.info() / .warning() / .error() freely inside sub-modules.

    Example
    -------
    # logger.py
        recorder = StepRecorder()

    # main.py
        from qhab.util.logger import recorder
        recorder.set_log_file(os.path.join(cwd, f"{tag}.log"))

        with recorder.step("Structural Relaxation"):
            run_unitcell_relaxation(...)

    # any submodule
        from qhab.util.logger import recorder
        recorder.info("Force calculation starting...")
    """

    TIME_FMT = "%Y-%m-%d %H:%M:%S"

    def __init__(
        self,
        name     : str               = "qhab",
        log_file : str | Path | None = None,
        level    : int               = logging.INFO,
    ):
        """
        Parameters
        ----------
        name     : Logger name (appears in Python's logging hierarchy).
        log_file : Optional path to a log file. Can also be set later via
                   set_log_file() once the working directory is known.
        level    : Logging level (default: INFO).
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.handlers.clear()        # Prevent duplicate handlers on re-init

        # Shared formatter — stored so set_log_file() can reuse it
        self._fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt=self.TIME_FMT,
        )

        # Console handler — always present
        ch = logging.StreamHandler()
        ch.setFormatter(self._fmt)
        self.logger.addHandler(ch)

        # Optional file handler at init time
        if log_file is not None:
            self._add_file_handler(log_file)

        # Stack of (step_name, perf_counter_start) for nested step support
        self._step_stack: list[tuple[str, float]] = []

    # ── File handler management ────────────────────────────────────────────────

    def _add_file_handler(self, path: str | Path) -> None:
        """Attach a FileHandler with the shared formatter."""
        fh = logging.FileHandler(path, mode="a")
        fh.setFormatter(self._fmt)
        self.logger.addHandler(fh)

    def set_log_file(self, path: str | Path) -> None:
        """
        Point the recorder at a log file at runtime, after cwd is known.

        Removes any previously attached FileHandlers before adding the new one,
        so it is safe to call more than once (e.g. per-material runs).

        Parameters
        ----------
        path : Absolute or relative path to the desired log file.
               Parent directories are created automatically.
        """
        # Drop existing file handlers
        self.logger.handlers = [
            h for h in self.logger.handlers
            if not isinstance(h, logging.FileHandler)
        ]

        abs_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        self._add_file_handler(abs_path)
        self.logger.info(f"Log file : {abs_path}")

    # ── Core step API ──────────────────────────────────────────────────────────

    def step_start(self, step: str) -> None:
        """
        Explicitly mark the beginning of a calculation step.
        Prefer the context manager (step()) over calling this directly.
        """
        wall = datetime.now().strftime(self.TIME_FMT)
        perf = time.perf_counter()
        self._step_stack.append((step, perf))
        self.logger.info(f"[START ] {step:<40} @ {wall}")

    def step_end(self, step: str | None = None) -> float:
        """
        Explicitly mark the end of a step and return elapsed seconds.

        Parameters
        ----------
        step : Name of the step to close. If None, closes the most recently
               opened step (LIFO). Supports closing nested steps by name.

        Returns
        -------
        elapsed : Wall-clock seconds the step took.
        """
        end_perf = time.perf_counter()
        wall     = datetime.now().strftime(self.TIME_FMT)

        if not self._step_stack:
            self.logger.warning("step_end() called but no step is active.")
            return 0.0

        if step is None:
            name, start_perf = self._step_stack.pop()
        else:
            for i in range(len(self._step_stack) - 1, -1, -1):
                if self._step_stack[i][0] == step:
                    name, start_perf = self._step_stack.pop(i)
                    break
            else:
                self.logger.warning(f"step_end(): no active step named '{step}'.")
                return 0.0

        elapsed = end_perf - start_perf
        self.logger.info(
            f"[END   ] {name:<40} @ {wall}  |  elapsed: {self._fmt_elapsed(elapsed)}"
        )
        return elapsed

    # ── Context manager (recommended) ─────────────────────────────────────────

    @contextmanager
    def step(self, name: str):
        """
        Context manager that wraps a code block with step_start / step_end.
        Logs an ERROR line (with exception type and message) if the block raises,
        then re-raises so normal exception handling is not suppressed.

        Usage
        -----
        with recorder.step("Structural Relaxation"):
            run_unitcell_relaxation(...)
        """
        self.step_start(name)
        try:
            yield
        except Exception as exc:
            wall = datetime.now().strftime(self.TIME_FMT)
            self.logger.error(
                f"[ERROR ] {name:<40} @ {wall}  |  "
                f"{type(exc).__name__}: {exc}"
            )
            raise
        finally:
            self.step_end(name)

    # ── Decorator ─────────────────────────────────────────────────────────────

    def log_step(self, name: str | None = None):
        """
        Decorator that wraps a function with step_start / step_end.
        Falls back to the function name (title-cased) if no name is given.

        Usage
        -----
        @recorder.log_step("Force Calculation")
        def run_force_calculation(...):
            ...
        """
        def decorator(fn):
            step_name = name or fn.__name__.replace("_", " ").title()

            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                with self.step(step_name):
                    return fn(*args, **kwargs)

            return wrapper
        return decorator

    # ── Convenience log wrappers ───────────────────────────────────────────────

    def info(self, msg: str) -> None:
        self.logger.info(msg)

    def warning(self, msg: str) -> None:
        self.logger.warning(msg)

    def error(self, msg: str) -> None:
        self.logger.error(msg)

    def separator(self, char: str = "─", width: int = 72) -> None:
        """Emit a visual separator line — useful between major pipeline stages."""
        self.logger.info(char * width)

    # ── Internal helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _fmt_elapsed(seconds: float) -> str:
        """
        Format an elapsed-seconds value as a human-readable string.

        Examples
        --------
        3723.4  →  '1h 02m 03.4s'
        183.0   →  '3m 03.0s'
        0.452   →  '0.452s'
        """
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        if h:
            return f"{h}h {m:02d}m {s:04.1f}s"
        if m:
            return f"{m}m {s:04.1f}s"
        return f"{s:.3f}s"
