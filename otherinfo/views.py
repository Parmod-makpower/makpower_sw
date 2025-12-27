# views.py
from rest_framework import viewsets, permissions
from .models import SamplingSheet, NotInStockReport
from .serializers import SamplingSheetSerializer, NotInStoctSerializer

class SamplingSheetViewSet(viewsets.ModelViewSet):
    queryset = SamplingSheet.objects.all().order_by("party_name")
    serializer_class = SamplingSheetSerializer
    permission_classes = [permissions.IsAuthenticated]

class NotInStockViewSet(viewsets.ModelViewSet):
    serializer_class = NotInStoctSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = NotInStockReport.objects.all().order_by("party_name")

        # ✅ Admin → all data
        if user.role == "ADMIN":
            return qs

        # ✅ CRM → initials based filtering
        if user.role == "CRM" and user.name:
            # Ajit Mishra → AM
            parts = user.name.strip().split()
            initials = "".join(p[0] for p in parts).upper()

            return qs.filter(order_no__icontains=initials)

        # ❌ Baaki roles ko kuch nahi
        return qs.none()
