from django.contrib import admin
from core.models import Office, Staff, Student, ClearanceRequest, Clearance
@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('user', 'office', 'role', 'is_dormitory_owner')
    list_filter = ('office', 'is_dormitory_owner')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'get_full_name', 'course', 'year_level', 'is_boarder')
    list_filter = ('course', 'year_level', 'is_boarder')
    search_fields = ('student_id', 'user__username', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Full Name'

@admin.register(ClearanceRequest)
class ClearanceRequestAdmin(admin.ModelAdmin):
    list_display = ('student', 'office', 'status', 'reviewed_by', 'request_date', 'reviewed_date')
    list_filter = ('status', 'office', 'request_date')
    search_fields = ('student__student_id', 'student__user__username', 'office__name')
    raw_id_fields = ('student', 'reviewed_by')
    readonly_fields = ('request_date',)
    date_hierarchy = 'request_date'

@admin.register(Clearance)
class ClearanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'is_cleared', 'program_chair_approved', 'cleared_date')
    list_filter = ('is_cleared', 'program_chair_approved')
    search_fields = ('student__student_id', 'student__user__username')
    raw_id_fields = ('student',)
    readonly_fields = ('cleared_date',)
    date_hierarchy = 'cleared_date'

    actions = ['approve_program_chair']

    def approve_program_chair(self, request, queryset):
        for clearance in queryset:
            if clearance.is_cleared:
                clearance.program_chair_approved = True
                clearance.save()
    approve_program_chair.short_description = "Approve selected clearances by program chair"

