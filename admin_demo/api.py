import json
import os
from datetime import datetime

from django.views.generic import TemplateView
from rest_framework.response import Response
from rest_framework.views import APIView

from .logic import (
    ELIGIBLE_CATEGORIES_FOR_TEETIME,
    PLAYERS_ELIGIBLE_FLAGS,
    PLAYERS_MEET_MIN_HANDICAP,
    eligible_category_ids_for_teetime,
    players_meeting_min_handicap,
    players_with_eligibility,
)
from .models import ClubRules

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
DEFAULT_TEETIME_ISO = "2026-09-18T07:00:00+00:00"
BOOKING_MIN_HANDICAP = 18


def get_min_handicap(club_name):
    """Pulls bookings.min_handicap from a club's ClubRules row - the "DAO
    function" for this mockup. Falls back to BOOKING_MIN_HANDICAP if the
    club or the field isn't set."""
    club = ClubRules.objects.filter(club_name=club_name).first()
    if club is None:
        return BOOKING_MIN_HANDICAP
    return club.rules.get("bookings", {}).get("min_handicap", BOOKING_MIN_HANDICAP)


def _load_fixture(filename):
    with open(os.path.join(FIXTURES_DIR, filename)) as f:
        return json.load(f)


def _booking_logic_payload():
    return {
        "eligible_categories_for_teetime": ELIGIBLE_CATEGORIES_FOR_TEETIME,
        "players_eligible_flags": PLAYERS_ELIGIBLE_FLAGS,
        "players_meet_min_handicap": PLAYERS_MEET_MIN_HANDICAP,
    }


class BookingLogicView(APIView):
    """Serves the booking-rules json-logic tree so it can be evaluated
    identically in Python (server-side validation) and JS (client-side,
    e.g. FormKit conditionals) from the same source of truth."""

    def get(self, request):
        return Response(_booking_logic_payload())


class LogicDemoPageView(TemplateView):
    """Renders the initial eligible/disabled player list server-side, using
    the exact same admin_demo.logic functions and fixture data that the
    page's JS later re-runs client-side when the teetime is changed. In a
    real system this view would pull the teesheet/player data from the DAO
    layer instead of these fixtures - the json-logic rule itself, and how
    it's evaluated, would be identical."""

    template_name = "admin_demo/logic_demo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Matches the real endpoint's shape (its top-level "data" property):
        # data.teesheet.fairways[0] carries both .ruleset.rules and .slots
        # together, not as separate payloads.
        teesheet_data = _load_fixture("example_teesheet.json")
        fairway = teesheet_data["teesheet"]["fairways"][0]
        rules = fairway["ruleset"]["rules"]
        slots = fairway["slots"]
        players = _load_fixture("example_players.json")
        min_handicap = get_min_handicap("club_1")

        # The teesheet is only for this one date - what a player actually
        # picks from is one of its slots, so build the hour/minute options
        # from there rather than a free-form time input.
        slot_times = [
            {"time": slot["time"][11:16], "bookable": slot["bookable"]}
            for slot in slots
        ]
        hours = sorted({t["time"][:2] for t in slot_times})
        hour_options = [
            {
                "hour": h,
                "bookable": any(
                    t["bookable"] for t in slot_times if t["time"][:2] == h
                ),
            }
            for h in hours
        ]
        default_hour = DEFAULT_TEETIME_ISO[11:13]
        default_minute = DEFAULT_TEETIME_ISO[14:16]
        minute_options_for_default_hour = [
            {"minute": t["time"][3:5], "bookable": t["bookable"]}
            for t in slot_times
            if t["time"][:2] == default_hour
        ]

        teetime = datetime.fromisoformat(DEFAULT_TEETIME_ISO)
        eligible_category_ids = eligible_category_ids_for_teetime(rules, teetime)
        category_flags = players_with_eligibility(players, eligible_category_ids)
        handicap_flags = players_meeting_min_handicap(players, min_handicap)
        initial_rows = [
            (player, category_ok, handicap_ok)
            for (player, category_ok), (_, handicap_ok) in zip(
                category_flags, handicap_flags
            )
        ]

        context["fixed_date_iso"] = DEFAULT_TEETIME_ISO[:10]
        context["fixed_date_display"] = teetime.strftime("%A %d %B %Y")
        context["hour_options"] = hour_options
        context["default_hour"] = default_hour
        context["minute_options_for_default_hour"] = minute_options_for_default_hour
        context["default_minute"] = default_minute
        context["slot_times_json"] = json.dumps(slot_times)
        context["initial_eligible_category_ids"] = eligible_category_ids
        context["min_handicap"] = min_handicap
        context["initial_rows"] = initial_rows
        context["category_message"] = PLAYERS_ELIGIBLE_FLAGS["message"]
        context["handicap_message"] = PLAYERS_MEET_MIN_HANDICAP["message"]
        context["initial_rule_output_json"] = json.dumps(
            _booking_logic_payload(), indent=2
        )
        # The true, untouched inputs - not merged with target_day/target_time/
        # min_handicap/eligible_category_ids, so they can be manually cross-
        # referenced against the small "parameters" block below for any row.
        context["initial_raw_rules_json"] = json.dumps(rules, indent=2)
        context["initial_raw_players_json"] = json.dumps(players, indent=2)
        context["initial_parameters_json"] = json.dumps(
            {
                "target_day": teetime.isoweekday(),
                "target_time": teetime.strftime("%H:%M:%S"),
                "eligible_category_ids": eligible_category_ids,
                "min_handicap": min_handicap,
            },
            indent=2,
        )
        context["teesheet_rules_json"] = json.dumps(rules)
        context["players_json"] = json.dumps(players)
        return context
