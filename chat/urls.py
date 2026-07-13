from django.urls import path
from .views import signup_view, login_view, upload_chat_file, list_rooms, start_private_chat, add_contact, create_group_chat, list_users, mark_room_read, profile_settings, upload_profile_picture, upload_group_picture

urlpatterns = [
    path('api/signup/', signup_view, name='signup'),
    path('api/login/', login_view, name='login'),
    path('api/chat/upload/', upload_chat_file, name='upload_chat_file'),
    path('api/chat/rooms/', list_rooms, name='list_rooms'),
    path('api/chat/rooms/start/', start_private_chat, name='start_private_chat'),
    path('api/chat/contacts/add/', add_contact, name='add_contact'),
    path('api/chat/rooms/group/', create_group_chat, name='create_group_chat'),
    path('api/chat/users/', list_users, name='list_users'),
    path('api/chat/rooms/<int:room_id>/read/', mark_room_read),
    path('api/chat/profile/', profile_settings, name='profile_settings'),
    path('api/chat/profile/upload/', upload_profile_picture),
    path('api/chat/rooms/<int:room_id>/picture/', upload_group_picture),
]