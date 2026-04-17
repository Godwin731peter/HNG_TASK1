from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.HealthView.as_view(), name='health'),
    path('profiles/', views.ProfileListView.as_view(), name='profiles-list'),
    path('profiles/<uuid:profile_id>/', views.ProfileDetailView.as_view(), name='profile-detail'),
]