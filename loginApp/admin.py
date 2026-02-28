from django.contrib import admin
from django.utils.html import format_html
from .models import CustomerSignUp


@admin.register(CustomerSignUp)
class CustomerSignUpAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'username', 'full_name', 'email', 'designation',
        'phone', 'address', 'profile_thumb',
    )
    search_fields = (
        'user__username', 'user__email',
        'first_name', 'last_name', 'designation', 'phone',
    )
    ordering = ('user__username',)
    readonly_fields = ('user', 'profile_thumb')

    fieldsets = (
        ('Account', {
            'fields': ('user',),
        }),
        ('Personal Info', {
            'fields': (
                'first_name', 'last_name', 'email',
                'phone', 'designation', 'address', 'information',
            ),
        }),
        ('Profile Picture', {
            'fields': ('profile_picture', 'profile_thumb'),
        }),
    )

    def username(self, obj):
        return obj.user.username
    username.short_description = "Username"
    username.admin_order_field = 'user__username'

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()
    full_name.short_description = "Full Name"

    def email(self, obj):
        return obj.email
    email.short_description = "Email"

    def profile_thumb(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="/media/{}" style="height:40px;width:40px;'
                'border-radius:50%;object-fit:cover;" />',
                obj.profile_picture,
            )
        return "—"
    profile_thumb.short_description = "Photo"
