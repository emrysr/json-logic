"""json-logic rules shared between Python (server-side) and JS (client-side,
via the same rule tree fetched from /api/logic/booking) so both sides make
the same booking decisions from one source of truth.

Each exported rule is an envelope - {"description", "message", "rule"} -
rather than a bare json-logic tree. "rule" is what actually gets evaluated;
"description" and "message" are metadata for humans (self-documentation,
and the reason to show when a rule evaluates to False) that ride alongside
it but never touch the evaluator."""

from json_logic import jsonLogic

# A fairway's ruleset.rules entries look like:
#   {"category": {"id": 21, "name": "Bronze"}, "period": {"start": {"id": 1},
#    "end": {"id": 5}}, "start_time": "07:00:00", "end_time": "16:00:00"}
# `target_day` (ISO weekday, Monday=1..Sunday=7) and `target_time`
# ("HH:MM:SS") are merged onto each rule before evaluation, so the same
# rule tree works with any json-logic engine without a "parent scope"
# accessor.
ELIGIBLE_CATEGORIES_FOR_TEETIME = {
    "description": (
        "Finds every player category permitted to book a given fairway at a "
        "given day/time, by matching the fairway's ruleset.rules entries on "
        "period (day-of-week range) and start_time/end_time."
    ),
    "message": "This category is not permitted to book at the selected time.",
    "rule": {
        "map": [
            {
                "filter": [
                    {"var": "rules"},
                    {
                        "and": [
                            {
                                "<=": [
                                    {"var": "period.start.id"},
                                    {"var": "target_day"},
                                ]
                            },
                            {"<=": [{"var": "target_day"}, {"var": "period.end.id"}]},
                            {"<=": [{"var": "start_time"}, {"var": "target_time"}]},
                            {"<=": [{"var": "target_time"}, {"var": "end_time"}]},
                        ]
                    },
                ]
            },
            {"var": "category.id"},
        ]
    },
}


def augment_rules_with_teetime(fairway_rules, teetime):
    """The exact `{"rules": [...]}` data ELIGIBLE_CATEGORIES_FOR_TEETIME is
    evaluated against - exposed separately so callers can display it."""
    target_day = teetime.isoweekday()
    target_time = teetime.strftime("%H:%M:%S")
    return [
        {**rule, "target_day": target_day, "target_time": target_time}
        for rule in fairway_rules
    ]


def eligible_category_ids_for_teetime(fairway_rules, teetime):
    """fairway_rules: list of ruleset.rules dicts from the teesheet response.
    teetime: a timezone-aware datetime for the slot being checked.
    Returns the deduped set of category ids allowed to play at that time."""
    augmented = augment_rules_with_teetime(fairway_rules, teetime)
    category_ids = jsonLogic(
        ELIGIBLE_CATEGORIES_FOR_TEETIME["rule"], {"rules": augmented}
    )
    return sorted(set(category_ids))


# Rather than filtering players down to only the eligible ones, this maps
# every player (in the same order) to a plain eligible/not-eligible flag,
# so the full list can be rendered with ineligible rows shown as disabled
# instead of removed. `eligible_category_ids` is merged onto each player
# before evaluation - same "no parent scope inside map" reasoning as above.
PLAYERS_ELIGIBLE_FLAGS = {
    "description": (
        "Flags every player (preserving the full list) with whether their "
        "category is in the set of category ids eligible for the teetime "
        "being checked."
    ),
    "message": "This player's category is not eligible for the selected teetime.",
    "rule": {
        "map": [
            {"var": "players"},
            {"in": [{"var": "category.id"}, {"var": "eligible_category_ids"}]},
        ]
    },
}


def augment_players_with_eligible_category_ids(players, eligible_category_ids):
    """The exact `{"players": [...]}` data PLAYERS_ELIGIBLE_FLAGS is
    evaluated against - exposed separately so callers can display it."""
    return [
        {**player, "eligible_category_ids": eligible_category_ids}
        for player in players
    ]


def players_with_eligibility(players, eligible_category_ids):
    """Returns [(player, is_eligible), ...] preserving the full player list,
    with is_eligible computed via the shared PLAYERS_ELIGIBLE_FLAGS rule."""
    augmented = augment_players_with_eligible_category_ids(
        players, eligible_category_ids
    )
    flags = jsonLogic(PLAYERS_ELIGIBLE_FLAGS["rule"], {"players": augmented})
    return list(zip(players, flags))


# `min_handicap` comes from a club's ClubRules.rules.bookings.min_handicap -
# the club-configured floor a player's handicap must meet to book. Same
# map-with-merged-context shape as PLAYERS_ELIGIBLE_FLAGS.
PLAYERS_MEET_MIN_HANDICAP = {
    "description": (
        "Flags every player (preserving the full list) with whether their "
        "handicap meets the club's configured bookings.min_handicap floor."
    ),
    "message": "This player's handicap does not meet the club's minimum handicap requirement.",
    "rule": {
        "map": [
            {"var": "players"},
            {"<=": [{"var": "min_handicap"}, {"var": "handicap"}]},
        ]
    },
}


def augment_players_with_min_handicap(players, min_handicap):
    """The exact `{"players": [...]}` data PLAYERS_MEET_MIN_HANDICAP is
    evaluated against - exposed separately so callers can display it."""
    return [{**player, "min_handicap": min_handicap} for player in players]


def players_meeting_min_handicap(players, min_handicap):
    """Returns [(player, meets_min_handicap), ...] preserving the full
    player list, via the shared PLAYERS_MEET_MIN_HANDICAP rule."""
    augmented = augment_players_with_min_handicap(players, min_handicap)
    flags = jsonLogic(PLAYERS_MEET_MIN_HANDICAP["rule"], {"players": augmented})
    return list(zip(players, flags))
