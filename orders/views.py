from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import SSOrder, SSOrderItem,CRMVerifiedOrderItem, CRMVerifiedOrder, Product
from products.models import Product
from django.contrib.auth import get_user_model
from .serializers import SSOrderSerializer,SS_to_CRM_Orders, CRMVerifiedOrderSerializer, CRMVerifiedOrderListSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django.shortcuts import get_object_or_404
from django.db.models import Q
from decimal import Decimal
from .pagination import StandardResultsSetPagination


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


class SSOrderHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        orders = SSOrder.objects.filter(ss_user=user).select_related(
            "ss_user", "assigned_crm"
        ).prefetch_related("items__product").order_by("-created_at")[:20]

        serializer = SSOrderSerializer(orders, many=True)
        return Response({"results": serializer.data})  # ✅ अब results key आएगी


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
  
 
class CRMOrderListView(ListAPIView):
    serializer_class = SS_to_CRM_Orders
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            SSOrder.objects.filter(assigned_crm=user)
            .exclude(crm_verified_versions__isnull=False)   # already verified हटाना
            .select_related("ss_user", "assigned_crm")      # foreign keys optimize
            .prefetch_related("items__product")             # items + product optimize
            .order_by("-created_at")
        )


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


class CRMVerifiedOrderHistoryView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CRMVerifiedOrderListSerializer
    pagination_class = StandardResultsSetPagination


    def get_queryset(self):
        user = self.request.user
        qs = CRMVerifiedOrder.objects.all()
        # Admin can see all; CRM sees only their own
        if not (getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)):
           qs = qs.filter(crm_user=user)


        # Filters
        status_param = self.request.query_params.get('status')
        q = self.request.query_params.get('q')
        start_date = self.request.query_params.get('start_date') # YYYY-MM-DD
        end_date = self.request.query_params.get('end_date')


        if status_param:
         qs = qs.filter(status=status_param)
        if start_date:
         qs = qs.filter(verified_at__date__gte=start_date)
        if end_date:
         qs = qs.filter(verified_at__date__lte=end_date)
        if q:
         qs = qs.filter(
            Q(original_order__order_id__icontains=q) |
            Q(original_order__ss_user__party_name__icontains=q) |
            Q(original_order__ss_user__name__icontains=q)
        )


        return (
            qs.select_related('original_order', 'crm_user', 'original_order__ss_user')
            .prefetch_related('items__product')
            .order_by('-verified_at')
            )

    
class CRMVerifiedOrderCompareView(APIView):
    def get(self, request, crm_order_id):
        crm_order = get_object_or_404(
            CRMVerifiedOrder.objects.select_related('original_order', 'crm_user', 'original_order__ss_user')
            .prefetch_related('items__product', 'original_order__items__product'),
            id=crm_order_id,
        )

        ss_order = crm_order.original_order  # ✅ सही field use किया

        ss_items = {i.product_id: i for i in ss_order.items.all()} if ss_order else {}
        crm_items = {i.product_id: i for i in crm_order.items.all()}

        product_ids = set(ss_items.keys()) | set(crm_items.keys())

        compare_rows = []
        for pid in product_ids:
            ss_it = ss_items.get(pid)
            crm_it = crm_items.get(pid)

            # ✅ Product Name Safe
            if ss_it and ss_it.product:
                product_name = ss_it.product.product_name
            elif crm_it and crm_it.product:
                product_name = crm_it.product.product_name
            else:
                product_name = "Unknown Product"

            ss_qty = ss_it.quantity if ss_it else 0
            crm_qty = crm_it.quantity if crm_it else 0
            ss_price = Decimal(ss_it.price) if ss_it else Decimal("0")
            crm_price = Decimal(crm_it.price) if crm_it else Decimal("0")

            compare_rows.append({
                "product": pid,
                "product_name": product_name,
                "ss_qty": ss_qty,
                "crm_qty": crm_qty,
                "qty_diff": int(crm_qty) - int(ss_qty),
                "ss_price": ss_price,
                "crm_price": crm_price,
                "price_diff": crm_price - ss_price,
                "ss_is_scheme_item": bool(getattr(ss_it, "is_scheme_item", False)),
            })

        ss_total = Decimal(ss_order.total_amount or 0) if ss_order else Decimal("0")
        crm_total = Decimal(crm_order.total_amount or 0)

        return Response({
            "order_id": ss_order.order_id if ss_order else None,
            "ss": {
                "id": ss_order.id if ss_order else None,
                "order_id": ss_order.order_id if ss_order else None,
                "ss_party_name": ss_order.ss_user.party_name if ss_order and ss_order.ss_user else None,
                "ss_user_name": ss_order.ss_user.name if ss_order and ss_order.ss_user else None,
                "created_at": ss_order.created_at if ss_order else None,
                "total_amount": ss_order.total_amount if ss_order else 0,
                "items": [
                    {
                        "product": i.product_id,
                        "product_name": i.product.product_name if i.product else "",
                        "quantity": i.quantity,
                        "price": i.price,
                    }
                    for i in ss_order.items.all()
                ] if ss_order else [],
            },
            "crm": {
                "id": crm_order.id,
                # ✅ username → name or mobile or party_name
                "crm_name": (
                    crm_order.crm_user.name
                    or crm_order.crm_user.party_name
                    or crm_order.crm_user.mobile
                    if crm_order.crm_user else None
                ),
                "verified_at": crm_order.verified_at,
                "status": crm_order.status,
                "notes": crm_order.notes,
                "total_amount": crm_order.total_amount,
                "items": [
                    {
                        "product": i.product_id,
                        "product_name": i.product.product_name if i.product else "",
                        "quantity": i.quantity,
                        "price": i.price,
                    }
                    for i in crm_order.items.all()
                ],
            },
            "compare_items": compare_rows,
            "totals": {
                "ss_total": ss_total,
                "crm_total": crm_total,
                "amount_diff": crm_total - ss_total,
            },
        })

