from django.urls import path
from .views import CargoListCreateView,CargoBulkUploadView, GSTView

urlpatterns = [
    path("cargo/", CargoListCreateView.as_view(), name="cargo-list-create"),
    path("gst/", GSTView.as_view(), name="cargo-list-create"),
    path("cargo/bulk-upload/", CargoBulkUploadView.as_view()),
]