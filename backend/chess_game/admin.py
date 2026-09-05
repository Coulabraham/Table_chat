from django.contrib import admin
from .models import ChessState, Lesson, LessonProgress, ProcessedMove

admin.site.register([ChessState, Lesson, LessonProgress, ProcessedMove])
