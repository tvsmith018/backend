import json
import logging

from channels.db import database_sync_to_async
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from rest_framework import serializers

from articles.models import ArticleView, ArticleViewDaily, Articles
from common.consumers.base import BaseCommentConsumer
from common.mixins.article import ArticleMixin
from users.models import Users

logger = logging.getLogger("articles")


class WatchInitSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="watch_init")
    user_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    session_key = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)
    source = serializers.ChoiceField(
        required=False,
        choices=[
            ArticleView.SourceChoices.WEB,
            ArticleView.SourceChoices.MOBILE,
            ArticleView.SourceChoices.API,
            ArticleView.SourceChoices.EMBED,
            ArticleView.SourceChoices.OTHER,
        ],
        default=ArticleView.SourceChoices.WEB,
    )


class WatchProgressSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="watch_progress")
    view_event_id = serializers.IntegerField(min_value=1)
    watched_seconds = serializers.IntegerField(min_value=0)


class ArticleViewTrackingConsumer(BaseCommentConsumer, ArticleMixin):
    COUNT_THRESHOLD_SECONDS = 20

    async def connect(self):
        self.article_id = self.scope["url_route"]["kwargs"]["article_id"]
        try:
            article = await self.get_article(self.article_id)
            self.article_pk = article.pk
        except Exception:
            logger.exception(
                "article_view_socket_connect_failed article_id=%s",
                self.article_id,
            )
            await self.close(code=4004)
            return
        await self.accept()
        logger.info(
            "article_view_socket_connected article_id=%s article_pk=%s",
            self.article_id,
            self.article_pk,
        )

    async def disconnect(self, close_code):
        logger.info(
            "article_view_socket_disconnected article_id=%s article_pk=%s close_code=%s",
            getattr(self, "article_id", None),
            getattr(self, "article_pk", None),
            close_code,
        )

    async def receive(self, text_data):
        try:
            payload = json.loads(text_data)
            action = payload.get("action", "watch_progress")
            logger.info(
                "article_view_socket_action article_pk=%s action=%s payload_keys=%s",
                getattr(self, "article_pk", None),
                action,
                sorted(payload.keys()),
            )

            if action == "watch_init":
                await self._handle_watch_init(payload)
                return

            if action == "watch_end":
                await self._handle_watch_progress(payload)
                return

            await self._handle_watch_progress(payload)
        except serializers.ValidationError as exc:
            logger.warning(
                "article_view_socket_validation_error article_pk=%s error=%s",
                getattr(self, "article_pk", None),
                exc.detail,
            )
            await self.send_json(
                {
                    "eventType": "watch_error",
                    "code": "validation_error",
                    "detail": exc.detail,
                }
            )
        except Exception:
            logger.exception(
                "article_view_socket_receive_failed article_pk=%s",
                getattr(self, "article_pk", None),
            )
            await self.send_json(
                {
                    "eventType": "watch_error",
                    "code": "server_error",
                }
            )

    async def _handle_watch_init(self, payload):
        serializer = WatchInitSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        view_event = await self._create_view_event(serializer.validated_data)
        logger.info(
            "article_view_created article_pk=%s view_event_id=%s source=%s user_id=%s session=%s",
            self.article_pk,
            view_event.id,
            view_event.source,
            view_event.user_id,
            bool(view_event.session_key),
        )

        await self.send_json(
            {
                "eventType": "watch_initialized",
                "viewEventId": view_event.id,
                "watchedSeconds": view_event.watched_seconds,
                "isCounted": view_event.is_counted,
                "isUnique": view_event.is_unique,
            }
        )

    async def _handle_watch_progress(self, payload):
        serializer = WatchProgressSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        result = await self._update_view_progress(
            view_event_id=serializer.validated_data["view_event_id"],
            watched_seconds=serializer.validated_data["watched_seconds"],
        )
        if not result:
            logger.warning(
                "article_view_progress_missing_event article_pk=%s requested_event_id=%s",
                self.article_pk,
                serializer.validated_data["view_event_id"],
            )
            return
        logger.info(
            "article_view_progress article_pk=%s view_event_id=%s watched=%s counted=%s unique=%s",
            self.article_pk,
            result["view_event_id"],
            result["watched_seconds"],
            result["is_counted"],
            result["is_unique"],
        )

        await self.send_json(
            {
                "eventType": "watch_progress_ack",
                "viewEventId": result["view_event_id"],
                "watchedSeconds": result["watched_seconds"],
                "isCounted": result["is_counted"],
                "isUnique": result["is_unique"],
            }
        )

    @database_sync_to_async
    def _create_view_event(self, data):
        article = Articles.objects.get(pk=self.article_pk)
        user = self._resolve_user(data.get("user_id"))

        view_event = ArticleView.objects.create(
            article=article,
            user=user,
            session_key=(data.get("session_key") or "").strip() or None,
            ip_address=self._extract_ip_address(),
            user_agent=self._extract_user_agent(),
            source=data.get("source", ArticleView.SourceChoices.WEB),
            is_counted=False,
            is_unique=False,
            watched_seconds=0,
        )
        self._increment_raw_view_totals(article.id)
        return view_event

    @database_sync_to_async
    def _update_view_progress(self, view_event_id: int, watched_seconds: int):
        with transaction.atomic():
            view_event = (
                ArticleView.objects.select_for_update()
                .select_related("article")
                .filter(id=view_event_id, article_id=self.article_pk)
                .first()
            )
            if not view_event:
                return None

            next_seconds = max(int(watched_seconds), view_event.watched_seconds)
            crossed_threshold = (
                not view_event.is_counted
                and next_seconds >= self.COUNT_THRESHOLD_SECONDS
            )

            view_event.watched_seconds = next_seconds

            if crossed_threshold:
                is_unique = not self._has_prior_counted_view(view_event)
                view_event.is_counted = True
                view_event.is_unique = is_unique
                self._increment_article_totals(view_event.article_id, is_unique=is_unique)
                self._increment_daily_totals(view_event.article_id, is_unique=is_unique)

            view_event.save(update_fields=["watched_seconds", "is_counted", "is_unique"])

            return {
                "view_event_id": view_event.id,
                "watched_seconds": view_event.watched_seconds,
                "is_counted": view_event.is_counted,
                "is_unique": view_event.is_unique,
            }

    def _increment_article_totals(self, article_id: int, is_unique: bool):
        Articles.objects.filter(id=article_id).update(
            counted_views_count=F("counted_views_count") + 1,
            unique_views_count=F("unique_views_count") + (1 if is_unique else 0),
            last_viewed_at=timezone.now(),
        )

    def _increment_raw_view_totals(self, article_id: int):
        Articles.objects.filter(id=article_id).update(
            views_count=F("views_count") + 1,
        )
        today = timezone.now().date()
        daily, _ = ArticleViewDaily.objects.get_or_create(article_id=article_id, date=today)
        ArticleViewDaily.objects.filter(id=daily.id).update(
            views_count=F("views_count") + 1,
        )

    def _increment_daily_totals(self, article_id: int, is_unique: bool):
        today = timezone.now().date()
        daily, _ = ArticleViewDaily.objects.get_or_create(article_id=article_id, date=today)

        updates = {"counted_views_count": F("counted_views_count") + 1}
        if is_unique:
            updates["unique_views_count"] = F("unique_views_count") + 1

        ArticleViewDaily.objects.filter(id=daily.id).update(**updates)

    def _has_prior_counted_view(self, current_view: ArticleView) -> bool:
        base_queryset = ArticleView.objects.filter(
            article_id=current_view.article_id,
            is_counted=True,
        ).exclude(id=current_view.id)

        if current_view.user_id:
            return base_queryset.filter(user_id=current_view.user_id).exists()

        if current_view.session_key:
            return base_queryset.filter(session_key=current_view.session_key).exists()

        if current_view.ip_address:
            return base_queryset.filter(
                ip_address=current_view.ip_address,
                user_agent=current_view.user_agent,
            ).exists()

        return base_queryset.filter(
            Q(session_key__isnull=True) | Q(session_key="")
        ).exists()

    def _resolve_user(self, payload_user_id):
        scope_user = self.scope.get("user")
        if scope_user and getattr(scope_user, "is_authenticated", False):
            return scope_user

        raw_user_id = str(payload_user_id or "").strip()
        if not raw_user_id.isdigit():
            return None

        return Users.objects.filter(id=int(raw_user_id)).first()

    def _extract_ip_address(self):
        headers = {
            key.decode("latin1").lower(): value.decode("latin1")
            for key, value in self.scope.get("headers", [])
        }
        forwarded_for = headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip() or None

        client = self.scope.get("client")
        if isinstance(client, (tuple, list)) and len(client) > 0:
            return client[0]

        return None

    def _extract_user_agent(self):
        headers = {
            key.decode("latin1").lower(): value.decode("latin1")
            for key, value in self.scope.get("headers", [])
        }
        return headers.get("user-agent")
