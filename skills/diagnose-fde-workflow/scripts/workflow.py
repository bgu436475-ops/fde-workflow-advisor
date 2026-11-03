#!/usr/bin/env python3
"""Validate a workflow and render evidence-aware, deterministic scene artifacts."""
import argparse
import html
import json
import math
from pathlib import Path
import sys
import unicodedata

STATUSES = {'user_reported', 'verified', 'inference', 'unknown', 'hypothetical'}
MODES = {'rules', 'ai', 'human', 'mixed', 'unknown'}
TYPES = {'remove_merge', 'rules', 'ai_assist', 'human_in_loop', 'human', 'foundation_defer'}
STATUS_LABEL = {'user_reported':'用户自述', 'verified':'已核验', 'inference':'分析估算', 'unknown':'未知', 'hypothetical':'演示假设'}
TYPE_LABEL = {'remove_merge':'删除或合并','rules':'规则自动化','ai_assist':'AI 辅助','human_in_loop':'人机协作','human':'人工负责','foundation_defer':'先补基础或暂缓'}
ROLLOUT_LABEL = {'scope':'试点范围','samples':'样本与覆盖','baseline':'原流程基线','owner':'业务负责人','reviewer':'审核人','maintainer':'维护人','gates':'质量门槛','stop':'暂停条件','fallback':'人工恢复'}
DECISION_LABEL = {'pilot':'建议小范围试点','defer':'建议暂缓建设','needs_input':'需补关键条件后决定'}


def number(v):
    return type(v) in (int, float) and math.isfinite(v) and v >= 0


