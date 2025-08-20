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
    Comentario,
    QuadroKanban,
    ColunaKanban,
    CartaoKanban,
    Membro
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
        fields = ['tipo', 'valor', 'categoria', 'descricao', 'data', 'grupo', 'parcelas', 'anexo', 'recorrente', 'pago', 'data_pagamento']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'input', 'style': 'box-shadow: 0 1px 3px rgba(0,0,0,0.1);'}),
            'valor': forms.NumberInput(attrs={'step': '0.01', 'class': 'input', 'style': 'box-shadow: 0 1px 3px rgba(0,0,0,0.1);'}),
            'categoria': forms.TextInput(attrs={'class': 'input', 'style': 'box-shadow: 0 1px 3px rgba(0,0,0,0.1);'}),
            'parcelas': forms.NumberInput(attrs={'min': 1, 'step': 1, 'class': 'input', 'style': 'box-shadow: 0 1px 3px rgba(0,0,0,0.1);'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'class': 'textarea', 'style': 'box-shadow: 0 1px 3px rgba(0,0,0,0.1);'}),
            'anexo': forms.ClearableFileInput(attrs={'class': 'file-input', 'style': 'opacity: 0; position: absolute;'}),
            'data_pagamento': forms.DateInput(attrs={'type': 'date', 'class': 'input', 'style': 'box-shadow: 0 1px 3px rgba(0,0,0,0.1);'}),
            'recorrente': forms.CheckboxInput(attrs={'class': 'checkbox'}),
            'pago': forms.CheckboxInput(attrs={'class': 'checkbox'}),
        }

class ConviteForm(forms.Form):
    username = forms.CharField(max_length=150, label='Nome de usuário')
    papel = forms.ChoiceField(choices=Membro.ROLES, label='Papel no grupo')

class QuadroKanbanForm(forms.ModelForm):
    class Meta:
        model = QuadroKanban
        fields = ['nome', 'descricao', 'responsavel']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3, 'class': 'textarea'}),
            'responsavel': forms.Select(attrs={'class': 'select'})
        }
        
    def __init__(self, *args, grupo=None, **kwargs):
        super().__init__(*args, **kwargs)
        if grupo:
            # Limitar responsáveis aos membros do grupo
            self.fields['responsavel'].queryset = User.objects.filter(
                membro__grupo=grupo
            )

class CartaoKanbanForm(forms.ModelForm):
    data_limite = forms.DateTimeField(
        required=False,
        widget=forms.SplitDateTimeWidget(
            date_attrs={'type': 'date', 'class': 'input'},
            time_attrs={'type': 'time', 'class': 'input'}
        )
    )
    
    class Meta:
        model = CartaoKanban
        fields = ['titulo', 'descricao', 'prioridade', 'data_limite']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'input'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'class': 'textarea'}),
            'prioridade': forms.Select(attrs={'class': 'select'})
        }
        
    def __init__(self, *args, quadro=None, **kwargs):
        super().__init__(*args, **kwargs)
        if quadro:
            # Campo para selecionar a coluna do cartão
            self.fields['coluna'] = forms.ModelChoiceField(
                queryset=ColunaKanban.objects.filter(quadro=quadro),
                widget=forms.Select(attrs={'class': 'select'})
            )
            
            # Campo para selecionar responsáveis (membros do grupo)
            self.fields['responsaveis'] = forms.ModelMultipleChoiceField(
                queryset=User.objects.filter(membro__grupo=quadro.grupo),
                widget=forms.SelectMultiple(attrs={'class': 'select is-multiple'}),
                required=False
            )

class TransacaoFiltroForm(forms.Form):
    TIPO_CHOICES = (
        ('', 'Todos'),
        ('receita', 'Receita'),
        ('despesa', 'Despesa'),
    )
    
    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'input', 'style': 'box-shadow: 0 1px 3px rgba(0,0,0,0.1);'}),
        label='Data Início'
    )
    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'input', 'style': 'box-shadow: 0 1px 3px rgba(0,0,0,0.1);'}),
        label='Data Fim'
    )
    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'select is-fullwidth', 'style': 'box-shadow: 0 1px 3px rgba(0,0,0,0.1);'}),
        label='Tipo'
    )
    categoria = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'input', 'style': 'box-shadow: 0 1px 3px rgba(0,0,0,0.1);', 'placeholder': 'Categoria'}),
        label='Categoria'
    )
    grupo = forms.ModelChoiceField(
        queryset=Grupo.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'select is-fullwidth', 'style': 'box-shadow: 0 1px 3px rgba(0,0,0,0.1);'}),
        label='Grupo',
        empty_label='Todos os grupos'
    )
    pesquisa = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'input', 'style': 'box-shadow: 0 1px 3px rgba(0,0,0,0.1);', 'placeholder': 'Pesquisar...'}),
        label='Pesquisar'
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['grupo'].queryset = Grupo.objects.filter(membros=user)

class ConfiguracaoNotificacaoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoNotificacao
        fields = [
            'email_tarefas',
            'email_grupos',
            'email_financas',
            'notificacao_browser',
            'antecedencia_tarefa',
            'notificar_despesas_recorrentes',
            'notificar_receitas_programadas',
            'notificar_transacoes_vencidas'
        ]
        labels = {
            'email_tarefas': 'Receber e-mails sobre tarefas',
            'email_grupos': 'Receber e-mails sobre grupos',
            'email_financas': 'Receber e-mails sobre finanças',
            'notificacao_browser': 'Ativar notificações no navegador',
            'antecedencia_tarefa': 'Antecedência para alertas de tarefas (horas)',
            'notificar_despesas_recorrentes': 'Alertar sobre despesas recorrentes',
            'notificar_receitas_programadas': 'Alertar sobre receitas programadas',
            'notificar_transacoes_vencidas': 'Alertar sobre transações vencidas'
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
    username = forms.CharField(
        label='Nome de usuário',
        widget=forms.TextInput(attrs={
            'placeholder': 'Digite o @username do usuário que deseja convidar',
            'autocomplete': 'off',
            'class': 'input username-autocomplete'
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

    def clean_username(self):
        username = self.cleaned_data['username']
        if username.startswith('@'):
            username = username[1:]
        if not User.objects.filter(username=username).exists():
            raise forms.ValidationError('Usuário com este nome de usuário não encontrado.')
        return username