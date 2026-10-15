import re

# 每份 fixture 的期望，按 fixture 名取。新增样本只需在这里加一项。
# 写法与 AI-office-competitor-daily 的 auto-score-node 保持一致。
EXPECT = {
    # F1 正例：情报与反馈互相印证
    'F1-正例': {
        'must_sections': ['背景与问题', '目标与成功指标', '需求清单', '功能详情'],
        'items_count': 2,
        'must_items': [{'id': 'R1'}, {'id': 'R2'}],
        # 允许出现在「非目标」并说明理由，但不得进入需求清单
        'must_not_in_items': ['导入速度'],
        'forbid_words': ['更好的体验', '提升效率'],
    },
    # F2 反抄袭：竞品有、用户无
    'F2-反抄袭': {
        'must_sections': ['背景与问题', '目标与成功指标', '需求清单'],
        'items_count': 1,
        'must_items': [{'id': 'R1'}],
        'must_not_in_items': ['配图'],
        'forbid_words': ['更好的体验', '提升效率'],
    },
    # F3 素材不足：不得编造
    'F3-素材不足': {
        'must_sections': [],
        'items_count': 0,
        'must_items': [],
        'must_not_in_items': ['VLOOKUP', 'AI 公式', 'AI 纪要'],
        'forbid_words': ['更好的体验', '提升效率'],
    },
}

FORBID_WORDS = [
    '更好的体验', '提升效率', '优化流程', '加强', '赋能', '闭环',
    '一定程度', '尽可能', '尽快', '合理',
]
PLACEHOLDERS = ['待补充', '待确认', 'TBD', 'TODO', 'XXX', '{{']


def _parse_rows(text):
    """解析需求清单表格，返回 {R编号: [单元格...]}。"""
    out = {}
    for line in (text or '').splitlines():
        if re.match(r'\s*\|\s*R\d+\s*\|', line):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if cells:
                out[cells[0]] = cells
    return out


def main(out: str, fixture: str) -> dict:
    """按样本期望给 PRD 打分，输出 score / fails。

    out:     生成的 PRD Markdown 全文
    fixture: 样本名，用于在 EXPECT 里取期望
    """
    exp = EXPECT.get(fixture)
    if not exp:
        return {'score': '-', 'fails': '没有 %s 的期望，跳过打分' % fixture}

    text = out or ''
    rows = _parse_rows(text)
    checks = []  # (名称, 是否通过, 说明)

    # 必填章节
    for sec in exp.get('must_sections', []):
        checks.append(('章节 %s' % sec, sec in text, '未出现'))

    # 需求条数
    checks.append(('需求条数', len(rows) == exp.get('items_count', len(rows)),
                   '共 %d 条，应为 %d' % (len(rows), exp.get('items_count', len(rows)))))

    # 指定需求与优先级
    for m in exp.get('must_items', []):
        rid = m['id']
        if rid not in rows:
            checks.append(('收录 %s' % rid, False, '未找到该需求'))
            continue
        if 'priority' in m:
            got = rows[rid][2] if len(rows[rid]) > 2 else ''
            checks.append(('%s 优先级' % rid, got == m['priority'],
                           '为 %s，应为 %s' % (got, m['priority'])))

    # 应被过滤的内容（全文范围）
    for f in exp.get('must_filtered', []):
        checks.append(('过滤 %s' % f, f not in text, '仍出现在 PRD 中'))

    # 不得出现在需求清单中——但允许出现在「非目标」等章节并说明理由
    rows_text = '\n'.join('|'.join(v) for v in rows.values())
    for f in exp.get('must_not_in_items', []):
        checks.append(('需求清单不含 %s' % f, f not in rows_text, '出现在需求清单中'))

    # 禁用空话
    hits = [w for w in exp.get('forbid_words', FORBID_WORDS) if w in text]
    checks.append(('无禁用空话', not hits, '出现：' + '、'.join(hits)))

    # 占位符残留
    ph = [p for p in PLACEHOLDERS if p in text]
    checks.append(('无占位符残留', not ph, '出现：' + '、'.join(ph)))

    passed = sum(1 for _, ok, _ in checks if ok)
    fails = ['%s：%s' % (n, why) for n, ok, why in checks if not ok]
    return {'score': '%d/%d' % (passed, len(checks)), 'fails': '；'.join(fails) or '全部通过'}
