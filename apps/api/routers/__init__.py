from apps.api.routers.auth import router as auth_router
from apps.api.routers.chat import router as chat_router
from apps.api.routers.multimodal import router as multimodal_router
from apps.api.routers.memory import router as memory_router
from apps.api.routers.system import router as system_router
from apps.api.routers.keys import router as keys_router

__all__ = [
    "auth_router",
    "chat_router",
    "multimodal_router",
    "memory_router",
    "system_router",
    "keys_router",
]
