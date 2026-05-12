from rest_framework import serializers

from .models import Track, UserTrack


class TrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class UserTrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTrack
        fields = ['id', 'suap_user_id', 'track', 'status', 'enrolled_at', 'completed_at']
        # Protegendo campos críticos: o aluno não pode mandar datas forçadas no POST
        read_only_fields = ['enrolled_at', 'completed_at']

    def validate(self, data):
        # self.instance existe quando é um PUT/PATCH (atualização).
        # Se não existe, é um POST (nova criação/inscrição).
        is_creation = self.instance is None

        # Pega os dados da requisição ou da instância atual (se for atualização)
        track = data.get('track', getattr(self.instance, 'track', None))
        status = data.get('status', getattr(self.instance, 'status', None))
        suap_user_id = data.get('suap_user_id', getattr(self.instance, 'suap_user_id', None))

        if is_creation:
            # REGRA: Trilha tem que estar Publicada
            if track and track.status != 'PUBLISHED':
                raise serializers.ValidationError(
                    {"track": "Não é possível se inscrever. Esta trilha não está publicada ou foi arquivada."}
                )

            # REGRA: Inscrição Única (Não pode ter matrícula ativa ou concluída na mesma trilha)
            existing_enrollment = UserTrack.objects.filter(
                suap_user_id=suap_user_id, track=track, status__in=['IN_PROGRESS', 'COMPLETED']
            ).exists()

            if existing_enrollment:
                raise serializers.ValidationError(
                    {"suap_user_id": "Você já possui uma inscrição ativa ou já concluiu esta trilha."}
                )

        return data
