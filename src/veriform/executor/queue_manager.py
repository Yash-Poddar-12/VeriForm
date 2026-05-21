"""
veriform.executor.queue_manager
===============================
Background execution task queue system.
Abstracts asyncio.Queue for easy swap to Redis/Celery later.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable, Coroutine, Any, Optional

from veriform.config import settings
from veriform.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class TaskPayload:
    run_id: str
    target_url: str
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300

class TaskQueue:
    """In-memory async task queue for orchestrating background runs."""
    
    def __init__(self, concurrency: int = 2):
        self.queue: asyncio.Queue[TaskPayload] = asyncio.Queue()
        self.concurrency = concurrency
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._handler: Optional[Callable[[TaskPayload], Coroutine[Any, Any, None]]] = None

    def set_handler(self, handler: Callable[[TaskPayload], Coroutine[Any, Any, None]]) -> None:
        """Register the callback that processes tasks."""
        self._handler = handler

    async def push(self, payload: TaskPayload) -> None:
        """Enqueue a task."""
        await self.queue.put(payload)
        logger.info("Enqueued task for run_id=%s", payload.run_id)

    async def start(self) -> None:
        """Start worker loop."""
        if self._running:
            return
        
        if not self._handler:
            raise RuntimeError("TaskQueue started without a handler")
            
        self._running = True
        for i in range(self.concurrency):
            task = asyncio.create_task(self._worker_loop(i))
            self._workers.append(task)
            
        logger.info("TaskQueue started with %d workers", self.concurrency)

    async def stop(self) -> None:
        """Gracefully shutdown workers."""
        self._running = False
        # Cancel idle workers
        for worker in self._workers:
            worker.cancel()
            
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("TaskQueue stopped")

    async def _worker_loop(self, worker_id: int) -> None:
        logger.debug("Worker %d started", worker_id)
        while self._running:
            try:
                payload = await self.queue.get()
            except asyncio.CancelledError:
                break

            try:
                # Execution Isolation via asyncio.wait_for (timeout enforcement)
                await asyncio.wait_for(self._handler(payload), timeout=payload.timeout_seconds)
            except asyncio.TimeoutError:
                logger.error("Worker %d: Task %s timed out", worker_id, payload.run_id)
                await self._handle_retry(payload)
            except Exception as exc:
                logger.error("Worker %d: Task %s failed: %s", worker_id, payload.run_id, exc)
                await self._handle_retry(payload)
            finally:
                self.queue.task_done()
                
    async def _handle_retry(self, payload: TaskPayload) -> None:
        if payload.retry_count < payload.max_retries:
            payload.retry_count += 1
            logger.info("Retrying run_id=%s (attempt %d)", payload.run_id, payload.retry_count)
            await self.push(payload)
        else:
            logger.error("Max retries reached for run_id=%s. Failing task.", payload.run_id)
            from veriform.services.services import ExecutionService
            svc = ExecutionService()
            await svc.update_status(payload.run_id, "failed")

# Global queue singleton
task_queue = TaskQueue(concurrency=settings.max_concurrent_runs)
