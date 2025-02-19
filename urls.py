from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core import views as core_views

urlpatterns = [
    path('admin/dashboard/', core_views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/create/', core_views.create_user, name='create_user'),
    path('admin/', admin.site.urls),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('', include('core.urls')),
]
