from django.contrib import admin
from django.urls import path

from admin_demo.api import BookingLogicView, LogicDemoPageView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/logic/booking", BookingLogicView.as_view(), name="logic-booking"),
    path("logic-demo/", LogicDemoPageView.as_view(), name="logic-demo"),
    path("", LogicDemoPageView.as_view(), name="logic-demo-root"),
]
