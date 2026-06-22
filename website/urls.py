from django.urls import path

from . import views

app_name = "website"

urlpatterns = [
    path("", views.home, name="home"),
    path("academics/", views.academics, name="academics"),
    path("academics/partial/", views.academics_partial, name="academics_partial"),
    path("admissions/", views.admissions, name="admissions"),
    path("admissions/partial/", views.admissions_partial, name="admissions_partial"),
    path("news/", views.news, name="news"),
    path("download/", views.cloudinary_download, name="cloudinary_download"),
    path("downloads/", views.downloads, name="downloads"),
    path("downloads/partial/", views.downloads_partial, name="downloads_partial"),
    path("students/", views.students, name="students"),
    path("students/partial/", views.students_partial, name="students_partial"),
    path("faculty/", views.faculty, name="faculty"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
]
