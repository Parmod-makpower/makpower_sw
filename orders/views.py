
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.db import transaction
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone

from datetime import datetime, timedelta

from openpyxl import Workbook
import openpyxl
import logging

from rest_framework.parsers import MultiPartParser

from .models import (
    SSOrder,
    SSOrderItem,
    CRMVerifiedOrderItem,
    CRMVerifiedOrder,
    Product,
    DispatchOrder,
)

from orders.models import PendingOrderItemSnapshot

from .serializers import (
    SSOrderSerializer,
    SS_to_CRM_Orders,
    CRMVerifiedOrderSerializer,
    VerifiedOrderHistorysSerializer,
    VerifiedOrderDetailsSerializer,
    CombinedOrderTrackSerializer,
    SSOrderSerializerTrack,
    DispatchOrderSerializer,
    HROrderListSerializer,
)

from .utils import send_whatsapp_template

from products.utils import (
    recalculate_virtual_stock,
    write_to_sheet,
)

logger = logging.getLogger(__name__)
User = get_user_model()

# Order Create----------

class SSOrderCreateView(APIView):
    def post(self, request):
        data = request.data

        try:
            ss_user = User.objects.get(id=data['user_id'])
            crm_user = User.objects.get(id=data['crm_id'])
            total = data['total']
            items = data['items']
            scheme_items = data.get('eligibleSchemes', [])

            # ✅ Items को Tempered और Non-Tempered में बाँटें
            tempered_items = []
            non_tempered_items = []

            for item in items:
                product = Product.objects.get(product_id=item['id'])
                sub_category = getattr(product, "sub_category", "") or ""
                if "tempered" in sub_category.lower():
                    tempered_items.append(item)
                else:
                    non_tempered_items.append(item)

            # ✅ Helper function: order create + items insert
            def create_order(order_items, label="Normal"):
                if not order_items:
                    return None

                total_amt = sum(
                    (i['price'] or 0) * i['quantity'] for i in order_items
                )

                order = SSOrder.objects.create(
                    ss_user=ss_user,
                    assigned_crm=crm_user,
                    total_amount=total_amt,
                    note=f"{label} Order"  # optional tag for clarity
                )

                for item in order_items:
                    product = Product.objects.get(product_id=item['id'])
                    SSOrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item['quantity'],
                        price=item['price'] or 0,
                        is_scheme_item=False,
                        ss_virtual_stock=item.get('ss_virtual_stock', getattr(product, 'stock_quantity', 0))
                    )

                return order

            # ✅ Create two orders
            tempered_order = create_order(tempered_items, label="Tempered")
            normal_order = create_order(non_tempered_items, label="Accessories")

            # ✅ Scheme items — सिर्फ Non-Tempered order में add करो
            if normal_order and scheme_items:
                for reward in scheme_items:
                    product_id = (
                        reward.get('product_id') or
                        (reward.get('product', {}).get('id') if isinstance(reward.get('product'), dict) else reward.get('product'))
                    )
                    if not product_id:
                        continue

                    try:
                        product = Product.objects.get(product_id=product_id)
                        SSOrderItem.objects.create(
                            order=normal_order,
                            product=product,
                            quantity=reward.get('quantity', 0),
                            price=0,
                            is_scheme_item=True,
                            ss_virtual_stock=getattr(product, 'virtual_stock', getattr(product, 'stock_quantity', 0))
                        )
                    except Product.DoesNotExist:
                        continue

            # ✅ WhatsApp send (अब दोनों orders के लिए)
            crm_numbers = {
                2: "7678491163",
                4: "9312093178",
                7: "8595957195",
                8: "9266877089",
                9: "9266767418",
                133: "9306443566",
            }
            crm_number = crm_numbers.get(crm_user.id)
            if crm_number:
                template_name = "app_new_order"
                template_language = "EN"

                for each_order in [tempered_order, normal_order]:
                    if each_order:
                        parameters = [
                            ss_user.party_name or ss_user.name,
                            str(each_order.order_id),
                            str(each_order.total_amount)
                        ]
                        send_whatsapp_template(crm_number, template_name, template_language, parameters)


            # ✅ Response
            return Response({
                "message": "Orders placed successfully.",
                "orders": {
                    "tempered_order": SSOrderSerializer(tempered_order).data if tempered_order else None,
                    "normal_order": SSOrderSerializer(normal_order).data if normal_order else None,
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print("❌ Exception occurred during order placement:")
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class SimpleSSOrderCreateView(APIView):
    """
    Only creates empty order
    No products, no items
    """

    def post(self, request):
        try:
            ss_id = request.data.get("ss_id")
            crm_id = request.data.get("crm_id")
            note = request.data.get("note", "")

            if not ss_id or not crm_id:
                return Response(
                    {"error": "ss_id and crm_id are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            ss_user = User.objects.get(id=ss_id)
            crm_user = User.objects.get(id=crm_id)

            order = SSOrder.objects.create(
                ss_user=ss_user,
                assigned_crm=crm_user,
                total_amount=0,
                status="PENDING",
                note=note or "Empty Order"
            )

            return Response({
                "message": "Order created successfully",
                "order": SSOrderSerializer(order).data
            }, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            return Response(
                {"error": "Invalid SS or CRM"},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# Order Details Page --------------

class CRMOrderListView(ListAPIView):
    serializer_class = SS_to_CRM_Orders
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        status_filter = self.request.query_params.get("status", "PENDING")

        base_queryset = (
            SSOrder.objects
            .filter(status=status_filter)
            .exclude(crm_verified_versions__isnull=False)
            .select_related(
                "ss_user",
                "assigned_crm"
            )
            .prefetch_related(
                "items__product"
            )
            .order_by("-created_at")
        )

        # 🔹 Admin → all orders
        if user.is_staff or user.is_superuser:
            return base_queryset[:20]

        # 🔹 CRM → only assigned orders
        return base_queryset.filter(assigned_crm=user)[:25]

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
                return Response(
                    {"error": "Order already verified"}, status=status.HTTP_400_BAD_REQUEST
                )

            with transaction.atomic():
                # Create CRM verification record
                crm_order = CRMVerifiedOrder.objects.create(
                    original_order=original_order,
                    crm_user=crm_user,
                    status=data["status"],
                    dispatch_location=data.get("dispatch_location"),
                )

                # Original SS items map
                ss_items = SSOrderItem.objects.filter(order=original_order).select_related("product")
                ss_map = {
                    i.product.product_id: {
                        "product_obj": i.product,
                        "quantity": i.quantity,
                        "ss_virtual_stock": i.ss_virtual_stock,
                    }
                    for i in ss_items
                }

                # If whole order rejected -> mark items rejected
                if data["status"] == "REJECTED":
                    for pid, info in ss_map.items():
                        CRMVerifiedOrderItem.objects.create(
                            crm_order=crm_order,
                            product=info["product_obj"],
                            quantity=info["quantity"],
                            ss_virtual_stock=info.get("ss_virtual_stock", 0),
                            is_rejected=True,
                        )

                    # delete snapshots (no reservation anymore)
                    pending_snapshots = PendingOrderItemSnapshot.objects.filter(order=original_order)
                    affected_products = [snap.product for snap in pending_snapshots]
                    pending_snapshots.delete()

                    for p in set(affected_products):
                        recalculate_virtual_stock(p)

                else:
                    # Partial / Full approval
                    payload_items = data.get("items", [])
                    kept_products = set()
                    approved_map = {}
                    affected_products = set()

                    for item in payload_items:
                        product = Product.objects.get(product_id=item["product"])
                        try:
                            qty = int(item.get("quantity", 0))
                        except (TypeError, ValueError):
                            qty = 0

                        kept_products.add(product.product_id)
                        approved_map[product.product_id] = qty

                        ss_item = SSOrderItem.objects.filter(order=original_order, product=product).first()

                       

                        # ✅ अगर SSOrderItem नहीं मिला, तो product.virtual_stock का इस्तेमाल करो
                        if ss_item:
                            ss_virtual_stock_value = ss_item.ss_virtual_stock
                        else:
                            ss_virtual_stock_value = product.virtual_stock or 0

                        CRMVerifiedOrderItem.objects.create(
                            crm_order=crm_order,
                            product=product,
                            quantity=qty,
                           
                            ss_virtual_stock=ss_virtual_stock_value,
                            is_rejected=False,
                        )


                    # Products removed by CRM are considered rejected
                    deleted_products = set(ss_map.keys()) - kept_products
                    for pid in deleted_products:
                        info = ss_map[pid]
                        CRMVerifiedOrderItem.objects.create(
                            crm_order=crm_order,
                            product=info["product_obj"],
                            quantity=info["quantity"],
                            ss_virtual_stock=info.get("ss_virtual_stock", 0),
                            is_rejected=True,
                        )

                    # Update PendingOrderItemSnapshot
                    for pid, approved_qty in approved_map.items():
                        prod_obj = ss_map.get(pid, {}).get("product_obj")
                        if not prod_obj:
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

                # Update order status
                original_order.status = data["status"]
                original_order.save(update_fields=["status"])

            return Response(
                {
                    "message": "Order verified successfully",
                    "crm_order": CRMVerifiedOrderSerializer(crm_order).data,
                },
                status=status.HTTP_201_CREATED,
            )

        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# After Verify Order --------

class FinalOrderHistoryView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VerifiedOrderHistorysSerializer

    def get_queryset(self):
        user = self.request.user

        qs = CRMVerifiedOrder.objects.select_related(
            "original_order",
            "original_order__ss_user",
            "crm_user"
        )

        # ✅ User restriction
        if not user.is_staff and not user.is_superuser:
            qs = qs.filter(crm_user=user)

        # ✅ Query params
        q = self.request.query_params.get("q")
        party = self.request.query_params.get("party")
        punched = self.request.query_params.get("punched")
        from_date = self.request.query_params.get("from_date")
        to_date = self.request.query_params.get("to_date")

        # ✅ Search (order id / order code)
        if q:
            qs = qs.filter(
                Q(id__icontains=q) |
                Q(original_order__order_id__icontains=q)
            )

        # ✅ Party filter
        if party:
            qs = qs.filter(
                original_order__ss_user__party_name__icontains=party
            )

        # ✅ Date filter
        if from_date and to_date:
            qs = qs.filter(
                verified_at__date__range=[from_date, to_date]
            )

        # ✅ punched filter
        if punched is not None:
            qs = qs.filter(punched=(punched.lower() == "true"))

        # ✅ Always latest first
        return qs.order_by("-verified_at")[:50]  # max 50 records

class FinalOrderDetailsView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VerifiedOrderDetailsSerializer

    def get_object(self):
        user = self.request.user
        order_id = self.kwargs.get("order_id")  # ✅ URL se lo

        qs = CRMVerifiedOrder.objects.select_related(
            "original_order",
            "original_order__ss_user",
            "crm_user"
        ).prefetch_related("items")

        if not user.is_staff and not user.is_superuser:
            qs = qs.filter(crm_user=user)

        return get_object_or_404(qs, id=order_id)  # ✅ ID search

class AddItemToCRMVerifiedOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        crm_order = get_object_or_404(CRMVerifiedOrder, pk=pk)

        product_id = request.data.get("product_id")
        raw_qty = request.data.get("quantity")

        if not product_id or not raw_qty:
            return Response(
                {"error": "Product ID and quantity are required."},
                status=400
            )

        # ✅ SAFE quantity
        try:
            quantity = int(raw_qty)
        except (TypeError, ValueError):
            return Response({"error": "Invalid quantity."}, status=400)


        product = get_object_or_404(Product, product_id=product_id)

        # ✅ Prevent duplicate product
        if CRMVerifiedOrderItem.objects.filter(
            crm_order=crm_order, product=product
        ).exists():
            return Response(
                {"error": "This product is already added in this order."},
                status=400
            )

        # ✅ Stock logic
        ss_stock = getattr(product, "ss_virtual_stock", 0)
        virtual_stock = getattr(product, "virtual_stock", 0)

        new_item = CRMVerifiedOrderItem.objects.create(
            crm_order=crm_order,
            product=product,
            quantity=quantity,
            ss_virtual_stock=ss_stock if ss_stock > 0 else virtual_stock
        )

        return Response(
            {
                "message": "Product added successfully!",
                "item_id": new_item.id,
                "product_name": product.product_name,
                "quantity": quantity,
            },
            status=201
        )

@api_view(['POST'])
def punch_order_to_sheet(request):
    try:
        data = request.data

        order_id = data.get("order_id")
        ss_party_name = data.get("ss_party_name")
        crm_name = data.get("crm_name")
        ss_id = data.get("id")
        dispatch_location = data.get("dispatch_location", "")
        items = data.get("items", [])
        is_single_row = data.get("is_single_row", False)

        if not order_id or not items:
            return Response({"error": "Missing order_id or items"}, status=400)

        # 🔐 Bulk punch only → prevent double punch
        order_obj = None
        if not is_single_row:
            order_obj = CRMVerifiedOrder.objects.filter(
                original_order__order_id=order_id,
                punched=False
            ).first()

            if not order_obj:
                return Response(
                    {"error": "Order already punched"},
                    status=400
                )

        ist_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        rows = [
            [
                item.get("product_name", ""),
                int(item.get("quantity", 0)),
                ss_party_name,
                ss_id,
                crm_name,
                item.get("id", ""),
                ist_timestamp,
                order_id,
                dispatch_location,
            ]
            for item in items
        ]

        # ✅ Always write to sheet
        write_to_sheet(
            settings.SHEET_ID_NEW,
            "order_data_from_app",
            rows
        )

        # ✅ Mark punched ONLY for bulk punch
        if not is_single_row and order_obj:
            order_obj.punched = True
            order_obj.dispatch_location = dispatch_location
            order_obj.save(update_fields=["punched", "dispatch_location"])

        return Response({
            "success": True,
            "message": f"{len(rows)} rows punched successfully",
            "single_row": is_single_row
        })

    except Exception as e:
        logger.error("🚨 Error in punch_order_to_sheet", exc_info=True)
        return Response(
            {"success": False, "error": str(e)},
            status=500
        )



# Others Views ---------------------

class CRMOrderBulkDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        order_ids = request.data.get("order_ids", [])

        # ✅ ONLY ADMIN CAN DELETE
        if user.role != "ADMIN":
            return Response(
                {"error": "You are not allowed to delete orders."},
                status=status.HTTP_403_FORBIDDEN
            )

        if not order_ids:
            return Response(
                {"error": "No orders selected"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ ADMIN can delete ANY order
        orders = SSOrder.objects.filter(id__in=order_ids)

        if not orders.exists():
            return Response(
                {"error": "No valid orders found"},
                status=status.HTTP_404_NOT_FOUND
            )

        affected_products = []

        with transaction.atomic():
            for order in orders:
                snapshots = PendingOrderItemSnapshot.objects.filter(order=order)
                affected_products.extend([s.product for s in snapshots])
                snapshots.delete()
                order.delete()

            # ✅ Recalculate stock once per product
            for product in set(affected_products):
                recalculate_virtual_stock(product)

        return Response(
            {"message": f"{orders.count()} orders permanently deleted"},
            status=status.HTTP_200_OK
        )

@api_view(['POST'])
def hold_order(request, order_id):
    try:
        crm_user = request.user
        order = get_object_or_404(SSOrder, id=order_id, assigned_crm=crm_user)

        # वो snapshots लो जो पहले order verify/forward होने पर बने थे
        pending_snapshots = PendingOrderItemSnapshot.objects.filter(order=order)
        affected_products = [snap.product for snap in pending_snapshots]

        with transaction.atomic():

            # ✅ पहले snapshots delete — ये stock restore का trigger है
            pending_snapshots.delete()

            # ✅ हर product का virtual stock दोबारा calculate
            for p in set(affected_products):
                recalculate_virtual_stock(p)

            # ✅ Order status update
            order.status = "HOLD"
            order.notes = request.data.get("notes", order.notes)
            order.save()

        return Response(
            {"message": "Order put on HOLD and stock restored."},
            status=200
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"error": str(e)}, status=400)


@api_view(['POST'])
def reject_order(request, order_id):
    try:
        crm_user = request.user
        order = get_object_or_404(SSOrder, id=order_id, assigned_crm=crm_user)

        # वो snapshots लो जो पहले order verify/forward होने पर बने थे
        pending_snapshots = PendingOrderItemSnapshot.objects.filter(order=order)
        affected_products = [snap.product for snap in pending_snapshots]

        with transaction.atomic():

            # ✅ पहले snapshots delete — ये stock restore का trigger है
            pending_snapshots.delete()

            # ✅ हर product का virtual stock दोबारा calculate
            for p in set(affected_products):
                recalculate_virtual_stock(p)

            # ✅ Order status update
            order.status = "REJECTED"
            order.notes = request.data.get("notes", order.notes)
            order.save()

        return Response(
            {"message": "Order  Reject and stock restored."},
            status=200
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"error": str(e)}, status=400)



@api_view(["GET"])
def list_orders_by_role(request):
    user = request.user
    order_id = request.GET.get("order_id")
    party_name = request.GET.get("party_name")
    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")

    # 🟦 Base Query
    if user.role == "ADMIN":
        orders = SSOrder.objects.all()
    elif user.role == "CRM":
        orders = SSOrder.objects.filter(assigned_crm=user)
    elif user.role == "SS":
        orders = SSOrder.objects.filter(ss_user=user)
    else:
        orders = SSOrder.objects.none()

    # 🟦 Filters
    if order_id:
        orders = orders.filter(order_id__icontains=order_id)

    if party_name:
        orders = orders.filter(ss_user__party_name__icontains=party_name)

    if from_date:
        orders = orders.filter(created_at__date__gte=from_date)

    if to_date:
        orders = orders.filter(created_at__date__lte=to_date)

    # 🟦 Default limit (latest 50)
    if not (from_date or to_date or order_id or party_name):
        orders = orders.order_by("-created_at")[:30]
    else:
        orders = orders.order_by("-created_at")

    serializer = SSOrderSerializerTrack(orders, many=True)
    return Response(serializer.data)


# class CombinedOrderTrackView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, order_id):
#         user = request.user

#         try:
#             order = SSOrder.objects.get(order_id=order_id)
#         except SSOrder.DoesNotExist:
#             return Response({"error": "Order not found"}, status=404)

#         # ✅ CRM apne assigned orders hi dekhega
#         if not (user.is_staff or user.is_superuser):
#             if order.assigned_crm != user and order.ss_user != user:
#                 return Response({"error": "Not authorized"}, status=403)


#         data = CombinedOrderTrackSerializer(order).data
#         return Response(data, status=200)

class CombinedOrderTrackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        user = request.user

        print("🔍 TRACK ORDER ID RECEIVED:", repr(order_id))

        try:
            order = SSOrder.objects.select_related(
                "ss_user",
                "assigned_crm"
            ).get(order_id=order_id)

            print("✅ ORDER FOUND:", order.id, order.order_id)

        except SSOrder.DoesNotExist:
            return Response(
                {"error": "Order not found"},
                status=404
            )

        # ADMIN / STAFF / SUPERUSER
        if user.is_staff or user.is_superuser:
            pass

        # ASM
        elif user.role == "ASM":
            from asm.models import ASMSSAssignment

            assigned = ASMSSAssignment.objects.filter(
                asm=user,
                ss=order.ss_user,
                is_active=True,
                ss__is_active=True,
            ).exists()

            if not assigned:
                return Response(
                    {"error": "Not authorized"},
                    status=403
                )

        # CRM / SS
        elif order.assigned_crm != user and order.ss_user != user:
            return Response(
                {"error": "Not authorized"},
                status=403
            )

        data = CombinedOrderTrackSerializer(order).data

        return Response(data, status=200)

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


class CRMVerifiedItemUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """
        Update quantity or price of a verified order item
        """
        try:
            item = CRMVerifiedOrderItem.objects.get(pk=pk)
        except CRMVerifiedOrderItem.DoesNotExist:
            return Response({"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

        quantity = request.data.get("quantity")
        price = request.data.get("price")

        if quantity is not None:
            item.quantity = quantity
        if price is not None:
            item.price = price

        item.save()
        return Response({"message": "Item updated successfully"})


class CRMVerifiedItemDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            item = CRMVerifiedOrderItem.objects.get(pk=pk)
            item.delete()
            return Response({"message": "Item deleted successfully"}, status=status.HTTP_200_OK)
        except CRMVerifiedOrderItem.DoesNotExist:
            return Response({"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND)


class DispatchOrderListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DispatchOrderSerializer

    def get_queryset(self):
        qs = DispatchOrder.objects.all()

        from_date = self.request.query_params.get("from")
        to_date = self.request.query_params.get("to")

        if from_date:
            qs = qs.filter(order_packed_time__date__gte=from_date)

        if to_date:
            qs = qs.filter(order_packed_time__date__lte=to_date)

        qs = qs.order_by("-order_packed_time")

        # ✅ ONLY limit when NO filters
        if not from_date and not to_date:
            return qs[:10]

        return qs


class DeleteAllDispatchOrders(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        count, _ = DispatchOrder.objects.all().delete()
        return Response(
            {
                "message": "सभी dispatch orders delete हो गए",
                "deleted_count": count
            },
            status=status.HTTP_200_OK
        )
    
class DeleteSelectedDispatchOrders(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get("ids", [])
        count, _ = DispatchOrder.objects.filter(id__in=ids).delete()
        return Response(
            {"deleted_count": count},
            status=200
        )


class DownloadDispatchExcel(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Dispatch Orders"

        # Header
        ws.append([
            "order_id",
            "product",
            "quantity",
            "order_packed_time",  # optional
        ])

        # Example row (optional)
        ws.append([
            "ORD-12345",
            "Product A",
            10,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=dispatch_orders.xlsx"
        wb.save(response)
        return response


# class DownloadDispatchExcel(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         wb = openpyxl.Workbook()
#         ws = wb.active
#         ws.title = "Dispatch Records"

#         # =====================================================
#         # HEADER
#         # =====================================================

#         ws.append([
#             "CRM Item ID",
#             "Order ID",
#             "Product",
#             "Quantity",
#             "Dispatch Location",
#             "Order Packed Time",
#         ])

#         # =====================================================
#         # FETCH NEW DISPATCH RECORDS
#         # =====================================================

#         records = (
#             DispatchRecord.objects
#             .select_related(
#                 "crm_item",
#                 "crm_item__product",
#                 "crm_item__crm_order",
#                 "crm_item__crm_order__original_order",
#             )
#             .order_by(
#                 "-order_packed_time",
#                 "-updated_at",
#             )
#         )

#         # =====================================================
#         # DATA
#         # =====================================================

#         for record in records:

#             crm_item = record.crm_item
#             crm_order = crm_item.crm_order
#             original_order = (
#                 crm_order.original_order
#                 if crm_order
#                 else None
#             )

#             product = crm_item.product

#             # -------------------------------------------------
#             # ORDER ID
#             # -------------------------------------------------

#             order_id = (
#                 original_order.order_id
#                 if original_order
#                 else "-"
#             )

#             # -------------------------------------------------
#             # PRODUCT NAME
#             # -------------------------------------------------

#             product_name = "-"

#             if product:
#                 product_name = (
#                     getattr(
#                         product,
#                         "product_name",
#                         None,
#                     )
#                     or getattr(
#                         product,
#                         "name",
#                         None,
#                     )
#                     or str(product)
#                 )

#             # -------------------------------------------------
#             # APPEND ROW
#             # -------------------------------------------------

#             ws.append([
#                 crm_item.id,
#                 order_id,
#                 product_name,
#                 record.quantity,
#                 record.dispatch_location,
#                 (
#                     record.order_packed_time.strftime(
#                         "%Y-%m-%d %H:%M:%S"
#                     )
#                     if record.order_packed_time
#                     else ""
#                 ),
#             ])

#         # =====================================================
#         # EXCEL FORMATTING
#         # =====================================================

#         ws.freeze_panes = "A2"

#         ws.column_dimensions["A"].width = 16
#         ws.column_dimensions["B"].width = 18
#         ws.column_dimensions["C"].width = 35
#         ws.column_dimensions["D"].width = 14
#         ws.column_dimensions["E"].width = 20
#         ws.column_dimensions["F"].width = 24

#         # =====================================================
#         # RESPONSE
#         # =====================================================

#         response = HttpResponse(
#             content_type=(
#                 "application/vnd.openxmlformats-officedocument."
#                 "spreadsheetml.sheet"
#             )
#         )

#         response[
#             "Content-Disposition"
#         ] = (
#             'attachment; filename="dispatch_records.xlsx"'
#         )

#         wb.save(response)

#         return response



class UploadDispatchExcel(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get("file")

        if not file:
            return Response(
                {
                    "message": "Excel file required",
                    "created": 0,
                    "failed": 0,
                    "errors": [],
                },
                status=400,
            )

        # ---------------------------------------------------------
        # LOAD EXCEL
        # ---------------------------------------------------------
        try:
            wb = openpyxl.load_workbook(
                file,
                read_only=True,
                data_only=True,
            )

            ws = wb.active

        except Exception as exc:
            return Response(
                {
                    "message": "Invalid Excel file",
                    "created": 0,
                    "failed": 0,
                    "errors": [
                        f"Excel file could not be opened: {str(exc)}"
                    ],
                },
                status=400,
            )

        objects = []
        errors = []

        total_rows = 0
        skipped_blank_rows = 0

        # ---------------------------------------------------------
        # HELPERS
        # ---------------------------------------------------------
        def clean_text(value):
            if value is None:
                return ""

            return str(value).strip()

        def parse_quantity(value):
            """
            Safely convert Excel quantity into positive integer.
            """

            if value is None:
                return None

            if isinstance(value, bool):
                return None

            if isinstance(value, int):
                return value if value > 0 else None

            if isinstance(value, float):
                if value <= 0:
                    return None

                if not value.is_integer():
                    return None

                return int(value)

            text = str(value).strip()

            if not text:
                return None

            try:
                number = float(text)

                if number <= 0:
                    return None

                if not number.is_integer():
                    return None

                return int(number)

            except (ValueError, TypeError):
                return None

        def parse_packed_time(value):
            """
            Supports:
            - Excel datetime
            - DD-MM-YYYY HH:MM
            - DD-MM-YYYY HH:MM:SS
            - DD/MM/YYYY HH:MM
            - DD/MM/YYYY HH:MM:SS
            - YYYY-MM-DD HH:MM
            - YYYY-MM-DD HH:MM:SS

            Invalid/blank date is treated as an error.
            """

            if value is None:
                return None

            # Excel native datetime
            if isinstance(value, datetime):
                return value

            text = str(value).strip()

            if not text:
                return None

            formats = [
                "%d-%m-%Y %H:%M",
                "%d-%m-%Y %H:%M:%S",
                "%d/%m/%Y %H:%M",
                "%d/%m/%Y %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d %H:%M:%S",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(text, fmt)
                except ValueError:
                    continue

            return None

        # ---------------------------------------------------------
        # READ ROWS
        # ---------------------------------------------------------
        for index, row in enumerate(
            ws.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2,
        ):
            total_rows += 1

            # Make sure row has at least 4 columns
            row = list(row)

            while len(row) < 4:
                row.append(None)

            order_id = row[0]
            product = row[1]
            quantity = row[2]
            packed_time = row[3]

            clean_order_id = clean_text(order_id)
            clean_product = clean_text(product)

            # -----------------------------------------------------
            # BLANK ROW
            # -----------------------------------------------------
            if (
                not clean_order_id
                and not clean_product
                and quantity in (None, "")
                and packed_time in (None, "")
            ):
                skipped_blank_rows += 1
                continue

            # -----------------------------------------------------
            # ORDER ID VALIDATION
            # -----------------------------------------------------
            if not clean_order_id:
                errors.append(
                    f"Row {index}: Missing Order ID"
                )
                continue

            # -----------------------------------------------------
            # PRODUCT VALIDATION
            # -----------------------------------------------------
            if not clean_product:
                errors.append(
                    f"Row {index}: Missing Product"
                )
                continue

            # -----------------------------------------------------
            # QUANTITY VALIDATION
            # -----------------------------------------------------
            final_quantity = parse_quantity(quantity)

            if final_quantity is None:
                errors.append(
                    f"Row {index}: Invalid Quantity "
                    f"({quantity!r})"
                )
                continue

            # -----------------------------------------------------
            # PACKED TIME VALIDATION
            # -----------------------------------------------------
            final_time = parse_packed_time(packed_time)

            if final_time is None:
                errors.append(
                    f"Row {index}: Invalid Packed Time "
                    f"({packed_time!r})"
                )
                continue

            # -----------------------------------------------------
            # CREATE OBJECT FOR BULK INSERT
            # -----------------------------------------------------
            objects.append(
                DispatchOrder(
                    order_id=clean_order_id[:20],
                    product=clean_product[:100],
                    quantity=final_quantity,
                    order_packed_time=final_time,
                )
            )

        # ---------------------------------------------------------
        # BULK INSERT
        # ---------------------------------------------------------
        created = 0

        try:
            if objects:
                with transaction.atomic():
                    DispatchOrder.objects.bulk_create(
                        objects,
                        batch_size=1000,
                    )

                created = len(objects)

        except Exception as exc:
            return Response(
                {
                    "message": "Database error while uploading",
                    "created": 0,
                    "failed": total_rows - skipped_blank_rows,
                    "total_rows": total_rows,
                    "errors": [
                        f"Database error: {str(exc)}"
                    ],
                },
                status=500,
            )

        # ---------------------------------------------------------
        # FINAL RESPONSE
        # ---------------------------------------------------------
        failed = len(errors)

        return Response(
            {
                "message": "Upload completed",

                "total_rows": total_rows,

                "created": created,

                "failed": failed,

                "blank_rows": skipped_blank_rows,

                # Full error list
                # Frontend can show all failed rows.
                "errors": errors,
            },
            status=200,
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_orders_report(request):

    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")
    report_type = request.GET.get("report_type", "ss")

    if not from_date or not to_date:
        return HttpResponse(
            "from_date and to_date required",
            status=400
        )

    start_date = timezone.make_aware(
        datetime.strptime(from_date, "%Y-%m-%d")
    )

    end_date = timezone.make_aware(
        datetime.strptime(to_date, "%Y-%m-%d")
        + timedelta(days=1)
    )

    wb = Workbook()
    ws = wb.active

    # =====================================================
    # SS ORDERS REPORT
    # =====================================================
    if report_type == "ss":

        ws.title = "SS Orders"

        ws.append([
            "Order ID",
            "Order Date",
            "Party Name",
            "CRM Name",
            "Status",
            "Product",
            "Quantity",
        ])

        orders = (
            SSOrder.objects
            .filter(
                created_at__gte=start_date,
                created_at__lt=end_date
            )
            .select_related(
                "ss_user",
                "assigned_crm"
            )
            .prefetch_related(
                "items__product"
            )
            .order_by("-created_at")
        )

        for order in orders:

            for item in order.items.all():

                ws.append([
                    order.order_id,

                    order.created_at.strftime(
                        "%d-%m-%Y %H:%M"
                    ),

                    getattr(
                        order.ss_user,
                        "party_name",
                        ""
                    ),

                    getattr(
                        order.assigned_crm,
                        "name",
                        ""
                    ),

                    order.status,

                    item.product.product_name
                    if item.product else "",

                    item.quantity,
                ])

    # =====================================================
    # CRM VERIFIED REPORT
    # =====================================================
    else:

        ws.title = "CRM Verified Orders"

        ws.append([
            "Order ID",
            "Verified Date",
            "Party Name",
            "CRM Name",
            "Status",
            "Product",
            "Quantity",
        ])

        orders = (
            CRMVerifiedOrder.objects
            .filter(
                verified_at__gte=start_date,
                verified_at__lt=end_date
            )
            .select_related(
                "crm_user",
                "original_order",
                "original_order__ss_user"
            )
            .prefetch_related(
                "items__product"
            )
            .order_by("-verified_at")
        )

        for order in orders:

            for item in order.items.all():

                ws.append([
                    order.original_order.order_id,

                    order.verified_at.strftime(
                        "%d-%m-%Y %H:%M"
                    ),

                    getattr(
                        order.original_order.ss_user,
                        "party_name",
                        ""
                    ),

                    getattr(
                        order.crm_user,
                        "name",
                        ""
                    ),

                    order.status,

                    item.product.product_name
                    if item.product else "",

                    item.quantity,
                ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; filename="{report_type}_orders_{from_date}_to_{to_date}.xlsx"'
    )

    wb.save(response)

    return response


@api_view(["GET"])
def hr_orders(request):
    user = request.user

    if user.role in ["ADMIN", "HR"]:
        orders = SSOrder.objects.select_related(
            "ss_user",
            "assigned_crm",
        )

    elif user.role == "CRM":
        orders = (
            SSOrder.objects.select_related(
                "ss_user",
                "assigned_crm",
            ).filter(
                assigned_crm=user
            )
        )

    else:
        orders = SSOrder.objects.none()

    last_three_days = timezone.now().date() - timedelta(days=10)

    orders = orders.filter(
        created_at__date__gte=last_three_days
    )
   
    orders = orders.exclude(
        status__in=["APPROVED", "REJECTED"]
    )

    orders = orders.order_by("-created_at")

    serializer = HROrderListSerializer(
        orders,
        many=True,
    )

    return Response(serializer.data)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def hr_update_order_notes(request, pk):
    try:
        order = SSOrder.objects.get(id=pk)
    except SSOrder.DoesNotExist:
        return Response(
            {"detail": "Order not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    notes = request.data.get("notes", "").strip()

    order.notes = notes
    order.save(update_fields=["notes"])

    return Response(
        {
            "message": "Remarks updated successfully",
            "notes": order.notes,
        }
    )



# 25 september               ???????????????????????????????????????????????????????????????



# ============================================================
# DISPATCH VIEWS
# NEW DISPATCH SYSTEM
#
# Designed for:
# - 20K - 30K+ Excel rows
# - Chunked DB processing
# - Bulk create
# - Bulk update
# - Duplicate CRM Item IDs
# - Latest Excel value wins
# - Concurrency safe
# - Existing DispatchOrder system untouched
# ============================================================

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from openpyxl import load_workbook

from .models import (
    CRMVerifiedOrderItem,
    DispatchRecord,
)


# ============================================================
# CONFIGURATION
# ============================================================

# Number of records processed in one DB batch.
# 2000 is a good balance for 20K-30K+ uploads.
DISPATCH_BATCH_SIZE = 2000


# ============================================================
# EXCEL HELPERS
# ============================================================

def normalize_header(value):
    """
    Converts different Excel header styles into one normalized form.

    Examples:
        CRM Item ID
        crm_item_id
        CRM-Item-ID

    all become:

        crm item id
    """

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


def get_excel_value(row, header_map, *possible_names):
    """
    Returns the value from a row using possible header names.
    """

    for name in possible_names:
        normalized = normalize_header(name)

        if normalized in header_map:
            index = header_map[normalized]

            if index < len(row):
                return row[index]

    return None


def clean_positive_integer(value):
    """
    Converts Excel numeric values safely into positive integers.

    Examples:
        20       -> 20
        20.0     -> 20
        "20"     -> 20
        "20.0"   -> 20

    Invalid:
        0
        -10
        abc
        None
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None

    if number <= 0:
        return None

    return number


def parse_datetime(value):
    """
    Converts Excel datetime / supported string formats
    into timezone-aware datetime.
    """

    if not value:
        return None

    # Excel datetime object
    if hasattr(value, "year") and hasattr(value, "month"):

        dt = value

        if timezone.is_naive(dt):
            return timezone.make_aware(
                dt,
                timezone.get_current_timezone(),
            )

        return dt

    if isinstance(value, str):

        value = value.strip()

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",

            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y %H:%M",
            "%d-%m-%Y",

            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
        ]

        for fmt in formats:

            try:

                dt = datetime.strptime(
                    value,
                    fmt,
                )

                return timezone.make_aware(
                    dt,
                    timezone.get_current_timezone(),
                )

            except ValueError:
                continue

    return None


# ============================================================
# DISPATCH EXCEL UPLOAD
# ============================================================

class DispatchExcelUploadView(APIView):
    """
    NEW DISPATCH EXCEL UPLOAD API.

    Required Excel columns:

        CRM Item ID
        Quantity

    Optional:

        Order Packed Time

    --------------------------------------------------------
    IMPORTANT
    --------------------------------------------------------

    CRM Item ID means:

        CRMVerifiedOrderItem.id

    Example:

        152453
        153559
        153560

    Same CRM Item ID can appear multiple times.

    Example:

        152453 -> 20
        153559 -> 30
        152453 -> 70

    Final DB result:

        152453 -> 70
        153559 -> 30

    Latest row wins.

    --------------------------------------------------------
    PERFORMANCE
    --------------------------------------------------------

    Data is processed in chunks of 2000.

    30,000 rows therefore become approximately:

        15 batches

    We use:

        bulk_create()
        bulk_update()

    instead of one DB query per row.

    --------------------------------------------------------
    CONCURRENCY
    --------------------------------------------------------

    CRMVerifiedOrderItem rows are locked using:

        select_for_update()

    before checking/creating DispatchRecord.

    This prevents two simultaneous uploads from creating
    duplicate DispatchRecord rows for the same CRM item.
    """

    def post(self, request):

        # ====================================================
        # 1. GET FILE
        # ====================================================

        uploaded_file = request.FILES.get("file")

        if not uploaded_file:

            return Response(
                {
                    "success": False,
                    "message": "Excel file is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # 2. FILE EXTENSION CHECK
        # ====================================================

        filename = uploaded_file.name.lower()

        if not (
            filename.endswith(".xlsx")
            or filename.endswith(".xlsm")
        ):

            return Response(
                {
                    "success": False,
                    "message": (
                        "Only .xlsx or .xlsm Excel files "
                        "are supported."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # 3. OPEN EXCEL
        # ====================================================

        try:

            workbook = load_workbook(
                uploaded_file,
                read_only=True,
                data_only=True,
            )

            worksheet = workbook.active

        except Exception as exc:

            return Response(
                {
                    "success": False,
                    "message": (
                        f"Unable to read Excel file: {str(exc)}"
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # 4. READ HEADER
        # ====================================================

        rows = worksheet.iter_rows(
            values_only=True
        )

        try:

            headers = next(rows)

        except StopIteration:

            workbook.close()

            return Response(
                {
                    "success": False,
                    "message": "Excel file is empty.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # 5. CREATE HEADER MAP
        # ====================================================

        header_map = {}

        for index, header in enumerate(headers):

            normalized = normalize_header(header)

            if normalized:

                header_map[normalized] = index

        # ====================================================
        # 6. FIND CRM ITEM ID COLUMN
        # ====================================================

        crm_item_header = None

        crm_item_possible_headers = [
            "crm item id",
            "crm_item_id",
            "crm id",
            "crm item",
            "item id",
            "crmverifiedorderitem id",
            "crm verified order item id",
        ]

        for possible in crm_item_possible_headers:

            normalized = normalize_header(possible)

            if normalized in header_map:

                crm_item_header = normalized
                break

        # ====================================================
        # 7. FIND QUANTITY COLUMN
        # ====================================================

        quantity_header = None

        quantity_possible_headers = [
            "quantity",
            "qty",
            "dispatch quantity",
            "dispatch qty",
        ]

        for possible in quantity_possible_headers:

            normalized = normalize_header(possible)

            if normalized in header_map:

                quantity_header = normalized
                break

        # ====================================================
        # 8. REQUIRED HEADER VALIDATION
        # ====================================================

        if crm_item_header is None:

            workbook.close()

            return Response(
                {
                    "success": False,
                    "message": (
                        "CRM Item ID column is missing. "
                        "Use 'CRM Item ID'."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity_header is None:

            workbook.close()

            return Response(
                {
                    "success": False,
                    "message": (
                        "Quantity column is missing. "
                        "Use 'Quantity' or 'Qty'."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # 9. OPTIONAL PACKED TIME COLUMN
        # ====================================================

        packed_time_header = None

        packed_time_possible_headers = [
            "order packed time",
            "packed time",
            "dispatch time",
            "packed at",
            "order_packed_time",
            "packed_time",
        ]

        for possible in packed_time_possible_headers:

            normalized = normalize_header(possible)

            if normalized in header_map:

                packed_time_header = normalized
                break

        # ====================================================
        # 10. READ EXCEL
        #
        # We use a dictionary.
        #
        # This automatically makes the LAST occurrence
        # of the same CRM Item ID win.
        # ====================================================

        latest_rows = {}

        invalid_rows = []

        total_excel_rows = 0

        for row in rows:

            total_excel_rows += 1

            excel_row_number = total_excel_rows + 1

            # -----------------------------------------------
            # Empty row
            # -----------------------------------------------

            if (
                not row
                or all(
                    value is None
                    or str(value).strip() == ""
                    for value in row
                )
            ):

                continue

            # -----------------------------------------------
            # CRM ITEM ID
            # -----------------------------------------------

            crm_item_id = get_excel_value(
                row,
                header_map,
                crm_item_header,
            )

            # -----------------------------------------------
            # QUANTITY
            # -----------------------------------------------

            quantity = get_excel_value(
                row,
                header_map,
                quantity_header,
            )

            # -----------------------------------------------
            # PACKED TIME
            # -----------------------------------------------

            packed_time = None

            if packed_time_header:

                packed_time = get_excel_value(
                    row,
                    header_map,
                    packed_time_header,
                )

            # -----------------------------------------------
            # CLEAN CRM ITEM ID
            # -----------------------------------------------

            crm_item_id = clean_positive_integer(
                crm_item_id
            )

            if crm_item_id is None:

                invalid_rows.append(
                    {
                        "row": excel_row_number,
                        "reason": "Invalid CRM Item ID.",
                    }
                )

                continue

            # -----------------------------------------------
            # CLEAN QUANTITY
            # -----------------------------------------------

            quantity = clean_positive_integer(
                quantity
            )

            if quantity is None:

                invalid_rows.append(
                    {
                        "row": excel_row_number,
                        "crm_item_id": crm_item_id,
                        "reason": "Invalid quantity.",
                    }
                )

                continue

            # -----------------------------------------------
            # PARSE PACKED TIME
            # -----------------------------------------------

            parsed_packed_time = parse_datetime(
                packed_time
            )

            # -----------------------------------------------
            # LATEST VALUE WINS
            # -----------------------------------------------

            latest_rows[crm_item_id] = {
                "excel_row": excel_row_number,
                "crm_item_id": crm_item_id,
                "quantity": quantity,
                "order_packed_time": parsed_packed_time,
            }

        # ====================================================
        # CLOSE WORKBOOK
        # ====================================================

        workbook.close()

        # ====================================================
        # 11. NO VALID DATA
        # ====================================================

        if not latest_rows:

            return Response(
                {
                    "success": False,
                    "message": (
                        "No valid dispatch records found."
                    ),
                    "total_excel_rows": total_excel_rows,
                    "invalid_rows": invalid_rows,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ====================================================
        # 12. UNIQUE CRM ITEM IDS
        # ====================================================

        unique_item_ids = list(
            latest_rows.keys()
        )

        # ====================================================
        # 13. COUNTERS
        # ====================================================

        created_count = 0
        updated_count = 0

        invalid_crm_items = []

        processed_batches = 0

        total_unique_items = len(
            unique_item_ids
        )

        # ====================================================
        # 14. PROCESS IN CHUNKS
        # ====================================================

        for start_index in range(
            0,
            total_unique_items,
            DISPATCH_BATCH_SIZE,
        ):

            end_index = (
                start_index
                + DISPATCH_BATCH_SIZE
            )

            batch_item_ids = unique_item_ids[
                start_index:end_index
            ]

            processed_batches += 1

            # =================================================
            # EACH BATCH HAS ITS OWN TRANSACTION
            # =================================================

            with transaction.atomic():

                # =============================================
                # LOCK CRM ITEMS
                #
                # This is important for concurrent uploads.
                #
                # If two users upload same CRM Item ID,
                # database will serialize access to that
                # CRM item.
                # =============================================

                crm_items = (
                    CRMVerifiedOrderItem.objects
                    .select_for_update()
                    .select_related(
                        "crm_order",
                        "crm_order__original_order",
                    )
                    .filter(
                        id__in=batch_item_ids
                    )
                )

                crm_item_map = {
                    item.id: item
                    for item in crm_items
                }

                # =============================================
                # INVALID CRM ITEMS
                # =============================================

                for crm_item_id in batch_item_ids:

                    if crm_item_id not in crm_item_map:

                        invalid_crm_items.append(
                            crm_item_id
                        )

                # =============================================
                # ONLY VALID IDS
                # =============================================

                valid_batch_ids = [
                    item_id
                    for item_id in batch_item_ids
                    if item_id in crm_item_map
                ]

                if not valid_batch_ids:

                    continue

                # =============================================
                # GET EXISTING DISPATCH RECORDS
                #
                # Because CRM items are already locked above,
                # another concurrent importer cannot modify
                # these same CRM items while this transaction
                # is working.
                # =============================================

                existing_records = (
                    DispatchRecord.objects
                    .select_for_update()
                    .filter(
                        crm_item_id__in=valid_batch_ids
                    )
                )

                existing_map = {
                    record.crm_item_id: record
                    for record in existing_records
                }

                # =============================================
                # PREPARE BULK OPERATIONS
                # =============================================

                records_to_create = []
                records_to_update = []

                current_time = timezone.now()

                for crm_item_id in valid_batch_ids:

                    row_data = latest_rows[
                        crm_item_id
                    ]

                    crm_item = crm_item_map[
                        crm_item_id
                    ]

                    # -----------------------------------------
                    # DISPATCH LOCATION
                    # -----------------------------------------

                    dispatch_location = (
                        crm_item.crm_order.dispatch_location
                        or "Delhi"
                    )

                    # -----------------------------------------
                    # EXISTING RECORD
                    # -----------------------------------------

                    existing_record = (
                        existing_map.get(
                            crm_item_id
                        )
                    )

                    if existing_record:

                        # -------------------------------------
                        # UPDATE EXISTING
                        # -------------------------------------

                        existing_record.quantity = (
                            row_data["quantity"]
                        )

                        existing_record.dispatch_location = (
                            dispatch_location
                        )

                        # -------------------------------------
                        # IMPORTANT:
                        #
                        # If Excel contains packed time,
                        # update it.
                        #
                        # If Excel doesn't contain packed time,
                        # preserve existing DB value.
                        # -------------------------------------

                        if (
                            row_data[
                                "order_packed_time"
                            ]
                            is not None
                        ):

                            existing_record.order_packed_time = (
                                row_data[
                                    "order_packed_time"
                                ]
                            )

                        existing_record.updated_at = (
                            current_time
                        )

                        records_to_update.append(
                            existing_record
                        )

                    else:

                        # -------------------------------------
                        # CREATE NEW
                        # -------------------------------------

                        records_to_create.append(
                            DispatchRecord(
                                crm_item=crm_item,
                                quantity=row_data[
                                    "quantity"
                                ],
                                dispatch_location=(
                                    dispatch_location
                                ),
                                order_packed_time=(
                                    row_data[
                                        "order_packed_time"
                                    ]
                                ),
                            )
                        )

                # =============================================
                # BULK CREATE
                # =============================================

                if records_to_create:

                    DispatchRecord.objects.bulk_create(
                        records_to_create,
                        batch_size=1000,
                    )

                    created_count += len(
                        records_to_create
                    )

                # =============================================
                # BULK UPDATE
                # =============================================

                if records_to_update:

                    DispatchRecord.objects.bulk_update(
                        records_to_update,
                        fields=[
                            "quantity",
                            "dispatch_location",
                            "order_packed_time",
                            "updated_at",
                        ],
                        batch_size=1000,
                    )

                    updated_count += len(
                        records_to_update
                    )

        # ====================================================
        # 15. FINAL RESPONSE
        # ====================================================

        return Response(
            {
                "success": True,

                "message": (
                    "Dispatch Excel imported successfully."
                ),

                "summary": {
                    "total_excel_rows": (
                        total_excel_rows
                    ),

                    "unique_crm_items": (
                        total_unique_items
                    ),

                    "created": (
                        created_count
                    ),

                    "updated": (
                        updated_count
                    ),

                    "invalid_crm_items": (
                        len(
                            invalid_crm_items
                        )
                    ),

                    "invalid_rows": (
                        len(
                            invalid_rows
                        )
                    ),

                    "processed_batches": (
                        processed_batches
                    ),

                    "batch_size": (
                        DISPATCH_BATCH_SIZE
                    ),
                },

                "invalid_crm_item_ids": (
                    invalid_crm_items
                ),

                "invalid_rows": (
                    invalid_rows
                ),
            },
            status=status.HTTP_200_OK,
        )


from collections import defaultdict
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.db.models import (
    Case,
    CharField,
    Count,
    Exists,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    SSOrder,
    SSOrderItem,
    CRMVerifiedOrder,
    CRMVerifiedOrderItem,
    DispatchRecord,
)

from .order_records_serializers import (
    OrderRecordListSerializer,
    OrderRecordDetailSerializer,
)


User = get_user_model()


# ============================================================================
# PAGINATION
# ============================================================================

class OrderRecordPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


# ============================================================================
# BASIC HELPERS
# ============================================================================

def _field_exists(model, field_name):
    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False


def _user_display_name(user):
    if not user:
        return ""

    for field in (
        "party_name",
        "name",
        "username",
        "email",
    ):
        value = getattr(user, field, None)

        if value:
            return str(value).strip()

    first_name = getattr(user, "first_name", "") or ""
    last_name = getattr(user, "last_name", "") or ""

    return f"{first_name} {last_name}".strip()


def _user_mobile(user):
    if not user:
        return ""

    for field in (
        "mobile",
        "phone",
        "phone_number",
    ):
        value = getattr(user, field, None)

        if value:
            return str(value)

    return ""


def _user_search_q(relation, value):
    query = Q()

    searchable_fields = [
        "party_name",
        "name",
        "username",
        "first_name",
        "last_name",
        "email",
        "mobile",
        "phone",
        "phone_number",
    ]

    for field in searchable_fields:
        if _field_exists(User, field):
            query |= Q(
                **{
                    f"{relation}__{field}__icontains": value
                }
            )

    return query


def _get_user_role(user):
    role = getattr(user, "role", None)

    if role is None:
        role = getattr(user, "user_type", None)

    return str(role or "").upper().strip()


def _is_admin(user):
    return (
        bool(getattr(user, "is_superuser", False))
        or bool(getattr(user, "is_staff", False))
        or _get_user_role(user) == "ADMIN"
    )


# ============================================================================
# ROLE FILTERING
#
# IMPORTANT:
# This queryset intentionally stays LIGHT.
# No item joins.
# No verification subqueries.
# No dispatch annotations.
#
# This is what makes the normal first-page request fast.
# ============================================================================

def _get_role_filtered_queryset(user):

    queryset = (
        SSOrder.objects
        .select_related(
            "ss_user",
            "assigned_crm",
        )
    )

    if _is_admin(user):
        return queryset

    role = _get_user_role(user)

    if role == "CRM":
        return queryset.filter(
            assigned_crm=user
        )

    if role == "SS":
        return queryset.filter(
            ss_user=user
        )

    raise PermissionDenied(
        "You are not allowed to access order records."
    )


# ============================================================================
# LATEST VERIFICATION SUBQUERY
#
# Used ONLY when verification-related filtering is requested.
# Normal page loading does NOT use this.
# ============================================================================

def _latest_verification_queryset():
    return (
        CRMVerifiedOrder.objects
        .filter(
            original_order=OuterRef("pk")
        )
        .order_by(
            "-verified_at",
            "-pk",
        )
    )


def _latest_verification_id_subquery():
    return Subquery(
        _latest_verification_queryset()
        .values("id")[:1],
        output_field=IntegerField(),
    )


# ============================================================================
# DATE HELPERS
# ============================================================================

def _get_date(value):
    if not value:
        return None

    try:
        from datetime import date

        return date.fromisoformat(value)

    except (TypeError, ValueError):
        return None


def _apply_date_filters(queryset, request):

    from_date = _get_date(
        request.query_params.get("from_date")
    )

    to_date = _get_date(
        request.query_params.get("to_date")
    )

    # ------------------------------------------------------------------------
    # IMPORTANT:
    # Do NOT use created_at__date__gte/lte.
    #
    # Using a datetime range keeps the normal created_at index usable.
    # ------------------------------------------------------------------------

    if from_date:
        start_datetime = timezone.make_aware(
            datetime.combine(
                from_date,
                time.min,
            )
        )

        queryset = queryset.filter(
            created_at__gte=start_datetime
        )

    if to_date:
        end_datetime = timezone.make_aware(
            datetime.combine(
                to_date + timedelta(days=1),
                time.min,
            )
        )

        queryset = queryset.filter(
            created_at__lt=end_datetime
        )

    return queryset


# ============================================================================
# NORMAL FILTERS
# ============================================================================

def _apply_basic_filters(queryset, request):

    # ------------------------------------------------------------------------
    # SEARCH
    #
    # Accept both:
    #   ?search=
    #   ?q=
    #
    # This protects the API from frontend parameter mismatch.
    # ------------------------------------------------------------------------

    search = (
        request.query_params.get("search")
        or request.query_params.get("q")
        or ""
    )

    search = str(search).strip()

    if search:

        search_query = Q(
            order_id__icontains=search
        )

        search_query |= _user_search_q(
            "ss_user",
            search,
        )

        search_query |= _user_search_q(
            "assigned_crm",
            search,
        )

        queryset = queryset.filter(
            search_query
        )

    # ------------------------------------------------------------------------
    # PARTY
    # ------------------------------------------------------------------------

    party = str(
        request.query_params.get(
            "party",
            ""
        )
    ).strip()

    if party:

        party_query = _user_search_q(
            "ss_user",
            party,
        )

        queryset = queryset.filter(
            party_query
        )

    # ------------------------------------------------------------------------
    # ORDER STATUS
    # ------------------------------------------------------------------------

    order_status = str(
        request.query_params.get(
            "status",
            ""
        )
    ).strip()

    if order_status:

        queryset = queryset.filter(
            status__iexact=order_status
        )

    # ------------------------------------------------------------------------
    # DATES
    # ------------------------------------------------------------------------

    queryset = _apply_date_filters(
        queryset,
        request,
    )

    return queryset


# ============================================================================
# VERIFICATION FILTERS
#
# These are only applied when the user actually selects them.
# ============================================================================

def _apply_verification_filters(queryset, request):

    verification_status = str(
        request.query_params.get(
            "verification_status",
            ""
        )
    ).strip()

    punched = str(
        request.query_params.get(
            "punched",
            ""
        )
    ).strip().lower()

    needs_verification_filter = bool(
        verification_status
        or punched in {
            "true",
            "1",
            "yes",
            "false",
            "0",
            "no",
        }
    )

    if not needs_verification_filter:
        return queryset

    latest_verification_id = (
        _latest_verification_id_subquery()
    )

    queryset = queryset.annotate(
        _latest_verification_id=latest_verification_id
    )

    # ------------------------------------------------------------------------
    # VERIFICATION STATUS
    # ------------------------------------------------------------------------

    if verification_status:

        latest_status = Subquery(
            CRMVerifiedOrder.objects
            .filter(
                pk=OuterRef(
                    "_latest_verification_id"
                )
            )
            .values("status")[:1],
            output_field=CharField(),
        )

        queryset = queryset.annotate(
            _latest_verification_status=latest_status
        )

        queryset = queryset.filter(
            _latest_verification_status__iexact=(
                verification_status
            )
        )

    # ------------------------------------------------------------------------
    # PUNCHED
    # ------------------------------------------------------------------------

    if punched in {
        "true",
        "1",
        "yes",
        "false",
        "0",
        "no",
    }:

        punched_value = punched in {
            "true",
            "1",
            "yes",
        }

        latest_punched = Subquery(
            CRMVerifiedOrder.objects
            .filter(
                pk=OuterRef(
                    "_latest_verification_id"
                )
            )
            .values("punched")[:1]
        )

        queryset = queryset.annotate(
            _latest_punched=latest_punched
        )

        queryset = queryset.filter(
            _latest_punched=punched_value
        )

    return queryset


# ============================================================================
# DISPATCH FILTER
#
# This is intentionally kept out of the normal page query.
# It only executes when the user actually selects a dispatch filter.
# ============================================================================

def _apply_dispatch_filter(queryset, request):

    dispatch = str(
        request.query_params.get(
            "dispatch",
            ""
        )
    ).strip().upper()

    allowed_dispatch_statuses = {
        "NOT_VERIFIED",
        "NO_DISPATCH_REQUIRED",
        "PENDING",
        "PARTIAL",
        "DISPATCHED",
    }

    if dispatch not in allowed_dispatch_statuses:
        return queryset

    latest_verification = (
        _latest_verification_queryset()
    )

    latest_verification_id = Subquery(
        latest_verification
        .values("id")[:1],
        output_field=IntegerField(),
    )

    dispatchable_item_count = Subquery(
        CRMVerifiedOrderItem.objects
        .filter(
            crm_order_id=latest_verification_id,
            is_rejected=False,
        )
        .order_by()
        .values("crm_order_id")
        .annotate(
            total=Count("id")
        )
        .values("total")[:1],
        output_field=IntegerField(),
    )

    dispatched_item_count = Subquery(
        CRMVerifiedOrderItem.objects
        .filter(
            crm_order_id=latest_verification_id,
            is_rejected=False,
            dispatch_record__isnull=False,
        )
        .order_by()
        .values("crm_order_id")
        .annotate(
            total=Count("id")
        )
        .values("total")[:1],
        output_field=IntegerField(),
    )

    queryset = queryset.annotate(
        _latest_verification_id=latest_verification_id,
        _dispatchable_item_count=Coalesce(
            dispatchable_item_count,
            Value(0),
            output_field=IntegerField(),
        ),
        _dispatched_item_count=Coalesce(
            dispatched_item_count,
            Value(0),
            output_field=IntegerField(),
        ),
    )

    # ------------------------------------------------------------------------
    # NOT VERIFIED
    # ------------------------------------------------------------------------

    if dispatch == "NOT_VERIFIED":

        return queryset.filter(
            _latest_verification_id__isnull=True
        )

    # ------------------------------------------------------------------------
    # ALL REMAINING STATUSES REQUIRE VERIFICATION
    # ------------------------------------------------------------------------

    queryset = queryset.filter(
        _latest_verification_id__isnull=False
    )

    if dispatch == "NO_DISPATCH_REQUIRED":

        return queryset.filter(
            _dispatchable_item_count=0
        )

    if dispatch == "PENDING":

        return queryset.filter(
            _dispatchable_item_count__gt=0,
            _dispatched_item_count=0,
        )

    if dispatch == "DISPATCHED":

        return queryset.filter(
            _dispatchable_item_count__gt=0,
            _dispatched_item_count__gte=F(
                "_dispatchable_item_count"
            ),
        )

    if dispatch == "PARTIAL":

        return queryset.filter(
            _dispatchable_item_count__gt=0,
            _dispatched_item_count__gt=0,
            _dispatched_item_count__lt=F(
                "_dispatchable_item_count"
            ),
        )

    return queryset


# ============================================================================
# ALL LIST FILTERS
# ============================================================================

def _apply_filters(queryset, request):

    queryset = _apply_basic_filters(
        queryset,
        request,
    )

    queryset = _apply_verification_filters(
        queryset,
        request,
    )

    queryset = _apply_dispatch_filter(
        queryset,
        request,
    )

    return queryset


# ============================================================================
# PRODUCT HELPER
# ============================================================================

def _product_name(product):

    if not product:
        return ""

    for field in (
        "product_name",
        "name",
        "title",
    ):

        value = getattr(
            product,
            field,
            None,
        )

        if value:
            return str(value)

    return str(product)


# ============================================================================
# DISPATCH RECORD HELPER
# ============================================================================

def _get_dispatch_record(crm_item):

    try:
        return crm_item.dispatch_record

    except DispatchRecord.DoesNotExist:
        return None


# ============================================================================
# BULK LIST ENRICHMENT
#
# IMPORTANT:
# This is the main performance improvement.
#
# We first paginate SSOrder to 50 records.
# ONLY THEN do we fetch verification/items/dispatch information
# for those 50 orders.
# ============================================================================

def _build_bulk_list_data(orders):

    if not orders:
        return {}

    order_ids = [
        order.id
        for order in orders
    ]

    # ------------------------------------------------------------------------
    # 1. ORIGINAL ITEM COUNTS
    #
    # One query for the current page only.
    # ------------------------------------------------------------------------

    original_item_counts = defaultdict(int)

    original_item_rows = (
        SSOrderItem.objects
        .filter(
            order_id__in=order_ids
        )
        .values(
            "order_id"
        )
        .annotate(
            total=Count("id")
        )
    )

    for row in original_item_rows:

        original_item_counts[
            row["order_id"]
        ] = int(
            row["total"] or 0
        )

    # ------------------------------------------------------------------------
    # 2. LATEST VERIFICATION FOR CURRENT PAGE
    #
    # We fetch ALL verification rows belonging to these 50 orders.
    # Then pick the latest one in Python.
    #
    # This avoids one correlated subquery for every order.
    # ------------------------------------------------------------------------

    verification_rows = (
        CRMVerifiedOrder.objects
        .filter(
            original_order_id__in=order_ids
        )
        .select_related(
            "crm_user"
        )
        .order_by(
            "original_order_id",
            "-verified_at",
            "-pk",
        )
    )

    latest_verifications = {}

    for verification in verification_rows:

        if (
            verification.original_order_id
            not in latest_verifications
        ):

            latest_verifications[
                verification.original_order_id
            ] = verification

    verification_ids = [
        verification.id
        for verification in latest_verifications.values()
    ]

    # ------------------------------------------------------------------------
    # 3. VERIFIED ITEMS + DISPATCH RECORDS
    #
    # Django performs this as bulk queries instead of N+1.
    # ------------------------------------------------------------------------

    verified_items_by_verification = defaultdict(list)

    if verification_ids:

        verified_items = list(
            CRMVerifiedOrderItem.objects
            .filter(
                crm_order_id__in=verification_ids
            )
            .prefetch_related(
                "dispatch_record"
            )
        )

        for item in verified_items:

            verified_items_by_verification[
                item.crm_order_id
            ].append(item)

    # ------------------------------------------------------------------------
    # 4. BUILD FINAL PAGE DATA
    # ------------------------------------------------------------------------

    result = {}

    for order in orders:

        original_count = original_item_counts.get(
            order.id,
            0,
        )

        verification = latest_verifications.get(
            order.id
        )

        verified_items = []

        if verification:
            verified_items = (
                verified_items_by_verification.get(
                    verification.id,
                    [],
                )
            )

        verified_items_count = len(
            verified_items
        )

        dispatchable_items_count = 0
        dispatched_items_count = 0
        dispatched_quantity = 0

        if verification:

            for crm_item in verified_items:

                if crm_item.is_rejected:
                    continue

                dispatchable_items_count += 1

                dispatch = _get_dispatch_record(
                    crm_item
                )

                if dispatch:

                    dispatched_items_count += 1

                    dispatched_quantity += int(
                        dispatch.quantity or 0
                    )

        # --------------------------------------------------------------------
        # DISPATCH STATUS
        # --------------------------------------------------------------------

        if not verification:

            dispatch_status = "NOT_VERIFIED"

        elif dispatchable_items_count == 0:

            dispatch_status = "NO_DISPATCH_REQUIRED"

        elif dispatched_items_count == 0:

            dispatch_status = "PENDING"

        elif (
            dispatched_items_count
            >= dispatchable_items_count
        ):

            dispatch_status = "DISPATCHED"

        else:

            dispatch_status = "PARTIAL"

        result[order.id] = {
            "items_count": original_count,
            "verified_items_count": verified_items_count,
            "dispatched_items_count": dispatched_items_count,
            "dispatched_quantity": dispatched_quantity,
            "dispatch_status": dispatch_status,
            "verification": verification,
        }

    return result


# ============================================================================
# LIST SERIALIZATION
# ============================================================================

def _serialize_list_rows(
    orders,
    bulk_data,
):

    rows = []

    for order in orders:

        info = bulk_data.get(
            order.id,
            {},
        )

        verification = info.get(
            "verification"
        )

        rows.append({
            "id": order.id,

            "order_id": order.order_id,

            "ss_party_name": _user_display_name(
                order.ss_user
            ),

            "ss_user_name": _user_display_name(
                order.ss_user
            ),

            "crm_name": _user_display_name(
                order.assigned_crm
            ),

            "total_amount": str(
                order.total_amount
            ),

            "status": order.status or "",

            "verification_status": (
                verification.status
                if verification
                else None
            ),

            "punched": (
                bool(verification.punched)
                if verification
                else None
            ),

            "items_count": int(
                info.get(
                    "items_count",
                    0,
                )
            ),

            "verified_items_count": int(
                info.get(
                    "verified_items_count",
                    0,
                )
            ),

            "dispatched_items_count": int(
                info.get(
                    "dispatched_items_count",
                    0,
                )
            ),

            "dispatched_quantity": int(
                info.get(
                    "dispatched_quantity",
                    0,
                )
            ),

            "dispatch_status": info.get(
                "dispatch_status",
                "NOT_VERIFIED",
            ),

            "created_at": (
                order.created_at.isoformat()
                if order.created_at
                else ""
            ),
        })

    return rows


# ============================================================================
# LATEST VERIFICATION FOR DETAIL
# ============================================================================

def _get_latest_verification(order):

    return (
        CRMVerifiedOrder.objects
        .filter(
            original_order=order
        )
        .select_related(
            "crm_user"
        )
        .prefetch_related(
            "items__product",
            "items__dispatch_record",
        )
        .order_by(
            "-verified_at",
            "-pk",
        )
        .first()
    )


# ============================================================================
# DETAIL RESPONSE
# ============================================================================

def _build_detail_response(order):

    # ------------------------------------------------------------------------
    # ORIGINAL ITEMS
    # ------------------------------------------------------------------------

    original_items = list(
        order.items
        .select_related(
            "product"
        )
        .all()
    )

    # ------------------------------------------------------------------------
    # LATEST VERIFICATION
    # ------------------------------------------------------------------------

    verification = _get_latest_verification(
        order
    )

    # ------------------------------------------------------------------------
    # NOT VERIFIED
    # ------------------------------------------------------------------------

    if not verification:

        detail_items = []

        for original_item in original_items:

            detail_items.append({
                "crm_item_id": None,

                "product_id": original_item.product_id,

                "product_name": _product_name(
                    original_item.product
                ),

                "ordered_quantity": (
                    original_item.quantity
                ),

                "verified_quantity": None,

                "rejected": False,

                "dispatch_quantity": 0,

                "dispatch_location": None,

                "order_packed_time": None,
            })

        summary = {
            "items_count": len(
                original_items
            ),

            "verified_items_count": 0,

            "dispatchable_items_count": 0,

            "dispatched_items_count": 0,

            "dispatched_quantity": 0,

            "dispatch_status": "NOT_VERIFIED",
        }

        return {
            "order_id": order.order_id,

            "total_amount": str(
                order.total_amount
            ),

            "status": order.status or "",

            "created_at": (
                order.created_at.isoformat()
                if order.created_at
                else ""
            ),

            "ss_user": {
                "party_name": _user_display_name(
                    order.ss_user
                ),

                "name": _user_display_name(
                    order.ss_user
                ),

                "mobile": _user_mobile(
                    order.ss_user
                ),
            },

            "crm_user": {
                "name": "",
                "mobile": "",
            },

            "verification": None,

            "summary": summary,

            "items": detail_items,

            "note": order.note or "",

            "notes": order.notes or "",
        }

    # ------------------------------------------------------------------------
    # VERIFIED ITEMS
    # ------------------------------------------------------------------------

    verified_items = list(
        verification.items
        .select_related(
            "product"
        )
        .prefetch_related(
            "dispatch_record"
        )
        .all()
    )

    # ------------------------------------------------------------------------
    # MATCH ORIGINAL ITEMS
    # ------------------------------------------------------------------------

    original_by_product = defaultdict(list)

    for original_item in original_items:

        original_by_product[
            original_item.product_id
        ].append(original_item)

    # ------------------------------------------------------------------------
    # BUILD DETAIL ITEMS
    # ------------------------------------------------------------------------

    detail_items = []

    dispatched_quantity_total = 0
    dispatched_items_count = 0
    dispatchable_items_count = 0

    for crm_item in verified_items:

        original_item = None

        candidates = original_by_product.get(
            crm_item.product_id
        )

        if candidates:

            original_item = candidates.pop(
                0
            )

        dispatch = _get_dispatch_record(
            crm_item
        )

        dispatch_quantity = (
            int(dispatch.quantity)
            if dispatch
            else 0
        )

        if not crm_item.is_rejected:

            dispatchable_items_count += 1

            if dispatch:

                dispatched_items_count += 1

                dispatched_quantity_total += (
                    dispatch_quantity
                )

        detail_items.append({
            "crm_item_id": crm_item.id,

            "product_id": crm_item.product_id,

            "product_name": _product_name(
                crm_item.product
            ),

            "ordered_quantity": (
                original_item.quantity
                if original_item
                else 0
            ),

            "verified_quantity": (
                crm_item.quantity
            ),

            "rejected": bool(
                crm_item.is_rejected
            ),

            "dispatch_quantity": (
                dispatch_quantity
            ),

            "dispatch_location": (
                dispatch.dispatch_location
                if dispatch
                else None
            ),

            "order_packed_time": (
                dispatch.order_packed_time.isoformat()
                if (
                    dispatch
                    and dispatch.order_packed_time
                )
                else None
            ),
        })

    # ------------------------------------------------------------------------
    # REMAINING ORIGINAL ITEMS
    # ------------------------------------------------------------------------

    for remaining_items in (
        original_by_product.values()
    ):

        for original_item in remaining_items:

            detail_items.append({
                "crm_item_id": None,

                "product_id": (
                    original_item.product_id
                ),

                "product_name": _product_name(
                    original_item.product
                ),

                "ordered_quantity": (
                    original_item.quantity
                ),

                "verified_quantity": None,

                "rejected": False,

                "dispatch_quantity": 0,

                "dispatch_location": None,

                "order_packed_time": None,
            })

    # ------------------------------------------------------------------------
    # DISPATCH STATUS
    # ------------------------------------------------------------------------

    if dispatchable_items_count == 0:

        dispatch_status = (
            "NO_DISPATCH_REQUIRED"
        )

    elif dispatched_items_count == 0:

        dispatch_status = "PENDING"

    elif (
        dispatched_items_count
        >= dispatchable_items_count
    ):

        dispatch_status = "DISPATCHED"

    else:

        dispatch_status = "PARTIAL"

    # ------------------------------------------------------------------------
    # FINAL RESPONSE
    # ------------------------------------------------------------------------

    return {
        "order_id": order.order_id,

        "total_amount": str(
            order.total_amount
        ),

        "status": order.status or "",

        "created_at": (
            order.created_at.isoformat()
            if order.created_at
            else ""
        ),

        "ss_user": {
            "party_name": _user_display_name(
                order.ss_user
            ),

            "name": _user_display_name(
                order.ss_user
            ),

            "mobile": _user_mobile(
                order.ss_user
            ),
        },

        "crm_user": {
            "name": _user_display_name(
                verification.crm_user
            ),

            "mobile": _user_mobile(
                verification.crm_user
            ),
        },

        "verification": {
            "status": verification.status,

            "punched": bool(
                verification.punched
            ),

            "crm_name": _user_display_name(
                verification.crm_user
            ),

            "verified_at": (
                verification.verified_at.isoformat()
                if verification.verified_at
                else None
            ),

            "dispatch_location": (
                verification.dispatch_location
            ),
        },

        "summary": {
            "items_count": len(
                original_items
            ),

            "verified_items_count": len(
                verified_items
            ),

            "dispatchable_items_count": (
                dispatchable_items_count
            ),

            "dispatched_items_count": (
                dispatched_items_count
            ),

            "dispatched_quantity": (
                dispatched_quantity_total
            ),

            "dispatch_status": dispatch_status,
        },

        "items": detail_items,

        "note": order.note or "",

        "notes": order.notes or "",
    }


# ============================================================================
# LIST API
# ============================================================================

class OrderRecordsListView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    pagination_class = (
        OrderRecordPagination
    )

    def get(self, request):

        # ====================================================================
        # STEP 1
        # Lightweight role-filtered queryset
        #
        # IMPORTANT:
        # No item joins.
        # No dispatch joins.
        # No verification annotations.
        # ====================================================================

        queryset = _get_role_filtered_queryset(
            request.user
        )

        # ====================================================================
        # STEP 2
        # Apply requested filters
        # ====================================================================

        queryset = _apply_filters(
            queryset,
            request,
        )

        # ====================================================================
        # STEP 3
        # Stable ordering
        # ====================================================================

        queryset = queryset.order_by(
            "-created_at",
            "-pk",
        )

        # ====================================================================
        # STEP 4
        # PAGINATE FIRST
        #
        # This is the most important optimization.
        #
        # Database now selects ONLY current 50 orders.
        # ====================================================================

        paginator = self.pagination_class()

        page = paginator.paginate_queryset(
            queryset,
            request,
            view=self,
        )

        # ====================================================================
        # STEP 5
        # BULK ENRICH ONLY CURRENT PAGE
        # ====================================================================

        bulk_data = _build_bulk_list_data(
            page
        )

        # ====================================================================
        # STEP 6
        # SERIALIZE
        # ====================================================================

        data = _serialize_list_rows(
            page,
            bulk_data,
        )

        serializer = (
            OrderRecordListSerializer(
                data,
                many=True,
            )
        )

        return paginator.get_paginated_response(
            serializer.data
        )


# ============================================================================
# DETAIL API
# ============================================================================

class OrderRecordDetailView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request, pk):

        # --------------------------------------------------------------------
        # ROLE FILTER IS APPLIED AGAIN.
        #
        # So CRM/SS cannot access another user's order by changing URL ID.
        # --------------------------------------------------------------------

        queryset = _get_role_filtered_queryset(
            request.user
        )

        order = get_object_or_404(
            queryset,
            pk=pk,
        )

        data = _build_detail_response(
            order
        )

        serializer = (
            OrderRecordDetailSerializer(
                data
            )
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

# from collections import defaultdict

# from django.contrib.auth import get_user_model
# from django.core.exceptions import FieldDoesNotExist
# from django.db.models import (
#     Case,
#     CharField,
#     Count,
#     F,
#     IntegerField,
#     OuterRef,
#     Q,
#     Subquery,
#     Sum,
#     Value,
#     When,
# )
# from django.db.models.functions import Coalesce
# from django.shortcuts import get_object_or_404

# from rest_framework import status
# from rest_framework.exceptions import PermissionDenied
# from rest_framework.pagination import PageNumberPagination
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
# from rest_framework.views import APIView

# from .models import (
#     SSOrder,
#     SSOrderItem,
#     CRMVerifiedOrder,
#     CRMVerifiedOrderItem,
#     DispatchRecord,
# )

# from .order_records_serializers import (
#     OrderRecordListSerializer,
#     OrderRecordDetailSerializer,
# )


# User = get_user_model()


# # ============================================================
# # PAGINATION
# # ============================================================

# class OrderRecordPagination(PageNumberPagination):
#     page_size = 50
#     page_size_query_param = "page_size"
#     max_page_size = 100


# # ============================================================
# # USER HELPERS
# # ============================================================

# def _field_exists(model, field_name):
#     try:
#         model._meta.get_field(field_name)
#         return True
#     except FieldDoesNotExist:
#         return False


# def _user_display_name(user):
#     if not user:
#         return ""

#     for field in (
#         "party_name",
#         "name",
#         "username",
#         "email",
#     ):
#         value = getattr(user, field, None)

#         if value:
#             return str(value).strip()

#     first_name = getattr(user, "first_name", "") or ""
#     last_name = getattr(user, "last_name", "") or ""

#     full_name = f"{first_name} {last_name}".strip()

#     return full_name


# def _user_mobile(user):
#     if not user:
#         return ""

#     for field in (
#         "mobile",
#         "phone",
#         "phone_number",
#     ):
#         value = getattr(user, field, None)

#         if value:
#             return str(value)

#     return ""


# def _user_search_q(relation, value):
#     """
#     Builds a safe search query according to fields
#     actually existing on the custom User model.
#     """

#     query = Q()

#     searchable_fields = [
#         "party_name",
#         "name",
#         "username",
#         "first_name",
#         "last_name",
#         "email",
#         "mobile",
#         "phone",
#         "phone_number",
#     ]

#     for field in searchable_fields:
#         if _field_exists(User, field):
#             query |= Q(
#                 **{
#                     f"{relation}__{field}__icontains": value
#                 }
#             )

#     return query


# # ============================================================
# # ROLE
# # ============================================================

# def _get_user_role(user):
#     role = getattr(user, "role", None)

#     if role is None:
#         role = getattr(user, "user_type", None)

#     return str(role or "").upper().strip()


# def _is_admin(user):
#     return (
#         bool(getattr(user, "is_superuser", False))
#         or bool(getattr(user, "is_staff", False))
#         or _get_user_role(user) == "ADMIN"
#     )


# # ============================================================
# # BASE ROLE FILTER
# # ============================================================

# def _get_role_filtered_queryset(user):
#     """
#     IMPORTANT:
#     Role filtering happens directly in DB.
#     """

#     queryset = SSOrder.objects.select_related(
#         "ss_user",
#         "assigned_crm",
#     )

#     if _is_admin(user):
#         return queryset

#     role = _get_user_role(user)

#     if role == "CRM":
#         return queryset.filter(
#             assigned_crm=user
#         )

#     if role == "SS":
#         return queryset.filter(
#             ss_user=user
#         )

#     raise PermissionDenied(
#         "You are not allowed to access order records."
#     )


# # ============================================================
# # LATEST VERIFICATION SUBQUERY
# # ============================================================

# def _latest_verification_queryset():
#     return (
#         CRMVerifiedOrder.objects
#         .filter(
#             original_order=OuterRef("pk")
#         )
#         .order_by(
#             "-verified_at",
#             "-pk",
#         )
#     )


# # ============================================================
# # ANNOTATED LIST QUERYSET
# # ============================================================

# def _build_order_records_queryset(user):
#     queryset = _get_role_filtered_queryset(user)

#     latest_verification = _latest_verification_queryset()

#     latest_verification_id = Subquery(
#         latest_verification.values("id")[:1],
#         output_field=IntegerField(),
#     )

#     latest_verification_status = Subquery(
#         latest_verification.values("status")[:1],
#         output_field=CharField(),
#     )

#     latest_verification_punched = Subquery(
#         latest_verification.values("punched")[:1],
#     )

#     latest_verification_date = Subquery(
#         latest_verification.values("verified_at")[:1],
#     )

#     latest_dispatch_location = Subquery(
#         latest_verification.values("dispatch_location")[:1],
#         output_field=CharField(),
#     )

#     # --------------------------------------------------------
#     # VERIFIED ITEM COUNT
#     # --------------------------------------------------------

#     verified_item_count = Subquery(
#         CRMVerifiedOrderItem.objects
#         .filter(
#             crm_order_id=latest_verification_id
#         )
#         .order_by()
#         .values("crm_order_id")
#         .annotate(
#             total=Count("id")
#         )
#         .values("total")[:1],
#         output_field=IntegerField(),
#     )

#     # --------------------------------------------------------
#     # DISPATCHABLE ITEM COUNT
#     # --------------------------------------------------------

#     dispatchable_item_count = Subquery(
#         CRMVerifiedOrderItem.objects
#         .filter(
#             crm_order_id=latest_verification_id,
#             is_rejected=False,
#         )
#         .order_by()
#         .values("crm_order_id")
#         .annotate(
#             total=Count("id")
#         )
#         .values("total")[:1],
#         output_field=IntegerField(),
#     )

#     # --------------------------------------------------------
#     # DISPATCHED ITEM COUNT
#     # --------------------------------------------------------

#     dispatched_item_count = Subquery(
#         CRMVerifiedOrderItem.objects
#         .filter(
#             crm_order_id=latest_verification_id,
#             is_rejected=False,
#             dispatch_record__isnull=False,
#         )
#         .order_by()
#         .values("crm_order_id")
#         .annotate(
#             total=Count("id")
#         )
#         .values("total")[:1],
#         output_field=IntegerField(),
#     )

#     # --------------------------------------------------------
#     # DISPATCHED QUANTITY
#     # --------------------------------------------------------

#     dispatched_quantity = Subquery(
#         DispatchRecord.objects
#         .filter(
#             crm_item__crm_order_id=latest_verification_id
#         )
#         .order_by()
#         .values(
#             "crm_item__crm_order_id"
#         )
#         .annotate(
#             total=Sum("quantity")
#         )
#         .values("total")[:1],
#         output_field=IntegerField(),
#     )

#     queryset = queryset.annotate(
#         latest_verification_id=latest_verification_id,

#         latest_verification_status=latest_verification_status,

#         latest_verification_punched=latest_verification_punched,

#         latest_verification_date=latest_verification_date,

#         latest_dispatch_location=latest_dispatch_location,

#         items_count=Count(
#             "items",
#             distinct=True,
#         ),

#         verified_item_count=Coalesce(
#             verified_item_count,
#             Value(0),
#             output_field=IntegerField(),
#         ),

#         dispatchable_item_count=Coalesce(
#             dispatchable_item_count,
#             Value(0),
#             output_field=IntegerField(),
#         ),

#         dispatched_item_count=Coalesce(
#             dispatched_item_count,
#             Value(0),
#             output_field=IntegerField(),
#         ),

#         dispatched_quantity=Coalesce(
#             dispatched_quantity,
#             Value(0),
#             output_field=IntegerField(),
#         ),
#     )

#     # ========================================================
#     # DISPATCH STATUS
#     # ========================================================

#     queryset = queryset.annotate(
#         dispatch_status=Case(

#             When(
#                 latest_verification_id__isnull=True,
#                 then=Value("NOT_VERIFIED"),
#             ),

#             When(
#                 dispatchable_item_count=0,
#                 then=Value("NO_DISPATCH_REQUIRED"),
#             ),

#             When(
#                 dispatched_item_count=0,
#                 then=Value("PENDING"),
#             ),

#             When(
#                 dispatched_item_count__gte=F(
#                     "dispatchable_item_count"
#                 ),
#                 then=Value("DISPATCHED"),
#             ),

#             default=Value("PARTIAL"),

#             output_field=CharField(),
#         )
#     )

#     return queryset


# # ============================================================
# # DATE PARSER
# # ============================================================

# def _get_date(value):
#     if not value:
#         return None

#     try:
#         from datetime import date

#         return date.fromisoformat(value)

#     except (TypeError, ValueError):
#         return None


# # ============================================================
# # LIST FILTERS
# # ============================================================

# def _apply_filters(queryset, request):

#     # --------------------------------------------------------
#     # SEARCH
#     # --------------------------------------------------------

#     search = str(
#         request.query_params.get(
#             "search",
#             ""
#         )
#     ).strip()

#     if search:

#         search_query = Q(
#             order_id__icontains=search
#         )

#         search_query |= _user_search_q(
#             "ss_user",
#             search
#         )

#         search_query |= _user_search_q(
#             "assigned_crm",
#             search
#         )

#         queryset = queryset.filter(
#             search_query
#         )

#     # --------------------------------------------------------
#     # PARTY
#     # --------------------------------------------------------

#     party = str(
#         request.query_params.get(
#             "party",
#             ""
#         )
#     ).strip()

#     if party:

#         party_query = _user_search_q(
#             "ss_user",
#             party
#         )

#         queryset = queryset.filter(
#             party_query
#         )

#     # --------------------------------------------------------
#     # ORIGINAL ORDER STATUS
#     # --------------------------------------------------------

#     order_status = str(
#         request.query_params.get(
#             "status",
#             ""
#         )
#     ).strip()

#     if order_status:
#         queryset = queryset.filter(
#             status__iexact=order_status
#         )

#     # --------------------------------------------------------
#     # VERIFICATION STATUS
#     # --------------------------------------------------------

#     verification_status = str(
#         request.query_params.get(
#             "verification_status",
#             ""
#         )
#     ).strip()

#     if verification_status:
#         queryset = queryset.filter(
#             latest_verification_status__iexact=
#             verification_status
#         )

#     # --------------------------------------------------------
#     # PUNCHED
#     # --------------------------------------------------------

#     punched = str(
#         request.query_params.get(
#             "punched",
#             ""
#         )
#     ).strip().lower()

#     if punched in {
#         "true",
#         "1",
#         "yes",
#     }:

#         queryset = queryset.filter(
#             latest_verification_punched=True
#         )

#     elif punched in {
#         "false",
#         "0",
#         "no",
#     }:

#         queryset = queryset.filter(
#             latest_verification_punched=False
#         )

#     # --------------------------------------------------------
#     # DISPATCH
#     # --------------------------------------------------------

#     dispatch = str(
#         request.query_params.get(
#             "dispatch",
#             ""
#         )
#     ).strip().upper()

#     allowed_dispatch_statuses = {
#         "NOT_VERIFIED",
#         "NO_DISPATCH_REQUIRED",
#         "PENDING",
#         "PARTIAL",
#         "DISPATCHED",
#     }

#     if dispatch in allowed_dispatch_statuses:

#         queryset = queryset.filter(
#             dispatch_status=dispatch
#         )

#     # --------------------------------------------------------
#     # FROM DATE
#     # --------------------------------------------------------

#     from_date = _get_date(
#         request.query_params.get(
#             "from_date"
#         )
#     )

#     if from_date:

#         queryset = queryset.filter(
#             created_at__date__gte=from_date
#         )

#     # --------------------------------------------------------
#     # TO DATE
#     # --------------------------------------------------------

#     to_date = _get_date(
#         request.query_params.get(
#             "to_date"
#         )
#     )

#     if to_date:

#         queryset = queryset.filter(
#             created_at__date__lte=to_date
#         )

#     return queryset


# # ============================================================
# # LIST SERIALIZATION
# # ============================================================

# def _serialize_list_row(order):

#     total_amount = order.total_amount

#     return {
#         "id": order.id,

#         "order_id": order.order_id,

#         "ss_party_name": _user_display_name(
#             order.ss_user
#         ),

#         "ss_user_name": _user_display_name(
#             order.ss_user
#         ),

#         "crm_name": _user_display_name(
#             order.assigned_crm
#         ),

#         "total_amount": str(
#             total_amount
#         ),

#         "status": order.status or "",

#         "verification_status":
#             getattr(
#                 order,
#                 "latest_verification_status",
#                 None,
#             ),

#         "punched":
#             getattr(
#                 order,
#                 "latest_verification_punched",
#                 None,
#             ),

#         "items_count":
#             int(
#                 getattr(
#                     order,
#                     "items_count",
#                     0
#                 ) or 0
#             ),
#             "verified_items_count": int(
#     getattr(order, "verified_item_count", 0) or 0
# ),
#         "dispatched_items_count":
#             int(
#                 getattr(
#                     order,
#                     "dispatched_item_count",
#                     0
#                 ) or 0
#             ),

#         "dispatched_quantity":
#             int(
#                 getattr(
#                     order,
#                     "dispatched_quantity",
#                     0
#                 ) or 0
#             ),

#         "dispatch_status":
#             getattr(
#                 order,
#                 "dispatch_status",
#                 "NOT_VERIFIED",
#             ),

#         "created_at":
#             order.created_at.isoformat()
#             if order.created_at
#             else "",
#     }


# # ============================================================
# # DETAIL HELPERS
# # ============================================================

# def _product_name(product):

#     if not product:
#         return ""

#     for field in (
#         "product_name",
#         "name",
#         "title",
#     ):

#         value = getattr(
#             product,
#             field,
#             None
#         )

#         if value:
#             return str(value)

#     return str(product)


# def _get_dispatch_record(crm_item):

#     try:
#         return crm_item.dispatch_record

#     except DispatchRecord.DoesNotExist:
#         return None


# # ============================================================
# # DETAIL QUERY
# # ============================================================

# def _get_latest_verification(order):

#     return (
#         CRMVerifiedOrder.objects
#         .filter(
#             original_order=order
#         )
#         .select_related(
#             "crm_user"
#         )
#         .prefetch_related(
#             "items__product"
#         )
#         .order_by(
#             "-verified_at",
#             "-pk",
#         )
#         .first()
#     )


# # ============================================================
# # DETAIL RESPONSE
# # ============================================================

# def _build_detail_response(order):

#     original_items = list(
#         order.items
#         .select_related("product")
#         .all()
#     )

#     verification = _get_latest_verification(
#         order
#     )

#     # ========================================================
#     # NO VERIFICATION YET
#     # ========================================================

#     if not verification:

#         detail_items = []

#         for original_item in original_items:

#             detail_items.append({
#                 "crm_item_id": None,

#                 "product_id":
#                     original_item.product_id,

#                 "product_name":
#                     _product_name(
#                         original_item.product
#                     ),

#                 "ordered_quantity":
#                     original_item.quantity,

#                 "verified_quantity":
#                     None,

#                 "rejected": False,

#                 "dispatch_quantity": 0,

#                 "dispatch_location": None,

#                 "order_packed_time": None,
#             })

#         summary = {
#             "items_count": len(
#                 original_items
#             ),

#             "verified_items_count": 0,

#             "dispatchable_items_count": 0,

#             "dispatched_items_count": 0,

#             "dispatched_quantity": 0,

#             "dispatch_status":
#                 "NOT_VERIFIED",
#         }

#         return {
#             "order_id": order.order_id,

#             "total_amount":
#                 str(order.total_amount),

#             "status":
#                 order.status or "",

#             "created_at":
#                 order.created_at.isoformat()
#                 if order.created_at
#                 else "",

#             "ss_user": {
#                 "party_name":
#                     _user_display_name(
#                         order.ss_user
#                     ),

#                 "name":
#                     _user_display_name(
#                         order.ss_user
#                     ),

#                 "mobile":
#                     _user_mobile(
#                         order.ss_user
#                     ),
#             },

#             "crm_user": {
#                 "name": "",
#                 "mobile": "",
#             },

#             "verification": None,

#             "summary": summary,

#             "items": detail_items,

#             "note":
#                 order.note or "",

#             "notes":
#                 order.notes or "",
#         }

#     # ========================================================
#     # VERIFIED ITEMS
#     # ========================================================

#     verified_items = list(
#         verification.items
#         .select_related("product")
#         .prefetch_related("dispatch_record")
#         .all()
#     )

#     # ========================================================
#     # MATCH ORIGINAL ITEMS
#     # ========================================================

#     original_by_product = defaultdict(list)

#     for item in original_items:

#         original_by_product[
#             item.product_id
#         ].append(item)

#     detail_items = []

#     dispatched_quantity_total = 0

#     dispatched_items_count = 0

#     dispatchable_items_count = 0

#     for crm_item in verified_items:

#         original_item = None

#         candidates = original_by_product.get(
#             crm_item.product_id
#         )

#         if candidates:

#             original_item = candidates.pop(0)

#         dispatch = _get_dispatch_record(
#             crm_item
#         )

#         dispatch_quantity = (
#             int(dispatch.quantity)
#             if dispatch
#             else 0
#         )

#         if not crm_item.is_rejected:

#             dispatchable_items_count += 1

#             if dispatch:

#                 dispatched_items_count += 1

#                 dispatched_quantity_total += (
#                     dispatch_quantity
#                 )

#         detail_items.append({

#             "crm_item_id":
#                 crm_item.id,

#             "product_id":
#                 crm_item.product_id,

#             "product_name":
#                 _product_name(
#                     crm_item.product
#                 ),

#             "ordered_quantity":
#                 (
#                     original_item.quantity
#                     if original_item
#                     else 0
#                 ),

#             "verified_quantity":
#                 crm_item.quantity,

#             "rejected":
#                 bool(
#                     crm_item.is_rejected
#                 ),

#             "dispatch_quantity":
#                 dispatch_quantity,

#             "dispatch_location":
#                 (
#                     dispatch.dispatch_location
#                     if dispatch
#                     else None
#                 ),

#             "order_packed_time":
#                 (
#                     dispatch.order_packed_time.isoformat()
#                     if dispatch
#                     and dispatch.order_packed_time
#                     else None
#                 ),
#         })

#     # ========================================================
#     # ORIGINAL ITEMS THAT DID NOT HAVE CRM ITEM
#     # ========================================================

#     for product_id, remaining_items in (
#         original_by_product.items()
#     ):

#         for original_item in remaining_items:

#             detail_items.append({

#                 "crm_item_id": None,

#                 "product_id":
#                     original_item.product_id,

#                 "product_name":
#                     _product_name(
#                         original_item.product
#                     ),

#                 "ordered_quantity":
#                     original_item.quantity,

#                 "verified_quantity":
#                     None,

#                 "rejected": False,

#                 "dispatch_quantity": 0,

#                 "dispatch_location": None,

#                 "order_packed_time": None,
#             })

#     # ========================================================
#     # DISPATCH STATUS
#     # ========================================================

#     if dispatchable_items_count == 0:

#         dispatch_status = (
#             "NO_DISPATCH_REQUIRED"
#         )

#     elif dispatched_items_count == 0:

#         dispatch_status = "PENDING"

#     elif (
#         dispatched_items_count
#         >= dispatchable_items_count
#     ):

#         dispatch_status = "DISPATCHED"

#     else:

#         dispatch_status = "PARTIAL"

#     # ========================================================
#     # FINAL RESPONSE
#     # ========================================================

#     return {

#         "order_id":
#             order.order_id,

#         "total_amount":
#             str(order.total_amount),

#         "status":
#             order.status or "",

#         "created_at":
#             order.created_at.isoformat()
#             if order.created_at
#             else "",

#         "ss_user": {

#             "party_name":
#                 _user_display_name(
#                     order.ss_user
#                 ),

#             "name":
#                 _user_display_name(
#                     order.ss_user
#                 ),

#             "mobile":
#                 _user_mobile(
#                     order.ss_user
#                 ),
#         },

#         "crm_user": {

#             "name":
#                 _user_display_name(
#                     verification.crm_user
#                 ),

#             "mobile":
#                 _user_mobile(
#                     verification.crm_user
#                 ),
#         },

#         "verification": {

#             "status":
#                 verification.status,

#             "punched":
#                 bool(
#                     verification.punched
#                 ),

#             "crm_name":
#                 _user_display_name(
#                     verification.crm_user
#                 ),

#             "verified_at":
#                 (
#                     verification.verified_at.isoformat()
#                     if verification.verified_at
#                     else None
#                 ),
#                 "dispatch_location": verification.dispatch_location,
#         },

#         "summary": {

#             "items_count":
#                 len(original_items),

#             "verified_items_count":
#                 len(verified_items),

#             "dispatchable_items_count":
#                 dispatchable_items_count,

#             "dispatched_items_count":
#                 dispatched_items_count,

#             "dispatched_quantity":
#                 dispatched_quantity_total,

#             "dispatch_status":
#                 dispatch_status,
#         },

#         "items":
#             detail_items,

#         "note":
#             order.note or "",

#         "notes":
#             order.notes or "",
#     }


# # ============================================================
# # LIST API
# # ============================================================

# class OrderRecordsListView(APIView):

#     permission_classes = [
#         IsAuthenticated
#     ]

#     pagination_class = (
#         OrderRecordPagination
#     )

#     def get(self, request):

#         queryset = _build_order_records_queryset(
#             request.user
#         )

#         queryset = _apply_filters(
#             queryset,
#             request
#         )

#         queryset = queryset.order_by(
#             "-created_at",
#             "-pk",
#         )

#         paginator = self.pagination_class()

#         page = paginator.paginate_queryset(
#             queryset,
#             request,
#             view=self,
#         )

#         data = [
#             _serialize_list_row(order)
#             for order in page
#         ]

#         serializer = OrderRecordListSerializer(
#             data,
#             many=True,
#         )

#         return paginator.get_paginated_response(
#             serializer.data
#         )


# # ============================================================
# # DETAIL API
# # ============================================================

# class OrderRecordDetailView(APIView):

#     permission_classes = [
#         IsAuthenticated
#     ]

#     def get(self, request, pk):

#         queryset = _get_role_filtered_queryset(
#             request.user
#         )

#         order = get_object_or_404(
#             queryset,
#             pk=pk,
#         )

#         data = _build_detail_response(
#             order
#         )

#         serializer = OrderRecordDetailSerializer(
#             data
#         )

#         return Response(
#             serializer.data,
#             status=status.HTTP_200_OK,
#         )

