from django.db.models import (
    Count,
    Q,
    OuterRef,
    Subquery,
)
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.models import CustomUser
from orders.models import (
    SSOrder,
    CRMVerifiedOrder,
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
    Active SS IDs assigned to this ASM.

    Returned as a queryset so it can be used directly
    inside SSOrder filters without loading IDs into Python.
    """
    return (
        ASMSSAssignment.objects
        .filter(
            asm=asm_user,
            is_active=True,
            ss__is_active=True,
            ss__role="SS",
        )
        .values_list("ss_id", flat=True)
    )


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
# LIST ACTIVE ASSIGNMENTS
# =========================================================

class ASMSSAssignmentListView(APIView):
    """
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
    """

    permission_classes = [
        IsAuthenticated,
        IsCRMOrAdminForASMAssignment,
    ]

    def patch(self, request, pk):

        assignment = get_object_or_404(
            ASMSSAssignment.objects.select_related(
                "asm",
                "ss",
            ),
            pk=pk,
            is_active=True,
        )

        if (
            request.user.role == "CRM"
            and assignment.ss.crm_id != request.user.id
        ):
            return Response(
                {
                    "detail":
                    "You cannot modify this assignment."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        assignment.is_active = False

        assignment.save(
            update_fields=["is_active"]
        )

        return Response({
            "success": True,
            "message": "SS unassigned from ASM.",
        })


# =========================================================
# ASM DASHBOARD
# =========================================================

class ASMDashboardView(APIView):
    """
    VERY LIGHTWEIGHT ASM DASHBOARD.

    Returns ONLY active assigned SS users.

    No:
        - order statistics
        - product totals
        - recent orders
        - dispatch counts
        - CRM history
        - order items

    Purpose:
        Dashboard should load extremely fast.
    """

    permission_classes = [
        IsAuthenticated,
        IsASM,
    ]

    def get(self, request):

        assignments = (
            ASMSSAssignment.objects
            .filter(
                asm=request.user,
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

        ss_list = []

        for assignment in assignments:

            ss = assignment.ss

            ss_list.append({
                "assignment_id": assignment.id,
                "ss_id": ss.id,
                "user_id": ss.user_id,
                "name": ss.name,
                "party_name": ss.party_name,
                "mobile": ss.mobile,
            })

        return Response({
            "ss_list": ss_list,
        })


# =========================================================
# ASM → SINGLE SS
# PAGINATED ORDER LIST
# =========================================================

class ASMSSDetailView(APIView):
    """
    ASM opens one assigned SS.

    Returns:
        - basic SS information
        - 15 orders initially
        - next 15 through page parameter

    IMPORTANT:
        Order items are NOT returned.

        Product information is NOT returned.

        Full order information is NOT returned.

    Full order is handled by:
        /orders-tracking/:orderId
    """

    permission_classes = [
        IsAuthenticated,
        IsASM,
    ]

    PAGE_SIZE = 15

    def get(self, request, ss_id):

        # -------------------------------------------------
        # GET ASSIGNMENT + SS IN ONE QUERY
        # -------------------------------------------------

        assignment = (
            ASMSSAssignment.objects
            .filter(
                asm=request.user,
                ss_id=ss_id,
                is_active=True,
                ss__is_active=True,
                ss__role="SS",
            )
            .select_related("ss")
            .first()
        )

        if not assignment:

            return Response(
                {
                    "detail":
                    "This SS is not assigned to you."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        ss = assignment.ss

        # -------------------------------------------------
        # PAGE
        # -------------------------------------------------

        try:
            page = int(
                request.query_params.get(
                    "page",
                    1,
                )
            )
        except (TypeError, ValueError):
            page = 1

        page = max(page, 1)

        page_size = self.PAGE_SIZE

        start = (page - 1) * page_size

        # -------------------------------------------------
        # LATEST CRM SUBQUERIES
        #
        # Only latest CRM verification is needed.
        #
        # No CRM history is loaded.
        # -------------------------------------------------

        latest_crm = (
            CRMVerifiedOrder.objects
            .filter(
                original_order=OuterRef("pk")
            )
            .order_by("-verified_at")
        )

        # -------------------------------------------------
        # ORDER QUERY
        #
        # +1 record is loaded to determine has_next.
        #
        # NO ITEMS
        # NO PREFETCH
        # NO PRODUCT QUERY
        # NO DISPATCH QUERY
        # -------------------------------------------------

        orders = list(
            SSOrder.objects
            .filter(
                ss_user_id=ss.id
            )
            .select_related(
                "assigned_crm",
            )
            .annotate(
                latest_crm_id=Subquery(
                    latest_crm.values("id")[:1]
                ),
                latest_crm_name=Subquery(
                    latest_crm.values(
                        "crm_user__name"
                    )[:1]
                ),
                latest_crm_status=Subquery(
                    latest_crm.values(
                        "status"
                    )[:1]
                ),
                latest_crm_verified_at=Subquery(
                    latest_crm.values(
                        "verified_at"
                    )[:1]
                ),
                latest_crm_punched=Subquery(
                    latest_crm.values(
                        "punched"
                    )[:1]
                ),
                latest_dispatch_location=Subquery(
                    latest_crm.values(
                        "dispatch_location"
                    )[:1]
                ),
            )
            .order_by(
                "-created_at",
                "-id",
            )[start:start + page_size + 1]
        )

        # -------------------------------------------------
        # HAS NEXT
        # -------------------------------------------------

        has_next = len(orders) > page_size

        if has_next:
            orders = orders[:page_size]

        # -------------------------------------------------
        # SERIALIZE BASIC ORDER INFORMATION ONLY
        # -------------------------------------------------

        order_data = []

        for order in orders:

            order_data.append({

                "id": order.id,

                "order_id": order.order_id,

                "created_at": order.created_at,

                "status": order.status,

                "total_amount": order.total_amount,

                # -----------------------------------------
                # SS BASIC INFO
                # -----------------------------------------

                "ss": {
                    "id": ss.id,
                    "user_id": ss.user_id,
                    "name": ss.name,
                    "party_name": ss.party_name,
                },

                # -----------------------------------------
                # CRM BASIC INFO
                # -----------------------------------------

                "crm": (
                    {
                        "id": order.latest_crm_id,
                        "name": order.latest_crm_name,
                        "status": order.latest_crm_status,
                        "verified_at":
                            order.latest_crm_verified_at,
                        "punched":
                            order.latest_crm_punched,
                        "dispatch_location":
                            order.latest_dispatch_location,
                    }
                    if order.latest_crm_id
                    else None
                ),

                # -----------------------------------------
                # DIRECTLY ASSIGNED CRM
                # -----------------------------------------

                "assigned_crm": (
                    {
                        "id": order.assigned_crm.id,
                        "name": order.assigned_crm.name,
                        "user_id":
                            order.assigned_crm.user_id,
                    }
                    if order.assigned_crm
                    else None
                ),
            })

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return Response({

            # -------------------------------------------------
            # SS INFO
            # Dashboard cache can also reuse this.
            # -------------------------------------------------

            "ss": {
                "id": ss.id,
                "user_id": ss.user_id,
                "name": ss.name,
                "party_name": ss.party_name,
                "mobile": ss.mobile,
            },

            # -------------------------------------------------
            # ORDERS
            # -------------------------------------------------

            "orders": order_data,

            # -------------------------------------------------
            # PAGINATION
            # -------------------------------------------------

            "pagination": {
                "page": page,
                "page_size": page_size,
                "has_next": has_next,
                "next_page": (
                    page + 1
                    if has_next
                    else None
                ),
            },
        })


# =========================================================
# ASM ORDER DETAIL
# =========================================================
#
# REMOVED INTENTIONALLY.
#
# ASM will NOT use a separate order-detail API.
#
# Order click goes directly to:
#
#     /orders-tracking/:orderId
#
# Existing OrderTrackPage handles complete order data.
#
# =========================================================