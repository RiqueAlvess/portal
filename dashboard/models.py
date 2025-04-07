from django.db import models
from django.contrib.auth.models import User

class Empresa(models.Model):
    CODIGO = models.CharField(max_length=20, unique=True)
    RAZAOSOCIAL = models.CharField(max_length=200)
    ENDERECO = models.CharField(max_length=110)
    NUMEROENDERECO = models.CharField(max_length=20)
    COMPLEMENTOENDERECO = models.CharField(max_length=300)
    BAIRRO = models.CharField(max_length=80)
    CIDADE = models.CharField(max_length=50)
    CEP = models.CharField(max_length=11)
    UF = models.CharField(max_length=2)
    CNPJ = models.CharField(max_length=20)
    ATIVO = models.BooleanField(default=True)
    usuarios = models.ManyToManyField(User, through='UsuarioEmpresa')
    
    def __str__(self):
        return self.RAZAOSOCIAL

class UsuarioEmpresa(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    data_vinculo = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('usuario', 'empresa')
        

class EmpresaAtivaUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Empresa ativa do usuário"
        verbose_name_plural = "Empresas ativas dos usuários"

    def __str__(self):
        return f"{self.usuario.username} → {self.empresa.RAZAOSOCIAL if self.empresa else 'Nenhuma'}"