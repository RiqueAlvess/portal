from datetime import date, timedelta
from django.core.cache import cache
from django.db.models import F
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from dashboard.models import EmpresaAtivaUsuario
from absenteismo.models import Absenteismo
from funcionarios.models import Funcionario
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

@cache_page(300)
@login_required
def absenteismo(request):
    try:
        empresa_ativa = EmpresaAtivaUsuario.objects.get(usuario=request.user).empresa
    except EmpresaAtivaUsuario.DoesNotExist:
        return render(request, "erro.html", {"mensagem": "Empresa ativa não encontrada."})

    periodo = request.GET.get("periodo", "semestre")
    grupo = request.GET.get("grupo", "")
    tipo_duracao = request.GET.get("tipo_duracao", "")
    setor = request.GET.get("setor", "")
    hoje = date.today()
    if periodo == "trimestre":
        data_inicio = hoje - timedelta(days=90)
        dias_periodo = 90
    elif periodo == "mes":
        data_inicio = hoje - timedelta(days=30)
        dias_periodo = 30
    else:
        data_inicio = hoje - timedelta(days=180)
        dias_periodo = 180

    cache_key = f"absenteismo_{request.user.id}_{periodo}_{grupo}_{tipo_duracao}_{setor}"
    dados_cache = cache.get(cache_key)
    if dados_cache:
        return render(request, "absenteismo.html", dados_cache)

    base = Absenteismo.objects.filter(
        empresa=empresa_ativa,
        DT_INICIO_ATESTADO__gte=data_inicio,
        funcionario__isnull=False
    ).exclude(NOME_FUNCIONARIO__icontains="nomegenerico")

    if grupo:
        base = base.filter(SETOR__startswith=grupo)
    if setor:
        base = base.filter(SETOR=setor)
    if tipo_duracao:
        if tipo_duracao == "horas":
            base = base.filter(TIPO_ATESTADO=1)
        elif tipo_duracao == "1-3":
            base = base.filter(DIAS_AFASTADOS__gte=1, DIAS_AFASTADOS__lte=3, TIPO_ATESTADO=0)
        elif tipo_duracao == "4-7":
            base = base.filter(DIAS_AFASTADOS__gte=4, DIAS_AFASTADOS__lte=7, TIPO_ATESTADO=0)
        elif tipo_duracao == "8-14":
            base = base.filter(DIAS_AFASTADOS__gte=8, DIAS_AFASTADOS__lte=14, TIPO_ATESTADO=0)
        elif tipo_duracao == "15+":
            base = base.filter(DIAS_AFASTADOS__gte=15, TIPO_ATESTADO=0)

    valores = list(
        base.select_related("funcionario").values(
            "MATRICULA_FUNC", "NOME_FUNCIONARIO", "DIAS_AFASTADOS", "TIPO_ATESTADO", "SETOR",
            "CID_PRINCIPAL", "DESCRICAO_CID", "SEXO", "DT_INICIO_ATESTADO", "GRUPO_PATOLOGICO",
            "funcionario__DATA_NASCIMENTO"
        )
    )

    setores = sorted(set(v["SETOR"] for v in valores))
    total_atestados = len(valores)
    total_dias = sum(v["DIAS_AFASTADOS"] or 0 for v in valores)
    total_funcionarios = Funcionario.objects.filter(empresa=empresa_ativa).exclude(NOME__icontains="nomegenerico").count()
    media_dias = total_dias / total_atestados if total_atestados else 0
    media_atestados = total_atestados / total_funcionarios if total_funcionarios else 0
    total_horas_afastadas = total_dias * 8
    impacto_financeiro = total_horas_afastadas * 8.02
    dias_uteis = int(dias_periodo * 5 / 7) if dias_periodo else 0
    taxa_absenteismo = (total_dias / (total_funcionarios * dias_uteis) * 100) if total_funcionarios and dias_uteis else 0

    bradford_map = {}
    for v in valores:
        mat = v["MATRICULA_FUNC"]
        if mat not in bradford_map:
            bradford_map[mat] = {"func": v["NOME_FUNCIONARIO"], "episodios": 0, "dias": 0}
        bradford_map[mat]["episodios"] += 1
        bradford_map[mat]["dias"] += (v["DIAS_AFASTADOS"] or 0)
    bradford_list = []
    for mat, d in bradford_map.items():
        b = d["episodios"] * d["episodios"] * d["dias"]
        if b >= 500:
            risco = "ALTO"
        elif b >= 200:
            risco = "MÉDIO"
        else:
            risco = "BAIXO"
        bradford_list.append({
            "MATRICULA_FUNC": mat,
            "NOME_FUNCIONARIO": d["func"],
            "episodios": d["episodios"],
            "total_dias": d["dias"],
            "bradford": b,
            "risco": risco
        })
    bradford_list.sort(key=lambda x: x["bradford"], reverse=True)
    bradford_critico_count = sum(1 for x in bradford_list if x["risco"] == "ALTO")

    func_atestados = {}
    for v in valores:
        f_id = v["MATRICULA_FUNC"]
        func_atestados[f_id] = func_atestados.get(f_id, 0) + 1
    reincidencia_count = sum(1 for x in func_atestados.values() if x > 1)
    taxa_reincidencia = (reincidencia_count / len(func_atestados) * 100) if func_atestados else 0

    duracao_patterns = {"horas": 0, "1-3": 0, "4-7": 0, "8-14": 0, "15+": 0}
    for v in valores:
        if v["TIPO_ATESTADO"] == 1:
            duracao_patterns["horas"] += 1
        else:
            dias = v["DIAS_AFASTADOS"] or 0
            if 1 <= dias <= 3: duracao_patterns["1-3"] += 1
            elif 4 <= dias <= 7: duracao_patterns["4-7"] += 1
            elif 8 <= dias <= 14: duracao_patterns["8-14"] += 1
            elif dias >= 15: duracao_patterns["15+"] += 1

    dia_semana_count = {i: 0 for i in range(1, 8)}
    cids_por_dia_map = {i: {} for i in range(1, 8)}
    for v in valores:
        if not v["DT_INICIO_ATESTADO"]:
            continue

        d = v["DT_INICIO_ATESTADO"].isoweekday()
        d = d + 1 if d < 7 else 1
        dia_semana_count[d] += 1
        cid = v["GRUPO_PATOLOGICO"] or ""
        if cid:
            cids_por_dia_map[d][cid] = cids_por_dia_map[d].get(cid, 0) + 1

    cids_por_dia_semana = []
    duracao_por_dia_semana = []
    nome_dur = {"horas": "Horas", "13": "1-3 dias", "47": "4-7 dias", "814": "8-14 dias", "15": "15+ dias"}
    duracao_dia_map = {i: {"horas": 0, "13": 0, "47": 0, "814": 0, "15": 0, "total": 0} for i in range(1, 8)}

    for v in valores:
        if not v["DT_INICIO_ATESTADO"]:
            continue
        d = v["DT_INICIO_ATESTADO"].isoweekday()
        d = d + 1 if d < 7 else 1
        duracao_dia_map[d]["total"] += 1
        if v["TIPO_ATESTADO"] == 1:
            duracao_dia_map[d]["horas"] += 1
        else:
            dd = v["DIAS_AFASTADOS"] or 0
            if 1 <= dd <= 3: duracao_dia_map[d]["13"] += 1
            elif 4 <= dd <= 7: duracao_dia_map[d]["47"] += 1
            elif 8 <= dd <= 14: duracao_dia_map[d]["814"] += 1
            elif dd >= 15: duracao_dia_map[d]["15"] += 1

    for d in range(1, 8):
        top_cid = None
        max_count_cid = 0
        for c, ccount in cids_por_dia_map[d].items():
            if ccount > max_count_cid:
                max_count_cid = ccount
                top_cid = c
        if top_cid and dia_semana_count[d]:
            cids_por_dia_semana.append({
                "GRUPO_PATOLOGICO": top_cid,
                "count": max_count_cid,
                "percentage": round(100 * max_count_cid / dia_semana_count[d], 1)
            })
        else:
            cids_por_dia_semana.append({"GRUPO_PATOLOGICO": "Não disponível", "count": 0, "percentage": 0})
        tot = duracao_dia_map[d]["total"]
        if tot:
            cont_map = {
                "horas": duracao_dia_map[d]["horas"],
                "1-3": duracao_dia_map[d]["13"],
                "4-7": duracao_dia_map[d]["47"],
                "8-14": duracao_dia_map[d]["814"],
                "15+": duracao_dia_map[d]["15"]
            }
            max_d = max(cont_map, key=cont_map.get)
            duracao_por_dia_semana.append({
                "tipo": max_d, "count": cont_map[max_d],
                "percentage": round(100 * cont_map[max_d] / tot, 1)
            })
        else:
            duracao_por_dia_semana.append({"tipo": "Não disponível", "count": 0, "percentage": 0})

    setor_map = {}
    for v in valores:
        s = v["SETOR"]
        if s not in setor_map:
            setor_map[s] = {"count": 0, "dias": 0}
        setor_map[s]["count"] += 1
        setor_map[s]["dias"] += (v["DIAS_AFASTADOS"] or 0)
    absenteismo_por_setor_list = sorted(setor_map.items(), key=lambda x: x[1]["dias"], reverse=True)[:10]
    absenteismo_por_setor = [{"SETOR": k, "count": v["count"], "dias": v["dias"]} for k, v in absenteismo_por_setor_list]

    cid_map = {}
    for v in valores:
        cidp = v["CID_PRINCIPAL"]
        if cidp:
            if cidp not in cid_map:
                cid_map[cidp] = {
                    "DESCRICAO_CID": v["DESCRICAO_CID"] or "",
                    "count": 0,
                    "dias": 0
                }
            cid_map[cidp]["count"] += 1
            cid_map[cidp]["dias"] += (v["DIAS_AFASTADOS"] or 0)
    abscid = sorted(cid_map.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
    if abscid:
        absenteismo_por_cid = []
        for c, d in abscid:
            absenteismo_por_cid.append({
                "CID_PRINCIPAL": c,
                "DESCRICAO_CID": d["DESCRICAO_CID"],
                "count": d["count"],
                "dias": d["dias"]
            })
    else:
        absenteismo_por_cid = [{"CID_PRINCIPAL": "Sem dados", "DESCRICAO_CID": "", "count": 0, "dias": 0}]

    evol_map = {}
    for v in valores:
        d = v["DT_INICIO_ATESTADO"]
        if not d: 
            continue
        key = (d.year, d.month)
        if key not in evol_map:
            evol_map[key] = {"count": 0, "dias": 0}
        evol_map[key]["count"] += 1
        evol_map[key]["dias"] += (v["DIAS_AFASTADOS"] or 0)
    evol_sorted = sorted(evol_map.items(), key=lambda x: x[0])
    month_names = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    evolucao_mensal = []
    for (yy, mm), data_agg in evol_sorted:
        evolucao_mensal.append({
            "ano": yy,
            "mes": mm,
            "count": data_agg["count"],
            "dias": data_agg["dias"]
        })

    sexo_map = {}
    for v in valores:
        s = v["SEXO"]
        if s not in sexo_map: 
            sexo_map[s] = {"count": 0, "dias": 0}
        sexo_map[s]["count"] += 1
        sexo_map[s]["dias"] += (v["DIAS_AFASTADOS"] or 0)
    genero_analysis = sorted(sexo_map.items(), key=lambda x: x[0])

    cids_por_genero = {}
    sexo_labels = dict(Absenteismo.SEXO_CHOICES)
    genero_cid_map = {}
    for v in valores:
        s = v["SEXO"]
        g = sexo_labels.get(s, "Não informado")
        if v["GRUPO_PATOLOGICO"]:
            genero_cid_map.setdefault(g, {})
            genero_cid_map[g][v["GRUPO_PATOLOGICO"]] = genero_cid_map[g].get(v["GRUPO_PATOLOGICO"], 0) + 1
    for genero, cidcounts in genero_cid_map.items():
        top = sorted(cidcounts.items(), key=lambda x: x[1], reverse=True)[:5]
        cids_por_genero[genero] = [{"GRUPO_PATOLOGICO": t[0], "count": t[1]} for t in top]

    cids_por_prefixo_setor = {}
    prefixos = ["F", "M", "S", "T"]
    pref_map = {p: {} for p in prefixos}
    for v in valores:
        for p in prefixos:
            if v["SETOR"].startswith(p) and v["GRUPO_PATOLOGICO"]:
                pref_map[p][v["GRUPO_PATOLOGICO"]] = pref_map[p].get(v["GRUPO_PATOLOGICO"], 0) + 1
    for p in prefixos:
        top = sorted(pref_map[p].items(), key=lambda x: x[1], reverse=True)[:5]
        if top:
            cids_por_prefixo_setor[p] = [{"GRUPO_PATOLOGICO": t[0], "count": t[1]} for t in top]

    age_ranges = [(0,25,"18-25"),(26,35,"26-35"),(36,45,"36-45"),(46,55,"46-55"),(56,100,"56+")]
    age_cid_correlation = []
    for mn, mx, lbl in age_ranges:
        min_date = date(hoje.year - mx, hoje.month, hoje.day)
        max_date = date(hoje.year - mn, hoje.month, hoje.day)
        cid_counter = {}
        for v in valores:
            dnasc = v["funcionario__DATA_NASCIMENTO"]
            if dnasc and min_date <= dnasc <= max_date and v["GRUPO_PATOLOGICO"]:
                cid_counter[v["GRUPO_PATOLOGICO"]] = cid_counter.get(v["GRUPO_PATOLOGICO"], 0) + 1
        tops = sorted(cid_counter.items(), key=lambda x: x[1], reverse=True)[:3]
        for c, cnt in tops:
            age_cid_correlation.append({"age_range": lbl, "cid": c, "count": cnt})

    def safe_cid_label(item):
        cid = item.get('CID_PRINCIPAL','')
        desc = item.get('DESCRICAO_CID','')
        if not cid and not desc:
            return "Não classificado"
        if not desc:
            return cid
        return f"{cid} - {desc[:20]}"

    chart_data = {
        "duracao_patterns": {
            "labels": ["Horas","1-3 dias","4-7 dias","8-14 dias","15+ dias"],
            "data": [
                duracao_patterns["horas"],
                duracao_patterns["1-3"],
                duracao_patterns["4-7"],
                duracao_patterns["8-14"],
                duracao_patterns["15+"],
            ],
        },
        "dia_semana": {
            "labels": ["Domingo","Segunda","Terça","Quarta","Quinta","Sexta","Sábado"],
            "data": [dia_semana_count.get(i,0) for i in range(1,8)]
        },
        "absenteismo_por_setor": {
            "labels": [x["SETOR"] for x in absenteismo_por_setor],
            "data_count": [x["count"] for x in absenteismo_por_setor],
            "data_dias": [x["dias"] for x in absenteismo_por_setor],
        },
        "absenteismo_por_cid": {
            "labels": [safe_cid_label(x) for x in absenteismo_por_cid],
            "data_count": [x["count"] for x in absenteismo_por_cid],
            "data_dias": [x["dias"] for x in absenteismo_por_cid],
        },
        "evolucao_mensal": {"labels": [], "data_count": [], "data_dias": []},
        "genero": {
            "labels": ["Masculino","Feminino","Não informado"],
            "count": [0,0,0],
            "dias": [0,0,0]
        },
        "age_cid_correlation": {"data": age_cid_correlation},
        "cids_por_dia_semana": cids_por_dia_semana,
        "duracao_por_dia_semana": duracao_por_dia_semana,
    }

    for ev in evolucao_mensal:
        chart_data["evolucao_mensal"]["labels"].append(
            f"{month_names[ev['mes']-1]} {ev['ano']}"
        )
        chart_data["evolucao_mensal"]["data_count"].append(ev["count"])
        chart_data["evolucao_mensal"]["data_dias"].append(ev["dias"])

    for s, info in sexo_map.items():
        idx = 2
        if s == 1: idx = 0
        elif s == 2: idx = 1
        chart_data["genero"]["count"][idx] = info["count"]
        chart_data["genero"]["dias"][idx] = info["dias"]

    context = {
        "absenteismo_por_cid": absenteismo_por_cid,
        "empresa_ativa": empresa_ativa,
        "periodo": periodo,
        "grupo": grupo,
        "tipo_duracao": tipo_duracao,
        "setor": setor,
        "setores": setores,
        "total_funcionarios": total_funcionarios,
        "total_atestados": total_atestados,
        "total_dias": total_dias,
        "media_dias": media_dias,
        "media_atestados": media_atestados,
        "impacto_financeiro": impacto_financeiro,
        "bradford_critico_count": bradford_critico_count,
        "taxa_reincidencia": taxa_reincidencia,
        "taxa_absenteismo": taxa_absenteismo,
        "bradford_detalhado": bradford_list[:20],
        "cids_por_genero": cids_por_genero,
        "cids_por_prefixo_setor": cids_por_prefixo_setor,
        "chart_data": json.dumps(chart_data, cls=DecimalEncoder),
        "sexo_choices": dict(Absenteismo.SEXO_CHOICES)
    }

    cache.set(cache_key, context, 300)
    return render(request, "absenteismo.html", context)
