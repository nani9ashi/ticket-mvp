from django.contrib import admin
from .models import Ticket, Comment, TicketHistory

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "due_date", "requester", "assignee", "created_at", "updated_at")
    list_filter = ("status", "due_date")
    search_fields = ("title", "body")

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "author", "created_at")
    search_fields = ("body",)

@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "actor", "action", "from_value", "to_value", "created_at")
    list_filter = ("action",)
