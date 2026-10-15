"""节点自测：不依赖 Dify，直接用 Python 跑两个代码节点。

用法：python tests/test_nodes.py
"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hard = load('prd_hard', ROOT / 'nodes' / 'prd-hard-rule-node.py')
score = load('prd_score', ROOT / 'nodes' / 'prd-score-node.py')

SOURCE = (
    '用户反馈：会议纪要整理太慢了，每次要 40 分钟。'
    '另外希望支持导出，导出是用户反馈最多的功能。'
)

GOOD = """# 会议纪要生成 PRD

## 1. 背景与问题
- 目标用户：项目组
- 当前痛点：行政同学手工整理，平均每次 40 分钟

## 2. 目标与成功指标
| 指标 | 当前基线 | 目标值 | 观测方式 |
| 整理耗时 | 40 分钟 | 10 分钟 | 埋点 |

## 3. 需求清单
| 编号 | 需求描述 | 优先级 | 判断依据 | 验收标准 |
| R1 | 自动生成结构化纪要 | P0 | 用户侧每周 5 次会议，影响全部项目组 | 单次生成耗时不超过 30 秒，字段完整率 100% |
| R2 | 支持人工编辑后导出 | P1 | 用户侧编辑率约 30% | 编辑后导出成功率 100% |

## 4. 功能详情
### R1 自动生成结构化纪要
- 验收标准：单次生成耗时不超过 30 秒

## 5. 非目标（本期不做）
- 不做多语言

## 6. 依赖与风险
| 依赖 / 风险 | 说明 | 应对 |
| 语音识别准确率 | 口音影响 | 提供人工修正 |

## 7. 上线与验证计划
- 灰度 2 个团队，灰度期 2 周
"""

BAD = """# XX 功能 PRD

## 1. 背景与问题
- 目标用户：待补充
- 当前痛点：体验不好，希望提升效率

## 3. 需求清单
| 编号 | 需求描述 | 优先级 | 判断依据 | 验收标准 |
| R1 | 优化整体流程 | P9 | | 更好的体验 |
| R2 | 增加导出 | 高 | | - |

## 4. 功能详情
支持「智能推荐最佳会议时间」，已下线功能也一并恢复。
"""

# H8 正例：判断依据只提竞品 → 应被抓出
H8_ONLY_COMPETITOR = """## 3. 需求清单
| 编号 | 需求描述 | 优先级 | 判断依据 | 验收标准 |
| R1 | 上线 AI 配图 | P1 | 竞品飞书已上线该功能 | 生成成功率不低于 90% |
"""

# H8 反例：判断依据只提用户 → 不得误杀（差异化机会往往如此）
H8_ONLY_USER = """## 3. 需求清单
| 编号 | 需求描述 | 优先级 | 判断依据 | 验收标准 |
| R1 | 上线 AI 配图 | P1 | 用户反馈集中提出该诉求 | 生成成功率不低于 90% |
"""

# H9 反例：验收标准含主观词（"100% 可读"——数字外壳包着主观判断）
H9_SUBJECTIVE = """## 3. 需求清单
| 编号 | 需求描述 | 优先级 | 判断依据 | 验收标准 |
| R1 | 生成公式解释 | P1 | 用户侧反馈需要看懂公式 | 抽检 100% 可读 |

## 7. 上线与验证计划
- 灰度 2 周
"""

# H10 反例：上线计划没写灰度时长
H10_NO_TIMEBOX = """## 3. 需求清单
| 编号 | 需求描述 | 优先级 | 判断依据 | 验收标准 |
| R1 | 生成公式解释 | P1 | 用户侧反馈需要看懂公式 | 成功率不低于 90% |

## 7. 上线与验证计划
- 灰度 1 个部门
- 指标不达标则回滚
"""

FAILS = []


def check(label, cond, detail=''):
    if cond:
        print('  PASS  %s' % label)
    else:
        print('  FAIL  %s  %s' % (label, detail))
        FAILS.append(label)


print('=== 硬规则节点：H1-H10 ===')
good = hard.main(GOOD, SOURCE)
bad = hard.main(BAD, SOURCE)
check('合格 PRD 无硬规则问题', good['hard_issues'] == '无', good['hard_issues'])
check('劣质 PRD 被抓出问题', bad['hard_issues'] != '无')
for kw in ['缺少章节', '残留占位符', '禁用空话', '优先级非法', '验收标准不可测量', '无法溯源']:
    check('抓到 %s' % kw, kw in bad['hard_issues'], bad['hard_issues'][:120])

print()
print('=== 硬规则节点：H8 不对称判据 ===')
only_comp = hard.main(H8_ONLY_COMPETITOR, '')['hard_issues']
only_user = hard.main(H8_ONLY_USER, '')['hard_issues']
print('只提竞品 ->', only_comp)
print('只提用户 ->', only_user)
check('只提竞品被判 H8', 'H8' in only_comp, only_comp)
check('只提用户不被误杀', 'H8' not in only_user, only_user)

print()
print('=== 硬规则节点：H9 / H10 ===')
subj = hard.main(H9_SUBJECTIVE, '')['hard_issues']
timebox = hard.main(H10_NO_TIMEBOX, '')['hard_issues']
print('主观验收标准 ->', subj)
print('无灰度时长   ->', timebox)
check('验收标准含主观词被判 H9', 'H9' in subj, subj)
check('上线计划缺时长被判 H10', 'H10' in timebox, timebox)
check('H9 用例不误报 H10', 'H10' not in subj, subj)
check('H10 用例不误报 H9', 'H9' not in timebox, timebox)

print()
print('=== 金标准 PRD 必须满分 ===')
golden = (ROOT / 'examples' / 'golden-prd-F1.md').read_text(encoding='utf-8')
fixture = (ROOT / 'fixtures' / 'fixture-F1-crosscheck.txt').read_text(encoding='utf-8')
g_hard = hard.main(golden, fixture)['hard_issues']
print('硬规则 ->', g_hard)
check('金标准 PRD 通过全部硬规则（含 H8）', g_hard == '无', g_hard)
g_score = score.main(golden, 'F1-正例')
print('打分   ->', g_score['score'], '|', g_score['fails'])
check('金标准 PRD 对 F1 满分',
      g_score['score'].split('/')[0] == g_score['score'].split('/')[1], g_score['fails'])

print()
print('=== 打分节点：期望机制 ===')
r_none = score.main(golden, 'UNKNOWN')
check('未知样本给出跳过提示', r_none['score'] == '-' and '跳过' in r_none['fails'])
check('F1 期望已登记', 'F1-正例' in score.EXPECT)
check('F2 期望已登记', 'F2-反抄袭' in score.EXPECT)
check('F3 期望已登记', 'F3-素材不足' in score.EXPECT)

print()
if FAILS:
    print('结果：%d 项未通过 -> %s' % (len(FAILS), FAILS))
    raise SystemExit(1)
print('结果：全部通过')
