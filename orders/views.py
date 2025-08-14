from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import SSOrder, SSOrderItem,CRMVerifiedOrderItem, CRMVerifiedOrder
from products.models import Product
from django.contrib.auth import get_user_model
from .serializers import SSOrderSerializer, CRMVerifiedOrderSerializer, CRMVerifiedOrderHistorySerializer, CRMVerifiedOrderDetailSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, permissions
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django.shortcuts import get_object_or_404

User = get_user_model()

class SSOrderCreateView(APIView):
    def post(self, request):
        data = request.data
        
        try:
            ss_user = User.objects.get(id=data['user_id'])
            crm_user = User.objects.get(id=data['crm_id'])
            total = data['total']
            items = data['items']
            scheme_items = data.get('eligibleSchemes', [])

            order = SSOrder.objects.create(
                ss_user=ss_user,
                assigned_crm=crm_user,
                total_amount=total,
            )

            # Add selected products
            for item in items:
                product = Product.objects.get(product_id=item['id'])  
                SSOrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    price=item['price'] or 0,  
                    is_scheme_item=False,
                )

            # Add scheme reward items
            for scheme in scheme_items:
                for reward in scheme.get('rewards', []):
                    product_id = reward.get('product') or reward.get('product_id')
                    product = Product.objects.get(product_id=product_id) 
                    SSOrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=reward['quantity'],
                        price=0,
                        is_scheme_item=True,
                    )

            return Response({
                "message": "Order placed successfully.",
                "order": SSOrderSerializer(order).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print("❌ Exception occurred during order placement:")
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class SSOrderHistoryView(ListAPIView):
    serializer_class = SSOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return SSOrder.objects.filter(ss_user=user).order_by('-created_at')

class CRMOrderListView(ListAPIView):
    serializer_class = SSOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Exclude orders that already have any CRMVerifiedOrder (so CRM won't see verified ones)
        return SSOrder.objects.filter(assigned_crm=user).exclude(crm_verified_versions__isnull=False).order_by('-created_at')

class CRMOrderVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            crm_user = request.user
            data = request.data

            # make sure the order exists and is assigned to this CRM
            original_order = get_object_or_404(SSOrder, id=order_id, assigned_crm=crm_user)

            # prevent double verification (simple guard)
            if CRMVerifiedOrder.objects.filter(original_order=original_order).exists():
                return Response({"error": "Order already verified"}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                crm_order = CRMVerifiedOrder.objects.create(
                    original_order=original_order,
                    crm_user=crm_user,
                    status=data['status'],
                    notes=data.get('notes', ''),
                    total_amount=data.get('total_amount', 0)
                )

                # IMPORTANT: only save item lines if NOT rejected
                if data['status'] != 'REJECTED':
                    for item in data.get('items', []):
                        product = Product.objects.get(product_id=item['product'])
                        CRMVerifiedOrderItem.objects.create(
                            crm_order=crm_order,
                            product=product,
                            quantity=item['quantity'],
                            price=item.get('price', 0)
                        )

            return Response({
                "message": "Order verified successfully",
                "crm_order": CRMVerifiedOrderSerializer(crm_order).data
            }, status=status.HTTP_201_CREATED)

        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class SSOrderTrackView(RetrieveAPIView):
    serializer_class = SSOrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'order_id'

    def get_object(self):
        # Only owner (ss_user) can track their order
        user = self.request.user
        order = get_object_or_404(SSOrder, id=self.kwargs['order_id'], ss_user=user)
        return order



def _is_admin(user):
    # यदि आपके User मॉडल में role फील्ड है तो पहले वही चेक करें
    role = getattr(user, "role", None)
    if role and str(role).upper() == "ADMIN":
        return True
    # fallback: Django staff/superuser
    return bool(user.is_staff or user.is_superuser)

from rest_framework.pagination import PageNumberPagination

class CRMVerifiedOrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class CRMVerifiedOrdersList(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CRMVerifiedOrderHistorySerializer
    pagination_class = CRMVerifiedOrderPagination   # ✅ Pagination added

    def get_queryset(self):
        qs = CRMVerifiedOrder.objects.select_related("original_order", "crm_user")\
            .prefetch_related("items__product", "original_order__items__product")\
            .order_by('-verified_at')

        user = self.request.user

        # --- CRM filter (query param से) ---
        crm_id = self.request.query_params.get("crm_id")
        if crm_id:
            qs = qs.filter(crm_user_id=crm_id)

        # --- Date range filter ---
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date and end_date:
            qs = qs.filter(verified_at__date__range=[start_date, end_date])

        if _is_admin(user):
            return qs
        return qs.filter(crm_user=user)


class CRMVerifiedOrderUpdate(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CRMVerifiedOrderSerializer
    queryset = CRMVerifiedOrder.objects.all()

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user
        if _is_admin(user):
            return qs
        return qs.filter(crm_user=user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.notes = request.data.get("notes", instance.notes)
        instance.save()

        items_data = request.data.get("items", [])
        for item_data in items_data:
            try:
                item = instance.items.get(id=item_data["id"])
                item.quantity = item_data["quantity"]
                item.save()
            except CRMVerifiedOrderItem.DoesNotExist:
                pass

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class CRMVerifiedOrderDetail(generics.RetrieveAPIView):
    """
    एक ही response में:
    - SS का original order (items सहित)
    - CRM का verified order (items सहित)
    - compare list: product-wise SS_qty, CRM_qty, delta
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CRMVerifiedOrderDetailSerializer
    queryset = CRMVerifiedOrder.objects.select_related("original_order", "crm_user")\
        .prefetch_related("items__product", "original_order__items__product")

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_admin(user):
            return qs
        return qs.filter(crm_user=user)
