from rest_framework import viewsets, permissions
from .models import CargoDetails
from .serializers import CargoDetailsSerializer

class CargoDetailsViewSet(viewsets.ModelViewSet):
    queryset = CargoDetails.objects.all().order_by('-id')
    serializer_class = CargoDetailsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # ✅ frontend se bheji hui user id use karega
        serializer.save()
