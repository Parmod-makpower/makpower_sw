from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import RegexValidator  # ✅ Added

# -------------------------------
# Constants
# -------------------------------

USER_ROLES = (
    ('ADMIN', 'Admin'),
    ('CRM', 'CRM'),
    ('SS', 'Super Stockist'),
    ('DS', 'Distributor'),
)

def generate_user_id(role, last_id):
    prefix = {'ADMIN': 'AD', 'CRM': 'CRM', 'SS': 'SS', 'DS': 'DS'}
    return f"{prefix[role]}{str(last_id + 1).zfill(4)}"

# -------------------------------
# Custom User Manager
# -------------------------------

class CustomUserManager(BaseUserManager):
    def create_user(self, mobile, role=None, password=None, **extra_fields):
        if not mobile:
            raise ValueError('Mobile number is required')
        if not role:
            raise ValueError('Role is required')

        last_id = self.model.objects.filter(role=role).count()
        user_id = generate_user_id(role, last_id)

        user = self.model(
            mobile=mobile,
            role=role,
            user_id=user_id,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile, password=None, **extra_fields):
        extra_fields.setdefault('role', 'ADMIN')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(mobile=mobile, password=password, **extra_fields)

# -------------------------------
# Custom User Model
# -------------------------------

mobile_validator = RegexValidator(regex=r'^\d{10}$', message='Mobile number must be exactly 10 digits.')

class CustomUser(AbstractBaseUser, PermissionsMixin):
    user_id = models.CharField(max_length=20, unique=True)
    mobile = models.CharField(max_length=15, unique=True, validators=[mobile_validator])  # ✅ Added validator
    role = models.CharField(max_length=10, choices=USER_ROLES)

    name = models.CharField(max_length=100, blank=True, null=True) 
    email = models.EmailField(blank=True, null=True)
    party_name = models.CharField(max_length=150, blank=True, null=True)  
    dob = models.DateField(blank=True, null=True)

    crm = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='crm_users')
    ss = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='ss_users')

    created_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_users')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = ['role']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.user_id} - {self.mobile}"
