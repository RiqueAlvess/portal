from django.db import models
from dashboard.models import Empresa
from funcionarios.models import Funcionario
from django.utils import timezone


class Convocacao(models.Model):
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE, 
        related_name='convocacoes'
    )
    CODIGOEMPRESA = models.CharField(max_length=20)
    
    funcionario = models.ForeignKey(
        Funcionario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='convocacoes'
    )
    CODIGOFUNCIONARIO = models.CharField(max_length=50)
    
    NOMEABREVIADO = models.CharField(max_length=100, blank=True, null=True)
    UNIDADE = models.CharField(max_length=100, blank=True, null=True)
    CIDADE = models.CharField(max_length=100, blank=True, null=True)
    ESTADO = models.CharField(max_length=2, blank=True, null=True)
    BAIRRO = models.CharField(max_length=100, blank=True, null=True)
    ENDERECO = models.CharField(max_length=200, blank=True, null=True)
    CEP = models.CharField(max_length=10, blank=True, null=True)
    CNPJUNIDADE = models.CharField(max_length=20, blank=True, null=True)
    SETOR = models.CharField(max_length=100, blank=True, null=True)
    CARGO = models.CharField(max_length=100, blank=True, null=True)
    
    CPFFUNCIONARIO = models.CharField(max_length=20, blank=True, null=True)
    MATRICULA = models.CharField(max_length=30, blank=True, null=True)
    DATAADMISSAO = models.DateField(blank=True, null=True)
    NOME = models.CharField(max_length=120, blank=True, null=True)
    EMAILFUNCIONARIO = models.CharField(max_length=100, blank=True, null=True)
    TELEFONEFUNCIONARIO = models.CharField(max_length=20, blank=True, null=True)
    
    CODIGOEXAME = models.CharField(max_length=100)
    EXAME = models.CharField(max_length=100, blank=True, null=True)
    ULTIMOPEDIDO = models.DateField(blank=True, null=True)
    DATARESULTADO = models.DateField(blank=True, null=True)
    PERIODICIDADE = models.IntegerField(blank=True, null=True)
    REFAZER = models.DateField(blank=True, null=True)
    
    @property
    def STATUS(self):
        hoje = timezone.now().date()
        fim_de_ano = timezone.datetime(hoje.year, 12, 31).date()
        
        if not self.ULTIMOPEDIDO and not self.DATARESULTADO and not self.REFAZER:
            return "Sem histórico"
        elif self.ULTIMOPEDIDO and not self.DATARESULTADO and not self.REFAZER:
            return "Pendente"
        elif self.REFAZER and self.ULTIMOPEDIDO and self.DATARESULTADO and self.REFAZER <= hoje:
            return "Vencido"
        elif self.REFAZER and self.REFAZER <= fim_de_ano:
            return "A Vencer"
        elif self.REFAZER and self.REFAZER.year > hoje.year:
            return "Em dia"
        else:
            return None
    
    def __str__(self):
        return f"{self.NOME} - {self.EXAME}"
    
    def save(self, *args, **kwargs):
        if self.empresa:
            self.CODIGOEMPRESA = self.empresa.CODIGO
        if self.funcionario:
            self.CODIGOFUNCIONARIO = self.funcionario.CODIGO
            self.NOME = self.funcionario.NOME
            self.CPFFUNCIONARIO = self.funcionario.CPF
            self.MATRICULA = self.funcionario.MATRICULAFUNCIONARIO
            self.DATAADMISSAO = self.funcionario.DATA_ADMISSAO
            self.EMAILFUNCIONARIO = self.funcionario.EMAIL
            self.TELEFONEFUNCIONARIO = self.funcionario.TELEFONECELULAR
            self.SETOR = self.funcionario.NOMESETOR
            self.CARGO = self.funcionario.NOMECARGO
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Convocação"
        verbose_name_plural = "Convocações"
        unique_together = ('CODIGOFUNCIONARIO', 'CODIGOEXAME')