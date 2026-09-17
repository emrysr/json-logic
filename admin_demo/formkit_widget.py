import json

from django import forms
from django.utils.safestring import mark_safe


# Mirrors the shape of the `rules` JSONField. Group nodes describe nested
# objects; each leaf uses only FormKit's free/core inputs (radio, select,
# number, checkbox) - no Pro-only toggle/repeater.
def build_schema(cancellation_rule_count):
    def yes_no(name, label):
        return {
            "$formkit": "radio",
            "name": name,
            "label": label,
            "options": [
                {"label": "Yes", "value": True},
                {"label": "No", "value": False},
            ],
        }

    def number(name, label):
        return {"$formkit": "number", "name": name, "label": label}

    def select(name, label, options):
        return {
            "$formkit": "select",
            "name": name,
            "label": label,
            "options": options,
        }

    def section(title, group_name, children):
        return {
            "$el": "div",
            "attrs": {"class": "demo-section"},
            "children": [
                {
                    "$el": "h3",
                    "attrs": {"class": "demo-section-title"},
                    "children": [title],
                },
                {
                    "$formkit": "group",
                    "name": group_name,
                    "children": children,
                },
            ],
        }

    cancellation_rows = []
    for i in range(cancellation_rule_count):
        cancellation_rows.append(
            {
                "$formkit": "group",
                "name": str(i),
                "children": [
                    select(
                        "category",
                        "Category",
                        ["visitors", "members", "guests"],
                    ),
                    select("object", "Object", ["tee_booking"]),
                    select(
                        "period",
                        "Period",
                        ["<= 24 hrs", "<= 48 hrs", "48 hrs >"],
                    ),
                    number("refund_amount_pct", "Refund Amount %"),
                ],
            }
        )

    sections = [
        section(
            "Bookings",
            "bookings",
            [
                yes_no("visitor_bookings_allowed", "Visitor Bookings Allowed"),
                number(
                    "max_visitor_bookings_per_week", "Max Visitor Bookings / Week"
                ),
                select(
                    "visitor_bookings_when",
                    "Visitor Bookings When",
                    ["weekdays", "weekends", "anytime"],
                ),
                number("max_no_show_limit", "Max No-Show Limit"),
                number("min_handicap", "Min Handicap"),
            ],
        ),
        section(
            "Guests",
            "guests",
            [
                yes_no("guest_bookings_allowed", "Guest Bookings Allowed"),
                number(
                    "max_guests_per_member_per_week", "Max Guests / Member / Week"
                ),
                number("max_guests_per_booking", "Max Guests / Booking"),
                select(
                    "guest_bookings_when",
                    "Guest Bookings When",
                    ["weekdays", "weekends", "anytime"],
                ),
            ],
        ),
        section(
            "Merge Rules",
            "merge_rules",
            [
                yes_no("merge_tee_time_bookings", "Merge Tee Time Bookings"),
                select(
                    "tee_time_merge_range",
                    "Tee Time Merge Range",
                    ["15_minutes", "30_minutes", "45_minutes", "60_minutes"],
                ),
                select(
                    "merge_bookings_with",
                    "Merge Bookings With",
                    ["2_player_slots", "3_player_slots", "4_player_slots"],
                ),
            ],
        ),
        section(
            "Extras",
            "extras",
            [
                yes_no("extra_bookings", "Extra Bookings"),
                yes_no("golf_buggies", "Golf Buggies"),
                yes_no("electric_golf_trollies", "Electric Golf Trollies"),
                yes_no("standard_golf_trollies", "Standard Golf Trollies"),
            ],
        ),
        section(
            "Configuration",
            "configuration",
            [
                yes_no("check_in_required", "Check-In Required"),
                select(
                    "booking_interval", "Booking Interval", ["2_hrs", "4_hrs", "6_hrs"]
                ),
                select(
                    "advanced_booking_window",
                    "Advanced Booking Window",
                    ["7_days", "14_days", "21_days", "30_days"],
                ),
                select("countdown", "Countdown", ["3_mins", "6_mins", "10_mins"]),
            ],
        ),
        section(
            "Payments",
            "payments",
            [
                yes_no("split_payments", "Split Payments"),
                {
                    "$formkit": "checkbox",
                    "name": "payment_methods",
                    "label": "Payment Method(s)",
                    "options": ["online", "in_person", "card"],
                },
            ],
        ),
        section(
            "Cancellation Policies",
            "cancellation_policies",
            [
                yes_no("cancellation_allowed", "Cancellation Allowed"),
                {
                    "$formkit": "group",
                    "name": "rules",
                    "children": cancellation_rows,
                },
            ],
        ),
    ]

    return [
        {
            "$el": "div",
            "attrs": {"class": "demo-grid"},
            "children": sections,
        }
    ]


def collect_numeric_paths(node, prefix=()):
    """FormKit's `number` input doesn't cast its value - it returns a string.
    Walk the schema and record the dotted path of every number leaf so the
    widget's JS can coerce those values back to real numbers before saving.
    Anonymous `$el` wrappers (fieldset/legend) don't add a nesting level;
    named `group` nodes do.
    """
    if isinstance(node, list):
        paths = []
        for child in node:
            paths.extend(collect_numeric_paths(child, prefix))
        return paths
    if not isinstance(node, dict):
        return []
    if node.get("$formkit") == "group":
        return collect_numeric_paths(
            node.get("children", []), prefix + (node["name"],)
        )
    if node.get("$formkit") == "number":
        return [".".join(prefix + (node["name"],))]
    if "children" in node:
        return collect_numeric_paths(node["children"], prefix)
    return []


class FormKitJSONWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, str):
            try:
                data = json.loads(value) if value else {}
            except ValueError:
                data = {}
        else:
            data = value or {}

        cancellation_rule_count = len(
            data.get("cancellation_policies", {}).get("rules", [])
        )
        schema = build_schema(cancellation_rule_count)
        numeric_paths = collect_numeric_paths(schema)

        widget_id = (attrs or {}).get("id", f"id_{name}")
        mount_id = f"{widget_id}_mount"

        schema_json = json.dumps(schema).replace("</", "<\\/")
        data_json = json.dumps(data).replace("</", "<\\/")
        numeric_paths_json = json.dumps(numeric_paths).replace("</", "<\\/")

        return mark_safe(f"""
<style>
  /* The admin's own field label just repeats what the section titles
     below already say - drop it and reclaim the horizontal space. */
  label[for="{widget_id}"] {{
    display: none;
  }}
  #{mount_id}-wrap {{
    max-width: none;
    margin-top: 8px;
  }}
  #{mount_id}-wrap .demo-grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    align-items: flex-start;
  }}
  #{mount_id}-wrap .demo-section {{
    flex: 1 1 360px;
    border: 1px solid var(--hairline-color, #444);
    border-radius: 8px;
    padding: 8px 20px 20px;
    margin: 0;
    background: var(--darkened-bg, rgba(255, 255, 255, 0.03));
  }}
  #{mount_id}-wrap .demo-section-title {{
    font-weight: 600;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    opacity: 0.7;
    margin: 0;
    padding: 14px 0 10px;
    border-bottom: 1px solid var(--hairline-color, #444);
  }}
  #{mount_id}-wrap .formkit-outer {{
    margin-top: 16px;
    margin-bottom: 0;
  }}
  #{mount_id}-wrap .formkit-label,
  #{mount_id}-wrap .formkit-legend {{
    display: block;
    font-weight: 500;
    opacity: 0.85;
    margin-bottom: 6px;
  }}
  #{mount_id}-wrap .formkit-fieldset {{
    border: 0;
    margin: 0;
    padding: 0;
  }}
  #{mount_id}-wrap .formkit-options {{
    list-style: none;
    display: flex;
    gap: 20px;
    margin: 0;
    padding: 0;
  }}
  #{mount_id}-wrap .formkit-wrapper {{
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
  }}
  #{mount_id}-wrap .formkit-input[type="radio"],
  #{mount_id}-wrap .formkit-input[type="checkbox"] {{
    accent-color: var(--link-fg, #79aec8);
    width: 15px;
    height: 15px;
    margin: 0;
  }}
  #{mount_id}-wrap input.formkit-input,
  #{mount_id}-wrap select.formkit-input {{
    background: var(--body-bg, #fff);
    color: var(--body-fg, #333);
    border: 1px solid var(--border-color, #ccc);
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 13px;
    max-width: 260px;
  }}
</style>
<input type="hidden" name="{name}" id="{widget_id}">
<div id="{mount_id}-wrap">
  <div id="{mount_id}"></div>
</div>
<script type="importmap">
{{
  "imports": {{
    "vue": "https://esm.sh/vue@3.4.21",
    "@formkit/core": "https://esm.sh/@formkit/core@1.6.9",
    "@formkit/vue": "https://esm.sh/@formkit/vue@1.6.9?deps=vue@3.4.21",
    "@formkit/themes": "https://esm.sh/@formkit/themes@1.6.9"
  }}
}}
</script>
<script type="module">
import {{ createApp, h }} from 'vue'
import {{ plugin, defaultConfig, FormKit, FormKitSchema }} from '@formkit/vue'

const schema = {schema_json}
const initialData = {data_json}
const numericPaths = {numeric_paths_json}
const hiddenInput = document.getElementById('{widget_id}')
hiddenInput.value = JSON.stringify(initialData)

function coerceNumbers(obj) {{
    for (const path of numericPaths) {{
        const parts = path.split('.')
        let ref = obj
        for (let i = 0; i < parts.length - 1 && ref != null; i++) {{
            ref = ref[parts[i]]
        }}
        const key = parts[parts.length - 1]
        if (ref != null && typeof ref[key] === 'string' && ref[key] !== '' && !isNaN(ref[key])) {{
            ref[key] = Number(ref[key])
        }}
    }}
    return obj
}}

const App = {{
    setup() {{
        const onUpdate = (v) => {{ hiddenInput.value = JSON.stringify(coerceNumbers(v)) }}
        return () => h(
            FormKit,
            {{
                type: 'form',
                modelValue: initialData,
                'onUpdate:modelValue': onUpdate,
                actions: false,
            }},
            {{ default: () => h(FormKitSchema, {{ schema }}) }}
        )
    }},
}}

createApp(App).use(plugin, defaultConfig()).mount('#{mount_id}')
</script>
""")
