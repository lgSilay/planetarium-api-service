from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import mixins, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from planetarium.models import (
    ShowTheme,
    PlanetariumDome,
    AstronomyShow,
    ShowSession,
    Reservation,
)
from planetarium.permissions import IsAdminOrIfAuthenticatedReadOnly
from planetarium.serializers import (
    ShowThemeSerializer,
    PlanetariumDomeSerializer,
    AstronomyShowSerializer,
    AstronomyShowListSerializer,
    AstronomyShowDetailSerializer,
    ShowSessionSerializer,
    ShowSessionListSerializer,
    ShowSessionDetailSerializer,
    ReservationSerializer,
    ReservationListSerializer,
)


class ShowThemeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = ShowTheme.objects.all()
    serializer_class = ShowThemeSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class PlanetariumDomeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = PlanetariumDome.objects.all()
    serializer_class = PlanetariumDomeSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class AstronomyShowViewSet(
    ReadOnlyModelViewSet,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    queryset = AstronomyShow.objects.all()
    serializer_class = AstronomyShowSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        """Retrieve the AstronomyShow with filters"""
        title = self.request.query_params.get("title")
        show_theme = self.request.query_params.get("show_theme")

        queryset = self.queryset

        if title:
            queryset = queryset.filter(title__icontains=title)

        if show_theme:
            show_theme_ids = self._params_to_ints(show_theme)
            queryset = queryset.filter(show_theme__id__in=show_theme_ids)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return AstronomyShowListSerializer

        if self.action == "retrieve":
            return AstronomyShowDetailSerializer

        return AstronomyShowSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "title",
                type=str,
                description="Filter AstronomyShow by title"
            ),
            OpenApiParameter(
                "show_theme",
                type={"type": "list", "items": {"type": "number"}},
                description="Filter AstronomyShow by show_theme id"
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ShowSessionViewSet(viewsets.ModelViewSet):
    queryset = (
        ShowSession.objects.all()
        .select_related("astronomy_show", "planetarium_dome")
        .annotate(
            tickets_available=(
                F("planetarium_dome__rows") * F("planetarium_dome__seats_in_row")
                - Count("tickets")
            )
        )
    )
    serializer_class = ShowSessionSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        date = self.request.query_params.get("date")
        astronomy_show_id_str = self.request.query_params.get("astronomy_show")

        queryset = self.queryset

        if date:
            date = datetime.strptime(date, "%Y-%m-%d").date()
            queryset = queryset.filter(show_time__date=date)

        if astronomy_show_id_str:
            queryset = queryset.filter(astronomy_show_id=int(astronomy_show_id_str))

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return ShowSessionListSerializer

        if self.action == "retrieve":
            return ShowSessionDetailSerializer

        return ShowSessionSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "astronomy_show",
                type={"type": "list", "items": {"type": "number"}},
                description="Filter AstronomyShow by astronomy_show id"
            ),
            OpenApiParameter(
                "date",
                type=OpenApiTypes.DATE,
                description="Filter AstronomyShow session by date"
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ReservationPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


class ReservationViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    queryset = Reservation.objects.prefetch_related(
        "tickets__show_session__astronomy_show",
        "tickets__show_session__planetarium_dome",
    )
    serializer_class = ReservationSerializer
    pagination_class = ReservationPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return ReservationListSerializer

        return ReservationSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
