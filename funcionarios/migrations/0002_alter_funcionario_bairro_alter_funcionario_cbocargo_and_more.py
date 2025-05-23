# Generated by Django 5.2 on 2025-04-07 09:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funcionarios', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='funcionario',
            name='BAIRRO',
            field=models.CharField(blank=True, max_length=80, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='CBOCARGO',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='CCUSTO',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='CEP',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='CIDADE',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='CODIGOCARGO',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='CODIGOSETOR',
            field=models.CharField(blank=True, max_length=12, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='CODIGOUNIDADE',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='COR',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='CTPS',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='DATAULTALTERACAO',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='DEFICIENCIA',
            field=models.CharField(blank=True, max_length=861, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='DEFICIENTE',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='EMAIL',
            field=models.CharField(blank=True, max_length=400, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='ENDERECO',
            field=models.CharField(blank=True, max_length=110, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='ESCOLARIDADE',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='ESTADOCIVIL',
            field=models.IntegerField(blank=True, choices=[(1, 'Solteiro(a)'), (2, 'Casado(a)'), (3, 'Separado(a)'), (4, 'Desquitado(a)'), (5, 'Viuvo(a)'), (6, 'Outros'), (7, 'Divorciado(a)')], null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='MATRICULAFUNCIONARIO',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='MATRICULARH',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='NATURALIDADE',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='NM_MAE_FUNCIONARIO',
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='NOMECARGO',
            field=models.CharField(blank=True, max_length=130, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='NOMECENTROCUSTO',
            field=models.CharField(blank=True, max_length=130, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='NOMESETOR',
            field=models.CharField(blank=True, max_length=130, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='NOMEUNIDADE',
            field=models.CharField(blank=True, max_length=130, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='NUMERO_ENDERECO',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='ORGAOEMISSORRG',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='PIS',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='RAMAL',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='REGIMEREVEZAMENTO',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='REGIMETRABALHO',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='RG',
            field=models.CharField(blank=True, max_length=19, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='SERIECTPS',
            field=models.CharField(blank=True, max_length=25, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='SITUACAO',
            field=models.CharField(blank=True, max_length=12, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='TELCOMERCIAL',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='TELEFONECELULAR',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='TELEFONERESIDENCIAL',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='TIPOCONTATACAO',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='TURNOTRABALHO',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='UF',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='funcionario',
            name='UFRG',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
