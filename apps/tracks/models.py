import uuid

from django.core.exceptions import ValidationError
from django.db import models

# Create your models here.


class Track(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Rascunho'),
        ('PUBLISHED', 'Publicado'),
        ('ARCHIVED', 'Arquivado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator_id = models.UUIDField(help_text="UUID do professor criador (resolvido via API de Auth)")
    title = models.CharField(max_length=225)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        # Regra 2: Trilha Fantasma
        if self.status == 'PUBLISHED':
            if not self.pk or self.modules.count() == 0:
                raise ValidationError({"status": "Uma trilha não pode ser publicada sem ter pelo menos um módulo."})

    # CORREÇÃO 1: Voltou um nível de indentação
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # CORREÇÃO 1: Voltou um nível de indentação
    def delete(self, *args, **kwargs):
        # REGRA 3: Tapete Puxado
        has_active_students = self.enrollments.filter(status='IN_PROGRESS').exists()
        if has_active_students:
            raise ValidationError(
                "Não é possível apagar uma trilha com alunos em andamento. Mude o status para ARCHIVED."
            )

        # CORREÇÃO 2: Chamando o super().delete() no final, e não save()
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.title


class Module(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=225)
    description = models.TextField()
    display_order = models.IntegerField(help_text="Ordem do módulo dentro da trilha", default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'created_at']

    def __str__(self):
        return f"{self.track.title} - Módulo {self.display_order}: {self.title}"


class Content(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('VIDEO', 'Vídeo'),
        ('ARTICLE', 'Artigo'),
        ('REPOSITORY', 'Repositório'),
        ('CHALLENGE', 'Desafio'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='contents')
    title = models.CharField(max_length=255)
    description = models.TextField()
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    content_url = models.URLField(null=True, blank=True, help_text="URL para VIDEO, ARTICLE ou REPOSITORY")
    instructions = models.TextField(null=True, blank=True, help_text="Enunciado quando for um CHALLENGE")
    duration_minutes = models.IntegerField(null=True, blank=True, help_text="Estimativa em minutos")
    display_order = models.IntegerField(help_text="Ordem do conteúdo dentro do módulo", default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'created_at']

    def __str__(self):
        return f"{self.module.title} - [{self.content_type}] {self.title}"


class UserTrack(models.Model):
    STATUS_CHOICES = [
        ('IN_PROGRESS', 'Em Andamento'),
        ('COMPLETED', 'Concluído'),
        ('DROPPED', 'Desistente'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(help_text="UUID do aluno (resolvido via API de Auth)")
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user_id', 'track'], name='unique_user_track_enrollment')]

    def __str__(self):
        return f"Inscrição: {self.user_id} -> {self.track.title}"

    def clean(self):
        super().clean()

        if self._state.adding:
            if self.track and self.track.status != 'PUBLISHED':
                raise ValidationError({"track": "Inscrição bloqueada. A trilha deve estar no status PUBLISHED."})

            existing_enrollment = UserTrack.objects.filter(
                user_id=self.user_id, track=self.track, status__in=['IN_PROGRESS', 'COMPLETED']
            ).exists()

            if existing_enrollment:
                raise ValidationError(
                    {"user_id": "Este usuário já possui uma inscrição ativa ou concluída nesta trilha."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class UserModuleProgress(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('IN_PROGRESS', 'Em Andamento'),
        ('COMPLETED', 'Concluído'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_track = models.ForeignKey(UserTrack, on_delete=models.CASCADE, related_name='module_progress')
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    progress_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user_track', 'module'], name='unique_user_module_progress')]

    def clean(self):
        super().clean()
        # Regra 1: Anti-Pulo (Módulos)
        if self.status in ['IN_PROGRESS', 'COMPLETED']:
            # Busca o módulo anterior desta mesma trilha baseado na ordem (display_order)
            previous_module = (
                Module.objects.filter(track=self.module.track, display_order__lt=self.module.display_order)
                .order_by('-display_order')
                .first()
            )

            if previous_module:
                prev_progress = UserModuleProgress.objects.filter(
                    user_track=self.user_track, module=previous_module, status='COMPLETED'
                ).exists()

                if not prev_progress:
                    raise ValidationError(
                        {"status": f"Você precisa concluir o módulo '{previous_module.title}' antes de iniciar este."}
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class UserContentProgress(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('COMPLETED', 'Concluído'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_track = models.ForeignKey(UserTrack, on_delete=models.CASCADE, related_name='content_progress')
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user_track', 'content'], name='unique_user_content_progress')]

    def clean(self):
        super().clean()
        # Regra 1: Anti-Pulo (Conteúdos)
        if self.status == 'COMPLETED':
            # Busca o conteúdo anterior do mesmo módulo
            previous_content = (
                Content.objects.filter(module=self.content.module, display_order__lt=self.content.display_order)
                .order_by('-display_order')
                .first()
            )

            if previous_content:
                prev_progress = UserContentProgress.objects.filter(
                    user_track=self.user_track, content=previous_content, status='COMPLETED'
                ).exists()

                if not prev_progress:
                    raise ValidationError(
                        {"status": "Você precisa concluir o conteúdo anterior antes de avançar para este."}
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ChallengeSubmission(models.Model):
    AI_STATUS_CHOICES = [
        ('PENDING_AI', 'Pendente IA'),
        ('EVALUATING', 'Em Avaliação'),
        ('EVALUATED', 'Avaliado'),
        ('FAILED', 'Falha na Avaliação'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_track = models.ForeignKey(UserTrack, on_delete=models.CASCADE, related_name='submissions')
    challenge = models.ForeignKey(
        Content, on_delete=models.CASCADE, help_text="Deve apontar para um Content do tipo CHALLENGE"
    )
    github_url = models.URLField(help_text="URL enviada pelo aluno")
    ai_status = models.CharField(max_length=20, choices=AI_STATUS_CHOICES, default='PENDING_AI')
    ai_feedback = models.TextField(null=True, blank=True, help_text="Feedback assíncrono consumido da fila")
    ai_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    evaluated_at = models.DateTimeField(null=True, blank=True, help_text="Preenchido pelo worker da IA ao finalizar")
