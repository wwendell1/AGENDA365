from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views.grupos import (
    GroupViewSet, TaskViewSet, CommentViewSet,
    TaskFileViewSet, NotificationViewSet
)

# Criar router para as ViewSets
router = DefaultRouter()
router.register(r'grupos', GroupViewSet, basename='group')
router.register(r'tarefas', TaskViewSet, basename='task')
router.register(r'comentarios', CommentViewSet, basename='comment')
router.register(r'arquivos', TaskFileViewSet, basename='taskfile')
router.register(r'notificacoes', NotificationViewSet, basename='notification')

# URLs para as APIs
api_urlpatterns = [
    path('', include(router.urls)),
]

# URLs para as views baseadas em templates
urlpatterns = [
    # API URLs
    path('api/', include(api_urlpatterns)),
]