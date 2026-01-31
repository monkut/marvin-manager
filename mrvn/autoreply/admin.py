from django.contrib import admin

from .models import AutoReplyConfig, MessageFilter, RoutingRule


@admin.register(RoutingRule)
class RoutingRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "rule_type", "agent", "priority", "is_active"]
    list_filter = ["rule_type", "is_active", "agent"]
    search_fields = ["name", "pattern"]
    ordering = ["-priority", "name"]


@admin.register(AutoReplyConfig)
class AutoReplyConfigAdmin(admin.ModelAdmin):
    list_display = ["channel", "is_enabled", "default_agent", "max_messages_per_minute"]
    list_filter = ["is_enabled"]
    search_fields = ["channel__name"]


@admin.register(MessageFilter)
class MessageFilterAdmin(admin.ModelAdmin):
    list_display = ["name", "channel", "is_active"]
    list_filter = ["is_active", "channel"]
    search_fields = ["name", "pattern"]
