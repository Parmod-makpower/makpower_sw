# views.py
from rest_framework import viewsets, permissions
from .models import SamplingSheet
from .serializers import SamplingSheetSerializer

class SamplingSheetViewSet(viewsets.ModelViewSet):
    queryset = SamplingSheet.objects.all().order_by("party_name")
    serializer_class = SamplingSheetSerializer
    permission_classes = [permissions.IsAuthenticated]
