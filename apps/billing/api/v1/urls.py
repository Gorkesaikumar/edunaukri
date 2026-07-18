from django.urls import path

from apps.billing.api.v1.views import FeeScheduleListCreateView, PlacementFeeListView

urlpatterns = [
    path("fee-schedules/", FeeScheduleListCreateView.as_view(), name="fee-schedules"),
    path("placement-fees/", PlacementFeeListView.as_view(), name="placement-fees"),
]
