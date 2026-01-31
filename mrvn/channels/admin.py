from django.contrib import admin

from .models import Channel, ChannelCredential, ChatRoom, Contact


class ChannelCredentialInline(admin.StackedInline):
    model = ChannelCredential
    extra = 0


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ["name", "channel_type", "owner", "is_active", "created_datetime"]
    list_filter = ["channel_type", "is_active"]
    search_fields = ["name", "owner__username"]
    inlines = [ChannelCredentialInline]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["display_name", "platform_username", "channel", "is_blocked", "created_datetime"]
    list_filter = ["channel", "is_blocked"]
    search_fields = ["display_name", "platform_username", "platform_user_id"]


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ["name", "channel", "is_group", "is_active", "agent", "created_datetime"]
    list_filter = ["channel", "is_group", "is_active"]
    search_fields = ["name", "platform_chat_id"]
