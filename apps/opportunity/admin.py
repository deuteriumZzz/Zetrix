from django.contrib import admin
from django.utils import timezone

from .models import BusinessClimateProfile, BusinessClimateReview, ClimateDataSource


class ClimateDataSourceInline(admin.TabularInline):
    model = ClimateDataSource
    extra = 0


class BusinessClimateReviewInline(admin.TabularInline):
    model = BusinessClimateReview
    extra = 0
    fk_name = "profile"
    readonly_fields = ("generated_at", "confidence_score")


@admin.register(BusinessClimateProfile)
class BusinessClimateProfileAdmin(admin.ModelAdmin):
    list_display = ("__str__", "country", "region", "overall_complexity_score", "is_published")
    list_filter = ("country",)
    inlines = [ClimateDataSourceInline, BusinessClimateReviewInline]

    @admin.display(boolean=True)
    def is_published(self, obj):
        return obj.is_published


@admin.register(BusinessClimateReview)
class BusinessClimateReviewAdmin(admin.ModelAdmin):
    list_display = ("profile", "status", "confidence_score", "generated_at", "reviewed_by")
    list_filter = ("status",)
    actions = ["approve_reviews"]

    @admin.action(description="Approve selected reviews and publish their profiles")
    def approve_reviews(self, request, queryset):
        approved = 0
        for review in queryset:
            review.status = "approved"
            review.reviewed_by = request.user
            review.reviewed_at = timezone.now()
            review.save(update_fields=["status", "reviewed_by", "reviewed_at"])
            review.profile.published_review = review
            review.profile.save(update_fields=["published_review"])
            approved += 1
        self.message_user(request, f"Approved and published {approved} review(s).")
