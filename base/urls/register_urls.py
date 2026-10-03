from django.urls import path
from base.views import details, change, lookup

app_name = "register"
urlpatterns = [
    path("", lookup, name="lookup"),
    path("details/", details, name="details"),
    path("change/", change, name="change"),
    # path("done/", done, name="done"),
]
