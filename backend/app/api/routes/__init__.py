"""
API Routes package
"""
from fastapi import APIRouter
from app.api.routes import auth, users, tasks, leaderboard, schedules, profile, admin, webhook, development, questions, notifications, quests, cups, zalo, certifications, scheduled_jobs

# Main API router
api_router = APIRouter()

# Include auth routes
api_router.include_router(auth.router)

# Include user management routes (Admin)
api_router.include_router(users.router)

# Include admin operations routes
api_router.include_router(admin.router)

# Include task management routes
api_router.include_router(tasks.router)

# Include leaderboard routes
api_router.include_router(leaderboard.router)

# Include schedule and attendance routes
api_router.include_router(schedules.router)

# Include profile routes
api_router.include_router(profile.router)

# Include webhook routes (S4H check-in)
api_router.include_router(webhook.router)

# Include member development routes
api_router.include_router(development.router)

# Include question routes
api_router.include_router(questions.router)

# Include notification routes
api_router.include_router(notifications.router)

# Include Daily Quest routes
api_router.include_router(quests.router)

# Include Weekly Cup routes
api_router.include_router(cups.router)

# Include optional Zalo OA Daily Task Quiz routes
api_router.include_router(zalo.router)

# Include exams and digital certificates
api_router.include_router(certifications.router)

# Protected callbacks used by the free-tier external scheduler
api_router.include_router(scheduled_jobs.router)

# Future routes will be added here:
# api_router.include_router(skills.router)
