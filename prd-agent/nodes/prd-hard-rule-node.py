import re

# PRD 规范：唯一事实来源，与 Dify 环境变量 prd_rules 保持一致。
# 抽取 / 写作 / 评审三个节点都引用同一份规则，避免各节点各用一套标准。
REQUIRED_SECTIONS = [
    '背景与问题', '目标与成功指标', '需求清单', '功能详情',
    '非目标', '依赖与风险', '上线与验证计划',
]

# 禁用空话：判定标准不是「这个词本身有错」，而是「出现在 PRD 里且无主体、无指标 = 无法验收」。
FORBID_WORDS = [
    '更好的体验', '提升效率', '优化流程', '加强', '赋能', '闭环',
    '一定程度', '尽可能', '尽快', '合理',
]

PLACEHOLDERS = ['待补充', '待确认', 'TBD', 'TODO', 'XXX', '{{']

VALID_PRIORITY = {'P0', 'P1', 'P2', 'P3'}

# H8 用：竞品侧词 vs 用户侧词。
# 判据不是「提到竞品就错」，而是「只提竞品、没有用户侧支撑」才算照搬竞品。
# 只禁「只提竞品」，不禁「只提用户」——差异化机会往往就是竞品没做但用户需要。
COMPETITOR_WORDS = ['竞品', '友商', '对手', '对标', '飞书', '钉钉', '企业微信']
USER_SIDE_WORDS = ['用户', '客户', '反馈', '访谈', '工单', '痛点', '场景',
                   '影响面', '频次', '投诉', '调研']

# H9 用：主观形容词。出现在验收标准里 = 不可客观判定（除非另附操作化定义）。
SUBJECTIVE_WORDS = ['可读', '好用', '易用', '清晰', '流畅', '友好', '智能',
                    '高效', '美观', '稳定', '顺畅', '直观', '合理']

# 可测量：至少含一个数字，或一个明确的判定词
MEASURABLE = re.compile(r'[0-9０-９]|≥|≤|大于|小于|不少于|不超过|通过|不通过|达到|至少')

# 带引号的关键事实（用户原话、数据）
QUOTED = re.compile(r'[「“"\']([^」”"\']{4,})[」”"\']')


def main(prd: str, source: str) -> dict:
    """硬规则检查：只做确定性判断，不做任何语义理解。

    prd:    生成的 PRD Markdown 全文
    source: 输入素材原文（用于 H5 可追溯性比对）
    返回:   {"hard_issues": "问题1；问题2"}，无问题时为 "无"
    """
    text = prd or ''
    source = source or ''
    issues = []

    # H1 必填章节齐全
    for sec in REQUIRED_SECTIONS:
        if sec not in text:
            issues.append('缺少章节：%s' % sec)

    # H7 无占位符残留
    for ph in PLACEHOLDERS:
        if ph in text:
            issues.append('残留占位符：%s' % ph)

    # H4 无禁用空话
    for w in FORBID_WORDS:
        if w in text:
            issues.append('命中禁用空话：%s（需改写成「谁 / 什么场景 / 指标从 X 到 Y」）' % w)

    # H5 引用可追溯
    for q in QUOTED.findall(text):
        if q not in source:
            issues.append('引用无法溯源：「%s」' % q)

    # H2 / H3 / H6 逐条需求校验
    rows = [l for l in text.splitlines() if re.match(r'\s*\|\s*R\d+\s*\|', l)]
    if not rows:
        issues.append('需求清单为空或未使用 R 编号')
    for row in rows:
        cells = [c.strip() for c in row.strip().strip('|').split('|')]
        rid = cells[0] if cells else '?'
        if len(cells) >= 3 and cells[2] not in VALID_PRIORITY:
            issues.append('%s 优先级非法：%s（应为 P0-P3）' % (rid, cells[2]))
        if len(cells) >= 4 and not cells[3]:
            issues.append('%s 缺少优先级判断依据' % rid)
        # H8 判断依据不得只有竞品、没有用户侧支撑
        if len(cells) >= 4 and cells[3]:
            basis = cells[3]
            has_comp = any(w in basis for w in COMPETITOR_WORDS)
            has_user = any(w in basis for w in USER_SIDE_WORDS)
            if has_comp and not has_user:
                issues.append('%s 判断依据只提竞品、无用户侧支撑（H8）：%s' % (rid, basis))
        if len(cells) >= 5:
            ac = cells[4]
            if not ac or ac in ('-', '—'):
                issues.append('%s 缺少验收标准' % rid)
            elif not MEASURABLE.search(ac):
                issues.append('%s 验收标准不可测量：%s' % (rid, ac))
            elif any(w in ac for w in SUBJECTIVE_WORDS):
                bad = [w for w in SUBJECTIVE_WORDS if w in ac]
                issues.append('%s 验收标准含主观词、无法客观判定（H9）：%s（命中：%s）'
                              % (rid, ac, '、'.join(bad)))

    # H10 上线与验证计划必须写明灰度时长
    plan = re.search(r'上线与验证计划(.*?)(?=\n## |\Z)', text, re.S)
    if plan:
        if not re.search(r'\d+\s*(周|天|日|个月|月|小时)', plan.group(1)):
            issues.append('上线与验证计划未写明灰度时长（H10，如「灰度 2 周」）')

    return {'hard_issues': '；'.join(issues) if issues else '无'}
