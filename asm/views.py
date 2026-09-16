from django.db.models import (
    Count,
    Sum,
    Q,
    Prefetch,
)
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.models import CustomUser
from orders.models import (
    SSOrder,
    SSOrderItem,
    CRMVerifiedOrder,
    CRMVerifiedOrderItem,
    DispatchOrder,
)

from .models import ASMSSAssignment
from .permissions import (
    IsASM,
    IsCRMOrAdminForASMAssignment,
)
from .serializers import (
    ASMSSAssignmentSerializer,
)


# =========================================================
# HELPERS
# =========================================================

def _get_assigned_ss_ids(asm_user):
    """
    Returns active SS IDs assigned to this ASM.

    Values-list queryset is intentionally returned so it can
    be reused directly inside another queryset without first
    loading all IDs into Python.
    """
    return ASMSSAssignment.objects.filter(
        asm=asm_user,
        is_active=True,
        ss__is_active=True,
        ss__role="SS",
    ).values_list("ss_id", flat=True)


def _serialize_order_items(order):
    """
    Serialize SS order items.
    Product is already select_related by caller.
    """
    return [
        {
            "product_id": item.product.product_id,
            "product_name": item.product.product_name,
            "quantity": item.quantity,
            "price": item.price,
            "is_scheme_item": item.is_scheme_item,
        }
        for item in order.items.all()
    ]


def _serialize_crm_summary(crm_record):
    """
    Lightweight CRM verification summary.
    """
    if not crm_record:
        return None

    return {
        "id": crm_record.id,
        "name": crm_record.crm_user.name,
        "status": crm_record.status,
        "verified_at": crm_record.verified_at,
        "punched": crm_record.punched,
        "dispatch_location": crm_record.dispatch_location,
    }


# =========================================================
# CRM / ADMIN
# ASSIGN SS TO ASM
# =========================================================

