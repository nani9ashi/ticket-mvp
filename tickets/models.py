from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
import os

class TicketStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    PENDING = "PENDING", "Pending"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"

ALLOWED_TRANSITIONS = {
    TicketStatus.OPEN: {TicketStatus.IN_PROGRESS, TicketStatus.PENDING},
    TicketStatus.IN_PROGRESS: {TicketStatus.RESOLVED, TicketStatus.PENDING},
    TicketStatus.PENDING: {TicketStatus.IN_PROGRESS},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED},
    TicketStatus.CLOSED: set(),
}

ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".pdf", ".txt"}
MAX_FILE_BYTES = 5 * 1024 * 1024

def validate_attachment(f):
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in ALLOWED_EXTS:
        raise ValidationError("Invalid file extension.")
    if f.size > MAX_FILE_BYTES:
        raise ValidationError("File too large (max 5MB).")

class Ticket(models.Model):
    title = models.CharField(max_length=80)
    body = models.TextField(max_length=4000)
    status = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN)

    due_date = models.DateField(null=True, blank=True)

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_tickets",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )

    attachment = models.FileField(
        upload_to="attachments/",
        null=True,
        blank=True,
        validators=[validate_attachment],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.due_date is not None and self.due_date < timezone.localdate():
            raise ValidationError({"due_date": "Due date cannot be in the past."})

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in ALLOWED_TRANSITIONS.get(self.status, set())

    def __str__(self):
        return f"#{self.pk} {self.title}"

class Comment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

class TicketHistory(models.Model):
    class Action(models.TextChoices):
        CREATED = "CREATED"
        STATUS_CHANGED = "STATUS_CHANGED"
        ASSIGNEE_CHANGED = "ASSIGNEE_CHANGED"
        COMMENT_ADDED = "COMMENT_ADDED"
        DUE_DATE_CHANGED = "DUE_DATE_CHANGED"

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    action = models.CharField(max_length=30, choices=Action.choices)
    from_value = models.CharField(max_length=200, null=True, blank=True)
    to_value = models.CharField(max_length=200, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
