
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView, ListAPIView
from .models import CRMVerifiedOrder, SSOrder
from .serializers import CRMVerifiedOrderSerializer, SSOrderSerializer, CRMVerifiedOrderDetailSerializer, CRMVerifiedOrderListSerializer



class SSOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role != 'SS':
            return Response({'detail': 'Only SS can place orders'}, status=403)

        data = request.data.copy()
        data['ss'] = user.id
        data['crm'] = user.crm.id if user.crm else None  # linked CRM
        data['party_name'] = user.party_name

        serializer = SSOrderSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Order placed successfully', 'order': serializer.data}, status=201)
        return Response(serializer.errors, status=400)

# ✅ CRM creates or updates verified copy
class CRMVerifiedOrderCreateView(CreateAPIView):
    serializer_class = CRMVerifiedOrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(verified_by=self.request.user)

# ✅ CRM updates verified copy
class CRMVerifiedOrderUpdateView(RetrieveUpdateAPIView):
    queryset = CRMVerifiedOrder.objects.all()
    serializer_class = CRMVerifiedOrderSerializer
    permission_classes = [IsAuthenticated]

# ✅ CRM list its assigned SSOrders (without verified copy yet)
class UnverifiedSSOrdersList(ListAPIView):
    serializer_class = SSOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return SSOrder.objects.filter(crm=user).exclude(verified_order__isnull=False).order_by("-placed_at")


class CRMOrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'

class CRMVerifiedOrderHistoryView(ListAPIView):
    serializer_class = CRMVerifiedOrderListSerializer  # ✅ changed serializer
    permission_classes = [IsAuthenticated]
    pagination_class = CRMOrderPagination

    def get_queryset(self):
        user = self.request.user
        queryset = CRMVerifiedOrder.objects.select_related("ss_order").filter(
            verified_by=user
        ).order_by("-verified_at")

        status = self.request.query_params.get("status")
        start_date = self.request.query_params.get("start")
        end_date = self.request.query_params.get("end")

        if status:
            queryset = queryset.filter(status=status.upper())
        if start_date:
            queryset = queryset.filter(verified_at__date__gte=parse_date(start_date))
        if end_date:
            queryset = queryset.filter(verified_at__date__lte=parse_date(end_date))

        return queryset

class CRMVerifiedOrderDetailView(RetrieveAPIView):
    queryset = CRMVerifiedOrder.objects.all()
    serializer_class = CRMVerifiedOrderDetailSerializer
    permission_classes = [IsAuthenticated]

# from django.utils.dateparse import parse_date
# from rest_framework.generics import ListAPIView
from .serializers import AdminVerifiedOrderListSerializer
# from .models import CRMVerifiedOrder
# from .serializers import CRMOrderPagination
# from rest_framework.permissions import IsAuthenticated

class AdminVerifiedOrderHistoryView(ListAPIView):
    serializer_class = AdminVerifiedOrderListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CRMOrderPagination

    def get_queryset(self):
        queryset = CRMVerifiedOrder.objects.select_related("ss_order", "verified_by").all().order_by("-verified_at")
        status = self.request.query_params.get("status")
        crm = self.request.query_params.get("crm")
        start_date = self.request.query_params.get("start")
        end_date = self.request.query_params.get("end")

        if status:
            queryset = queryset.filter(status=status.upper())
        if crm:
            queryset = queryset.filter(verified_by_id=crm)
        if start_date:
            queryset = queryset.filter(verified_at__date__gte=parse_date(start_date))
        if end_date:
            queryset = queryset.filter(verified_at__date__lte=parse_date(end_date))

        return queryset
