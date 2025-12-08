from django.urls import path
from .views import PartyOrdersView

urlpatterns = [
    path("party-orders/<int:party_id>/", PartyOrdersView.as_view(), name="party-orders"),
]