def validate(m):
    errors = []
    def check(ok, message):
        if not ok:
            errors.append(message)
    def string(obj, key, where):
        check(isinstance(obj.get(key), str) and bool(obj.get(key, '').strip()), f'{where}.{key}: 需要非空字符串')
    def array(obj, key, where):
        val = obj.get(key)
        check(isinstance(val, list), f'{where}.{key}: 需要列表')
        return val if isinstance(val, list) else []
    if not isinstance(m, dict):
        return ['模型需要 JSON 对象']
    for k in ('title', 'goal', 'scope', 'case'):
        string(m, k, 'model')
    check(m.get('decision') in {'pilot', 'defer', 'needs_input'}, 'decision: 无效决策')
    evidence = array(m, 'evidence', 'model')
    evidence_ids = set()
    for i, e in enumerate(evidence):
        if not isinstance(e, dict):
            errors.append(f'evidence[{i}]: 需要对象'); continue
        for k in ('id', 'note'):
            string(e, k, f'evidence[{i}]')
        eid = e.get('id')
        check(isinstance(eid, str) and eid not in evidence_ids, f'evidence[{i}]: id 无效或重复')
        if isinstance(eid, str): evidence_ids.add(eid)
        check(e.get('status') in STATUSES, f'evidence[{i}]: status 无效')
    def refs(obj, where):
        val = array(obj, 'evidence_refs', where)
        check(bool(val), f'{where}: 需要来源引用，未知也应引用 unknown 记录')
        check(all(isinstance(r, str) and r in evidence_ids for r in val), f'{where}: 来源引用不存在')
    all_ids = set()
    for side in ('before', 'after'):
        nodes = array(m, side, 'model')
        check(len(nodes) <= 18, f'{side}: 超过 18 节点，请拆子流程')
        if side == 'after' and m.get('decision') == 'pilot':
            check(bool(nodes), 'pilot 需要 after 流程')
        ids = {n.get('id') for n in nodes if isinstance(n, dict) and isinstance(n.get('id'), str)}
        adjacency = {x: [] for x in ids}
        terminals = set()
        for i, n in enumerate(nodes):
            loc = f'{side}[{i}]'
            if not isinstance(n, dict): errors.append(f'{loc}: 需要对象'); continue
            for k in ('id', 'actor', 'action', 'input', 'output'): string(n, k, loc)
            nid = n.get('id')
            check(isinstance(nid, str) and nid not in all_ids, f'{loc}: id 无效或全局重复')
            if isinstance(nid, str): all_ids.add(nid)
            check(n.get('mode') in MODES, f'{loc}: mode 无效')
            check(n.get('basis') in STATUSES, f'{loc}: basis 无效')
            refs(n, loc)
            edges = array(n, 'next', loc)
            if not edges and isinstance(nid, str): terminals.add(nid)
            for j, edge in enumerate(edges):
                if not isinstance(edge, dict): errors.append(f'{loc}.next[{j}]: 需要对象'); continue
                target = edge.get('to')
                check(isinstance(target, str) and target in ids, f'{loc}: 边指向不存在的节点')
                string(edge, 'condition', f'{loc}.next[{j}]')
                check(type(edge.get('exception')) is bool, f'{loc}: exception 必须为布尔值')
                if isinstance(nid, str) and nid in adjacency and isinstance(target, str) and target in ids:
                    adjacency[nid].append(target)
        if nodes and isinstance(nodes[0], dict) and isinstance(nodes[0].get('id'), str):
            seen = set(); pending = [nodes[0]['id']]
            while pending:
                cur = pending.pop()
                if cur not in seen:
                    seen.add(cur); pending.extend(adjacency.get(cur, []))
            check(ids <= seen, f'{side}: 存在从起点不可达的节点')
            exits = set(terminals)
            while True:
                more = {x for x, dest in adjacency.items() if any(y in exits for y in dest)}
                if more <= exits: break
                exits.update(more)
            check(ids <= exits, f'{side}: 存在无法退出或人工结案的循环')
    opportunities = array(m, 'opportunities', 'model')
    opp_ids = set()
    for i, o in enumerate(opportunities):
        loc = f'opportunities[{i}]'
        if not isinstance(o, dict): errors.append(f'{loc}: 需要对象'); continue
        for k in ('id', 'reason', 'prerequisites', 'owner', 'acceptance'): string(o, k, loc)
        oid = o.get('id')
        check(isinstance(oid, str) and oid not in opp_ids, f'{loc}: id 无效或重复')
        if isinstance(oid, str): opp_ids.add(oid)
        steps = array(o, 'step_ids', loc)
        check(bool(steps) and all(isinstance(x, str) and x in all_ids for x in steps), f'{loc}: 步骤引用无效')
        check(o.get('type') in TYPES, f'{loc}: type 无效')
        refs(o, loc)
    for key in ('unknowns',):
        items = array(m, key, 'model')
        check(all(isinstance(x, str) and x.strip() for x in items), f'{key}: 需要非空字符串列表')
    questions = array(m, 'questions', 'model')
    check(len(questions) <= 3, 'questions: 每轮最多 3 个问题')
    for i, q in enumerate(questions):
        if not isinstance(q, dict): errors.append(f'questions[{i}]: 需要对象'); continue
        for k in ('text', 'changes_decision'): string(q, k, f'questions[{i}]')
    checks = array(m, 'self_checks', 'model')
    check(bool(checks) or m.get('decision') == 'needs_input', '推荐或暂缓需有反证记录')
    for i, row in enumerate(checks):
        if not isinstance(row, dict): errors.append(f'self_checks[{i}]: 需要对象'); continue
        for k in ('failure', 'verify', 'response'): string(row, k, f'self_checks[{i}]')
    rollout = m.get('rollout')
    check(isinstance(rollout, dict), 'rollout: 需要对象')
    if isinstance(rollout, dict):
        for k in ('scope','samples','baseline','owner','reviewer','maintainer','gates','stop','fallback'):
            string(rollout, k, 'rollout')
    check('metrics' in m, 'metrics: 缺失，未知请用 null')
    mt = m.get('metrics')
    if mt is not None:
        if not isinstance(mt, dict): errors.append('metrics: 需要对象或 null'); return errors
        check(mt.get('status') in STATUSES, 'metrics.status: 无效')
        string(mt, 'source_note', 'metrics')
        check(mt.get('unit') == 'labor_minutes_per_case', 'metrics.unit: 只支持每单人工分钟')
        check(type(mt.get('comparable_scope')) is bool, 'metrics.comparable_scope: 需要布尔值')
        routes = array(mt, 'routes', 'metrics')
        check(bool(routes) or mt.get('status') == 'unknown', 'metrics.routes: 参数存在时不能为空')
        weights = []
        for i, r in enumerate(routes):
            if not isinstance(r, dict): errors.append(f'metrics.routes[{i}]: 需要对象'); continue
            string(r, 'name', f'metrics.routes[{i}]')
            for k in ('weight','before_min','after_min','before_extra_min','after_extra_min'):
                check(number(r.get(k)), f'metrics.routes[{i}].{k}: 需要有限非负数')
            if number(r.get('weight')): weights.append(r['weight'])
        if routes: check(math.isclose(sum(weights), 1, abs_tol=1e-8, rel_tol=0), 'metrics.routes: 权重总和必须为 1')
        for k in ('cases_per_day','working_days_per_month'):
            check(k in mt and (mt.get(k) is None or number(mt.get(k))), f'metrics.{k}: 需要有限非负数或 null')
        excluded = array(mt, 'excluded_costs', 'metrics')
        check(all(isinstance(x, str) and x.strip() for x in excluded), 'metrics.excluded_costs: 需要非空字符串列表')
    return errors


