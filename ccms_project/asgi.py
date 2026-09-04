"""
ASGI config for ccms_project project.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ccms_project.settings')

# Coba gunakan Channels jika tersedia
try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    import core.routing
    application = ProtocolTypeRouter({
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(
                core.routing.websocket_urlpatterns
            )
        ),
    })
except (ImportError, AttributeError):
    # Fallback ke aplikasi ASGI normal jika Channels tidak tersedia
    application = get_asgi_application()
