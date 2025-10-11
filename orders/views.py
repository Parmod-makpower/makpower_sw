from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework import status as drf_status
from django.db import transaction
from .models import SSOrder, SSOrderItem,CRMVerifiedOrderItem, CRMVerifiedOrder, Product,DispatchOrder
from products.models import Product
from django.contrib.auth import get_user_model
from .serializers import SSOrderSerializer,SS_to_CRM_Orders, CRMVerifiedOrderSerializer, CRMVerifiedOrderListSerializer, SSOrderHistorySerializer,DispatchOrderSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch,Q
from .pagination import StandardResultsSetPagination
from .utils import send_whatsapp_template



from django.db import transaction
from orders.models import PendingOrderItemSnapshot
from products.utils import recalculate_virtual_stock
from products.models import Product


User = get_user_model()


class SSOrderCreateView(APIView):
    def post(self, request):
        data = request.data

        try:
            ss_user = User.objects.get(id=data['user_id'])
            crm_user = User.objects.get(id=data['crm_id'])
            total = data['total']
            items = data['items']
            scheme_items = data.get('eligibleSchemes', [])  # अब flat array

            # 🔹 नया Order बनाओ
            order = SSOrder.objects.create(
                ss_user=ss_user,
                assigned_crm=crm_user,
                total_amount=total,
            )

            # 🔹 Normal products add करो
            for item in items:
                product = Product.objects.get(product_id=item['id'])
                SSOrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    price=item['price'] or 0,
                    is_scheme_item=False,
                    ss_virtual_stock=item.get('ss_virtual_stock', getattr(product, 'stock_quantity', 0))
                )

            # 🔹 Scheme reward items add करो
            print("✅ Scheme Items Received:", scheme_items)  # debug log

            for reward in scheme_items:
                product_id = None

                # अगर product key integer है
                if isinstance(reward.get('product'), int):
                    product_id = reward['product']

                # अगर product key object है { id, name }
                elif isinstance(reward.get('product'), dict):
                    product_id = reward['product'].get('id')

                # fallback
                elif reward.get('product_id'):
                    product_id = reward['product_id']

                if not product_id:
                    print(f"⚠️ Skipped reward (no product_id): {reward}")
                    continue  # safety check

                try:
                    product = Product.objects.get(product_id=product_id)
                    SSOrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=reward.get('quantity', 0),
                        price=0,
                        is_scheme_item=True,
                    )
                except Product.DoesNotExist:
                    print(f"❌ Product not found for reward: {reward}")
                    continue

            # 🔹 CRM नंबर mapping
            crm_numbers = {
                2: "7678491163", # prince
                4: "9312093178", # Ankita
                7: "8595957195", # Ajit
                8: "9266877089", # Harish
                9: "9266767418", # Simran 
            }
            crm_number = crm_numbers.get(crm_user.id)

            # 🔹 WhatsApp Message भेजो
            if crm_number:
                template_name = "order_updation"  # Meta console template का नाम
                template_language = "EN"
                parameters = [
                    ss_user.party_name or ss_user.name,  # {{1}}
                    str(order.order_id),                 # {{2}}
                    str(order.total_amount)              # {{3}}
                ]
                send_whatsapp_template(crm_number, template_name, template_language, parameters)

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

        serializer = SSOrderHistorySerializer(orders, many=True)
        return Response({"results": serializer.data})  # ✅ अब results key आएगी
  

class CRMOrderListView(ListAPIView):
    serializer_class = SS_to_CRM_Orders
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            SSOrder.objects.filter(assigned_crm=user)
            .exclude(crm_verified_versions__isnull=False)
            .select_related("ss_user", "assigned_crm")
            .prefetch_related("items__product")
            .order_by("-created_at")
        )


class CRMOrderVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            crm_user = request.user
            data = request.data

            original_order = get_object_or_404(
                SSOrder, id=order_id, assigned_crm=crm_user
            )

            # Prevent duplicate verification
            if CRMVerifiedOrder.objects.filter(original_order=original_order).exists():
                return Response({"error": "Order already verified"}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                # Create CRM verification record
                crm_order = CRMVerifiedOrder.objects.create(
                    original_order=original_order,
                    crm_user=crm_user,
                    status=data["status"],
                    notes=data.get("notes", ""),
                    total_amount=data.get("total_amount", 0),
                )

                # Original SS items map
                ss_items = SSOrderItem.objects.filter(order=original_order).select_related("product")
                ss_map = {
                    i.product.product_id: {
                        "product_obj": i.product,
                        "quantity": i.quantity,
                        "price": i.price,
                    }
                    for i in ss_items
                }

                # If whole order rejected -> record items as rejected, remove snapshots, recalc
                if data["status"] == "REJECTED":
                    for pid, info in ss_map.items():
                        CRMVerifiedOrderItem.objects.create(
                            crm_order=crm_order,
                            product=info["product_obj"],
                            quantity=info["quantity"],
                            price=info["price"],
                            is_rejected=True,
                        )

                    # delete snapshots for this order (no reservation anymore)
                    pending_snapshots = PendingOrderItemSnapshot.objects.filter(order=original_order)
                    affected_products = [snap.product for snap in pending_snapshots]
                    pending_snapshots.delete()

                    for p in set(affected_products):
                        recalculate_virtual_stock(p)

                else:
                    # Partial / Full approval case
                    payload_items = data.get("items", [])
                    kept_products = set()
                    approved_map = {}  # product_id -> approved_qty
                    affected_products = set()

                    # create CRMVerifiedOrderItem for approved items
                    for item in payload_items:
                        product = Product.objects.get(product_id=item["product"])
                        qty = int(item.get("quantity", 0))
                        kept_products.add(product.product_id)
                        approved_map[product.product_id] = qty

                        ss_item = SSOrderItem.objects.get(order=original_order, product=product)

                        CRMVerifiedOrderItem.objects.create(
                            crm_order=crm_order,
                            product=product,
                            quantity=qty,
                            price=item.get("price", 0),
                            ss_virtual_stock=ss_item.ss_virtual_stock,  # ✅ add this
                            is_rejected=False,
                        )

                    # products removed by CRM are considered rejected
                    deleted_products = set(ss_map.keys()) - kept_products
                    for pid in deleted_products:
                        info = ss_map[pid]
                        CRMVerifiedOrderItem.objects.create(
                            crm_order=crm_order,
                            product=info["product_obj"],
                            quantity=info["quantity"],
                            price=info["price"],
                            ss_virtual_stock=info.get("ss_virtual_stock", 0),
                            is_rejected=True,
                        )

                    # Now update PendingOrderItemSnapshot to reflect approved quantities
                    #  - set snapshot.quantity = approved_qty for approved items
                    #  - delete snapshot for rejected items
                    for pid, approved_qty in approved_map.items():
                        prod_obj = ss_map.get(pid, {}).get("product_obj")
                        if not prod_obj:
                            # fallback if product was not in ss_map (rare)
                            prod_obj = Product.objects.get(product_id=pid)
                        PendingOrderItemSnapshot.objects.update_or_create(
                            order=original_order,
                            product=prod_obj,
                            defaults={"quantity": approved_qty},
                        )
                        affected_products.add(prod_obj)

                    for pid in deleted_products:
                        info = ss_map[pid]
                        PendingOrderItemSnapshot.objects.filter(order=original_order, product=info["product_obj"]).delete()
                        affected_products.add(info["product_obj"])

                    # Recalculate virtual stock for all affected products
                    for p in set(affected_products):
                        recalculate_virtual_stock(p)

                # Finally update order status
                original_order.status = data["status"]
                original_order.save(update_fields=["status"])

            return Response({
                "message": "Order verified successfully",
                "crm_order": CRMVerifiedOrderSerializer(crm_order).data,
            }, status=status.HTTP_201_CREATED)

        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            traceback.print_exc()
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
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        punched_param = self.request.query_params.get('punched')  # 🔹 new filter

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

        # 🔹 Handle punched filter
        if punched_param is not None:
            if punched_param.lower() == 'true':
                qs = qs.filter(punched=True)
            elif punched_param.lower() == 'false':
                qs = qs.filter(punched=False)
        else:
            # 🔹 Default: only show punched=False orders
            qs = qs.filter(punched=False)

        # Prefetch approved items
        non_rejected_prefetch = Prefetch(
            'items',
            queryset=CRMVerifiedOrderItem.objects.filter(is_rejected=False).select_related('product'),
            to_attr='approved_items_prefetched'
        )

        return (
            qs.select_related('original_order', 'crm_user', 'original_order__ss_user')
              .prefetch_related(non_rejected_prefetch)
              .order_by('-verified_at')
        )


class UpdateOrderStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        crm_order = get_object_or_404(CRMVerifiedOrder, pk=pk)
        new_status = request.data.get("status")
        notes = request.data.get("notes")

        if new_status not in ["HOLD", "APPROVED", "REJECTED"]:
            return Response({"detail": "Invalid status"}, status=drf_status.HTTP_400_BAD_REQUEST)

        crm_order.status = new_status
        crm_order.notes = notes if new_status in ["HOLD", "REJECTED"] else None
        crm_order.save(update_fields=["status", "notes"])

        ss_order = crm_order.original_order
        ss_order.status = new_status
        ss_order.notes = notes if new_status in ["HOLD", "REJECTED"] else None
        ss_order.save(update_fields=["status", "notes"])

        return Response({
            "detail": "Status updated successfully",
            "status": new_status,
            "notes": crm_order.notes
        })

    
@api_view(["GET"])
def get_orders_by_order_id(request, order_id):
    try:
        orders = DispatchOrder.objects.filter(order_id=order_id)
        
        if not orders.exists():
            return Response(
                {"message": "No orders found for this order_id"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DispatchOrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# orders/views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from products.utils import write_to_sheet
from orders.models import CRMVerifiedOrder
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
def punch_order_to_sheet(request):
    try:
        data = request.data

        # Extract required fields
        order_id = data.get("order_id")
        ss_party_name = data.get("ss_party_name")
        crm_name = data.get("crm_name")
        ss_id = data.get("id")
        items = data.get("items", [])

        # Validate input
        if not order_id or not items:
            return Response({"error": "Missing order_id or items"}, status=400)

        # Generate IST timestamp
        ist_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Prepare rows for Google Sheet
        rows = [
            [
                item.get("product_name", ""),
                item.get("quantity", 0),
                ss_party_name,
                ss_id,
                crm_name,
                item.get("id", ""),
                ist_timestamp,
                order_id,
            ]
            for item in items
        ]

        # ✅ Write to Google Sheet
        write_to_sheet(settings.SHEET_ID_NEW, "order_punch", rows)

        # ✅ Mark order as punched in DB
        updated_count = CRMVerifiedOrder.objects.filter(
            original_order__order_id=order_id
        ).update(punched=True)

        if updated_count == 0:
            logger.warning(f"No CRMVerifiedOrder found for order_id: {order_id}")
            return Response({"error": "No CRMVerifiedOrder found for this order_id"}, status=404)

        return Response({
            "success": True,
            "message": f"{len(rows)} rows written to sheet and order marked as punched"
        })

    except Exception as e:
        logger.error(f"Error in punch_order_to_sheet: {str(e)}", exc_info=True)
        return Response({"success": False, "error": "Internal server error"}, status=500)
