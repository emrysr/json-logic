import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from admin_demo.models import ClubRules

RAW_JSON = '{"bookings": {"visitor_bookings_allowed": true, "max_visitor_bookings_per_week": 2, "visitor_bookings_when": "weekdays", "max_no_show_limit": 2, "min_handicap": 18}, "guests": {"guest_bookings_allowed": true, "max_guests_per_member_per_week": 3, "max_guests_per_booking": 2, "guest_bookings_when": "weekdays"}, "merge_rules": {"merge_tee_time_bookings": true, "tee_time_merge_range": "30_minutes", "merge_bookings_with": "2_player_slots"}, "extras": {"extra_bookings": true, "golf_buggies": true, "electric_golf_trollies": true, "standard_golf_trollies": true}, "configuration": {"check_in_required": true, "booking_interval": "4_hrs", "advanced_booking_window": "21_days", "countdown": "6_mins"}, "payments": {"split_payments": true, "payment_methods": ["online"]}, "cancellation_policies": {"cancellation_allowed": true, "rules": [{"category": "visitors", "object": "tee_booking", "period": "<= 24 hrs", "refund_amount_pct": 0}, {"category": "visitors", "object": "tee_booking", "period": "<= 48 hrs", "refund_amount_pct": 50}, {"category": "visitors", "object": "tee_booking", "period": "48 hrs >", "refund_amount_pct": 100}]}}'


class Command(BaseCommand):
    help = "Creates the demo superuser (admin/admin) and seeds club_1/club_2 ClubRules."

    def handle(self, *args, **options):
        User = get_user_model()
        # Idempotent by design: always leaves admin/admin in a working state,
        # rather than only setting the password on first creation. Running
        # this again after a migration/db reset is the intended way to fix
        # a wiped or forgotten demo password, no separate changepassword step.
        user, created = User.objects.get_or_create(
            username="admin", defaults={"email": "admin@example.com"}
        )
        user.set_password("admin")
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.stdout.write(
            self.style.SUCCESS(
                "Created superuser admin/admin"
                if created
                else "Reset admin's password back to admin/admin"
            )
        )

        if ClubRules.objects.exists():
            self.stdout.write("ClubRules already seeded, skipping")
            return

        rules_data = json.loads(RAW_JSON)
        ClubRules.objects.create(club_name="club_1", rules=rules_data)

        club_2_rules = json.loads(RAW_JSON)
        club_2_rules["bookings"]["visitor_bookings_allowed"] = False
        club_2_rules["bookings"]["max_visitor_bookings_per_week"] = 0
        club_2_rules["bookings"]["min_handicap"] = 0
        club_2_rules["cancellation_policies"]["rules"] = club_2_rules[
            "cancellation_policies"
        ]["rules"][:1]
        ClubRules.objects.create(club_name="club_2", rules=club_2_rules)

        self.stdout.write(self.style.SUCCESS("Seeded club_1 and club_2"))
