from django.urls import path

from .views import (
    ASMSSAssignmentCreateView,
    ASMSSAssignmentListView,
    ASMSSAssignmentDeactivateView,
    ASMDashboardView,
    ASMSSDetailView,
)


urlpatterns = [

    # =====================================================
    # CRM / ADMIN — ASM ↔ SS ASSIGNMENTS
    # =====================================================

    path(
        "assignments/",
        ASMSSAssignmentListView.as_view(),
        name="asm-assignment-list",
    ),

    path(
        "assignments/create/",
        ASMSSAssignmentCreateView.as_view(),
        name="asm-assignment-create",
    ),

    path(
        "assignments/<int:pk>/deactivate/",
        ASMSSAssignmentDeactivateView.as_view(),
        name="asm-assignment-deactivate",
    ),

    # =====================================================
    # ASM — DASHBOARD
    # =====================================================

    path(
        "dashboard/",
        ASMDashboardView.as_view(),
        name="asm-dashboard",
    ),

    # =====================================================
    # ASM — SINGLE SS
    # =====================================================

    path(
        "ss/<int:ss_id>/",
        ASMSSDetailView.as_view(),
        name="asm-ss-detail",
    ),
]