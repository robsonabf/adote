# serializers.py
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import SolicitacaoDoacao, UserProfile, Muda
from django.db import IntegrityError


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'email', 'nome_completo', 'endereco', 'cidade', 'estado', 'telefone', 'cpf']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'profile']

    def create(self, validated_data):
        profile_data = validated_data.pop('profile')
        try:
            password = validated_data.pop('password', None)
            user = User.objects.create(**validated_data)
            if password:
                user.set_password(password)
                user.save()

                # Verifique se já existe um UserProfile para este usuário
            existing_profile = UserProfile.objects.filter(user=user).first()

            if existing_profile:
                # Se já existir, emita uma mensagem ou faça o que for necessário
                raise IntegrityError("UserProfile já existe para este usuário.")
            else:
                # Se não existir, crie um novo perfil
                UserProfile.objects.create(user=user, **profile_data)

            return user

        except IntegrityError as e:
            # Em caso de violação de unicidade (username duplicado), emita uma mensagem
            message = f"Erro ao registrar usuário: {e}"
            raise serializers.ValidationError(message)

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        profile_instance = instance.profile

        instance.email = validated_data.get('email', instance.email)
        instance.username = validated_data.get('username', instance.username)
        instance.save()

        profile_instance.email = profile_data.get('email', profile_instance.email)
        profile_instance.nome_completo = profile_data.get('nome_completo', profile_instance.nome_completo)
        profile_instance.endereco = profile_data.get('endereco', profile_instance.endereco)
        profile_instance.cidade = profile_data.get('cidade', profile_instance.cidade)
        profile_instance.estado = profile_data.get('estado', profile_instance.estado)
        profile_instance.telefone = profile_data.get('telefone', profile_instance.telefone)
        profile_instance.cpf = profile_data.get('cpf', profile_instance.cpf)
        profile_instance.save()

        return instance


class SolicitacaoDoacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolicitacaoDoacao
        fields = ['id', 'especie', 'quantidade_solicitada', 'status', 'local_de_plantio', 'data_solicitacao', 'observacoes']


class MudaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Muda
        fields = '__all__'
