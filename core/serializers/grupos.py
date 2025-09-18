from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.models.grupos import (
    Group, GroupMembership, GroupInvitation, Task, SubTask,
    Comment, TaskFile, TaskStatusHistory, Notification
)

User = get_user_model()

class UserBasicSerializer(serializers.ModelSerializer):
    """Serializer básico para informações de usuário."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class GroupSerializer(serializers.ModelSerializer):
    """Serializer completo para grupos."""
    member_count = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            'id', 'name', 'slug', 'description', 'avatar', 'color',
            'created_at', 'created_by', 'member_count', 'task_count',
            'user_role', 'is_active'
        ]
        read_only_fields = ['created_at', 'created_by', 'slug']

    def get_member_count(self, obj):
        return obj.members.count()

    def get_task_count(self, obj):
        return obj.tasks.count()

    def get_user_role(self, obj):
        user = self.context['request'].user
        try:
            membership = GroupMembership.objects.get(group=obj, user=user)
            return membership.role
        except GroupMembership.DoesNotExist:
            return None

class GroupMembershipSerializer(serializers.ModelSerializer):
    """Serializer para associação de membros ao grupo."""
    user = UserBasicSerializer(read_only=True)
    invited_by = UserBasicSerializer(read_only=True)

    class Meta:
        model = GroupMembership
        fields = ['id', 'user', 'group', 'role', 'joined_at', 'invited_by']
        read_only_fields = ['joined_at']

class GroupInvitationSerializer(serializers.ModelSerializer):
    """Serializer para convites de grupo."""
    invited_by = UserBasicSerializer(read_only=True)
    group = GroupSerializer(read_only=True)

    class Meta:
        model = GroupInvitation
        fields = [
            'id', 'group', 'email', 'token', 'role',
            'invited_by', 'created_at', 'expires_at', 'is_accepted'
        ]
        read_only_fields = ['token', 'created_at', 'invited_by']

class SubTaskSerializer(serializers.ModelSerializer):
    """Serializer para subtarefas."""
    completed_by = UserBasicSerializer(read_only=True)

    class Meta:
        model = SubTask
        fields = [
            'id', 'task', 'description', 'is_completed',
            'completed_at', 'completed_by', 'order'
        ]
        read_only_fields = ['completed_at', 'completed_by']

class TaskFileSerializer(serializers.ModelSerializer):
    """Serializer para arquivos de tarefa."""
    uploaded_by = UserBasicSerializer(read_only=True)

    class Meta:
        model = TaskFile
        fields = [
            'id', 'task', 'file', 'filename',
            'uploaded_by', 'uploaded_at', 'file_size'
        ]
        read_only_fields = ['uploaded_at', 'uploaded_by', 'file_size']

class CommentSerializer(serializers.ModelSerializer):
    """Serializer para comentários."""
    author = UserBasicSerializer(read_only=True)
    mentioned_users = UserBasicSerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = [
            'id', 'task', 'author', 'content',
            'created_at', 'updated_at', 'mentioned_users'
        ]
        read_only_fields = ['created_at', 'updated_at', 'author']

class TaskSerializer(serializers.ModelSerializer):
    """Serializer completo para tarefas."""
    created_by = UserBasicSerializer(read_only=True)
    assigned_to = UserBasicSerializer()
    collaborators = UserBasicSerializer(many=True)
    subtasks = SubTaskSerializer(many=True, read_only=True)
    files = TaskFileSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'group', 'title', 'description', 'status',
            'priority', 'created_by', 'assigned_to', 'collaborators',
            'due_date', 'created_at', 'updated_at', 'completed_at',
            'subtasks', 'files', 'comments'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'completed_at',
            'created_by'
        ]

class TaskStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer para histórico de status de tarefas."""
    changed_by = UserBasicSerializer(read_only=True)

    class Meta:
        model = TaskStatusHistory
        fields = [
            'id', 'task', 'old_status', 'new_status',
            'changed_by', 'changed_at'
        ]
        read_only_fields = ['changed_at', 'changed_by']

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer para notificações."""
    group = GroupSerializer(read_only=True)
    task = TaskSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'notification_type', 'group',
            'task', 'message', 'created_at', 'read_at',
            'is_read'
        ]
        read_only_fields = [
            'created_at', 'read_at', 'is_read'
        ]