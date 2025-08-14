from django.db import models
from cloudinary.models import CloudinaryField

# ✅ 2. Product Model
class Product(models.Model):
    product_id = models.IntegerField(unique=True, primary_key=True)  # Custom Primary Key
    product_name = models.CharField(max_length=50)
    sub_category = models.CharField(max_length=50,null=True, blank=True)
    cartoon_size = models.CharField(max_length=50, null=True, blank=True)
    price = models.CharField(max_length=10, null=True, blank=True)
    live_stock = models.IntegerField( null=True, blank=True)
    image = CloudinaryField('image', blank=True, null=True) 

    def __str__(self):
        return f"{self.product_id} - {self.product_name}"

# ✅ 3. SaleName Model (1 product → many sale names)
class SaleName(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, to_field='product_id', db_column='product_id', related_name="sale_names")
    sale_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.sale_name} for {self.product.product_name}"
    

# models.py
class Scheme(models.Model):
    name = models.CharField(max_length=255, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    created_by = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name or 'Unnamed Scheme'}"

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
    
