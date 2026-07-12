import json
import cloudinary.uploader
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model, authenticate, login
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from .authentication import CsrfExemptSessionAuthentication
from .models import Room, Message

User = get_user_model()
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@csrf_exempt
def signup_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            phone_number = data.get('phone_number')
            full_name = data.get('full_name', '')
            password = data.get('password')

            if not email or not phone_number or not password:
                return JsonResponse({'error': 'Please provide email, phone number, and password.'}, status=400)

            if User.objects.filter(email=email).exists():
                return JsonResponse({'error': 'A user with this email already exists.'}, status=400)

            if User.objects.filter(phone_number=phone_number).exists():
                return JsonResponse({'error': 'A user with this phone number already exists.'}, status=400)

            user = User.objects.create_user(
                email=email,
                phone_number=phone_number,
                full_name=full_name,
                password=password
            )

            return JsonResponse({'message': 'User registered successfully!', 'user_id': user.id}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                return JsonResponse({'error': 'Please provide both email and password.'}, status=400)

            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                return JsonResponse({
                    'message': 'Login successful!',
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'phone_number': user.phone_number,
                        'full_name': user.full_name
                    }
                }, status=200)
            else:
                return JsonResponse({'error': 'Invalid email or password.'}, status=401)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)


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


@api_view(['GET'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def online_users(request):
    online = User.objects.filter(is_online=True).values('id', 'full_name', 'email')
    return Response(list(online))


@api_view(['GET'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def list_rooms(request):
    rooms = Room.objects.filter(members=request.user).prefetch_related('members', 'messages')
    data = []
    for room in rooms:
        last_msg = room.messages.order_by('-timestamp').first()

        if room.is_group:
            display_name = room.name
            other_user_id = None
            is_online = False
        else:
            other_member = room.members.exclude(id=request.user.id).first()
            display_name = other_member.full_name if other_member else room.name
            other_user_id = other_member.id if other_member else None
            is_online = other_member.is_online if other_member else False

        if last_msg:
            if last_msg.text:
                preview = last_msg.text
            elif last_msg.file_type == 'image':
                preview = '📷 Photo'
            elif last_msg.file_type == 'file':
                preview = '📎 File'
            else:
                preview = ''
            last_time = last_msg.timestamp.isoformat()
        else:
            preview = 'No messages yet'
            last_time = room.created_at.isoformat()

        data.append({
            'id': room.id,
            'name': room.name,
            'display_name': display_name,
            'is_group': room.is_group,
            'other_user_id': other_user_id,
            'is_online': is_online,
            'last_message': preview,
            'last_message_time': last_time,
        })

    data.sort(key=lambda r: r['last_message_time'], reverse=True)
    return Response(data)


@api_view(['GET'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def list_users(request):
    users = User.objects.exclude(id=request.user.id).values('id', 'full_name', 'email', 'is_online')
    return Response(list(users))


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

    existing = Room.objects.filter(is_group=False, members=request.user).filter(members=other_user).first()
    if existing:
        return Response({'id': existing.id, 'name': existing.name})

    room_name = f"dm_{min(request.user.id, other_user.id)}_{max(request.user.id, other_user.id)}"
    room = Room.objects.create(name=room_name, is_group=False)
    room.members.add(request.user, other_user)

    return Response({'id': room.id, 'name': room.name}, status=201)


@api_view(['POST'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def create_group_chat(request):
    name = request.data.get('name')
    member_ids = request.data.get('member_ids', [])
    if not name:
        return Response({'error': 'Group name is required'}, status=400)

    room = Room.objects.create(name=name, is_group=True)
    room.members.add(request.user, *User.objects.filter(id__in=member_ids))

    return Response({'id': room.id, 'name': room.name}, status=201)