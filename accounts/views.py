from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import viewsets, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from .serializers import  SSUserSerializer, UserSerializer, SSUserSerializerDealer
from .models import CustomUser
from accounts.permissions import IsCRMOrAdmin


class IsCRM(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'CRM'


class LoginView(APIView):
    def post(self, request):
        mobile_or_id = request.data.get('mobile_or_id')
        password = request.data.get('password')

        if not mobile_or_id or not password:
            return Response({'detail': 'Mobile/User ID and Password are required.'}, status=400)

        user = CustomUser.objects.filter(
            Q(mobile=mobile_or_id) | Q(user_id=mobile_or_id)
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                return Response({'detail': 'Account is deactivated.'}, status=403)

            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data  # ✅ Full serialized user
            }, status=200)

        return Response({'detail': 'Invalid credentials'}, status=400)


class UserHierarchyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        role = user.role

        if role == 'ADMIN':
            crms = CustomUser.objects.filter(role='CRM')
            data = []
            for crm in crms:
                ss_users = CustomUser.objects.filter(role='SS', created_by=crm)
                ss_data = []
                for ss in ss_users:
                    ds_users = CustomUser.objects.filter(role='DS', ss=ss)
                    ss_data.append({
                        'ss': {
                            'id': ss.id,
                            'name': ss.name,
                            'party_name': ss.party_name,
                            'mobile': ss.mobile,
                            'user_id': ss.user_id
                        },
                        'ds_count': ds_users.count(),
                        'ds_list': list(ds_users.values('id', 'name','party_name', 'mobile', 'user_id'))
                    })
                data.append({
                    'crm': {
                        'id': crm.id,
                        'name': crm.name,
                        'mobile': crm.mobile,
                        'user_id': crm.user_id
                    },
                    'ss_count': ss_users.count(),
                    'ss_data': ss_data
                })
            return Response({
                'crm_count': crms.count(),
                'data': data
            })

        elif role == 'CRM':
            ss_users = CustomUser.objects.filter(role='SS', created_by=user)
            ss_data = []
            for ss in ss_users:
                ds_users = CustomUser.objects.filter(role='DS', ss=ss)
                ss_data.append({
                    'ss': {
                        'id': ss.id,
                        'name': ss.name,
                        'mobile': ss.mobile,
                        'party_name': ss.party_name,
                        'user_id': ss.user_id
                    },
                    'ds_count': ds_users.count(),
                    'ds_list': list(ds_users.values('id', 'name','party_name', 'mobile', 'user_id'))
                })
            return Response({
                'ss_count': ss_users.count(),
                'data': ss_data
            })

        elif role == 'SS':
            ds_users = CustomUser.objects.filter(role='DS', ss=user)
            return Response({
                'ds_count': ds_users.count(),
                'ds_list': list(ds_users.values('id', 'name', 'party_name', 'mobile', 'user_id'))
            })

        else:
            return Response({'detail': 'Unauthorized'}, status=403)


# class SSUserViewSet(viewsets.ModelViewSet):
#     serializer_class = SSUserSerializer

#     def get_queryset(self):
#         user = self.request.user

#         # Admin → sab users
#         if user.role == "ADMIN":
#             return CustomUser.objects.all()

#         # CRM → uske banaye users
#         return CustomUser.objects.filter(crm=user)

 
class SSUserViewSet(viewsets.ModelViewSet):
    serializer_class = SSUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsCRMOrAdmin]

    def get_queryset(self):
        user = self.request.user

        if user.role == "ADMIN":
            return CustomUser.objects.all()

        return CustomUser.objects.filter(crm=user)

    def get_serializer_context(self):
        return {'request': self.request}

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True   # 🔥 VERY IMPORTANT
        return super().update(request, *args, **kwargs)
    

# dealer form k liya

class SSUserListView(ListAPIView):
    serializer_class = SSUserSerializerDealer

    def get_queryset(self):
        return (
            CustomUser.objects
            .filter(role="SS", is_active=True)
            .select_related("crm")
            .order_by("name")
        )
    
    
# dealer form k liya