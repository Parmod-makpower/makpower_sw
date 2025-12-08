from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from orders.models import SSOrder
from .serializers import PartyOrdersSerializer, SingleOrderForPartySerializer

User = get_user_model()

class PartyOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, party_id):
        # party exists?
        party = get_object_or_404(User, id=party_id)

        # Authorization:
        # - staff/superuser => allowed
        # - the user themself => allowed
        # - CRM users who are assigned to at least one order of this party => allowed
        user = request.user
        if not (user.is_staff or user.is_superuser or user.id == party.id):
            # check if this user is assigned_crm for any order of this party
            assigned_exists = SSOrder.objects.filter(ss_user=party, assigned_crm=user).exists()
            if not assigned_exists:
                return Response({"error": "Not authorized to view this party's orders"}, status=403)

        # fetch all orders of this party (most recent first)
        orders_qs = SSOrder.objects.filter(ss_user=party).order_by("-created_at").prefetch_related("items", "crm_verified_versions__items")

        serialized_orders = SingleOrderForPartySerializer(orders_qs, many=True).data

        result = {
            "party_id": party.id,
            "party_name": getattr(party, "name", str(party)),
            "orders": serialized_orders,
            "total_orders": orders_qs.count(),
        }
        return Response(result, status=200)
