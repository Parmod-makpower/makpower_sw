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


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import PassportCouponRecord
from .serializers import PassportLookupSerializer, CouponSubmitSerializer


class PassportLookupView(APIView):
    def get(self, request):
        passport_number = request.query_params.get("passport_number")

        if not passport_number:
            return Response(
                {"error": "passport_number required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            record = PassportCouponRecord.objects.get(
                passport_number=passport_number
            )
            serializer = PassportLookupSerializer(record)
            return Response(serializer.data)

        except PassportCouponRecord.DoesNotExist:
            return Response(
                {"error": "Passport not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


class CouponSubmitView(APIView):
    def post(self, request):
        serializer = CouponSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        passport_number = serializer.validated_data["passport_number"]
        coupon_number = serializer.validated_data["coupon_number"]

        try:
            record = PassportCouponRecord.objects.get(
                passport_number=passport_number
            )
            record.coupon_number = coupon_number
            record.save()

            return Response({"success": True})

        except PassportCouponRecord.DoesNotExist:
            return Response(
                {"error": "Passport not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
