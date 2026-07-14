import uuid
import cloudinary.uploader
from django.contrib.auth import get_user_model, authenticate, login
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from .authentication import CsrfExemptSessionAuthentication
from .models import Room, Message, RoomReadStatus

User = get_user_model()
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@extend_schema(
    tags=['Auth'],
    summary='Register a new user',
    request=inline_serializer('SignupRequest', fields={
        'email': serializers.EmailField(),
        'phone_number': serializers.CharField(),
        'full_name': serializers.CharField(required=False),
        'password': serializers.CharField(),
    }),
    responses={201: inline_serializer('SignupResponse', fields={
        'message': serializers.CharField(),
        'user_id': serializers.IntegerField(),
    })},
)
@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def signup_view(request):
    try:
        data = request.data
        email = data.get('email')
        phone_number = data.get('phone_number')
        full_name = data.get('full_name', '')
        password = data.get('password')

        if not email or not phone_number or not password:
            return Response({'error': 'Please provide email, phone number, and password.'}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({'error': 'A user with this email already exists.'}, status=400)

        if User.objects.filter(phone_number=phone_number).exists():
            return Response({'error': 'A user with this phone number already exists.'}, status=400)

        user = User.objects.create_user(
            email=email,
            phone_number=phone_number,
            full_name=full_name,
            password=password
        )
        return Response({'message': 'User registered successfully!', 'user_id': user.id}, status=201)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@extend_schema(
    tags=['Auth'],
    summary='Login and get session cookie',
    request=inline_serializer('LoginRequest', fields={
        'email': serializers.EmailField(),
        'password': serializers.CharField(),
    }),
    responses={200: inline_serializer('LoginResponse', fields={
        'message': serializers.CharField(),
        'user': inline_serializer('UserInfo', fields={
            'id': serializers.IntegerField(),
            'email': serializers.EmailField(),
            'phone_number': serializers.CharField(),
            'full_name': serializers.CharField(),
            'profile_picture_url': serializers.CharField(),
        }),
    })},
)
@api_view(['POST'])
@authentication_classes([])
@permission_classes([])
def login_view(request):
    try:
        data = request.data
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return Response({'error': 'Please provide both email and password.'}, status=400)

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Login successful!',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'phone_number': user.phone_number,
                    'full_name': user.full_name,
                    'profile_picture_url': user.profile_picture_url,
                    'bio': user.bio,
                    'theme_preference': user.theme_preference,
                }
            }, status=200)
        else:
            return Response({'error': 'Invalid email or password.'}, status=401)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@extend_schema(
    tags=['Files'],
    summary='Upload a chat file or image',
    request=inline_serializer('FileUploadRequest', fields={'file': serializers.FileField()}),
    responses={200: inline_serializer('FileUploadResponse', fields={
        'file_url': serializers.CharField(),
        'file_type': serializers.CharField(),
    })},
)
@api_view(['POST'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def upload_chat_file(request):
    file = request.FILES.get('file')
    if not file:
        return Response({'error': 'No file provided'}, status=400)

    if file.size > MAX_FILE_SIZE:
        return Response({'error': 'File exceeds 5MB limit'}, status=400)

    is_image = file.content_type.startswith('image/')
    result = cloudinary.uploader.upload(
        file,
        resource_type='image' if is_image else 'raw',
        folder='chat_uploads/'
    )

    return Response({
        'file_url': result['secure_url'],
        'file_type': 'image' if is_image else 'file',
    })


@extend_schema(
    tags=['Messages'],
    summary='Get message history for a room',
    responses={200: inline_serializer('MessageItem', many=True, fields={
        'id': serializers.IntegerField(),
        'message': serializers.CharField(),
        'username': serializers.CharField(),
        'sender_id': serializers.IntegerField(),
        'file_url': serializers.CharField(),
        'file_type': serializers.CharField(),
        'timestamp': serializers.CharField(),
    })},
)
@api_view(['GET'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def room_message_history(request, room_name):
    room, _ = Room.objects.get_or_create(name=room_name)
    messages = room.messages.select_related('sender').order_by('timestamp')[:50]

    data = [{
        'id': m.id,
        'message': m.text,
        'username': m.sender.full_name or m.sender.email,
        'sender_id': m.sender.id,
        'file_url': m.file_url,
        'file_type': m.file_type,
        'parent_id': m.parent_id,
        'timestamp': m.timestamp.isoformat(),
    } for m in messages]

    return Response(data)


@extend_schema(
    tags=['Users'],
    summary='List currently online users',
    responses={200: inline_serializer('OnlineUser', many=True, fields={
        'id': serializers.IntegerField(),
        'full_name': serializers.CharField(),
        'email': serializers.EmailField(),
    })},
)
@api_view(['GET'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def online_users(request):
    online = User.objects.filter(is_online=True).values('id', 'full_name', 'email')
    return Response(list(online))


@extend_schema(
    tags=['Rooms'],
    summary='List all rooms for the current user',
    responses={200: inline_serializer('RoomItem', many=True, fields={
        'id': serializers.IntegerField(),
        'name': serializers.CharField(),
        'display_name': serializers.CharField(),
        'is_group': serializers.BooleanField(),
        'other_user_id': serializers.IntegerField(),
        'is_online': serializers.BooleanField(),
        'profile_picture_url': serializers.CharField(),
        'last_message': serializers.CharField(),
        'last_message_time': serializers.CharField(),
        'unread_count': serializers.IntegerField(),
    })},
)
@api_view(['GET'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def list_rooms(request):
    rooms = Room.objects.filter(members=request.user).prefetch_related('members', 'messages')
    data = []
    for room in rooms:
        last_msg = room.messages.order_by('-timestamp').first()

        if room.is_group:
            display_name = room.title or room.name
            other_user_id = None
            is_online = False
            profile_picture_url = room.profile_picture_url
        else:
            other_member = room.members.exclude(id=request.user.id).first()
            display_name = other_member.full_name if other_member else room.name
            other_user_id = other_member.id if other_member else None
            is_online = other_member.is_online if other_member else False
            profile_picture_url = other_member.profile_picture_url if other_member else None

        if last_msg:
            if last_msg.text:
                preview = last_msg.text
            elif last_msg.file_type == 'image':
                preview = 'Photo'
            elif last_msg.file_type == 'file':
                preview = 'File'
            else:
                preview = ''
            last_time = last_msg.timestamp.isoformat()
        else:
            preview = 'No messages yet'
            last_time = room.created_at.isoformat()

        last_read = RoomReadStatus.objects.filter(room=room, user=request.user).first()
        if last_read:
            unread_count = room.messages.filter(timestamp__gt=last_read.last_read_at).exclude(sender=request.user).count()
        else:
            unread_count = room.messages.exclude(sender=request.user).count()

        data.append({
            'id': room.id,
            'name': room.name,
            'display_name': display_name,
            'is_group': room.is_group,
            'other_user_id': other_user_id,
            'is_online': is_online,
            'profile_picture_url': profile_picture_url,
            'last_message': preview,
            'last_message_time': last_time,
            'unread_count': unread_count,
        })

    data.sort(key=lambda r: r['last_message_time'], reverse=True)
    return Response(data)


@extend_schema(
    tags=['Users'],
    summary='List contacts (users sharing a room with current user)',
    responses={200: inline_serializer('ContactUser', many=True, fields={
        'id': serializers.IntegerField(),
        'full_name': serializers.CharField(),
        'email': serializers.EmailField(),
        'is_online': serializers.BooleanField(),
        'profile_picture_url': serializers.CharField(),
    })},
)
@api_view(['GET'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def list_users(request):
    contact_ids = Room.objects.filter(members=request.user).values_list('members__id', flat=True).distinct()
    users = User.objects.filter(id__in=contact_ids).exclude(id=request.user.id).values(
        'id', 'full_name', 'email', 'is_online', 'profile_picture_url'
    )
    return Response(list(users))


def _get_or_create_private_room(current_user, other_user):
    existing = Room.objects.filter(is_group=False, members=current_user).filter(members=other_user).first()
    if existing:
        return existing, False

    room_name = f"dm_{min(current_user.id, other_user.id)}_{max(current_user.id, other_user.id)}"
    room = Room.objects.create(name=room_name, is_group=False)
    room.members.add(current_user, other_user)
    return room, True


@extend_schema(
    tags=['Rooms'],
    summary='Start or get a private chat room with another user',
    request=inline_serializer('StartChatRequest', fields={'user_id': serializers.IntegerField()}),
    responses={200: inline_serializer('StartChatResponse', fields={
        'id': serializers.IntegerField(),
        'name': serializers.CharField(),
    })},
)
@api_view(['POST'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def start_private_chat(request):
    other_user_id = request.data.get('user_id')
    if not other_user_id:
        return Response({'error': 'user_id is required'}, status=400)

    try:
        other_user = User.objects.get(id=other_user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)

    room, created = _get_or_create_private_room(request.user, other_user)
    status_code = 201 if created else 200
    return Response({'id': room.id, 'name': room.name}, status=status_code)


@extend_schema(
    tags=['Contacts'],
    summary='Add a contact by email or phone number',
    request=inline_serializer('AddContactRequest', fields={'identifier': serializers.CharField()}),
    responses={200: inline_serializer('AddContactResponse', fields={
        'id': serializers.IntegerField(),
        'name': serializers.CharField(),
        'contact': inline_serializer('ContactDetail', fields={
            'id': serializers.IntegerField(),
            'full_name': serializers.CharField(),
            'email': serializers.EmailField(),
            'phone_number': serializers.CharField(),
            'profile_picture_url': serializers.CharField(),
            'is_online': serializers.BooleanField(),
        }),
    })},
)
@api_view(['POST'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def add_contact(request):
    identifier = request.data.get('identifier', '').strip()
    if not identifier:
        return Response({'error': 'Please provide an email or phone number.'}, status=400)

    if '@' in identifier:
        contact = User.objects.filter(email__iexact=identifier).first()
    else:
        contact = User.objects.filter(phone_number=identifier).first()

    if not contact:
        return Response({'error': 'No user found with that email or phone number.'}, status=404)

    if contact.id == request.user.id:
        return Response({'error': 'You cannot add yourself as a contact.'}, status=400)

    room, created = _get_or_create_private_room(request.user, contact)
    status_code = 201 if created else 200
    return Response({
        'id': room.id,
        'name': room.name,
        'contact': {
            'id': contact.id,
            'full_name': contact.full_name,
            'email': contact.email,
            'phone_number': contact.phone_number,
            'profile_picture_url': contact.profile_picture_url,
            'is_online': contact.is_online,
        },
    }, status=status_code)


@extend_schema(
    tags=['Rooms'],
    summary='Create a group chat room',
    request=inline_serializer('CreateGroupRequest', fields={
        'name': serializers.CharField(),
        'member_ids': serializers.ListField(child=serializers.IntegerField()),
    }),
    responses={201: inline_serializer('CreateGroupResponse', fields={
        'id': serializers.IntegerField(),
        'name': serializers.CharField(),
        'display_name': serializers.CharField(),
    })},
)
@api_view(['POST'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def create_group_chat(request):
    display_name = request.data.get('name')
    member_ids = request.data.get('member_ids', [])
    if not display_name:
        return Response({'error': 'Group name is required'}, status=400)

    selected_member_ids = sorted({request.user.id, *[int(member_id) for member_id in member_ids if member_id]})
    existing_room = None

    for room in Room.objects.filter(is_group=True).prefetch_related('members'):
        room_member_ids = sorted(room.members.values_list('id', flat=True))
        if room_member_ids == selected_member_ids:
            existing_room = room
            break

    if existing_room:
        return Response({'id': existing_room.id, 'name': existing_room.name, 'display_name': existing_room.title or existing_room.name}, status=200)

    safe_name = f"group_{uuid.uuid4().hex[:12]}"
    room = Room.objects.create(name=safe_name, title=display_name.strip(), is_group=True)
    room.members.add(request.user, *User.objects.filter(id__in=member_ids))

    return Response({'id': room.id, 'name': room.name, 'display_name': room.title}, status=201)


@extend_schema(
    tags=['Rooms'],
    summary='Mark a room as read',
    responses={200: inline_serializer('MarkReadResponse', fields={'success': serializers.BooleanField()})},
)
@api_view(['POST'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def mark_room_read(request, room_id):
    try:
        room = Room.objects.get(id=room_id, members=request.user)
    except Room.DoesNotExist:
        return Response({'error': 'Room not found'}, status=404)

    status_obj, _ = RoomReadStatus.objects.get_or_create(room=room, user=request.user)
    status_obj.save()  # touches auto_now, refreshing last_read_at to now
    return Response({'success': True})


@extend_schema(
    tags=['Profile'],
    summary='Get or update the current user profile',
    request=inline_serializer('ProfileUpdateRequest', fields={
        'full_name': serializers.CharField(required=False),
        'phone_number': serializers.CharField(required=False),
        'bio': serializers.CharField(required=False),
        'theme_preference': serializers.ChoiceField(choices=['light', 'dark'], required=False),
    }),
    responses={200: inline_serializer('ProfileResponse', fields={
        'id': serializers.IntegerField(),
        'email': serializers.EmailField(),
        'phone_number': serializers.CharField(),
        'full_name': serializers.CharField(),
        'bio': serializers.CharField(),
        'theme_preference': serializers.CharField(),
        'profile_picture_url': serializers.CharField(),
        'is_online': serializers.BooleanField(),
    })},
)
@api_view(['GET', 'PATCH'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def profile_settings(request):
    if request.method == 'GET':
        return Response({
            'id': request.user.id,
            'email': request.user.email,
            'phone_number': request.user.phone_number,
            'full_name': request.user.full_name,
            'bio': request.user.bio,
            'theme_preference': request.user.theme_preference,
            'profile_picture_url': request.user.profile_picture_url,
            'is_online': request.user.is_online,
        })

    data = request.data
    updated_fields = []

    if 'full_name' in data:
        request.user.full_name = data.get('full_name', '').strip()
        updated_fields.append('full_name')

    if 'phone_number' in data:
        request.user.phone_number = data.get('phone_number', '').strip()
        updated_fields.append('phone_number')

    if 'bio' in data:
        request.user.bio = data.get('bio', '').strip()
        updated_fields.append('bio')

    if 'theme_preference' in data:
        theme = data.get('theme_preference', 'light').strip().lower()
        if theme not in {'light', 'dark'}:
            return Response({'error': 'Theme must be light or dark.'}, status=400)
        request.user.theme_preference = theme
        updated_fields.append('theme_preference')

    if updated_fields:
        request.user.save(update_fields=updated_fields)

    return Response({
        'id': request.user.id,
        'email': request.user.email,
        'phone_number': request.user.phone_number,
        'full_name': request.user.full_name,
        'bio': request.user.bio,
        'theme_preference': request.user.theme_preference,
        'profile_picture_url': request.user.profile_picture_url,
        'is_online': request.user.is_online,
    })


@extend_schema(
    tags=['Profile'],
    summary='Upload a profile picture',
    request=inline_serializer('ProfilePicRequest', fields={'file': serializers.ImageField()}),
    responses={200: inline_serializer('ProfilePicResponse', fields={'profile_picture_url': serializers.CharField()})},
)
@api_view(['POST'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def upload_profile_picture(request):
    file = request.FILES.get('file')
    if not file:
        return Response({'error': 'No file provided'}, status=400)

    if file.size > MAX_FILE_SIZE:
        return Response({'error': 'File exceeds 5MB limit'}, status=400)

    if not file.content_type.startswith('image/'):
        return Response({'error': 'Only image files are allowed'}, status=400)

    result = cloudinary.uploader.upload(
        file,
        resource_type='image',
        folder='profile_pics/',
    )

    request.user.profile_picture_url = result['secure_url']
    request.user.save(update_fields=['profile_picture_url'])

    return Response({'profile_picture_url': result['secure_url']})

@extend_schema(
    tags=['Rooms'],
    summary='Upload a group profile picture',
    request=inline_serializer('GroupPicRequest', fields={'file': serializers.ImageField()}),
    responses={200: inline_serializer('GroupPicResponse', fields={'profile_picture_url': serializers.CharField()})},
)
@api_view(['POST'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def upload_group_picture(request, room_id):
    try:
        room = Room.objects.get(id=room_id, is_group=True, members=request.user)
    except Room.DoesNotExist:
        return Response({'error': 'Group not found or you are not a member'}, status=404)

    file = request.FILES.get('file')
    if not file:
        return Response({'error': 'No file provided'}, status=400)

    if file.size > MAX_FILE_SIZE:
        return Response({'error': 'File exceeds 5MB limit'}, status=400)

    if not file.content_type.startswith('image/'):
        return Response({'error': 'Only image files are allowed'}, status=400)

    result = cloudinary.uploader.upload(
        file,
        resource_type='image',
        folder='group_pics/',
    )

    room.profile_picture_url = result['secure_url']
    room.save(update_fields=['profile_picture_url'])

    return Response({'profile_picture_url': result['secure_url']})  