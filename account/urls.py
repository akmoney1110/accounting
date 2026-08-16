# urls.py - Cleaned version
from django.urls import path
from .views import (
    # Auth
    LoginView, 
    LogoutView,
    
    # Admin
    AdminDashboardView, 
    CreateBatchView, 
    BatchDetailView,
    AddExpenseView, 
    RecordTransactionView,
    UpdateDryWeightView,
    RecordPaymentView,
    
    # Payment Allocation
    AllocatePaymentView,
    RemoveAllocationView,
    BatchDeleteView,
    
    # AJAX
    GetUsersByTypeView,
    GetProductsByUserView,
    GetUserProductRateView,
    UserProfileView,
    UserProfileEditView,  # NEW
    DeleteExpenseView,GetOutstandingBatchesView,
    
    # Portals
    VendorPortalView, 
    BatchListView,
    ClientPortalView,
    BatchEditView,UserListView,
    ProductListView,
    ProductCreateView,
    ProductUpdateView,
    ManagerDashboardView,
    StaffDashboardView,StaffListView,
    ExpenseListView,PaymentDetailView,
    ExpenseUpdateView,UserCreateView,ExpenseCreateView,PaymentListView,
)

urlpatterns = [
    # Authentication
    path('', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('manager/', ManagerDashboardView.as_view(), name='manager_dashboard'),
    path('staff/', StaffDashboardView.as_view(), name='staff_dashboard'),
    path('products/', ProductListView.as_view(), name='product_list'),
    path('products/create/', ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/edit/', ProductUpdateView.as_view(), name='product_edit'),
    path('expenses/', ExpenseListView.as_view(), name='expense_list'),
    path('expenses/<int:pk>/edit/', ExpenseUpdateView.as_view(), name='expense_edit'),
    path('users/create/', UserCreateView.as_view(), name='user_create'),
    path('payments/', PaymentListView.as_view(), name='payment_list'),
    path('payments/<int:pk>/', PaymentDetailView.as_view(), name='payment_detail'),


    # Admin Dashboard & Operations
    path('dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('batches/', BatchListView.as_view(), name='batch_list'),
    
    # Batches
    path('batches/create/', CreateBatchView.as_view(), name='batch_create'),
    path('batches/<int:pk>/', BatchDetailView.as_view(), name='batch_detail'),
    path('batches/<int:pk>/edit/', BatchEditView.as_view(), name='batch_edit'),
    path('batches/<int:pk>/delete/', BatchDeleteView.as_view(), name='batch_delete'),
    path('batches/<int:pk>/dry-weight/', UpdateDryWeightView.as_view(), name='update_dry_weight'),
    
    # Expenses
    path('batches/<int:batch_pk>/expense/', AddExpenseView.as_view(), name='add_expense'),
    path('expenses/<int:pk>/delete/', DeleteExpenseView.as_view(), name='delete_expense'),
    path('expenses/create/', ExpenseCreateView.as_view(), name='expense_create'),
    
    # Payments & Allocations
    path('batches/<int:batch_pk>/record-payment/', RecordPaymentView.as_view(), name='record_payment'),
    path('batches/<int:batch_pk>/allocate/', AllocatePaymentView.as_view(), name='allocate_payment'),
    path('allocations/<int:allocation_pk>/remove/', RemoveAllocationView.as_view(), name='remove_allocation'),
    
    # Transactions (standalone)
    path('transactions/add/', RecordTransactionView.as_view(), name='transaction_add'),

    # User Profiles
    path('profile/', UserProfileView.as_view(), name='my_profile'),
    path('profile/edit/', UserProfileEditView.as_view(), name='profile_edit'),  # NEW
    path('users/<int:pk>/profile/', UserProfileView.as_view(), name='user_profile'),
    path('partners/', UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/profile/edit/', UserProfileEditView.as_view(), name='user_profile_edit'),  # NEW
    path('staff-directory/', StaffListView.as_view(), name='staff_list'),


    # AJAX Helpers
    path('ajax/users-by-type/', GetUsersByTypeView.as_view(), name='ajax_users_by_type'),
    path('ajax/products-by-user/', GetProductsByUserView.as_view(), name='ajax_products_by_user'),
    path('ajax/user-product-rate/', GetUserProductRateView.as_view(), name='ajax_user_product_rate'),
    path('ajax/outstanding-batches/', GetOutstandingBatchesView.as_view(), name='ajax_outstanding_batches'),  # <-- ADD THIS
    # User Portals
    path('vendor/', VendorPortalView.as_view(), name='vendor_portal'),
    path('client/', ClientPortalView.as_view(), name='client_portal'),
]