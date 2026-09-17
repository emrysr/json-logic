from django import forms
from django.contrib import admin
from django.utils.safestring import mark_safe

from .formkit_widget import FormKitJSONWidget
from .models import ClubRules


@admin.display(description="Visitor Bookings Allowed", boolean=True)
def get_visitor_bookings_allowed(obj):
    return obj.rules.get("bookings", {}).get("visitor_bookings_allowed", False)


class ClubSwitcherWidget(forms.Select):
    """Renders `club_name` as a dropdown of every club; picking a different
    one navigates to that club's own change page, since each row is a
    separate ClubRules record rather than a field to rename in place."""

    def render(self, name, value, attrs=None, renderer=None):
        clubs = ClubRules.objects.order_by("id").values("id", "club_name")
        widget_id = (attrs or {}).get("id", f"id_{name}")
        options = "".join(
            '<option value="{name}" data-id="{id}"{selected}>{name}</option>'.format(
                name=club["club_name"],
                id=club["id"],
                selected=" selected" if club["club_name"] == value else "",
            )
            for club in clubs
        )
        return mark_safe(f"""
<select name="{name}" id="{widget_id}">{options}</select>
<script>
document.getElementById("{widget_id}").addEventListener("change", function (e) {{
    var id = e.target.selectedOptions[0].dataset.id;
    window.location = window.location.pathname.replace(/\\d+(?=\\/change\\/?$)/, id);
}});
</script>
<style>
  /* Django renders the object's __str__ as a redundant heading here;
     the club switcher above already communicates which club is open. */
  #content h2 {{ display: none; }}
</style>
""")


class ClubRulesAdminForm(forms.ModelForm):
    class Meta:
        model = ClubRules
        fields = "__all__"
        widgets = {
            "club_name": ClubSwitcherWidget,
            "rules": FormKitJSONWidget,
        }
        labels = {
            "club_name": "Club",
            "rules": "",
        }


@admin.register(ClubRules)
class ClubRulesAdmin(admin.ModelAdmin):
    form = ClubRulesAdminForm
    list_display = ("club_name", get_visitor_bookings_allowed)