class ASMSSAssignmentCreateView(APIView):
    """
    CRM / ADMIN can assign an SS to an ASM.
    """

    permission_classes = [
        IsAuthenticated,
        IsCRMOrAdminForASMAssignment,
    ]

    def post(self, request):
        serializer = ASMSSAssignmentSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        assignment = serializer.save()

        return Response(
            ASMSSAssignmentSerializer(
                assignment,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


# =========================================================
# CRM / ADMIN
# LIST ASSIGNMENTS
# =========================================================

class ASMSSAssignmentListView(APIView):
    """
    Returns active ASM ↔ SS assignments.

    CRM:
        Only its own SS assignments.

    ADMIN:
        All active assignments.
    """

    permission_classes = [
        IsAuthenticated,
        IsCRMOrAdminForASMAssignment,
    ]

    def get(self, request):

        queryset = (
            ASMSSAssignment.objects
            .filter(
                is_active=True,
                ss__is_active=True,
                ss__role="SS",
                asm__is_active=True,
                asm__role="ASM",
            )
            .select_related("asm", "ss")
            .order_by(
                "asm__name",
                "ss__party_name",
                "ss__name",
            )
        )

        if request.user.role == "CRM":
            queryset = queryset.filter(
                ss__crm_id=request.user.id
            )

        serializer = ASMSSAssignmentSerializer(
            queryset,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)


# =========================================================
# CRM / ADMIN
# DEACTIVATE ASSIGNMENT
# =========================================================

class ASMSSAssignmentDeactivateView(APIView):
    """
    Soft-deactivates an ASM ↔ SS assignment.

    Historical row remains in database.
    """

    permission_classes = [
        IsAuthenticated,
        IsCRMOrAdminForASMAssignment,
    ]

    def patch(self, request, pk):

        assignment = get_object_or_404(
            ASMSSAssignment.objects.select_related("asm", "ss"),
            pk=pk,
            is_active=True,
        )

        # CRM can only modify assignments belonging
        # to its own SS users.
        if (
            request.user.role == "CRM"
            and assignment.ss.crm_id != request.user.id
        ):
            return Response(
                {"detail": "You cannot modify this assignment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        assignment.is_active = False
        assignment.save(update_fields=["is_active"])

        return Response({
            "success": True,
            "message": "SS unassigned from ASM.",
        })


# =========================================================
# ASM DASHBOARD
# =========================================================

class ASMDashboardView(APIView):
    """
    Main ASM dashboard endpoint.

    One API provides:
      - dashboard summary
      - assigned SS list
      - product totals
      - latest 30 orders

    Performance:
      - No API-per-SS pattern
      - Only latest 30 orders load detailed data
      - Dispatch count uses one query
      - Aggregations are handled by database
      - No N+1 dispatch query
    """

    permission_classes = [
        IsAuthenticated,
        IsASM,
    ]

    def get(self, request):

        asm = request.user

        # -------------------------------------------------
        # ACTIVE ASSIGNMENTS
        # -------------------------------------------------

        assignments = list(
            ASMSSAssignment.objects
            .filter(
                asm=asm,
                is_active=True,
                ss__is_active=True,
                ss__role="SS",
            )
            .select_related("ss")
            .order_by(
                "ss__party_name",
                "ss__name",
            )
        )

        ss_ids = [assignment.ss_id for assignment in assignments]

        # -------------------------------------------------
        # NO ASSIGNED SS
        # -------------------------------------------------

        if not ss_ids:
            return Response({
                "summary": {
                    "ss_count": 0,
                    "order_count": 0,
                    "pending_count": 0,
                    "verified_count": 0,
                    "dispatched_count": 0,
                },
                "ss_list": [],
                "product_totals": [],
                "recent_orders": [],
            })

        # -------------------------------------------------
        # ORDER SUMMARY
        # -------------------------------------------------

        order_stats = (
            SSOrder.objects
            .filter(
                ss_user_id__in=ss_ids
            )
            .aggregate(
                total=Count("id"),
                pending=Count(
                    "id",
                    filter=Q(status="PENDING"),
                ),
            )
        )

        # -------------------------------------------------
        # VERIFIED COUNT
        # -------------------------------------------------

        verified_count = (
            CRMVerifiedOrder.objects
            .filter(
                original_order__ss_user_id__in=ss_ids,
                status="APPROVED",
            )
            .count()
        )

        # -------------------------------------------------
        # DISPATCH COUNT
        #
        # IMPORTANT:
        # DispatchOrder.order_id is CharField.
        #
        # CRMVerifiedOrder.id is Integer.
        #
        # Therefore we convert CRM IDs to strings BEFORE
        # sending them to PostgreSQL.
        #
        # Existing relationship is preserved:
        # DispatchOrder.order_id = str(CRMVerifiedOrder.id)
        # -------------------------------------------------

        verified_ids = list(
            CRMVerifiedOrder.objects
            .filter(
                original_order__ss_user_id__in=ss_ids
            )
            .values_list("id", flat=True)
        )

        dispatched_count = 0

        if verified_ids:

            dispatch_order_ids = [
                str(verified_id)
                for verified_id in verified_ids
            ]

            dispatched_count = (
                DispatchOrder.objects
                .filter(
                    order_id__in=dispatch_order_ids
                )
                .values("order_id")
                .distinct()
                .count()
            )

        # -------------------------------------------------
        # PRODUCT TOTALS
        # -------------------------------------------------

        product_totals = (
            SSOrderItem.objects
            .filter(
                order__ss_user_id__in=ss_ids
            )
            .values(
                "product_id",
                "product__product_name",
            )
            .annotate(
                total_quantity=Sum("quantity"),
            )
            .order_by("-total_quantity")
        )

        # -------------------------------------------------
        # SS STATISTICS
        # -------------------------------------------------

        ss_order_stats = (
            SSOrder.objects
            .filter(
                ss_user_id__in=ss_ids
            )
            .values("ss_user_id")
            .annotate(
                order_count=Count("id"),
                total_amount=Sum("total_amount"),
                pending_count=Count(
                    "id",
                    filter=Q(status="PENDING"),
                ),
            )
        )

        ss_stats_map = {
            row["ss_user_id"]: row
            for row in ss_order_stats
        }

        # -------------------------------------------------
        # SS LIST
        # -------------------------------------------------

        ss_list = []

        for assignment in assignments:

            ss = assignment.ss

            stats = ss_stats_map.get(
                ss.id,
                {
                    "order_count": 0,
                    "total_amount": 0,
                    "pending_count": 0,
                },
            )

            ss_list.append({
                "assignment_id": assignment.id,
                "ss_id": ss.id,
                "user_id": ss.user_id,
                "name": ss.name,
                "party_name": ss.party_name,
                "mobile": ss.mobile,
                "order_count": stats["order_count"] or 0,
                "pending_count": stats["pending_count"] or 0,
                "total_amount": stats["total_amount"] or 0,
            })

        # -------------------------------------------------
        # RECENT ORDER IDS
        #
        # Only latest 30 orders are loaded with their
        # related items + CRM history.
        #
        # This prevents the dashboard from loading thousands
        # of historical order records.
        # -------------------------------------------------

        recent_order_ids = list(
            SSOrder.objects
            .filter(
                ss_user_id__in=ss_ids
            )
            .order_by("-created_at")
            .values_list("id", flat=True)[:30]
        )

        recent_orders = []

        if recent_order_ids:

            # -------------------------------------------------
            # LOAD ONLY LATEST 30 ORDERS
            # -------------------------------------------------

            orders_queryset = (
                SSOrder.objects
                .filter(
                    id__in=recent_order_ids
                )
                .select_related(
                    "ss_user",
                    "assigned_crm",
                )
                .prefetch_related(
                    # -----------------------------------------
                    # ORDER ITEMS
                    # -----------------------------------------

                    Prefetch(
                        "items",
                        queryset=(
                            SSOrderItem.objects
                            .select_related("product")
                        ),
                    ),

                    # -----------------------------------------
                    # CRM HISTORY
                    #
                    # Dashboard only needs latest CRM record,
                    # but we keep all CRM versions available
                    # here to preserve current response logic.
                    # -----------------------------------------

                    Prefetch(
                        "crm_verified_versions",
                        queryset=(
                            CRMVerifiedOrder.objects
                            .select_related("crm_user")
                            .order_by("-verified_at")
                        ),
                        to_attr="asm_crm_versions",
                    ),
                )
            )

            # -------------------------------------------------
            # MAP ORDERS
            #
            # __in does not guarantee original ordering,
            # so restore newest-first order using IDs.
            # -------------------------------------------------

            orders_map = {
                order.id: order
                for order in orders_queryset
            }

            # -------------------------------------------------
            # SERIALIZE RECENT ORDERS
            # -------------------------------------------------

            for order_id in recent_order_ids:

                order = orders_map.get(order_id)

                if not order:
                    continue

                crm_versions = getattr(
                    order,
                    "asm_crm_versions",
                    [],
                )

                latest_crm = (
                    crm_versions[0]
                    if crm_versions
                    else None
                )

                recent_orders.append({
                    "id": order.id,
                    "order_id": order.order_id,

                    "ss_id": order.ss_user_id,
                    "ss_name": order.ss_user.name,
                    "ss_party_name": order.ss_user.party_name,

                    "created_at": order.created_at,
                    "status": order.status,
                    "total_amount": order.total_amount,

                    "crm": (
                        {
                            "id": latest_crm.id,
                            "name": latest_crm.crm_user.name,
                            "status": latest_crm.status,
                            "verified_at": latest_crm.verified_at,
                            "punched": latest_crm.punched,
                            "dispatch_location": latest_crm.dispatch_location,
                        }
                        if latest_crm
                        else None
                    ),

                    "items": [
                        {
                            "product_id": item.product.product_id,
                            "product_name": item.product.product_name,
                            "quantity": item.quantity,
                            "price": item.price,
                            "is_scheme_item": item.is_scheme_item,
                        }
                        for item in order.items.all()
                    ],
                })

        # -------------------------------------------------
        # FINAL RESPONSE
        # -------------------------------------------------

        return Response({
            "summary": {
                "ss_count": len(ss_list),
                "order_count": order_stats["total"] or 0,
                "pending_count": order_stats["pending"] or 0,
                "verified_count": verified_count,
                "dispatched_count": dispatched_count,
            },

            "ss_list": ss_list,

            "product_totals": [
                {
                    "product_id": row["product_id"],
                    "product_name": row["product__product_name"],
                    "total_quantity": row["total_quantity"] or 0,
                }
                for row in product_totals
            ],

            "recent_orders": recent_orders,
        })
# =========================================================
# ASM → SINGLE SS DETAILS
# =========================================================

class ASMSSDetailView(APIView):
    """
    Detailed information for one assigned SS.

    Existing response structure is preserved.
    """

    permission_classes = [
        IsAuthenticated,
        IsASM,
    ]

    def get(self, request, ss_id):

        # -------------------------------------------------
        # AUTHORIZATION + SS FETCH
        # -------------------------------------------------

        assignment_exists = ASMSSAssignment.objects.filter(
            asm=request.user,
            ss_id=ss_id,
            is_active=True,
            ss__is_active=True,
            ss__role="SS",
        ).exists()

        if not assignment_exists:
            return Response(
                {"detail": "This SS is not assigned to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ss = get_object_or_404(
            CustomUser.objects.only(
                "id",
                "user_id",
                "name",
                "party_name",
                "mobile",
                "role",
                "is_active",
            ),
            id=ss_id,
            role="SS",
            is_active=True,
        )

        # -------------------------------------------------
        # ORDER STATS
        # -------------------------------------------------

        order_stats = (
            SSOrder.objects
            .filter(ss_user_id=ss.id)
            .aggregate(
                order_count=Count("id"),
                total_amount=Sum("total_amount"),
                pending_count=Count(
                    "id",
                    filter=Q(status="PENDING"),
                ),
            )
        )

        # -------------------------------------------------
        # PRODUCT TOTALS
        # -------------------------------------------------

        product_totals = (
            SSOrderItem.objects
            .filter(
                order__ss_user_id=ss.id
            )
            .values(
                "product_id",
                "product__product_name",
            )
            .annotate(
                total_quantity=Sum("quantity")
            )
            .order_by("-total_quantity")
        )

        # -------------------------------------------------
        # ORDERS
        #
        # Still returning all orders to preserve current
        # frontend response contract.
        #
        # Later, if history becomes very large, pagination
        # can be added without changing the dashboard.
        # -------------------------------------------------

        orders = (
            SSOrder.objects
            .filter(
                ss_user_id=ss.id
            )
            .select_related(
                "ss_user",
                "assigned_crm",
            )
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=SSOrderItem.objects
                    .select_related("product"),
                ),
                Prefetch(
                    "crm_verified_versions",
                    queryset=CRMVerifiedOrder.objects
                    .select_related("crm_user")
                    .order_by("-verified_at"),
                    to_attr="asm_crm_versions",
                ),
            )
            .order_by("-created_at")
        )

        order_data = []

        for order in orders:

            crm_versions = getattr(
                order,
                "asm_crm_versions",
                [],
            )

            latest_crm = (
                crm_versions[0]
                if crm_versions
                else None
            )

            order_data.append({
                "id": order.id,
                "order_id": order.order_id,
                "created_at": order.created_at,
                "status": order.status,
                "total_amount": order.total_amount,

                "crm": _serialize_crm_summary(
                    latest_crm
                ),

                "items": _serialize_order_items(
                    order
                ),
            })

        return Response({
            "ss": {
                "id": ss.id,
                "user_id": ss.user_id,
                "name": ss.name,
                "party_name": ss.party_name,
                "mobile": ss.mobile,
            },

            "summary": {
                "order_count": order_stats["order_count"] or 0,
                "total_amount": order_stats["total_amount"] or 0,
                "pending_count": order_stats["pending_count"] or 0,
            },

            "product_totals": [
                {
                    "product_id": row["product_id"],
                    "product_name": row["product__product_name"],
                    "total_quantity": row["total_quantity"] or 0,
                }
                for row in product_totals
            ],

            "orders": order_data,
        })


# =========================================================
# ASM → SINGLE ORDER DETAILS
# =========================================================

class ASMOrderDetailView(APIView):
    """
    Detailed lifecycle information for one order.

    ASM can only open an order belonging to an actively
    assigned SS.
    """

    permission_classes = [
        IsAuthenticated,
        IsASM,
    ]

    def get(self, request, order_id):

        # -------------------------------------------------
        # ORDER
        # -------------------------------------------------

        order = get_object_or_404(
            SSOrder.objects
            .filter(
                ss_user_id__in=_get_assigned_ss_ids(
                    request.user
                )
            )
            .select_related(
                "ss_user",
                "assigned_crm",
            )
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=SSOrderItem.objects
                    .select_related("product"),
                ),
                Prefetch(
                    "crm_verified_versions",
                    queryset=CRMVerifiedOrder.objects
                    .select_related("crm_user")
                    .prefetch_related(
                        Prefetch(
                            "items",
                            queryset=CRMVerifiedOrderItem.objects
                            .filter(is_rejected=False)
                            .select_related("product"),
                        )
                    )
                    .order_by("-verified_at"),
                    to_attr="asm_crm_versions",
                ),
            ),
            order_id=order_id,
        )

        crm_versions = getattr(
            order,
            "asm_crm_versions",
            [],
        )

        # -------------------------------------------------
        # DISPATCH OPTIMIZATION
        #
        # OLD:
        # One DispatchOrder query per CRM version.
        #
        # NEW:
        # One DispatchOrder query for all CRM versions.
        # -------------------------------------------------

        crm_ids = [
            crm.id
            for crm in crm_versions
        ]

        dispatch_map = {}

        if crm_ids:

            dispatch_rows = (
                DispatchOrder.objects
                .filter(
                    order_id__in=[
                        str(crm_id)
                        for crm_id in crm_ids
                    ]
                )
                .values(
                    "order_id",
                    "product",
                    "quantity",
                    "order_packed_time",
                )
            )

            for row in dispatch_rows:

                dispatch_map.setdefault(
                    row["order_id"],
                    []
                ).append({
                    "product": row["product"],
                    "quantity": row["quantity"],
                    "order_packed_time": row[
                        "order_packed_time"
                    ],
                })

        # -------------------------------------------------
        # CRM HISTORY
        # -------------------------------------------------

        crm_data = []

        for crm_record in crm_versions:

            crm_dispatch = dispatch_map.get(
                str(crm_record.id),
                [],
            )

            crm_data.append({
                "id": crm_record.id,
                "crm_name": crm_record.crm_user.name,
                "status": crm_record.status,
                "verified_at": crm_record.verified_at,
                "punched": crm_record.punched,
                "dispatch_location": crm_record.dispatch_location,

                "items": [
                    {
                        "product_id": item.product.product_id,
                        "product_name": item.product.product_name,
                        "quantity": item.quantity,
                        "is_rejected": item.is_rejected,
                    }
                    for item in crm_record.items.all()
                ],

                "dispatch": crm_dispatch,
            })

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return Response({
            "order": {
                "id": order.id,
                "order_id": order.order_id,
                "created_at": order.created_at,
                "status": order.status,
                "total_amount": order.total_amount,

                "ss": {
                    "id": order.ss_user.id,
                    "user_id": order.ss_user.user_id,
                    "name": order.ss_user.name,
                    "party_name": order.ss_user.party_name,
                    "mobile": order.ss_user.mobile,
                },

                "crm_assigned": (
                    {
                        "id": order.assigned_crm.id,
                        "name": order.assigned_crm.name,
                        "user_id": order.assigned_crm.user_id,
                    }
                    if order.assigned_crm
                    else None
                ),

                "items": [
                    {
                        "product_id": item.product.product_id,
                        "product_name": item.product.product_name,
                        "quantity": item.quantity,
                        "price": item.price,
                        "is_scheme_item": item.is_scheme_item,
                        "ss_virtual_stock": item.ss_virtual_stock,
                    }
                    for item in order.items.all()
                ],

                "crm_history": crm_data,
            }
        })