def calculate(m):
    mt = m.get('metrics')
    if mt is None or mt.get('status') == 'unknown':
        return {'available': False, 'reason': '缺少可计算参数，不填入默认数字'}
    if not mt['comparable_scope']:
        return {'available': False, 'reason': '前后业务范围不可比'}
    before = sum(r['weight'] * (r['before_min'] + r['before_extra_min']) for r in mt['routes'])
    after = sum(r['weight'] * (r['after_min'] + r['after_extra_min']) for r in mt['routes'])
    saved = before - after
    day = None if mt['cases_per_day'] is None else saved * mt['cases_per_day'] / 60
    month = None if day is None or mt['working_days_per_month'] is None else day * mt['working_days_per_month']
    return {'available': True, 'status': mt['status'], 'source_note': mt['source_note'],
            'before_min': before, 'after_min': after, 'saved_min_per_case': saved,
            'labor_reduction_pct': None if before == 0 else saved / before * 100,
            'released_hours_per_day': day, 'released_hours_per_month': month,
            'excluded_costs': mt['excluded_costs'],
            'limit': '仅为合计人工工时；不等于现金节省、裁员、周期提升或营收增长'}


def wrap(value, max_units=48):
    result, line, units = [], '', 0
    for ch in str(value):
        u = 2 if unicodedata.east_asian_width(ch) in ('W','F') else 1
        if ch == '\n' or units + u > max_units:
            result.append(line); line = ''; units = 0
        if ch != '\n': line += ch; units += u
    if line: result.append(line)
    return result or ['']


