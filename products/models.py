from django.db import models
from cloudinary.models import CloudinaryField

# ✅ 2. Product Model
class Product(models.Model):
    product_id = models.IntegerField(unique=True, primary_key=True)
    product_name = models.CharField(max_length=100, db_index=True)
    sub_category = models.CharField(max_length=50, null=True, blank=True)
    cartoon_size = models.CharField(max_length=50, null=True, blank=True)
    mah = models.CharField(max_length=50, null=True, blank=True)
    product_type = models.CharField(max_length=50, null=True, blank=True)
    guarantee = models.CharField(max_length=50, null=True, blank=True)
    price = models.CharField(max_length=10, null=True, blank=True)
    ds_price = models.CharField(max_length=10, null=True, blank=True)
    dlr_price = models.CharField(max_length=10, null=True, blank=True)
    moq = models.IntegerField(null=True, blank=True)
    live_stock = models.IntegerField(null=True, blank=True)
    virtual_stock = models.IntegerField(null=True, blank=True, default=0) 
    mumbai_stock = models.IntegerField(null=True, blank=True)
    quantity_type = models.CharField(max_length=50, default="MOQ")
    rack_no = models.CharField(max_length=50, null=True, blank=True)
    image = CloudinaryField('image', blank=True, null=True)
    image2 = CloudinaryField('image2', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product_id} - {self.product_name}"



# ✅ 3. SaleName Model (1 product → many sale names)
class SaleName(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, to_field='product_id', db_column='product_id', related_name="sale_names")
    sale_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.sale_name} for {self.product.product_name}"
    
# =========================================================
# PRODUCT PRICE HISTORY
# =========================================================

class ProductPriceHistory(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="price_history",
        db_index=True
    )

    # -----------------------------------------------------
    # SS PRICE
    # -----------------------------------------------------

    old_price = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )

    new_price = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )

    # -----------------------------------------------------
    # DS PRICE
    # -----------------------------------------------------

    old_ds_price = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )

    new_ds_price = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )

    # -----------------------------------------------------
    # DLR PRICE
    # -----------------------------------------------------

    old_dlr_price = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )

    new_dlr_price = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )

    # -----------------------------------------------------
    # USER
    # -----------------------------------------------------

    changed_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.PROTECT,
        related_name="product_price_changes"
    )

    # -----------------------------------------------------
    # TIMESTAMP
    # -----------------------------------------------------

    changed_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    # -----------------------------------------------------
    # BUSINESS EFFECTIVE DATE
    # -----------------------------------------------------

    applicable_from = models.DateField(
        db_index=True
    )

    # -----------------------------------------------------
    # REASON
    # -----------------------------------------------------

    reason = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    def __str__(self):
        return (
            f"{self.product.product_id} - "
            f"{self.old_price} → {self.new_price}"
        )


class Scheme(models.Model):
    created_by = models.CharField(max_length=100)
    in_box = models.BooleanField(default=False)

    def __str__(self):
        return f"Scheme {self.id}"  # ID दिखाएंगे क्योंकि name हटा दिया है

class SchemeCondition(models.Model):
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='conditions')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    min_quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"Buy {self.min_quantity} of {self.product}"

class SchemeReward(models.Model):
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='rewards')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"Get {self.quantity} free {self.product}"
