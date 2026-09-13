from django.urls import path

from base.views import ClubDirectoryView, MyMembershipsView

urlpatterns = [
    path(
        'clubs-directory/',
        ClubDirectoryView.as_view(),
        name='base-club-directory'
    ),
    path(
        'my-memberships/',
        MyMembershipsView.as_view(),
        name='base-my-club-memberships'
    ),
]
