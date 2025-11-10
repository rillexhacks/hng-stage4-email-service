import time
from enum import Enum
from typing import Callable, Any, Union
import logging
import asyncio

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    pass


class CircuitBreaker:

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 30,
        half_open_attempts: int = 1,
        name: str = "default",
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_attempts = half_open_attempts
        self.name = name

        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float = 0
        self.last_state_change_time: float = time.time()

        logger.info(
            f"Circuit breaker '{self.name}' initialized: "
            f"threshold={failure_threshold}, timeout={timeout}s"
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:

        self._check_circuit_state()
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:

        self._check_circuit_state()
        try:
            # Handle both async and sync functions
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _check_circuit_state(self):

        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.timeout:
                self._transition_to_half_open()
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Retry after {self.timeout - (time.time() - self.last_failure_time):.1f}s"
                )

    def _on_success(self):

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"Circuit breaker '{self.name}': Success in HALF_OPEN "
                f"({self.success_count}/{self.half_open_attempts})"
            )

            # If enough successes, close the circuit
            if self.success_count >= self.half_open_attempts:
                self._transition_to_closed()
        else:
            # Reset failure count on success in CLOSED state
            self.failure_count = 0

    def _on_failure(self):

        self.failure_count += 1
        self.last_failure_time = time.time()

        logger.warning(
            f"Circuit breaker '{self.name}': Failure recorded "
            f"({self.failure_count}/{self.failure_threshold})"
        )

        # Transition to OPEN if threshold exceeded
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()

        # Transition back to OPEN from HALF_OPEN on failure
        elif self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()

    def _transition_to_open(self):

        self.state = CircuitState.OPEN
        self.last_state_change_time = time.time()
        logger.error(
            f" Circuit breaker '{self.name}' OPENED. "
            f"Service appears to be down. Waiting {self.timeout}s before retry."
        )

    def _transition_to_half_open(self):

        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.failure_count = 0
        self.last_state_change_time = time.time()
        logger.info(
            f" Circuit breaker '{self.name}' HALF_OPEN. " f"Testing service recovery..."
        )

    def _transition_to_closed(self):

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change_time = time.time()
        logger.info(
            f" Circuit breaker '{self.name}' CLOSED. "
            f"Service recovered successfully."
        )

    def get_state(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_state_change_time": self.last_state_change_time,
            "uptime_seconds": time.time() - self.last_state_change_time,
        }

    def reset(self):

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")
