from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.conf import settings
from .models import Ticket, Comment, TicketHistory, TicketStatus

def role_of(user):
    names = set(user.groups.values_list("name", flat=True))
    if "Admin" in names:
        return "Admin"
    if "Agent" in names:
        return "Agent"
    return "Requester"

def is_agent_user(user: User) -> bool:
    return user.groups.filter(name="Agent").exists()

def can_view(user, ticket: Ticket) -> bool:
    if getattr(settings, "INTENTIONAL_BUG_IDOR", False):
        return True

    r = role_of(user)
    if r in ("Admin", "Agent"):
        return True
    return ticket.requester_id == user.id

def can_update_status(user, ticket: Ticket) -> bool:
    r = role_of(user)
    if r == "Admin":
        return True
    if r == "Agent" and ticket.assignee_id == user.id:
        return True
    return False

@login_required
def ticket_list(request):
    r = role_of(request.user)
    qs = Ticket.objects.all().order_by("-created_at")

    if r == "Requester":
        qs = qs.filter(requester=request.user)

    status = request.GET.get("status") or ""
    q = (request.GET.get("q") or "").strip()

    if status:
        qs = qs.filter(status=status)

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))

    return render(request, "tickets/list.html", {
        "tickets": qs,
        "role": r,
        "status": status,
        "q": q,
        "statuses": TicketStatus.choices,
    })

@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not can_view(request.user, ticket):
        return HttpResponseForbidden("forbidden")

    r = role_of(request.user)
    next_candidates = [s for s in TicketStatus.values if ticket.can_transition_to(s)]
    agents = User.objects.filter(groups__name="Agent").order_by("username")

    return render(request, "tickets/detail.html", {
        "ticket": ticket,
        "role": r,
        "next_candidates": next_candidates,
        "agents": agents,
        "can_update_status": can_update_status(request.user, ticket),
    })

@login_required
def ticket_create(request):
    if role_of(request.user) != "Requester":
        return HttpResponseForbidden("forbidden")

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        body = (request.POST.get("body") or "").strip()
        attachment = request.FILES.get("attachment")

        t = Ticket(
            title=title,
            body=body,
            requester=request.user,
            attachment=attachment,
        )

        try:
            t.full_clean()
        except Exception as e:
            return render(request, "tickets/create.html", {"error": str(e)})

        t.save()
        TicketHistory.objects.create(
            ticket=t,
            actor=request.user,
            action=TicketHistory.Action.CREATED
        )
        return redirect("ticket_detail", pk=t.pk)

    return render(request, "tickets/create.html")


@login_required
def ticket_change_status(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not can_view(request.user, ticket):
        return HttpResponseForbidden("forbidden")
    if request.method != "POST":
        return HttpResponseForbidden("POST only")

    if role_of(request.user) == "Agent" and ticket.assignee_id is None:
        return HttpResponseForbidden("unassigned ticket cannot be updated by agent")

    if not can_update_status(request.user, ticket):
        return HttpResponseForbidden("forbidden")

    new_status = request.POST.get("status")
    if new_status not in TicketStatus.values:
        return HttpResponseForbidden("invalid")

    if not ticket.can_transition_to(new_status):
        return HttpResponseForbidden("invalid transition")

    old = ticket.status
    ticket.status = new_status
    ticket.save(update_fields=["status", "updated_at"])

    TicketHistory.objects.create(
        ticket=ticket,
        actor=request.user,
        action=TicketHistory.Action.STATUS_CHANGED,
        from_value=old,
        to_value=new_status,
    )
    return redirect("ticket_detail", pk=ticket.pk)

@login_required
def ticket_assign(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if role_of(request.user) != "Admin":
        return HttpResponseForbidden("forbidden")
    if request.method != "POST":
        return HttpResponseForbidden("POST only")

    assignee_id = request.POST.get("assignee_id") or ""
    if assignee_id == "":
        old = str(ticket.assignee_id) if ticket.assignee_id else ""
        ticket.assignee = None
        ticket.save(update_fields=["assignee", "updated_at"])
        TicketHistory.objects.create(
            ticket=ticket, actor=request.user,
            action=TicketHistory.Action.ASSIGNEE_CHANGED,
            from_value=old, to_value="",
        )
        return redirect("ticket_detail", pk=ticket.pk)

    user = get_object_or_404(User, pk=int(assignee_id))
    if not is_agent_user(user):
        return HttpResponseForbidden("assignee must be Agent")

    old = str(ticket.assignee_id) if ticket.assignee_id else ""
    ticket.assignee = user
    ticket.save(update_fields=["assignee", "updated_at"])

    TicketHistory.objects.create(
        ticket=ticket,
        actor=request.user,
        action=TicketHistory.Action.ASSIGNEE_CHANGED,
        from_value=old,
        to_value=str(user.id),
    )
    return redirect("ticket_detail", pk=ticket.pk)

@login_required
def ticket_add_comment(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not can_view(request.user, ticket):
        return HttpResponseForbidden("forbidden")
    if request.method != "POST":
        return HttpResponseForbidden("POST only")

    body = (request.POST.get("body") or "").strip()
    if not body:
        return redirect("ticket_detail", pk=ticket.pk)

    Comment.objects.create(ticket=ticket, author=request.user, body=body)
    TicketHistory.objects.create(
        ticket=ticket,
        actor=request.user,
        action=TicketHistory.Action.COMMENT_ADDED,
    )
    return redirect("ticket_detail", pk=ticket.pk)

@login_required
def ticket_change_due_date(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if role_of(request.user) != "Admin":
        return HttpResponseForbidden("forbidden")
    if request.method != "POST":
        return HttpResponseForbidden("POST only")

    due = request.POST.get("due_date") or ""
    old = ticket.due_date.isoformat() if ticket.due_date else ""

    if due == "":
        ticket.due_date = None
    else:
        ticket.due_date = due
        ticket.full_clean()

    ticket.save(update_fields=["due_date", "updated_at"])

    new = ticket.due_date.isoformat() if ticket.due_date else ""
    TicketHistory.objects.create(
        ticket=ticket, actor=request.user,
        action=TicketHistory.Action.DUE_DATE_CHANGED,
        from_value=old, to_value=new,
    )
    return redirect("ticket_detail", pk=ticket.pk)
