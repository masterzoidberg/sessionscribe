"""
SessionManager for managing multiple concurrent CaptureSession instances.
Replaces global _capture state with thread-safe session management.
"""

import asyncio
from typing import Dict, Optional, List
import logging
from .session import CaptureSession, SessionState

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages multiple concurrent capture sessions."""
    
    def __init__(self):
        self._sessions: Dict[str, CaptureSession] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_monitoring()
    
    async def get_or_create_session(self, session_id: str, config: Dict) -> CaptureSession:
        """Get existing session or create new one."""
        async with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                logger.info(f"Retrieved existing session {session_id} (state: {session.state})")
                return session
            
            session = CaptureSession(session_id, config)
            self._sessions[session_id] = session
            logger.info(f"Created new session {session_id}")
            return session
    
    async def get_session(self, session_id: str) -> Optional[CaptureSession]:
        """Get existing session by ID."""
        async with self._lock:
            return self._sessions.get(session_id)
    
    async def remove_session(self, session_id: str) -> bool:
        """Remove and cleanup session."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found for removal")
                return False
            
            # Stop and cleanup session
            if session.is_active:
                await session.stop()
            await session.cleanup()
            
            # Remove from manager
            del self._sessions[session_id]
            logger.info(f"Removed session {session_id}")
            return True
    
    async def list_sessions(self) -> List[Dict]:
        """List all sessions with their info."""
        async with self._lock:
            return [session.get_info() for session in self._sessions.values()]
    
    async def get_active_sessions(self) -> List[CaptureSession]:
        """Get all currently active sessions."""
        async with self._lock:
            return [s for s in self._sessions.values() if s.is_active]
    
    async def stop_all_sessions(self) -> int:
        """Stop all active sessions. Returns count of sessions stopped."""
        sessions_to_stop = await self.get_active_sessions()
        stopped_count = 0
        
        for session in sessions_to_stop:
            try:
                if await session.stop():
                    stopped_count += 1
            except Exception as e:
                logger.error(f"Error stopping session {session.session_id}: {e}")
        
        logger.info(f"Stopped {stopped_count} of {len(sessions_to_stop)} active sessions")
        return stopped_count
    
    async def cleanup_inactive_sessions(self) -> int:
        """Remove sessions that are stopped or in error state."""
        async with self._lock:
            to_remove = []
            for session_id, session in self._sessions.items():
                if session.state in [SessionState.STOPPED, SessionState.ERROR]:
                    # Check if session has been inactive for more than 5 minutes
                    if session.stopped_at and (asyncio.get_event_loop().time() - session.stopped_at) > 300:
                        to_remove.append(session_id)
            
            # Remove inactive sessions
            for session_id in to_remove:
                session = self._sessions[session_id]
                await session.cleanup()
                del self._sessions[session_id]
                logger.info(f"Cleaned up inactive session {session_id}")
            
            return len(to_remove)
    
    def _start_cleanup_monitoring(self):
        """Start background task for periodic cleanup."""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(300)  # 5 minutes
                    cleaned = await self.cleanup_inactive_sessions()
                    if cleaned > 0:
                        logger.info(f"Cleaned up {cleaned} inactive sessions")
                except Exception as e:
                    logger.error(f"Error in cleanup loop: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def shutdown(self):
        """Shutdown manager and cleanup all sessions."""
        logger.info("Shutting down session manager...")
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Stop and cleanup all sessions
        await self.stop_all_sessions()
        
        async with self._lock:
            session_ids = list(self._sessions.keys())
            for session_id in session_ids:
                session = self._sessions[session_id]
                await session.cleanup()
                del self._sessions[session_id]
        
        logger.info(f"Session manager shutdown complete. Cleaned up {len(session_ids)} sessions.")
    
    def get_stats(self) -> Dict:
        """Get manager statistics."""
        states = {}
        active_count = 0
        
        for session in self._sessions.values():
            state = session.state.value
            states[state] = states.get(state, 0) + 1
            if session.is_active:
                active_count += 1
        
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": active_count,
            "session_states": states,
            "uptime": asyncio.get_event_loop().time()
        }


# Global session manager instance
session_manager = SessionManager()