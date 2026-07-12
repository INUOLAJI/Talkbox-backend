from django.urls import path
from .views import signup_view, login_view, upload_chat_file, list_rooms, start_private_chat, create_group_chat, list_users

urlpatterns = [
    path('api/signup/', signup_view, name='signup'),
    path('api/login/', login_view, name='login'),
    path('api/chat/upload/', upload_chat_file, name='upload_chat_file'),
    path('api/chat/rooms/', list_rooms, name='list_rooms'),
    path('api/chat/rooms/start/', start_private_chat, name='start_private_chat'),
    path('api/chat/rooms/group/', create_group_chat, name='create_group_chat'),
    path('api/chat/users/', list_users, name='list_users'),
]