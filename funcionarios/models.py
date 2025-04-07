from django.db import models
from dashboard.models import Empresa

class Funcionario(models.Model):
    SEXO_CHOICES = (
        (1, 'Masculino'),
        (2, 'Feminino'),
    )
    
    ESTADOCIVIL_CHOICES = (
        (1, 'Solteiro(a)'),
        (2, 'Casado(a)'),
        (3, 'Separado(a)'),
        (4, 'Desquitado(a)'),
        (5, 'Viuvo(a)'),
        (6, 'Outros'),
        (7, 'Divorciado(a)'),
    )
    
    CODIGOEMPRESA = models.CharField(max_length=20)
    NOMEEMPRESA = models.CharField(max_length=200)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='funcionarios')
    
    CODIGO = models.CharField(max_length=20)
    NOME = models.CharField(max_length=120)
    CPF = models.CharField(max_length=19)
    SEXO = models.IntegerField(choices=SEXO_CHOICES)
    DATA_NASCIMENTO = models.DateField()
    DATA_ADMISSAO = models.DateField()
    
    CODIGOUNIDADE = models.CharField(max_length=20, null=True, blank=True)
    NOMEUNIDADE = models.CharField(max_length=130, null=True, blank=True)
    CODIGOSETOR = models.CharField(max_length=12, null=True, blank=True)
    NOMESETOR = models.CharField(max_length=130, null=True, blank=True)
    CODIGOCARGO = models.CharField(max_length=10, null=True, blank=True)
    NOMECARGO = models.CharField(max_length=130, null=True, blank=True)
    CBOCARGO = models.CharField(max_length=10, null=True, blank=True)
    CCUSTO = models.CharField(max_length=50, null=True, blank=True)
    NOMECENTROCUSTO = models.CharField(max_length=130, null=True, blank=True)
    MATRICULAFUNCIONARIO = models.CharField(max_length=30, null=True, blank=True)
    RG = models.CharField(max_length=19, null=True, blank=True)
    UFRG = models.CharField(max_length=10, null=True, blank=True)
    ORGAOEMISSORRG = models.CharField(max_length=20, null=True, blank=True)
    SITUACAO = models.CharField(max_length=12, null=True, blank=True)
    PIS = models.CharField(max_length=20, null=True, blank=True)
    CTPS = models.CharField(max_length=30, null=True, blank=True)
    SERIECTPS = models.CharField(max_length=25, null=True, blank=True)
    ESTADOCIVIL = models.IntegerField(choices=ESTADOCIVIL_CHOICES, null=True, blank=True)
    TIPOCONTATACAO = models.IntegerField(null=True, blank=True)
    DATA_DEMISSAO = models.DateField(null=True, blank=True)
    ENDERECO = models.CharField(max_length=110, null=True, blank=True)
    NUMERO_ENDERECO = models.CharField(max_length=20, null=True, blank=True)
    BAIRRO = models.CharField(max_length=80, null=True, blank=True)
    CIDADE = models.CharField(max_length=50, null=True, blank=True)
    UF = models.CharField(max_length=20, null=True, blank=True)
    CEP = models.CharField(max_length=10, null=True, blank=True)
    TELEFONERESIDENCIAL = models.CharField(max_length=20, null=True, blank=True)
    TELEFONECELULAR = models.CharField(max_length=20, null=True, blank=True)
    EMAIL = models.CharField(max_length=400, null=True, blank=True)
    DEFICIENTE = models.IntegerField(null=True, blank=True)
    DEFICIENCIA = models.CharField(max_length=861, null=True, blank=True)
    NM_MAE_FUNCIONARIO = models.CharField(max_length=120, null=True, blank=True)
    DATAULTALTERACAO = models.DateField(null=True, blank=True)
    MATRICULARH = models.CharField(max_length=30, null=True, blank=True)
    COR = models.IntegerField(null=True, blank=True)
    ESCOLARIDADE = models.IntegerField(null=True, blank=True)
    NATURALIDADE = models.CharField(max_length=50, null=True, blank=True)
    RAMAL = models.CharField(max_length=10, null=True, blank=True)
    REGIMEREVEZAMENTO = models.IntegerField(null=True, blank=True)
    REGIMETRABALHO = models.CharField(max_length=500, null=True, blank=True)
    TELCOMERCIAL = models.CharField(max_length=20, null=True, blank=True)
    TURNOTRABALHO = models.IntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = ['CODIGOEMPRESA', 'CODIGO']
    
    def save(self, *args, **kwargs):
        if self.empresa:
            self.CODIGOEMPRESA = self.empresa.CODIGO
            self.NOMEEMPRESA = self.empresa.RAZAOSOCIAL
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.NOME