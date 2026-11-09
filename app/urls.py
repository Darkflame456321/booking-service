from django.urls import path
from drf_spectacular.renderers import OpenApiJsonRenderer
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from app import views

urlpatterns = [
    path("rooms/create", views.create_room),
    path("rooms/delete", views.delete_room),
    path("rooms/list", views.list_rooms),
    path("bookings/create", views.create_booking),
    path("bookings/delete", views.delete_booking),
    path("bookings/list", views.list_bookings),
    path("healthz", views.health),
    path(
        "openapi.json",
        SpectacularAPIView.as_view(renderer_classes=[OpenApiJsonRenderer]),
        name="schema",
    ),
    path("docs", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

handler400 = "app.middleware.bad_request"
handler404 = "app.middleware.not_found"
handler500 = "app.middleware.server_error"
