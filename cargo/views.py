from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from .models import Cargo
from .serializers import CargoSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.models import CustomUser


class CargoListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CargoSerializer

    def get_queryset(self):
        return Cargo.objects.select_related("party")

    def perform_create(self, serializer):
        serializer.save()


class CargoBulkUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        rows = request.data

        created_count = 0
        updated_count = 0
        error_rows = []

        for i, row in enumerate(rows):
            try:
                party_name = row.get("party_name")

                party = CustomUser.objects.filter(
                    party_name__iexact=party_name,
                    role="SS"
                ).first()

                if not party:
                    error_rows.append(f"Row {i+1}: Party not found")
                    continue

                obj, created = Cargo.objects.update_or_create(
                    party=party,  # 👈 unique condition
                    defaults={
                        "cargo_name": row.get("cargo_name"),
                        "parcel_size": row.get("parcel_size"),
                        "cargo_location": row.get("cargo_location"),
                        "mobile_number": row.get("mobile_number"),
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                error_rows.append(f"Row {i+1}: {str(e)}")

        return Response({
            "created": created_count,
            "updated": updated_count,
            "errors": error_rows
        })