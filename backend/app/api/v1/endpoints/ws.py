import asyncio
import json
import logging
import uuid
import redis.asyncio as redis
from redis.exceptions import ConnectionError, RedisError
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
from app.core.config import settings
from app.core.auth import AuthProvider

logger = logging.getLogger(__name__)
router = APIRouter()

# PHASE 4: REDIS PUB/SUB WEBSOCKET SYNC
# Distributed event bus for multi-instance deployment.
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class DistributedConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.pubsub = redis_client.pubsub()
        self.listener_task = None

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
            try:
                # Subscribe to the user's specific channel
                await self.pubsub.subscribe(f"user_events:{user_id}")
            except (ConnectionError, RedisError) as e:
                logger.warning(f"Redis unavailable for subscribe: {e}. Falling back to in-memory only.")
        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected via WS. Active sessions on this instance: {len(self.active_connections[user_id])}")

        # Start background listener if not already running
        if self.listener_task is None or self.listener_task.done():
            self.listener_task = asyncio.create_task(self._listen_to_redis())

    async def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                try:
                    # Unsubscribe when no active sessions remain on this instance
                    await self.pubsub.unsubscribe(f"user_events:{user_id}")
                except (ConnectionError, RedisError):
                    pass

    async def broadcast_to_user(self, user_id: str, message: dict):
        """Publish event to Redis so ALL instances receive it. Fallback to in-memory."""
        try:
            await redis_client.publish(f"user_events:{user_id}", json.dumps(message))
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis unavailable for publish: {e}. Falling back to in-memory broadcast.")
            if user_id in self.active_connections:
                for connection in self.active_connections[user_id]:
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        logger.error(f"Error sending to WS client (fallback): {e}")

    async def _listen_to_redis(self):
        """Background task running on every instance to receive Redis messages and push to local WS clients."""
        while True:
            try:
                async for message in self.pubsub.listen():
                    if message['type'] == 'message':
                        channel = message['channel']
                        user_id = channel.split(":")[1]
                        data = json.loads(message['data'])
                        
                        if user_id in self.active_connections:
                            for connection in self.active_connections[user_id]:
                                try:
                                    await connection.send_json(data)
                                except Exception as e:
                                    logger.error(f"Error sending to WS client: {e}")
            except (ConnectionError, RedisError) as e:
                logger.error(f"Redis Pub/Sub listener failed: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Redis Pub/Sub listener critical failure: {e}")
                await asyncio.sleep(5)


manager = DistributedConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    PHASE 3: WEBSOCKET COOKIE AUTH
    Realtime WebSocket Gateway backed by Redis Pub/Sub, authenticated securely via HttpOnly cookies.
    """
    token = websocket.cookies.get("token")
    if not token:
        logger.warning("WebSocket connection rejected: No secure cookie found.")
        await websocket.close(code=1008)
        return
        
    try:
        user = AuthProvider.verify_token(token)
        user_id = str(user["id"])
    except Exception:
        logger.warning("WebSocket connection rejected: Invalid secure cookie.")
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive and handle client pings
            data = await websocket.receive_text()
            await manager.broadcast_to_user(user_id, {"type": "ack", "msg": "Ping received"})
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WS error: {e}")
        await manager.disconnect(websocket, user_id)
