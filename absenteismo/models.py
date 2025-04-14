from django.db import models
from dashboard.models import Empresa
from funcionarios.models import Funcionario
from django.contrib.postgres.fields import ArrayField


class Absenteismo(models.Model):
    TIPO_ATESTADO_CHOICES = (
        (0, 'Atestado em dias'),
        (1, 'Declaração em horas'),
    )
    
    SEXO_CHOICES = (
        (0, 'Não preenchido'),
        (1, 'Masculino'),
        (2, 'Feminino'),
    )
   
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE, 
        related_name='absenteismos'
    )
    
    funcionario = models.ForeignKey(
        Funcionario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='absenteismos'
    )
    
    codigo_empresa = models.CharField(max_length=20, db_column='codigo_empresa')
  
    MATRICULA_FUNC = models.CharField(max_length=30, null=True, blank=True)
    NOME_FUNCIONARIO = models.CharField(max_length=120, null=True, blank=True)
    
    UNIDADE = models.CharField(max_length=130, null=True, blank=True)
    SETOR = models.CharField(max_length=130, null=True, blank=True)

    DT_NASCIMENTO = models.DateField(null=True, blank=True)
    SEXO = models.IntegerField(choices=SEXO_CHOICES, null=True, blank=True, default=0)
 
    TIPO_ATESTADO = models.IntegerField(choices=TIPO_ATESTADO_CHOICES, default=0)
    DT_INICIO_ATESTADO = models.DateField()
    DT_FIM_ATESTADO = models.DateField()
    HORA_INICIO_ATESTADO = models.CharField(max_length=5, null=True, blank=True)
    HORA_FIM_ATESTADO = models.CharField(max_length=5, null=True, blank=True)
    DIAS_AFASTADOS = models.IntegerField(null=True, blank=True)
    HORAS_AFASTADO = models.CharField(max_length=5, null=True, blank=True)

    CID_PRINCIPAL = models.CharField(max_length=10, null=True, blank=True)
    DESCRICAO_CID = models.CharField(max_length=264, null=True, blank=True)
    GRUPO_PATOLOGICO = models.CharField(max_length=80, null=True, blank=True)
    TIPO_LICENCA = models.CharField(max_length=100, null=True, blank=True)
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Absenteísmo"
        verbose_name_plural = "Absenteísmos"
        ordering = ['-DT_INICIO_ATESTADO']
        indexes = [
            models.Index(fields=['codigo_empresa']),
            models.Index(fields=['MATRICULA_FUNC']),
            models.Index(fields=['funcionario']),
            models.Index(fields=['DT_INICIO_ATESTADO']),
            models.Index(fields=['DT_FIM_ATESTADO']),
            models.Index(fields=['CID_PRINCIPAL']),
        ]
    
    def __str__(self):
        nome = self.NOME_FUNCIONARIO or f"Matrícula: {self.MATRICULA_FUNC}" or "Funcionário não identificado"
        return f"{nome} - {self.DT_INICIO_ATESTADO} a {self.DT_FIM_ATESTADO}"
    
    def save(self, *args, **kwargs):
        if not self.DIAS_AFASTADOS and self.DT_INICIO_ATESTADO and self.DT_FIM_ATESTADO:
            delta = self.DT_FIM_ATESTADO - self.DT_INICIO_ATESTADO
            self.DIAS_AFASTADOS = delta.days + 1
        
        if self.empresa:
            self.codigo_empresa = self.empresa.CODIGO
        
        if not self.funcionario and self.MATRICULA_FUNC and self.codigo_empresa:
            try:
                func = Funcionario.objects.filter(
                    MATRICULAFUNCIONARIO=self.MATRICULA_FUNC,
                    CODIGOEMPRESA=self.codigo_empresa
                ).first()
                
                if func:
                    self.funcionario = func
            except Exception as e:
                print(f"Erro ao vincular funcionário: {e}")
        
        if self.funcionario:
            if not self.NOME_FUNCIONARIO:
                self.NOME_FUNCIONARIO = self.funcionario.NOME
            if not self.DT_NASCIMENTO:
                self.DT_NASCIMENTO = self.funcionario.DATA_NASCIMENTO
            if not self.SEXO and self.funcionario.SEXO:
                self.SEXO = self.funcionario.SEXO
            if not self.MATRICULA_FUNC:
                self.MATRICULA_FUNC = self.funcionario.MATRICULAFUNCIONARIO
        
        super().save(*args, **kwargs)


class CNAE(models.Model):
    """
    Cadastro de CNAEs.
    Pode ser associado a várias empresas, ou somente guardado
    para uso genérico na aplicação.
    """
    codigo = models.CharField(max_length=100, unique=True)
    descricao = models.CharField(max_length=10000, blank=True)

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"
    
    class Meta:
        db_table = 'cnae'
    

class NTEP(models.Model):
    """
    Nexo Técnico Epidemiológico Previdenciário
    relacionando um CNAE com uma lista de CIDs.
    """
    cnae = models.OneToOneField(
        CNAE, 
        on_delete=models.CASCADE,
        related_name='ntep'
    )
    descricao = models.CharField(max_length=10000, blank=True)
    cids = ArrayField(models.CharField(max_length=100), blank=True, default=list)

    def __str__(self):
        return f"NTEP - {self.cnae.codigo} | {self.descricao}"
    
    class Meta:
        db_table = 'ntep'