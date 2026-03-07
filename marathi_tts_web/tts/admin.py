import logging
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.urls import path, reverse
from django.utils.html import format_html
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
import csv
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from datetime import datetime
from django.shortcuts import render
from django.contrib import messages
from io import TextIOWrapper

logger = logging.getLogger(__name__)
from .models import UserInput
from .models.correction import MarathiCorrection
from models.correction_model import MarathiCorrectionModel

# Create the correction model instance after Django is fully initialized
correction_model = None

class CustomAdminSite(admin.AdminSite):
    site_header = 'Marathi TTS Administration'
    site_title = 'Marathi TTS Admin'
    index_template = 'admin/custom_index.html'
    login_template = 'admin/custom_login.html'
    logout_template = 'admin/custom_logout.html'
    
    # Enhanced Search
    search_fields = ['name', 'description']

    def get_app_list(self, request, app_label=None):
        """
        Return a sorted list of all the installed apps that have been
        registered in this site.
        """
        app_list = super().get_app_list(request)
        if (app_label):
            return [app for app in app_list if app['app_label'] == app_label]
        return [app for app in app_list if app['app_label'] != 'admin']

    def index(self, request, extra_context=None):
        try:
            extra_context = extra_context or {}
            extra_context.update({
                'user_count': User.objects.count(),
                'active_users': User.objects.filter(is_active=True).count(),
                'last_scan_date': getattr(request.user, 'last_login', timezone.now()),
            })
            return super().index(request, extra_context)
        except Exception as e:
            logger.error(f"Error in admin index: {e}")
            return super().index(request, {})

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('export-users/', self.admin_view(self.export_users), name='export_users'),
            path('export-logs/', self.admin_view(self.export_logs), name='export_logs'),
            path('activity-log/', self.admin_view(self.activity_log), name='activity_log'),
            path('stats/', self.admin_view(self.stats_view), name='stats'),
            path('export-data/', self.admin_view(self.export_data), name='export_data'),
            path('dashboard/', self.admin_view(self.dashboard_view), name='dashboard'),

        ]
        return custom_urls + urls

    def export_data(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="export.csv"'
        
        writer = csv.writer(response)
        # Add export logic here
        return response
    
    def dashboard_view(self, request):
        context = {
            'user_count': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'last_scan_date': getattr(request.user, 'last_login', timezone.now()),
            'site_stats': self.get_site_stats(),
        }
        return render(request, 'admin/dashboard.html', context)
    
    def get_site_stats(self):
        return {
            'total_models': len(self._registry),
            'recent_actions': LogEntry.objects.all()[:5],
        }

    def activity_log(self, request):
        context = {
            'recent_actions': LogEntry.objects.select_related('user', 'content_type')[:50],
            'title': 'Recent Activity Log'
        }
        return render(request, 'admin/activity_log.html', context)

    def stats_view(self, request):
        now = timezone.now()
        context = {
            'user_stats': {
                'total': User.objects.count(),
                'active': User.objects.filter(is_active=True).count(),
                'staff': User.objects.filter(is_staff=True).count(),
                'new_today': User.objects.filter(date_joined__date=now.date()).count(),
            },
            'security_stats': {
                'last_scan': getattr(request.user, 'last_login', now),
                'failed_logins': LogEntry.objects.filter(action_flag=3).count(),
            },
            'system_stats': {
                'total_models': len(self._registry),
                'total_entries': sum(model.objects.count() for model in self._registry.keys()),
            }
        }
        return render(request, 'admin/stats_dashboard.html', context)

    def export_users(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users.csv"'
        writer = csv.writer(response)
        writer.writerow(['Username', 'Email', 'First Name', 'Last Name', 'Active', 'Staff', 'Last Login'])
        
        for user in User.objects.all():
            writer.writerow([
                user.username, user.email, user.first_name, user.last_name,
                user.is_active, user.is_staff, user.last_login
            ])
        return response

    def export_logs(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="activity_logs.csv"'
        writer = csv.writer(response)
        writer.writerow(['Time', 'User', 'Action', 'Object'])
        
        for log in LogEntry.objects.select_related('user', 'content_type')[:1000]:
            writer.writerow([
                log.action_time, log.user, log.get_action_flag_display(),
                f"{log.content_type} - {log.object_repr}"
            ])
        return response

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'last_login', 'get_groups')
    list_filter = ('is_active', 'is_staff', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)
    
    def get_groups(self, obj):
        return ", ".join([g.name for g in obj.groups.all()])
    get_groups.short_description = 'Groups'

class CustomGroupAdmin(GroupAdmin):
    list_display = ('name', 'get_users_count')
    search_fields = ('name',)
    
    def get_users_count(self, obj):
        return obj.user_set.count()
    get_users_count.short_description = 'Users Count'

class UserInputAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'text', 'content', 'user__username')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

class MarathiCorrectionAdmin(admin.ModelAdmin):
    list_display = ('incorrect_text', 'correct_text', 'category', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('incorrect_text', 'correct_text', 'notes')
    ordering = ('-created_at',)
    change_list_template = 'admin/marathicorrection/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.import_csv_view, name='import_corrections_csv'),
            path('batch-add/', self.batch_add_view, name='batch_add_corrections'),
            path('export-csv/', self.export_csv, name='export_csv'),
        ]
        return custom_urls + urls

    def import_csv_view(self, request):
        if request.method == 'POST' and request.FILES.get('csv_file'):
            csv_file = TextIOWrapper(request.FILES['csv_file'].file, encoding='utf-8')
            reader = csv.DictReader(csv_file)
            
            success_count = 0
            error_count = 0
            
            for row in reader:
                try:
                    MarathiCorrection.objects.get_or_create(
                        incorrect_text=row['incorrect_text'],
                        defaults={
                            'correct_text': row['correct_text'],
                            'category': row.get('category', ''),
                            'notes': row.get('notes', '')
                        }
                    )
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    continue

            messages.success(request, f'Successfully imported {success_count} corrections. {error_count} errors.')
            return HttpResponseRedirect("../")
            
        return render(request, 'admin/marathicorrection/import_csv.html')

    def batch_add_view(self, request):
        if request.method == 'POST':
            text_data = request.POST.get('corrections_text', '')
            lines = text_data.strip().split('\n')
            
            success_count = 0
            error_count = 0
            
            for line in lines:
                try:
                    incorrect, correct, category, notes = line.strip().split(',', 3)
                    MarathiCorrection.objects.get_or_create(
                        incorrect_text=incorrect.strip(),
                        defaults={
                            'correct_text': correct.strip(),
                            'category': category.strip(),
                            'notes': notes.strip()
                        }
                    )
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    continue

            messages.success(request, f'Successfully added {success_count} corrections. {error_count} errors.')
            return HttpResponseRedirect("../")
            
        return render(request, 'admin/marathicorrection/batch_add.html')

    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="marathi_corrections.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['incorrect_text', 'correct_text', 'category', 'notes'])
        
        for correction in MarathiCorrection.objects.all():
            writer.writerow([
                correction.incorrect_text,
                correction.correct_text,
                correction.category,
                correction.notes
            ])
        
        return response

    def _refresh_global_service(self):
        """Refresh the global correction service instance"""
        from tts.views.ai_view import correction_service
        if correction_service and correction_service.corrector:
            correction_service.corrector.correction_model.load_rules()
            logger.info("Global correction service refreshed")

    def save_model(self, request, obj, form, change):
        """Called when saving a correction through admin"""
        logger.info(f"Saving correction: {obj.incorrect_text} → {obj.correct_text}")
        super().save_model(request, obj, form, change)
        self._refresh_global_service()
        messages.success(request, "Correction rules updated")

    def delete_model(self, request, obj):
        """Called when deleting a correction"""
        logger.info(f"Deleting correction: {obj.incorrect_text} → {obj.correct_text}")
        super().delete_model(request, obj)
        self._refresh_global_service()
        messages.success(request, "Correction rules updated")

    def delete_queryset(self, request, queryset):
        """Called when multiple corrections are deleted"""
        super().delete_queryset(request, queryset)
        self._refresh_global_service()
        messages.success(request, "Correction rules updated")

    actions = ['export_csv']

# Create custom admin site instance
admin_site = CustomAdminSite(name='marathi_tts_admin')

# Register models with custom admin site
admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)
admin_site.register(UserInput, UserInputAdmin)
admin_site.register(MarathiCorrection, MarathiCorrectionAdmin)

# Add admin actions
@admin.action(description="Mark selected users as active")
def make_active(modeladmin, request, queryset):
    queryset.update(is_active=True)

@admin.action(description="Mark selected users as inactive")
def make_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)

# Add to UserAdmin actions
CustomUserAdmin.actions = [make_active, make_inactive]

# Replace default admin site
admin.site = admin_site