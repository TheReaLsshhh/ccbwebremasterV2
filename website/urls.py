from django.urls import path

from . import views

app_name = "website"

urlpatterns = [
    path("", views.home, name="home"),
    path("academics/", views.academics, name="academics"),
    path("admissions/", views.admissions, name="admissions"),
    path("news/", views.news, name="news"),
    path("downloads/", views.downloads, name="downloads"),
    path("students/", views.students, name="students"),
    path("faculty/", views.faculty, name="faculty"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
]
