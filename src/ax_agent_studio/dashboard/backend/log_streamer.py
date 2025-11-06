"""
Log Streamer
WebSocket streaming of monitor logs
"""

import asyncio
from pathlib import Path

import aiofiles
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect


class LogStreamer:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    async def stream_logs(self, websocket: WebSocket, monitor_id: str):
        """Stream logs for a specific monitor via WebSocket"""
        try:
            log_file = self.log_dir / f"{monitor_id}.log"

            if not log_file.exists():
                await websocket.send_json(
                    {"type": "error", "message": f"Log file not found for monitor {monitor_id}"}
                )
                return

            # Send existing logs first
            try:
                async with aiofiles.open(log_file, "r", encoding="utf-8", errors="replace") as f:
                    content = await f.read()
                    if content:
                        await websocket.send_json(
                            {"type": "log", "monitor_id": monitor_id, "content": content}
                        )
            except Exception as e:
                await websocket.send_json(
                    {"type": "error", "message": f"Error reading log file: {e}"}
                )
                return

            # Tail new logs
            await self._tail_log_file(websocket, log_file, monitor_id)
        except WebSocketDisconnect:
            # Client disconnected - exit quietly
            return

    async def stream_all_logs(self, websocket: WebSocket):
        """Stream logs from all monitors via WebSocket"""
        try:
            # Get all log files
            log_files = list(self.log_dir.glob("*.log"))

            if not log_files:
                await websocket.send_json({"type": "info", "message": "No log files found"})

            # Send existing logs from all files
            for log_file in log_files:
                try:
                    monitor_id = log_file.stem
                    async with aiofiles.open(
                        log_file, "r", encoding="utf-8", errors="replace"
                    ) as f:
                        content = await f.read()
                        if content:
                            await websocket.send_json(
                                {"type": "log", "monitor_id": monitor_id, "content": content}
                            )
                except Exception as e:
                    print(f"Error reading {log_file}: {e}")

            # Tail all log files concurrently
            tasks = [
                self._tail_log_file(websocket, log_file, log_file.stem) for log_file in log_files
            ]

            await asyncio.gather(*tasks, return_exceptions=True)
        except WebSocketDisconnect:
            # Client disconnected - exit quietly
            return

    async def _tail_log_file(self, websocket: WebSocket, log_file: Path, monitor_id: str):
        """Tail a log file and send new lines via WebSocket"""
        import os

        # Wait for file to exist (up to 2 seconds)
        wait_attempts = 20
        for _ in range(wait_attempts):
            if log_file.exists():
                break
            await asyncio.sleep(0.1)

        # If file still doesn't exist, silently skip it
        if not log_file.exists():
            return

        try:
            async with aiofiles.open(log_file, "r", encoding="utf-8", errors="replace") as f:
                # Seek to end
                await f.seek(0, 2)
                last_pos = await f.tell()
                truncation_logged = False  # Track if we've logged truncation

                while True:
                    # Check if file still exists
                    if not log_file.exists():
                        return

                    # Check if file was truncated (cleared)
                    current_size = os.path.getsize(log_file)
                    if current_size < last_pos:
                        # File was truncated, reset to beginning
                        await f.seek(0)
                        last_pos = 0
                        # Only log once per truncation cycle
                        if not truncation_logged:
                            print(f"Detected truncation of {log_file}, resetting position")
                            truncation_logged = True
                    else:
                        # Reset flag when file size is normal
                        truncation_logged = False

                    line = await f.readline()

                    if line:
                        # New content available
                        await websocket.send_json(
                            {"type": "log", "monitor_id": monitor_id, "content": line}
                        )
                        last_pos = await f.tell()
                    else:
                        # No new content, wait a bit
                        await asyncio.sleep(0.1)

        except FileNotFoundError:
            # File was deleted, silently exit
            return
        except asyncio.CancelledError:
            # Task cancelled during shutdown - exit quietly
            return
        except WebSocketDisconnect:
            # Client disconnected (browser closed, network issue) - exit quietly
            return
        except Exception as e:
            # Only print non-file-related errors
            error_msg = str(e) or repr(e)
            if "No such file or directory" not in error_msg:
                print(f"Error tailing {log_file}: {type(e).__name__}: {error_msg}")
                import traceback

                traceback.print_exc()
