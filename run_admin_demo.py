import json
import os
import sys

import django
from django.conf import settings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="demo-secret-key",
        ALLOWED_HOSTS=["*"],
        ROOT_URLCONF=__name__,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": os.path.join(BASE_DIR, "admin_demo.sqlite3"),
            }
        },
        INSTALLED_APPS=[
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "django.contrib.staticfiles",
            "django_json_widget",
            "rest_framework",
            "admin_demo",
        ],
        MIDDLEWARE=[
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.common.CommonMiddleware",
        ],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                    ],
                },
            },
        ],
        STATIC_URL="/static/",
        USE_TZ=True,
    )
    django.setup()

from django.contrib import admin  # noqa: E402
from django.urls import path  # noqa: E402

from admin_demo.api import BookingLogicView, LogicDemoPageView  # noqa: E402

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/logic/booking", BookingLogicView.as_view(), name="logic-booking"),
    path("logic-demo/", LogicDemoPageView.as_view(), name="logic-demo"),
]


if __name__ == "__main__":
    from django.core.management import call_command

    call_command("migrate", "--run-syncdb", verbosity=0)

    from django.contrib.auth import get_user_model

    User = get_user_model()
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@example.com", "admin")

    from admin_demo.models import ClubRules

    raw_json = '{"bookings": {"visitor_bookings_allowed": true, "max_visitor_bookings_per_week": 2, "visitor_bookings_when": "weekdays", "max_no_show_limit": 2, "min_handicap": 18}, "guests": {"guest_bookings_allowed": true, "max_guests_per_member_per_week": 3, "max_guests_per_booking": 2, "guest_bookings_when": "weekdays"}, "merge_rules": {"merge_tee_time_bookings": true, "tee_time_merge_range": "30_minutes", "merge_bookings_with": "2_player_slots"}, "extras": {"extra_bookings": true, "golf_buggies": true, "electric_golf_trollies": true, "standard_golf_trollies": true}, "configuration": {"check_in_required": true, "booking_interval": "4_hrs", "advanced_booking_window": "21_days", "countdown": "6_mins"}, "payments": {"split_payments": true, "payment_methods": ["online"]}, "cancellation_policies": {"cancellation_allowed": true, "rules": [{"category": "visitors", "object": "tee_booking", "period": "<= 24 hrs", "refund_amount_pct": 0}, {"category": "visitors", "object": "tee_booking", "period": "<= 48 hrs", "refund_amount_pct": 50}, {"category": "visitors", "object": "tee_booking", "period": "48 hrs >", "refund_amount_pct": 100}]}}'
    rules_data = json.loads(raw_json)

    if not ClubRules.objects.exists():
        ClubRules.objects.create(club_name="club_1", rules=rules_data)

        club_2_rules = json.loads(raw_json)
        club_2_rules["bookings"]["visitor_bookings_allowed"] = False
        club_2_rules["bookings"]["max_visitor_bookings_per_week"] = 0
        club_2_rules["bookings"]["min_handicap"] = 0
        club_2_rules["cancellation_policies"]["rules"] = club_2_rules[
            "cancellation_policies"
        ]["rules"][:1]
        ClubRules.objects.create(club_name="club_2", rules=club_2_rules)

    call_command("runserver", "0.0.0.0:8765", use_reloader=False)
