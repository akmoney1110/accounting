from rest_framework import serializers
from decimal import Decimal
from django.db.models import Sum
from .models import User, Product, Batch, ShrinkageLog, Expense, Transaction


# --------------------------------------------------
# 1. USER & PRODUCT SERIALIZERS
# --------------------------------------------------
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Batch, Product  # Adjust model imports as needed

User = get_user_model()


# ----------------------------------------------------
# 1. USER & REGISTER SERIALIZERS
# ----------------------------------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role']

    def create(self, validated_data):
        # Create user with hashed password
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            role=validated_data.get('role', 'CLIENT')
        )
        return user


# ----------------------------------------------------
# 2. BATCH & PRODUCT SERIALIZERS
# ----------------------------------------------------
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'unit']


class BatchSerializer(serializers.ModelSerializer):
    vendor_details = UserSerializer(source='vendor', read_only=True)
    client_details = UserSerializer(source='client', read_only=True)
    product_details = ProductSerializer(source='product', read_only=True)

    class Meta:
        model = Batch
        fields = [
            'id',
            'batch_code',
            'product',
            'product_details',
            'vendor',
            'vendor_details',
            'client',
            'client_details',
            'wet_weight_kg',
            'dry_weight_kg',
            'vendor_total_due',
            'client_total_billed',
            'is_processed',
            'created_at',
        ]
        read_only_fields = ['vendor_total_due', 'client_total_billed', 'is_processed']


class ProcessShrinkageSerializer(serializers.Serializer):
    dry_weight_kg = serializers.FloatField(required=True)

    def validate_dry_weight_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError("Dry weight must be greater than zero.")
        return value

class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'phone']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'unit', 'description', 'is_active']


# --------------------------------------------------
# 2. SHRINKAGE & EXPENSE SERIALIZERS
# --------------------------------------------------

class ShrinkageLogSerializer(serializers.ModelSerializer):
    weight_loss_kg = serializers.ReadOnlyField()
    shrinkage_percentage = serializers.ReadOnlyField()

    class Meta:
        model = ShrinkageLog
        fields = [
            'id', 'batch', 'drying_start_date', 'drying_end_date', 
            'notes', 'weight_loss_kg', 'shrinkage_percentage', 'logged_at'
        ]
        read_only_fields = ['batch']


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['id', 'batch', 'title', 'amount', 'expense_date', 'created_at']


# --------------------------------------------------
# 3. BATCH SERIALIZERS
# --------------------------------------------------

class BatchSerializer(serializers.ModelSerializer):
    vendor_details = UserSummarySerializer(source='vendor', read_only=False, required=False)
    client_details = UserSummarySerializer(source='client', read_only=True)
    product_details = ProductSerializer(source='product', read_only=True)

    vendor_total_due = serializers.ReadOnlyField()
    client_total_billed = serializers.ReadOnlyField()
    shrinkage_log = ShrinkageLogSerializer(read_only=True)
    expenses = ExpenseSerializer(many=True, read_only=True)

    class Meta:
        model = Batch
        fields = [
            'id', 'batch_code', 'vendor', 'vendor_details', 'client', 'client_details',
            'product', 'product_details', 'wet_weight_kg', 'dry_weight_kg',
            'vendor_rate_per_kg', 'client_rate_per_kg', 'is_processed',
            'vendor_total_due', 'client_total_billed', 'shrinkage_log', 'expenses',
            'created_at', 'updated_at'
        ]

    def validate(self, data):
        """Ensure dry weight does not exceed wet weight."""
        wet_weight = data.get('wet_weight_kg', getattr(self.instance, 'wet_weight_kg', None))
        dry_weight = data.get('dry_weight_kg', getattr(self.instance, 'dry_weight_kg', None))

        if dry_weight is not None and wet_weight is not None:
            if dry_weight > wet_weight:
                raise serializers.ValidationError({"dry_weight_kg": "Dry weight cannot exceed wet weight."})

        return data


# --------------------------------------------------
# 4. TRANSACTION / PAYMENT SERIALIZER
# --------------------------------------------------

class TransactionSerializer(serializers.ModelSerializer):
    user_details = UserSummarySerializer(source='user', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_ref', 'user', 'user_details', 'batch', 
            'amount', 'payment_method', 'notes', 'payment_date'
        ]

    def validate(self, data):
        """Validate transaction logic based on user role."""
        target_user = data['user']
        batch = data.get('batch')

        if target_user.role not in [User.Roles.VENDOR, User.Roles.CLIENT]:
            raise serializers.ValidationError({"user": "Transactions can only be logged for Vendors or Clients."})

        # Ensure batch belongs to the selected user if linked
        if batch:
            if target_user.role == User.Roles.VENDOR and batch.vendor != target_user:
                raise serializers.ValidationError({"batch": "Selected batch does not belong to this vendor."})
            elif target_user.role == User.Roles.CLIENT and batch.client != target_user:
                raise serializers.ValidationError({"batch": "Selected batch is not assigned to this client."})

        return data
