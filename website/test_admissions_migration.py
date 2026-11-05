from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class AdmissionsReplacementMigrationTests(TransactionTestCase):
    def test_checklist_attachments_remain_downloadable_after_replacement(self):
        old = [("website", "0017_page_banner_crop")]
        latest = [("website", "0018_program_logos_admissions_support")]
        executor = MigrationExecutor(connection)
        executor.migrate(old)
        try:
            apps = executor.loader.project_state(old).apps
            requirement = apps.get_model("website", "AdmissionRequirement")
            requirement.objects.create(title="Application form", description="Official instructions", document_file="admissions/keep.pdf", published=True)
            requirement.objects.create(title="Draft form", document_file="admissions/draft.pdf", published=False)
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            apps = executor.loader.project_state(latest).apps
            downloads = apps.get_model("website", "DownloadItem")
            self.assertTrue(downloads.objects.get(file="admissions/keep.pdf").published)
            self.assertFalse(downloads.objects.get(file="admissions/draft.pdf").published)
            self.assertEqual(downloads.objects.get(file="admissions/keep.pdf").description, "Official instructions")
            self.assertEqual(apps.get_model("website", "AdmissionSupport").objects.count(), 3)
            self.assertNotIn("website_admissionrequirement", connection.introspection.table_names())
        finally:
            MigrationExecutor(connection).migrate(latest)
