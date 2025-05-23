# Generated by Django 5.2 on 2025-04-07 09:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('dashboard', '0002_alter_empresa_ativo'),
    ]

    operations = [
        migrations.CreateModel(
            name='Funcionario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('CODIGOEMPRESA', models.CharField(max_length=20)),
                ('NOMEEMPRESA', models.CharField(max_length=200)),
                ('CODIGO', models.CharField(max_length=20)),
                ('NOME', models.CharField(max_length=120)),
                ('CODIGOUNIDADE', models.CharField(max_length=20)),
                ('NOMEUNIDADE', models.CharField(max_length=130)),
                ('CODIGOSETOR', models.CharField(max_length=12)),
                ('NOMESETOR', models.CharField(max_length=130)),
                ('CODIGOCARGO', models.CharField(max_length=10)),
                ('NOMECARGO', models.CharField(max_length=130)),
                ('CBOCARGO', models.CharField(max_length=10)),
                ('CCUSTO', models.CharField(max_length=50)),
                ('NOMECENTROCUSTO', models.CharField(max_length=130)),
                ('MATRICULAFUNCIONARIO', models.CharField(max_length=30)),
                ('CPF', models.CharField(max_length=19)),
                ('RG', models.CharField(max_length=19)),
                ('UFRG', models.CharField(max_length=10)),
                ('ORGAOEMISSORRG', models.CharField(max_length=20)),
                ('SITUACAO', models.CharField(max_length=12)),
                ('SEXO', models.IntegerField(choices=[(1, 'Masculino'), (2, 'Feminino')])),
                ('PIS', models.CharField(max_length=20)),
                ('CTPS', models.CharField(max_length=30)),
                ('SERIECTPS', models.CharField(max_length=25)),
                ('ESTADOCIVIL', models.IntegerField(choices=[(1, 'Solteiro(a)'), (2, 'Casado(a)'), (3, 'Separado(a)'), (4, 'Desquitado(a)'), (5, 'Viuvo(a)'), (6, 'Outros'), (7, 'Divorciado(a)')])),
                ('TIPOCONTATACAO', models.IntegerField()),
                ('DATA_NASCIMENTO', models.DateField()),
                ('DATA_ADMISSAO', models.DateField()),
                ('DATA_DEMISSAO', models.DateField(blank=True, null=True)),
                ('ENDERECO', models.CharField(max_length=110)),
                ('NUMERO_ENDERECO', models.CharField(max_length=20)),
                ('BAIRRO', models.CharField(max_length=80)),
                ('CIDADE', models.CharField(max_length=50)),
                ('UF', models.CharField(max_length=20)),
                ('CEP', models.CharField(max_length=10)),
                ('TELEFONERESIDENCIAL', models.CharField(max_length=20)),
                ('TELEFONECELULAR', models.CharField(max_length=20)),
                ('EMAIL', models.CharField(max_length=400)),
                ('DEFICIENTE', models.IntegerField()),
                ('DEFICIENCIA', models.CharField(max_length=861)),
                ('NM_MAE_FUNCIONARIO', models.CharField(max_length=120)),
                ('DATAULTALTERACAO', models.DateField()),
                ('MATRICULARH', models.CharField(max_length=30)),
                ('COR', models.IntegerField()),
                ('ESCOLARIDADE', models.IntegerField()),
                ('NATURALIDADE', models.CharField(max_length=50)),
                ('RAMAL', models.CharField(max_length=10)),
                ('REGIMEREVEZAMENTO', models.IntegerField()),
                ('REGIMETRABALHO', models.CharField(max_length=500)),
                ('TELCOMERCIAL', models.CharField(max_length=20)),
                ('TURNOTRABALHO', models.IntegerField()),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='funcionarios', to='dashboard.empresa')),
            ],
            options={
                'unique_together': {('CODIGOEMPRESA', 'CODIGO')},
            },
        ),
    ]
