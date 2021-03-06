#!/usr/bin/env python
#-*- coding: ISO-8859-1 -*-

import jinja2
import sqlite3
from numpy import *
from tempfile import NamedTemporaryFile

class StdDev:
    def __init__(self):
        self.values = []

    def step(self, value):
        self.values.append(value)

    def finalize(self):
        return array(self.values).std()

def limpa(s):
    try:
        return '%s' % s
    except:
        try:
            return '%s' % s.decode('iso-8859-1')
        except:
            return '%s' % s.decode('utf-8')
        
def nomes(s):
    t = {
        'direta': 'Direta',
        'trust': 'RBC',
        'item': 'RBI',
        'profile': 'RBP',
        'amigos': 'Amigos',
        'desconhecidos': 'Desconhecidos'
    }
    if s in t:
        return t[s]
    return s
def gen_tabela(x_labels, graph, out_name, title='', xlabel='', ylabel=''):
    keys = sorted(graph.keys())
    bold = lambda s: r'\textbf{%s}' % s
    out = r"""
\begin{table}
\centering
\begin{tabular}{c%s}
    \hline
    \hline
    %s
""" % (('c' * len(x_labels)), r'\textbf{Tipo de recomenda��o} & ' + '& '.join(map(bold, x_labels)) + r' \\')
    for key in keys:
        out += r'\hline '
        out += '\n'
        out += str(limpa(key)) + ' & ' + ' & '.join(map(limpa, graph[key])) + r' \\'
        out += '\n'
    out += r"""\hline        
\end{tabular}
\caption{\it %s}
\label{table:%s}
\end{table}
""" % (limpa(title), out_name.replace('.pdf','').replace('grafico_', ''))

    print out


def run(cmd):
    import subprocess
    return subprocess.Popen(cmd,stdout=subprocess.PIPE).communicate()[0]

def call_script(input, output):
    out = run(['./bargraph.pl', '-gnuplot', '-pdf', input])
    file(output,'w+').write(out)

def gen_bar(x_labels, graph, out_name, yformat='%g', title='', xlabel='', ylabel='', sort=False, sort_col=0, rotate=False, type='cluster', errorbar=False):
    
    conf = NamedTemporaryFile()
    conf.write('=%s;%s\n' % (type, ';'.join(x_labels)))
    conf.write('=table\n=stackabs\n')
    conf.write('yformat=%s\n' % yformat)
    if title:
        conf.write('title=%s\n' % title)
    if xlabel:
        conf.write('xlabel=%s\n' % xlabel)
    if ylabel:
        conf.write('ylabel=%s\n' % ylabel)
    if not rotate:
        conf.write('=norotate\n')
    graph_items = graph.items()
    if sort:
        graph_items.sort(cmp=lambda a,b: cmp(a[1][sort_col], b[1][sort_col]))
    if not errorbar:
        for x, y_list in graph_items:
            columns = ' '.join(map(str, y_list))
            conf.write('%s %s\n' % (x, columns))
    else:
        conf.write('=nogridy\n')
        for x, y_list in graph_items:
            assert(len(y_list) == 2)
            columns = ' '.join(map(str, y_list[:1]))
            conf.write('%s %s\n' % (x, columns))
        conf.write('=yerrorbars\n')
        for x, y_list in graph_items:
            columns = ' '.join(map(lambda x: str(x/2.0), y_list[1:]))
            conf.write('%s %s\n' % (x, columns))

    conf.flush()
    call_script(conf.name, out_name)
    #raw_input(out_name)
    conf.close()
    
    sgraph = r"""
\begin{figure}
    \centering
    \includegraphics[width=\textwidth]{imagens/%s}
    \caption{\it %s}
    \label{fig:%s}
\end{figure}""" % (out_name.replace('.pdf',''), limpa(title), out_name.replace('.pdf','').replace('grafico_', ''))
    print sgraph
    gen_tabela(x_labels, graph, out_name, title, xlabel, ylabel)