def svg_scene(m):
    esc = lambda x: html.escape(str(x), quote=True)
    layouts = []
    for side, x in (('before',24),('after',744)):
        pos = {}; y = 115
        for n in m[side]:
            lines = [f'{n["id"]} · {n["actor"]} · {STATUS_LABEL[n["basis"]]}']
            for label, key in (('动作','action'),('输入','input'),('输出','output')):
                lines.extend(wrap(f'{label}：{n[key]}'))
            for e in n['next']:
                lines.extend(wrap(f'{"异常" if e["exception"] else "条件"}：{e["condition"]} → {e["to"]}'))
            height = 28 + len(lines) * 23
            pos[n['id']] = (y, height, lines)
            y += height + 52
        layouts.append((side,x,pos,max(y,250)))
    height = max(t[3] for t in layouts) + 40
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1464" height="{height}" viewBox="0 0 1464 {height}" role="img" aria-label="业务流程前后对照">',
             '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0 0L0 6L8 3Z" fill="#6d7c89"/></marker></defs>',
             '<rect width="100%" height="100%" fill="white"/>',
             f'<text x="24" y="30" font-size="21" fill="#152d3e">{esc(m["title"])}</text>']
    for side, x, pos, _ in layouts:
        parts.append(f'<g font-family="Noto Sans CJK SC,Microsoft YaHei,sans-serif"><text x="{x}" y="80" font-size="22">{"改造前" if side == "before" else "改造后"}</text>')
        if not pos:
            parts.append(f'<text x="{x}" y="145" font-size="17">待确认或暂不改造，未编造流程</text>')
        edge_index = 0
        for n in m[side]:
            y,h,lines = pos[n['id']]
            fill = '#e9f4ef' if n['mode'] in ('ai','rules') else ('#fff3df' if n['mode']=='mixed' else '#f0f3f6')
            parts.append(f'<rect x="{x}" y="{y}" width="535" height="{h}" rx="10" fill="{fill}" stroke="#b5c2cc"/>')
            for i,line in enumerate(lines):
                parts.append(f'<text x="{x+14}" y="{y+25+i*23}" font-size="16" fill="#172e3d">{esc(line)}</text>')
            for j,e in enumerate(n['next']):
                ty,th,_ = pos[e['to']]
                start, end = y+h/2, ty+th/2
                lane = x+552+(edge_index%8)*15
                edge_index += 1
                color = '#a96920' if e['exception'] else '#6d7c89'
                dash = ' stroke-dasharray="5 4"' if e['exception'] else ''
                parts.append(f'<path d="M{x+535} {start} H{lane} V{end} H{x+535}" fill="none" stroke="{color}" stroke-width="2"{dash} marker-end="url(#arrow)"/>')
        parts.append('</g>')
    parts.append('</svg>')
    return ''.join(parts)


def render(m, output):
    esc = lambda x: html.escape(str(x), quote=True)
    svg = svg_scene(m)
    metric = calculate(m)
    rows = []
    if metric['available']:
        for label,key in [('改造前人工分钟／单','before_min'),('改造后人工分钟／单','after_min'),('人工耗时下降 %','labor_reduction_pct'),('月释放容量小时','released_hours_per_month')]:
            v=metric[key]; rows.append(f'<tr><th>{label}</th><td>{"未知" if v is None else f"{v:.2f}"}</td></tr>')
        metric_html = f'<p><strong>{esc(STATUS_LABEL[metric["status"]])}</strong>：{esc(metric["source_note"])}</p><table>{"".join(rows)}</table><p>{esc(metric["limit"])}</p><p>未计入：{esc("；".join(metric["excluded_costs"]) or "声明无；仍需核对")}</p>'
    else:
        metric_html = '<p>'+esc(metric['reason'])+'。</p>'
    details = []
    for side in ('before','after'):
        for n in m[side]:
            edges = '；'.join(f'{e["condition"]} → {e["to"]}' for e in n['next']) or '终点'
            details.append(f'<li><b>{esc(n["id"])} {esc(n["action"])}</b>：{esc(edges)}；依据 {esc(", ".join(n["evidence_refs"]))}</li>')
    evidence=''.join(f'<li>{esc(e["id"])} · {esc(STATUS_LABEL[e["status"]])}：{esc(e["note"])}</li>' for e in m['evidence'])
    opp=''.join(f'<li><strong>{esc(TYPE_LABEL[o["type"]])}</strong>：{esc(o["reason"])}<br/>前提：{esc(o["prerequisites"])}；责任人：{esc(o["owner"])}；验收：{esc(o["acceptance"])}</li>' for o in m['opportunities'])
    checks=''.join(f'<li>{esc(c["failure"])}；验证：{esc(c["verify"])}；调整：{esc(c["response"])}</li>' for c in m['self_checks'])
    unknown=''.join(f'<li>{esc(x)}</li>' for x in m['unknowns']) or '<li>未列未知项，请确认是否已充分核验。</li>'
    rollout=''.join(f'<li><b>{esc(ROLLOUT_LABEL.get(k,k))}</b>：{esc(v)}</li>' for k,v in m['rollout'].items())
    text=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(m['title'])}</title>
