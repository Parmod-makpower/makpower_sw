import io
import pandas as pd
from django.http import FileResponse
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from openpyxl import Workbook

from .models import CargoDetails
from .serializers import CargoDetailsSerializer

User = get_user_model()

class CargoDetailsViewSet(viewsets.ModelViewSet):
    serializer_class = CargoDetailsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # अगर ADMIN login है → सभी cargo दिखाओ
        if user.role == "ADMIN":
            return CargoDetails.objects.all().order_by('-id')

        # अगर CRM login है → सिर्फ उसी CRM के SS users के cargo दिखाओ
        if user.role == "CRM":
            ss_users = User.objects.filter(created_by=user, role="SS")
            return CargoDetails.objects.filter(user__in=ss_users).order_by('-id')

        # अगर SS login है → सिर्फ अपने cargo दिखाओ
        return CargoDetails.objects.filter(user=user).order_by('-id')

    def perform_create(self, serializer):
        serializer.save()

    # 🧾 Custom API: Bulk Excel Upload
    @action(detail=False, methods=['post'], url_path='upload-excel')
    def upload_excel(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "कोई फ़ाइल अपलोड नहीं की गई।"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_excel(file)
        except Exception as e:
            return Response({"error": f"फ़ाइल पढ़ने में त्रुटि: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        required_cols = ['user', 'cargo_name', 'cargo_mobile_number', 'cargo_location', 'parcel_size']
        for col in required_cols:
            if col not in df.columns:
                return Response({"error": f"Missing column: {col}"}, status=status.HTTP_400_BAD_REQUEST)

        results = {"created": 0, "updated": 0, "skipped": 0}

        for _, row in df.iterrows():
            user_id = row.get('user')
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                results["skipped"] += 1
                continue

            cargo_data = {
                "cargo_name": row.get('cargo_name', ''),
                "cargo_mobile_number": row.get('cargo_mobile_number', ''),
                "cargo_location": row.get('cargo_location', ''),
                "parcel_size": row.get('parcel_size', ''),
            }

            existing = CargoDetails.objects.filter(user=user).first()
            if existing:
                for field, value in cargo_data.items():
                    setattr(existing, field, value)
                existing.save()
                results["updated"] += 1
            else:
                CargoDetails.objects.create(user=user, **cargo_data)
                results["created"] += 1

        return Response({"message": "Upload completed", "results": results}, status=status.HTTP_200_OK)

    # 🧩 Excel Download Template API
    @action(detail=False, methods=['get'], url_path='download-template')
    def download_template(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = "CargoDetailsTemplate"

        headers = ['user', 'cargo_name', 'cargo_mobile_number', 'cargo_location', 'parcel_size']
        ws.append(headers)
        ws.append(["1", "Example Cargo", "9876543210", "Delhi", "Medium"])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = FileResponse(buffer, as_attachment=True, filename="CargoDetailsTemplate.xlsx")
        return response
