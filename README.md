# Talkbox — Backend

A Django Channels WebSocket backend for the Talkbox real-time chat app. Supports private and group messaging, JWT auth, file uploads via Cloudinary, presence tracking, and a full Swagger API.

## 🚀 Live API

**Backend Repo:** [https://github.com/INUOLAJU/Talkbox-backend.git](https://github.com/INUOLAJU/Talkbox-backend.git)

Once running locally, API docs are available at:

```
http://127.0.0.1:8000/api/schema/swagger/
http://127.0.0.1:8000/api/schema/redoc/
```

---

## 🛠 Tech Stack

| Tool | Purpose |
|------|---------|
| Django 6 | Web framework |
| Django Channels 4 | WebSocket support |
| Daphne | ASGI server |
| Django REST Framework | REST API |
| drf-spectacular | Swagger / ReDoc docs |
| djangorestframework-simplejwt | JWT authentication |
| PostgreSQL (Supabase) | Database |
| Cloudinary | File & image storage |
| Redis | Channel layer (production) |
| django-cors-headers | CORS handling |

---

## 📦 Features

- User registration and JWT login
- Real-time messaging via WebSocket consumers
- Private and group chat rooms
- Unread message tracking per user per room
- Online/offline presence broadcasting
- File and image upload to Cloudinary (max 5MB)
- Profile management (name, phone, bio, avatar, theme)
- Group picture upload
- Add contacts by email or phone number
- Full OpenAPI 3 documentation (Swagger & ReDoc)

---

## 📌 API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/signup/` | Register a new user |
| POST | `/api/login/` | Login and get session cookie |

### Rooms
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chat/rooms/` | List all rooms for current user |
| POST | `/api/chat/rooms/start/` | Start or get a private chat |
| POST | `/api/chat/rooms/group/` | Create a group chat |
| POST | `/api/chat/rooms/<id>/read/` | Mark a room as read |
| POST | `/api/chat/rooms/<id>/picture/` | Upload group picture |

### Contacts
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/contacts/add/` | Add contact by email or phone |

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chat/users/` | List contacts |

### Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET / PATCH | `/api/chat/profile/` | Get or update profile |
| POST | `/api/chat/profile/upload/` | Upload profile picture |

### Files
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/upload/` | Upload a chat file or image |

### WebSocket
| URL | Description |
|-----|-------------|
| `ws://<host>/ws/chat/<room_name>/` | Connect to a chat room |

> Full request/response schemas available at `/api/schema/swagger/`

---

## ⚙️ Local Setup

### Prerequisites
- Python 3.10+
- PostgreSQL or a Supabase account
- Redis (for production channel layer)

### Installation

```bash
# Clone the repo
git clone https://github.com/INUOLAJU/Talkbox-backend.git
cd Talkbox-backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True

DB_NAME=postgres
DB_USER=postgres.your-project-ref
DB_PASS=your-supabase-password
DB_HOST=aws-0-eu-west-1.pooler.supabase.com
DB_PORT=6543

CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

### Run the server

```bash
python manage.py migrate
python manage.py runserver
```

API available at `http://127.0.0.1:8000`

Swagger docs at:
```
http://127.0.0.1:8000/api/schema/swagger/
http://127.0.0.1:8000/api/schema/redoc/
```

---

## 🗂 Project Structure

```
backend/
├── chat/
│   ├── migrations/
│   ├── admin.py
│   ├── authentication.py   # CSRF-exempt session auth
│   ├── consumers.py        # WebSocket consumer
│   ├── middleware.py
│   ├── models.py           # User, Room, Message, RoomReadStatus
│   ├── routing.py          # WebSocket URL routing
│   ├── urls.py             # REST URL patterns
│   └── views.py            # All API views with Swagger schemas
├── config/
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py             # Root URLs + Swagger routes
│   └── wsgi.py
├── manage.py
└── requirements.txt
```

---

## 🔌 Frontend

**Frontend Repo:** [https://github.com/INUOLAJU/Talkbox.git](https://github.com/INUOLAJU/Talkbox.git)

---

## 📄 License

MIT
