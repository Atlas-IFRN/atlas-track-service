import uuid

from django.db import models

# Create your models here.


class Track(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Rascunho'),
        ('PUBLISHED', 'Publicado'),
        ('ARCHIVED', 'Arquivado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    suap_creator_id = models.CharField(max_length=225, help_text="ID do professor criador vindo da API do SUAP")
    title = models.CharField(max_length=225)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Module(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=225)
    description = models.TextField()
    duration_hours = models.IntegerField(help_text="Duração estimada do módulo em horas")
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.track.title} - {self.title}"


class TrackChallenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='challenges')
    title = models.CharField(max_length=225)
    instructions = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self


class UserTrack(models.Model):
    STATUS_CHOICES = [
        ('IN_PROGRESS', 'Em Andamento'),
        ('COMPLETED', 'Concluído'),
        ('DROPPED', 'Desistente'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    suap_user_id = models.CharField(max_length=255, help_text="Identificador do aluno via SUAP")
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Inscrição: {self.suap_user_id} -> {self.track.title}"


class UserModuleProgress(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('COMPLETED', 'Concluído'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_track = models.ForeignKey(UserTrack, on_delete=models.CASCADE, related_name='module_progress')
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    completed_at = models.DateTimeField(null=True, blank=True)


class ChallengeSubmission(models.Model):
    AI_STATUS_CHOICES = [
        ('PENDING_AI', 'Pendente IA'),
        ('EVALUATED', 'Avaliado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_track = models.ForeignKey(UserTrack, on_delete=models.CASCADE, related_name='submissions')
    challenge = models.ForeignKey(TrackChallenge, on_delete=models.CASCADE)
    github_url = models.URLField(help_text="URL enviada pelo aluno")
    ai_status = models.CharField(max_length=20, choices=AI_STATUS_CHOICES, default='PENDING_AI')
    ai_feedback = models.TextField(null=True, blank=True, help_text="Feedback assíncrono consumido da fila")
    ai_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