def gen_erro(c):
    graph = {}
    c.execute("select avg(abs(r.stars-sr.predicted_rating)+0.0) as erro, sr.algorithm from ratings r, system_recommendations sr where r.product_id = sr.product_id and r.user_id = sr.user_id group by sr.algorithm union all select avg(abs(5-r.stars)+0.0), 'direta' from ratings r, user_recommendations ur, users u where r.product_id = ur.product_id and r.user_id = ur.target_id and u.id = r.user_id")
    for erro_medio, algoritmo in c.fetchall():
        algoritmo = nomes(algoritmo)
        graph[algoritmo] = [erro_medio]
    gen_bar(['Erro M�dio Absoluto'], graph, 'grafico_erro.pdf',
        title='Erro m�dio absoluto (MAE) das recomenda��es',
        yformat='%g', sort=True, sort_col=0)

def gen_media_prevista(c):
    graph = {}
    c.execute("select avg(r.stars), avg (sr.predicted_rating), sr.algorithm from ratings r, system_recommendations sr where r.product_id = sr.product_id and r.user_id = sr.user_id group by sr.algorithm union all select avg(r.stars), 5, 'direta' from ratings r, user_recommendations ur, users u where r.product_id = ur.product_id and r.user_id = ur.target_id and u.id = r.user_id")
    for media_rating, media_prevista, algoritmo in c.fetchall():
        algoritmo = nomes(algoritmo)
        graph[algoritmo] = [media_rating, media_prevista]
    gen_bar(['Nota M�dia Real', 'Nota M�dia Prevista'], graph, 'grafico_media_prevista.pdf',
        title='Compara��o entre as nota m�dias das avalia��es feitas e as previstas pelos algoritmos',
        yformat='%g', sort=True, sort_col=1, type='stacked')

def gen_notas(c):
    graph = {}
    c.execute("select r.stars as nota, count(*)*100/(select count(*) from system_recommendations _sr, users _u where _sr.algorithm = sr.algorithm and _u.id = _sr.user_id and _u.stage_number >=6), sr.algorithm from ratings r, system_recommendations sr, users u where r.product_id = sr.product_id and r.user_id = sr.user_id and u.id = sr.user_id and u.stage_number >=6 group by nota, sr.algorithm union all select r.stars as nota, count(*)*100/(select count(*) from user_recommendations _ur, users _u where _u.id = _ur.target_id and _u.stage_number >=6), 'direta' from ratings r, user_recommendations ur, users u where r.product_id = ur.product_id and r.user_id = ur.target_id and u.id = r.user_id and u.stage_number >=6 group by nota")
    for faixa, p, algoritmo in c.fetchall():
        algoritmo = nomes(algoritmo)
        agrupa = {1:0, 2:0, 3: 1, 4: 2, 5: 2}
        graph.setdefault(algoritmo, [0,0,0])
        graph[algoritmo][agrupa[faixa]] += p
        
    gen_bar(['Rejei��o (1-2)', 'Indiferente (3)', 'Aceita��o (4-5)'], graph, 'grafico_notas.pdf',
        title='Porcentagem das notas em cada faixa comparadas por tipo de recomenda��o',
        yformat='%g%%', sort=True, sort_col=0)

def gen_notas_medias(c):
    graph = {}
    c.execute("select avg(r.stars), stddev(r.stars) from ratings r, user_recommendations ur, users u where r.product_id = ur.product_id and r.user_id = ur.target_id and u.id = r.user_id")
    graph['Direta'] = c.fetchone()
    
    c.execute("select avg(r.stars), stddev(r.stars), sr.algorithm from ratings r, system_recommendations sr where r.product_id = sr.product_id and r.user_id = sr.user_id group by sr.algorithm")
    
    for media, desvio, algoritmo in c.fetchall():
        algoritmo = nomes(algoritmo)
        graph[algoritmo] = (media, desvio)
    gen_bar(['M�dia'], graph, 'grafico_notas_medias.pdf',
        title='Notas por tipo de recomenda��o',yformat='%g', sort=True, sort_col=0, errorbar=True)
    
    graph = {}
    c.execute("select avg(r.stars), stddev(r.stars) from ratings r, user_recommendations ur, users u where r.product_id = ur.product_id and r.user_id = ur.target_id and u.id = r.user_id and ur.sender_id in (select _u.id from users _u where _u.group_id = u.group_id and _u.id <> u.id)")
    graph['Amigos'] = c.fetchone()
    
    c.execute("select avg(r.stars), stddev(r.stars) from ratings r, user_recommendations ur, users u where r.product_id = ur.product_id and r.user_id = ur.target_id and u.id = r.user_id and ur.sender_id in (select _u.id from users _u where _u.group_id <> u.group_id and _u.id <> u.id)")
    graph['Desconhecidos'] = c.fetchone()
    
    gen_bar(['M�dia'], graph, 'grafico_notas_medias_diretas.pdf',
        title='Notas das recomenda��es diretas',yformat='%g', sort=True, sort_col=0, errorbar=True)
    
