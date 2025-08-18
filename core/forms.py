from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib.auth.views import LoginView
from .models import (
    Tarefa, 
    Grupo, 
    TransacaoFinanceira, 
    Perfil, 
    ConfiguracaoNotificacao,
    Comentario
)

# Corrigindo a classe CustomLoginView
class CustomLoginView(LoginView):
    template_name = 'core/auth/login.html'
    redirect_authenticated_user = True

# Renomeando para RegistroUsuarioForm para manter consistência
class RegistroUsuarioForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['avatar', 'bio', 'tema', 'notificacoes_email']

class ExcluirContaForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label='Senha',
        help_text='Digite sua senha para confirmar a exclusão da conta.'
    )
    confirmar_exclusao = forms.BooleanField(
        required=True,
        label='Confirmo que desejo excluir minha conta',
        help_text='Esta ação não pode ser desfeita.'
    )

class RecuperarSenhaForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        help_text='Digite o email associado à sua conta para receber instruções de recuperação de senha.'
    )

class DefinirNovaSenhaForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].help_text = 'A senha deve ter pelo menos 8 caracteres e não pode ser muito comum.'
        self.fields['new_password2'].help_text = 'Digite a mesma senha novamente para verificação.'

class TarefaForm(forms.ModelForm):
    data = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    hora = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    anexos = forms.FileField(required=False, widget=forms.ClearableFileInput(attrs={'multiple': True}))

    class Meta:
        model = Tarefa
        fields = [
            'titulo',
            'descricao',
            'responsavel',
            'grupo',
            'prioridade'
        ]
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.data_limite:
            self.initial['data'] = self.instance.data_limite.date()
            self.initial['hora'] = self.instance.data_limite.time()

class GrupoForm(forms.ModelForm):
    class Meta:
        model = Grupo
        fields = ['nome', 'descricao']

class TransacaoForm(forms.ModelForm):
    class Meta:
        model = TransacaoFinanceira
        fields = ['tipo', 'valor', 'categoria', 'descricao', 'data', 'grupo']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'valor': forms.NumberInput(attrs={'step': '0.01'}),
        }

class ConfiguracaoNotificacaoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoNotificacao
        fields = [
            'email_tarefas',
            'email_grupos',
            'email_financas',
            'notificacao_browser',
            'antecedencia_tarefa'
        ]
        labels = {
            'email_tarefas': 'Receber e-mails sobre tarefas',
            'email_grupos': 'Receber e-mails sobre grupos',
            'email_financas': 'Receber e-mails sobre finanças',
            'notificacao_browser': 'Ativar notificações no navegador',
            'antecedencia_tarefa': 'Antecedência para alertas de tarefas (horas)'
        }

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto']
        widgets = {
            'texto': forms.Textarea(attrs={
                'rows': 3,
                'class': 'textarea',
                'placeholder': 'Digite seu comentário... Use @username para mencionar alguém'
            })
        }

    def clean_texto(self):
        texto = self.cleaned_data.get('texto')
        if not texto:
            raise forms.ValidationError('O comentário não pode estar vazio.')
        if len(texto) < 2:
            raise forms.ValidationError('O comentário deve ter pelo menos 2 caracteres.')
        return texto

    def save(self, commit=True):
        comentario = super().save(commit=False)
        if commit:
            comentario.save()
            # Processa menções após salvar
            mencoes = []
            palavras = comentario.texto.split()
            for palavra in palavras:
                if palavra.startswith('@'):
                    username = palavra[1:]
                    try:
                        usuario = User.objects.get(username=username)
                        mencoes.append(usuario)
                    except User.DoesNotExist:
                        continue
            
            comentario.mencoes.set(mencoes)
            
            # Cria notificações para usuários mencionados
            for usuario in mencoes:
                Notificacao.objects.create(
                    usuario=usuario,
                    tipo='mencao',
                    conteudo=f'{comentario.autor.username} mencionou você em um comentário na tarefa "{comentario.tarefa.titulo}"'
                )
        return comentario

class ConviteForm(forms.Form):
    email = forms.EmailField(
        label='Email do usuário',
        widget=forms.EmailInput(attrs={
            'placeholder': 'Digite o email do usuário que deseja convidar'
        })
    )
    papel = forms.ChoiceField(
        label='Papel no grupo',
        choices=[('member', 'Membro'), ('admin', 'Administrador')],
        initial='member',
        widget=forms.Select(attrs={
            'class': 'select'
        })
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError('Usuário com este email não encontrado.')
        return email