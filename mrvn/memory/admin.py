from django.contrib import admin

from .models import CONTENT_PREVIEW_LENGTH, ConversationSummary, Message, Session


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["role", "content", "platform_message_id", "created_datetime"]
    can_delete = False
    max_num = 20


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["id", "chat_room", "contact", "agent", "is_active", "created_datetime"]
    list_filter = ["is_active", "agent"]
    search_fields = ["chat_room__name", "contact__display_name"]
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "role", "content_preview", "created_datetime"]
    list_filter = ["role", "session__agent"]
    search_fields = ["content", "platform_message_id"]

    def content_preview(self, obj: Message) -> str:
        if len(obj.content) > CONTENT_PREVIEW_LENGTH:
            return obj.content[:CONTENT_PREVIEW_LENGTH] + "..."
        return obj.content

    content_preview.short_description = "Content"  # type: ignore[attr-defined]


@admin.register(ConversationSummary)
class ConversationSummaryAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "messages_summarized", "created_datetime"]
    list_filter = ["session__agent"]
    search_fields = ["summary"]
