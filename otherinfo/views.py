# views.py
from rest_framework import viewsets, permissions
from .models import SamplingSheet, NotInStockReport, Mahotsav
from .serializers import SamplingSheetSerializer, NotInStoctSerializer, MahotsavSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from otherinfo.sync import (
    sync_sampling_sheet,
    sync_not_in_stock,
    sync_mahotsav_sheet,
)

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


class MahotsavViewSet(viewsets.ModelViewSet):
    queryset = Mahotsav.objects.all().order_by("party_name")
    serializer_class = MahotsavSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(["POST"])
def run_scheduler_now(request):
    job_type = request.data.get("type")

    try:
        if job_type == "sampling":
            sync_sampling_sheet()

        elif job_type == "not_in_stock":
            sync_not_in_stock()

        elif job_type == "mahotsav":
            sync_mahotsav_sheet()

        else:
            return Response(
                {"error": "Invalid scheduler type"},
                status=400
            )

        return Response({
            "success": True,
            "message": f"{job_type} sync completed"
        })

    except Exception as e:
        return Response({
            "success": False,
            "error": str(e)
        }, status=500)
    