<style>body{{font:16px/1.7 system-ui,sans-serif;color:#172e3d;max-width:1500px;margin:32px auto;padding:0 24px}}h1{{font-size:28px}}h2{{margin-top:32px}}.scene{{overflow:auto;border:1px solid #d7e0e5}}svg{{display:block;max-width:none}}table{{border-collapse:collapse}}th,td{{padding:8px 16px;border:1px solid #ccd6dd;text-align:left}}li{{margin:10px 0}}.muted{{color:#596c78}}</style>
<h1>{esc(m['title'])}</h1><p>{esc(m['goal'])}</p><p>范围：{esc(m['scope'])}<br/>同笔业务：{esc(m['case'])}<br/>建议状态：{esc(DECISION_LABEL[m['decision']])}</p>
<p class="muted">方案示意，非已部署系统。绿色表示规则或 AI 处理，灰色表示人工或待确认，橙色表示协作；虚线表示异常。图过宽可横向查看。</p>
<div class="scene">{svg}</div><h2>效果口径</h2>{metric_html}<h2>机会与前提</h2><ul>{opp}</ul><h2>反证与调整</h2><ul>{checks}</ul><h2>试点与恢复</h2><ul>{rollout}</ul><h2>待确认</h2><ul>{unknown}</ul><details><summary>步骤条件和来源</summary><ul>{''.join(details)}</ul><ul>{evidence}</ul></details></html>'''
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(text,encoding='utf-8'); output.with_suffix('.svg').write_text(svg,encoding='utf-8')


def storyboard(m, output):
    def steps(side):
        return '；'.join(f'[{n["id"]}] {n["actor"]}：{n["action"]}' for n in m[side]) or '待确认，不虚构动作'
    exceptions = [f'[{n["id"]} → {e["to"]}] {e["condition"]}' for n in m['after'] for e in n['next'] if e['exception']]
    result=calculate(m)
    effect = ('缺少可比参数，展示待采集指标' if not result['available'] else
              f'{STATUS_LABEL[result["status"]]}；每单人工 {result["before_min"]:.2f} → {result["after_min"]:.2f} 分钟；不等于周期或现金收益')
    scenes=[('0–10 秒','同一笔业务进入原流程',steps('before')),
            ('10–22 秒','重放同一笔业务，展示新的处理方式',steps('after')),
            ('22–36 秒','展示条件分支与人工接手','；'.join(exceptions) or '模型未列异常支路，需确认是否足够'),
            ('36–48 秒','展示最终交付物及责任人', '；'.join(f'[{n["id"]}] {n["actor"]}：{n["output"]}' for n in m['after'] if not n['next']) or '暂缓或待补充，不演示不存在的优化结果'),
            ('48–60 秒','对照效果、来源与适用前提',effect)]
    out=[f'# {m["title"]} 视频分镜草案','',f'案例：{m["case"]}','', '状态：仅已生成分镜，视频成片尚未生成。节点顺序用于讲解，执行条件以流程边为准。','']
    for time,title,detail in scenes: out += [f'## {time} {title}', '', detail, '']
    out+=['## 旁白与制作约束','','围绕角色动作和交付物写旁白，不逐字朗读所有节点。保留编号供校对；长流程先缩小范围。数字、字幕和镜头均使用本模型；来源状态在效果画面可见。客户补料等未知等待不可用压缩动画伪装成实际耗时。','', '待确认：'+'；'.join(m['unknowns'])]
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text('\n'.join(out),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('validate','calculate','render','storyboard'))
    parser.add_argument('model',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        m=json.loads(args.model.read_text(encoding='utf-8'))
        errors=validate(m)
        if errors:
            print(json.dumps({'valid':False,'errors':errors},ensure_ascii=False,indent=2));return 2
        if args.command=='validate': print(json.dumps({'valid':True},ensure_ascii=False));return 0
        if args.command=='calculate':
            print(json.dumps(calculate(m),ensure_ascii=False,indent=2,allow_nan=False));return 0
        if args.output is None: parser.error('render 与 storyboard 必须提供 --output')
        if args.command=='render': render(m,args.output)
        else: storyboard(m,args.output)
        print(str(args.output.resolve()));return 0
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print(json.dumps({'valid':False,'errors':[str(exc)]},ensure_ascii=False));return 2


if __name__=='__main__': sys.exit(main())
