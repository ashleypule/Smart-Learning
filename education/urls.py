from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from .views import generate_quiz, submit_quiz
from .views import voice_assistant_view, index


urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('select_grade/', views.select_grade, name='select_grade'),
    path('select_subject/', views.select_subject, name='select_subject'),
    path('ask_question/', views.ask_question, name='ask_question'),
    path('select_school_level/', views.select_school_level, name='select_school_level'),
    path('generate_content/', views.generate_content, name='generate_content'),
    path('index', index, name='index'),
    path('assistant/voice-assistant/', voice_assistant_view, name='voice_assistant'),
    path('quiz/', views.generate_quiz, name='quiz'),
    path('quiz/submit/', views.submit_quiz, name='submit_quiz'),
    path('results/<int:score>/<int:total>/<str:passed>/', views.results, name='results'),
    path('generate_quiz/', views.generate_quiz, name='generate_quiz'),
    path('capture_solution/', views.solution_capture_view, name='capture_solution'),
    path('edit/<int:solution_id>/', views.edit_solution, name='edit_solution'),
    path('detail/<int:solution_id>/', views.solution_detail, name='solution_detail'),
    path('correct_essay/', views.correct_essay, name='correct_essay'),
]