def gen_serendipidade(c):
    graph = {}
    c.execute("select count(*)*100/(select count(*) from system_recommendations _sr, users _u where _sr.algorithm = sr.algorithm and _u.id = _sr.user_id and _u.stage_number >=6), sr.algorithm from ratings r, system_recommendations sr, users u where r.product_id = sr.product_id and r.user_id = sr.user_id and u.id = r.user_id and u.stage_number >=6 and r.stars >=4 and r.unknown='t' group by sr.algorithm union all select count(*)*100/(select count(*) from user_recommendations _ur, users _u where _u.id = _ur.target_id and _u.stage_number >=6), 'direta' from ratings r, user_recommendations ur, users u where r.product_id = ur.product_id and r.user_id = ur.target_id and u.id = r.user_id and u.stage_number >=6 and r.stars >= 4 and r.unknown='t'")
    for taxa, algoritmo in c.fetchall():
        algoritmo = nomes(algoritmo)
        graph[algoritmo] = [taxa]
    gen_bar(['Taxa de Serendipidade'], graph, 'grafico_serendipidade.pdf',
        title='Taxa de serendipidade por tipo de recomenda��o',
        yformat='%g%%', sort=True, sort_col=0)
    
    graph = {}
    c.execute("select count(*)*100/(select count(*) from user_recommendations _ur, users _u where _u.id = _ur.target_id and _u.stage_number >=6 and _ur.sender_id in (select distinct __u.id from users __u where __u.group_id = _u.group_id and __u.id <> _u.id)), 'amigos' from ratings r, user_recommendations ur, users u where r.product_id = ur.product_id and r.user_id = ur.target_id and u.id = r.user_id and u.stage_number >=6 and r.stars >= 4 and r.unknown='t' and ur.sender_id in (select distinct _u.id from users _u where _u.group_id = u.group_id and _u.id <> u.id) union all select count(*)*100/(select count(*) from user_recommendations _ur, users _u where _u.id = _ur.target_id and _u.stage_number >=6 and _ur.sender_id in (select distinct __u.id from users __u where __u.group_id <> _u.group_id and __u.id <> _u.id)), 'desconhecidos' from ratings r, user_recommendations ur, users u where r.product_id = ur.product_id and r.user_id = ur.target_id and u.id = r.user_id and u.stage_number >=6 and r.stars >= 4 and r.unknown='t' and ur.sender_id in (select distinct _u.id from users _u where _u.group_id <> u.group_id and _u.id <> u.id)")
    for taxa, algoritmo in c.fetchall():
        algoritmo = nomes(algoritmo)
        graph[algoritmo] = [taxa]
    gen_bar(['Taxa de Serendipidade'], graph, 'grafico_serendipidade_diretas.pdf',
        title='Taxa de serendipidade comparando amigos e desconhecidos',
        yformat='%g%%', sort=True, sort_col=0)
    
def main():
    con = sqlite3.connect('../prototipo/experimento/db/production.sqlite3')
    con.create_aggregate("stddev", 1, StdDev)
    c = con.cursor()
    gen_erro(c)
    gen_media_prevista(c)
    gen_notas(c)
    gen_notas_medias(c)
    gen_serendipidade(c)

main()
