from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import DSOrder, DSOrderItem, Product
from .serializers import DSOrderSerializer

import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class DSOrderCreateView(APIView):
   

    @transaction.atomic
    def post(self, request):
        try:
            data = request.data

            # ✅ Validate user
            ds_user = get_object_or_404(User, id=data.get("user_id"))

            items = data.get("items", [])
            scheme_items = data.get("eligibleSchemes", [])

            if not items:
                return Response(
                    {"error": "No items provided"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ✅ Calculate total amount (ONLY paid items)
            total_amount = sum(
                (item.get("price", 0) or 0) * item.get("quantity", 0)
                for item in items
            )

            # ✅ Create SINGLE Order
            order = DSOrder.objects.create(
                ds_user=ds_user,
                total_amount=total_amount,
                note="Order Created"
            )

            # ✅ Insert normal order items
            for item in items:
                product = get_object_or_404(Product, product_id=item["id"])

                DSOrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.get("quantity", 0),
                    price=item.get("price", 0) or 0,
                    is_scheme_item=False,
                    ds_virtual_stock=item.get(
                        "ds_virtual_stock",
                        getattr(product, "stock_quantity", 0)
                    )
                )

            # ✅ Insert scheme items (price = 0)
            for reward in scheme_items:
                product_id = (
                    reward.get("product_id")
                    or reward.get("product", {}).get("id")
                    if isinstance(reward.get("product"), dict)
                    else reward.get("product")
                )

                if not product_id:
                    continue

                try:
                    product = Product.objects.get(product_id=product_id)
                except Product.DoesNotExist:
                    continue

                DSOrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=reward.get("quantity", 0),
                    price=0,
                    is_scheme_item=True,
                    ds_virtual_stock=getattr(
                        product,
                        "virtual_stock",
                        getattr(product, "stock_quantity", 0)
                    )
                )

            # ✅ Response
            return Response(
                {
                    "message": "Order placed successfully",
                    "order": DSOrderSerializer(order).data,
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.exception("❌ Error while creating order")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class DSMyLatestOrdersView(APIView):
    """
    ✅ DS can see only his own latest 10 orders
    ✅ Optimized with prefetch
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user  # DS user

        orders = (
            DSOrder.objects
            .filter(ds_user=user)
            .prefetch_related(
                Prefetch("items", queryset=DSOrderItem.objects.select_related("product"))
            )
            .order_by("-created_at")[:10]
        )

        serializer = DSOrderSerializer(orders, many=True)

        return Response(
            {
                "count": len(serializer.data),
                "orders": serializer.data
            }
        )
