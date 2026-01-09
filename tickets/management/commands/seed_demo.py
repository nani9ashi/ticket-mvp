from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, User
from tickets.models import Ticket, TicketHistory, Comment, TicketStatus

DEMO_PASSWORD = "pass1234"

class Command(BaseCommand):
    help = "Create demo groups/users and sample tickets"

    def handle(self, *args, **options):
        requester_g, _ = Group.objects.get_or_create(name="Requester")
        agent_g, _ = Group.objects.get_or_create(name="Agent")
        admin_g, _ = Group.objects.get_or_create(name="Admin")

        def get_or_create_user(username, group: Group):
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            user.groups.add(group)
            return user

        req1 = get_or_create_user("requester1", requester_g)
        req2 = get_or_create_user("requester2", requester_g)
        ag1 = get_or_create_user("agent1", agent_g)
        ag2 = get_or_create_user("agent2", agent_g)
        ad1 = get_or_create_user("admin1", admin_g)

        if not Ticket.objects.exists():
            t1 = Ticket.objects.create(
                title="Cannot login on IE11",
                body="Legacy customer reports login failure.",
                requester=req1,
                status=TicketStatus.OPEN,
                assignee=None,
            )
            TicketHistory.objects.create(ticket=t1, actor=req1, action=TicketHistory.Action.CREATED)

            t2 = Ticket.objects.create(
                title="Invoice CSV export wrong header",
                body="Column names mismatch spec.",
                requester=req2,
                status=TicketStatus.IN_PROGRESS,
                assignee=ag1,
            )
            TicketHistory.objects.create(ticket=t2, actor=req2, action=TicketHistory.Action.CREATED)
            TicketHistory.objects.create(ticket=t2, actor=ad1, action=TicketHistory.Action.ASSIGNEE_CHANGED, from_value="", to_value=str(ag1.id))
            TicketHistory.objects.create(ticket=t2, actor=ag1, action=TicketHistory.Action.STATUS_CHANGED, from_value=TicketStatus.OPEN, to_value=TicketStatus.IN_PROGRESS)

            Comment.objects.create(ticket=t2, author=ag1, body="I will investigate export mapping.")
            TicketHistory.objects.create(ticket=t2, actor=ag1, action=TicketHistory.Action.COMMENT_ADDED)

        self.stdout.write(self.style.SUCCESS("Seed completed."))
        self.stdout.write(self.style.WARNING(f"Demo password: {DEMO_PASSWORD}"))
        self.stdout.write("Users: requester1 requester2 agent1 agent2 admin1")
