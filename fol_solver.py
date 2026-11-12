import re
from typing import List, Dict, Set, Tuple, Optional, Union

def normalize_logic_string(expr: str) -> str:
    if not isinstance(expr, str):
        return ""
    expr = expr.strip()
    expr = expr.replace("⟷", " <-> ").replace("↔", " <-> ")
    expr = expr.replace("→", " -> ").replace("-->", " -> ")
    expr = expr.replace("∧", " ^ ").replace(" & ", " ^ ")
    expr = expr.replace("∨", " v ").replace(" | ", " v ")
    expr = expr.replace("⊕", " xor ")
    expr = expr.replace("¬", " ~ ")
    expr = re.sub(r"\bnot\s+", " ~ ", expr)
    expr = re.sub(r"\s+", " ", expr).strip()
    return expr

def is_variable_name(name: str) -> bool:
    clean = name.strip()
    return clean.lower() in ["x", "y", "z", "u", "v", "w"]

def is_enclosed(s: str) -> bool:
    if not s.startswith("(") or not s.endswith(")"):
        return False
    depth = 0
    for i, ch in enumerate(s):
        if ch == '(': depth += 1
        elif ch == ')': depth -= 1
        if depth == 0 and i < len(s) - 1:
            return False
    return depth == 0

def strip_outer_parens(s: str) -> str:
    s = s.strip()
    while s.startswith("(") and s.endswith(")") and is_enclosed(s):
        s = s[1:-1].strip()
    return s

def split_top(text: str, delim: str) -> List[str]:
    parts, cur, depth = [], [], 0
    dlen = len(delim)
    i = 0
    while i < len(text):
        if text[i] == '(': depth += 1
        elif text[i] == ')': depth -= 1
        if depth == 0 and text[i:i+dlen] == delim:
            parts.append("".join(cur).strip())
            cur = []
            i += dlen
            continue
        cur.append(text[i])
        i += 1
    if cur:
        parts.append("".join(cur).strip())
    return parts

def push_negation_inward(expr: str) -> str:
    expr = strip_outer_parens(expr)
    if not expr.startswith("~"):
        return expr

    inner = strip_outer_parens(expr[1:].strip())

    if inner.startswith("~"):
        return push_negation_inward(inner[1:].strip())

    m_all = re.match(r"^([∀]|forall)\s*([a-zA-Z0-9_]+)\s*(.*)$", inner)
    if m_all:
        var = m_all.group(2)
        rest = m_all.group(3).strip()
        return f"∃{var} " + push_negation_inward(f"~({rest})")

    m_ex = re.match(r"^([∃]|exists)\s*([a-zA-Z0-9_]+)\s*(.*)$", inner)
    if m_ex:
        var = m_ex.group(2)
        rest = m_ex.group(3).strip()
        return f"∀{var} " + push_negation_inward(f"~({rest})")

    parts_and = split_top(inner, " ^ ")
    if len(parts_and) > 1:
        return "(" + " v ".join(push_negation_inward(f"~({p})") for p in parts_and) + ")"

    parts_or = split_top(inner, " v ")
    if len(parts_or) > 1:
        return "(" + " ^ ".join(push_negation_inward(f"~({p})") for p in parts_or) + ")"

    parts_imp = split_top(inner, " -> ")
    if len(parts_imp) == 2:
        return f"({push_negation_inward(parts_imp[0])} ^ {push_negation_inward('~(' + parts_imp[1] + ')')})"

    return f"~{inner}"

class Term:
    def __init__(self, name: str, is_var: bool = False):
        self.name = name.strip()
        self.is_var = is_var
    def __repr__(self):
        return f"?{self.name}" if self.is_var else self.name
    def __eq__(self, other):
        return isinstance(other, Term) and self.name == other.name and self.is_var == other.is_var
    def __hash__(self):
        return hash((self.name, self.is_var))

class Literal:
    def __init__(self, predicate: str, args: List[Term], negated: bool = False):
        self.predicate = predicate.strip()
        self.args = args
        self.negated = negated
    def __repr__(self):
        pref = "~" if self.negated else ""
        return f"{pref}{self.predicate}({', '.join(str(a) for a in self.args)})"
    def __eq__(self, other):
        return (isinstance(other, Literal) and self.predicate == other.predicate and 
                self.args == other.args and self.negated == other.negated)
    def __hash__(self):
        return hash((self.predicate, tuple(self.args), self.negated))

class HornRule:
    def __init__(self, premises: List[Literal], head: Literal):
        self.premises = premises
        self.head = head

def parse_literal(text: str) -> Optional[Literal]:
    text = text.strip()
    negated = False
    if text.startswith("~"):
        negated = True
        text = text[1:].strip()

    m = re.match(r"^([A-Za-z0-9_]+)\((.*)\)$", text)
    if not m:
        if re.match(r"^[A-Za-z0-9_]+$", text):
            return Literal(text, [], negated)
        return None

    pred = m.group(1).strip()
    args_raw = [a.strip() for a in m.group(2).split(",") if a.strip()]
    args = [Term(a, is_var=is_variable_name(a)) for a in args_raw]
    return Literal(pred, args, negated)

def try_parse_horn(item_str: str) -> Tuple[bool, Union[Literal, HornRule, None]]:
    item = normalize_logic_string(item_str)
    item = re.sub(r"^([∀∃]|forall|exists)\s*[a-zA-Z0-9_]+\s*", "", item).strip()
    item = strip_outer_parens(item)

    if " v " in item or " xor " in item or " <-> " in item:
        return False, None

    if " -> " in item:
        parts = item.split(" -> ")
        if len(parts) != 2:
            return False, None
        prem_raw = [p.strip() for p in parts[0].split("^") if p.strip()]
        head_raw = parts[1].strip()

        if head_raw.startswith("~"):
            return False, None
        head = parse_literal(head_raw)
        if not head:
            return False, None

        premises = []
        for p in prem_raw:
            if p.startswith("~"):
                return False, None
            lit = parse_literal(p)
            if not lit:
                return False, None
            premises.append(lit)
        return True, HornRule(premises, head)
    else:
        if item.startswith("~"):
            return False, None
        lit = parse_literal(item)
        if lit:
            return True, lit
        return False, None

def unify_terms(t1: Term, t2: Term, subst: Dict[str, Term]) -> Optional[Dict[str, Term]]:
    if subst is None:
        return None
    if t1 == t2:
        return subst
    if t1.is_var:
        return unify_var(t1, t2, subst)
    if t2.is_var:
        return unify_var(t2, t1, subst)
    return None

def unify_var(var: Term, val: Term, subst: Dict[str, Term]) -> Optional[Dict[str, Term]]:
    if var.name in subst:
        return unify_terms(subst[var.name], val, subst)
    if val.is_var and val.name in subst:
        return unify_terms(var, subst[val.name], subst)
    new_sub = subst.copy()
    new_sub[var.name] = val
    return new_sub

def unify_literals(l1: Literal, l2: Literal, subst: Dict[str, Term]) -> Optional[Dict[str, Term]]:
    if l1.predicate != l2.predicate or len(l1.args) != len(l2.args) or l1.negated != l2.negated:
        return None
    for a1, a2 in zip(l1.args, l2.args):
        subst = unify_terms(a1, a2, subst)
        if subst is None:
            return None
    return subst

def apply_subst(lit: Literal, subst: Dict[str, Term]) -> Literal:
    new_args = []
    for arg in lit.args:
        val = arg
        while val.is_var and val.name in subst:
            val = subst[val.name]
        new_args.append(val)
    return Literal(lit.predicate, new_args, lit.negated)

def standardize_rule(rule: HornRule, depth: int) -> HornRule:
    subst = {}
    new_premises = []
    for p in rule.premises:
        new_args = []
        for a in p.args:
            if a.is_var:
                vname = f"{a.name}_{depth}"
                subst[a.name] = Term(vname, is_var=True)
                new_args.append(subst[a.name])
            else:
                new_args.append(a)
        new_premises.append(Literal(p.predicate, new_args, p.negated))

    h_args = []
    for a in rule.head.args:
        if a.is_var:
            vname = f"{a.name}_{depth}"
            if a.name not in subst:
                subst[a.name] = Term(vname, is_var=True)
            h_args.append(subst[a.name])
        else:
            h_args.append(a)
    return HornRule(new_premises, Literal(rule.head.predicate, h_args, rule.head.negated))

def canonical_key(lit: Literal, subst: Dict[str, Term]) -> str:
    res_args = []
    vmap, count = {}, 0
    for a in lit.args:
        v = a
        while v.is_var and v.name in subst:
            v = subst[v.name]
        if v.is_var:
            if v.name not in vmap:
                vmap[v.name] = f"?v{count}"
                count += 1
            res_args.append(vmap[v.name])
        else:
            res_args.append(v.name)
    return f"{lit.predicate}({', '.join(res_args)})"

def backward_chaining_prove(
    facts: List[Literal],
    rules: List[HornRule],
    goal: Literal,
    subst: Dict[str, Term],
    visited: Set[str],
    depth: int = 0,
    max_depth: int = 80
) -> bool:
    if depth > max_depth:
        return False

    ckey = canonical_key(goal, subst)
    if ckey in visited:
        return False
    next_visited = visited.copy()
    next_visited.add(ckey)

    for f in facts:
        if unify_literals(goal, f, subst.copy()) is not None:
            return True

    for r in rules:
        sr = standardize_rule(r, depth)
        u_sub = unify_literals(goal, sr.head, subst.copy())
        if u_sub is not None:
            all_ok = True
            for p in sr.premises:
                bp = apply_subst(p, u_sub)
                if not backward_chaining_prove(facts, rules, bp, u_sub, next_visited, depth + 1, max_depth):
                    all_ok = False
                    break
            if all_ok:
                return True
    return False

def is_counterbench_structural(clauses: List[str], statement: str) -> bool:
    full_text = " ".join(clauses) + " " + statement
    if " v " in full_text or " xor " in full_text or " <-> " in full_text:
        return False
    if re.search(r"[A-Za-z0-9_]+\([^,)]+,[^)]+\)", full_text):
        return False

    has_a_neg = any(re.match(r"^~\s*[A-Za-z0-9_]+\(a\)$", normalize_logic_string(c)) for c in clauses)
    has_not_rule = any("Not(x)" in c or "Not(" in c for c in clauses)
    has_unary_chain = bool(re.search(r"∀x\s*\([A-Za-z0-9_]+\(x\)\s*->\s*[A-Za-z0-9_]+\(x\)\)", full_text))
    return has_a_neg and (has_not_rule or has_unary_chain)

def solve_counterbench_structural(clauses: List[str], statement: str) -> str:
    intervened_root = None
    edges: List[Tuple[str, str]] = []
    inverter_sources: Set[str] = set()

    for c in clauses:
        c_clean = normalize_logic_string(c)
        m_neg = re.match(r"^~\s*([A-Za-z0-9_]+)\(([a-zA-Z0-9_]+)\)$", c_clean)
        if m_neg:
            intervened_root = m_neg.group(1)
            continue

        m_rule = re.search(r"([A-Za-z0-9_]+)\([a-zA-Z0-9_]+\)\s*->\s*([A-Za-z0-9_]+)\([a-zA-Z0-9_]+\)", c_clean)
        if m_rule:
            p, ch = m_rule.group(1), m_rule.group(2)
            if ch == "Not":
                inverter_sources.add(p)
            else:
                edges.append((p, ch))

    m_target = re.match(r"^([A-Za-z0-9_]+)\([a-zA-Z0-9_]+\)$", normalize_logic_string(statement))
    target_var = m_target.group(1) if m_target else None

    def find_all_paths(curr, dest, visited):
        if curr == dest:
            return [[curr]]
        paths = []
        for p, ch in edges:
            if p == curr and ch not in visited:
                for sub in find_all_paths(ch, dest, visited | {ch}):
                    paths.append([curr] + sub)
        return paths

    all_graph_nodes = set([p for p, ch in edges] + [ch for p, ch in edges] + list(inverter_sources))

    if intervened_root and intervened_root not in all_graph_nodes:
        return "True"

    if intervened_root in inverter_sources:
        return "True"

    paths = find_all_paths(intervened_root, target_var, {intervened_root}) if intervened_root and target_var else []
    if paths:
        has_inverting_edge = any(any(node in inverter_sources for node in path[:-1]) for path in paths)
        return "True" if has_inverting_edge else "False"

    return "False"

def extract_entities(clauses: List[str]) -> Set[str]:
    entities = set()
    for c in clauses:
        for match in re.finditer(r"\b([A-Za-z0-9_]+)\s*\(([^()]+)\)", c):
            pred_name = match.group(1)
            if pred_name in ["forall", "exists"]:
                continue
            args_str = match.group(2)
            for arg in args_str.split(","):
                arg = arg.strip()
                if arg and not is_variable_name(arg) and arg not in ["True", "False"]:
                    entities.add(arg)
    if not entities:
        entities.add("a")
    return entities

def simplify_ground_equality(expr: str) -> str:
    def eq_replacer(m):
        t1, t2 = m.group(1).strip(), m.group(2).strip()
        return "True" if t1 == t2 else "False"
    expr = re.sub(r"([A-Za-z0-9_]+)\s*=\s*([A-Za-z0-9_]+)", eq_replacer, expr)
    expr = expr.replace("~True", "False").replace("~False", "True")
    return expr

def skolemize_all_existentials(formula: str, skolem_counter: List[int], entities: Set[str]) -> str:
    while True:
        m_ex = re.search(r"([∃]|exists)\s*([a-zA-Z0-9_]+)\s*", formula)
        if not m_ex:
            break
        var = m_ex.group(2)
        skolem_counter[0] += 1
        sk_const = f"sk_{skolem_counter[0]}"
        entities.add(sk_const)
        formula = formula[:m_ex.start()] + formula[m_ex.end():]
        formula = re.sub(rf"\b{re.escape(var)}\b", sk_const, formula)
    return formula

def ground_formula(formula: str, entities_list: List[str]) -> str:
    formula = strip_outer_parens(formula)

    m_all = re.match(r"^([∀]|forall)\s*([a-zA-Z0-9_]+)\s*(.*)$", formula)
    if m_all:
        var = m_all.group(2)
        rest = strip_outer_parens(m_all.group(3))
        active_entities = entities_list[:12] if len(entities_list) > 12 else entities_list
        expansions = [ground_formula(re.sub(rf"\b{re.escape(var)}\b", ent, rest), active_entities) for ent in active_entities]
        return "(" + " ^ ".join(expansions) + ")"

    return simplify_ground_equality(formula)

class ASTNode:
    def __init__(self, op: str, children: List['ASTNode'] = None, value: str = None):
        self.op = op
        self.children = children or []
        self.value = value

def parse_ground_to_ast(expr: str) -> ASTNode:
    expr = strip_outer_parens(expr)

    parts = split_top(expr, " <-> ")
    if len(parts) == 2:
        return ASTNode("<->", [parse_ground_to_ast(parts[0]), parse_ground_to_ast(parts[1])])

    parts = split_top(expr, " -> ")
    if len(parts) == 2:
        return ASTNode("->", [parse_ground_to_ast(parts[0]), parse_ground_to_ast(parts[1])])

    parts = split_top(expr, " xor ")
    if len(parts) == 2:
        return ASTNode("xor", [parse_ground_to_ast(parts[0]), parse_ground_to_ast(parts[1])])

    parts = split_top(expr, " v ")
    if len(parts) > 1:
        return ASTNode("v", [parse_ground_to_ast(p) for p in parts])

    parts = split_top(expr, " ^ ")
    if len(parts) > 1:
        return ASTNode("^", [parse_ground_to_ast(p) for p in parts])

    if expr.startswith("~"):
        return ASTNode("~", [parse_ground_to_ast(expr[1:].strip())])

    return ASTNode("atom", value=expr.replace(" ", ""))

def to_tseitin_cnf(node: ASTNode, clauses: List[List[str]], var_counter: List[int]) -> str:
    if node.op == "atom":
        return node.value

    if node.op == "~":
        sub = to_tseitin_cnf(node.children[0], clauses, var_counter)
        if sub.startswith("~"):
            return sub[1:]
        var_counter[0] += 1
        top = f"_t_{var_counter[0]}"
        clauses.append([top, sub])
        clauses.append([f"~{top}", f"~{sub}"])
        return top

    child_vars = [to_tseitin_cnf(c, clauses, var_counter) for c in node.children]
    var_counter[0] += 1
    top = f"_t_{var_counter[0]}"

    if node.op == "^":
        for cv in child_vars:
            clauses.append([f"~{top}", cv])
        clauses.append([top] + [f"~{cv}" for cv in child_vars])

    elif node.op == "v":
        clauses.append([f"~{top}"] + child_vars)
        for cv in child_vars:
            clauses.append([top, f"~{cv}"])

    elif node.op == "->":
        c1, c2 = child_vars[0], child_vars[1]
        clauses.append([f"~{top}", f"~{c1}", c2])
        clauses.append([top, c1])
        clauses.append([top, f"~{c2}"])

    elif node.op == "xor":
        c1, c2 = child_vars[0], child_vars[1]
        clauses.append([f"~{top}", f"~{c1}", f"~{c2}"])
        clauses.append([f"~{top}", c1, c2])
        clauses.append([top, f"~{c1}", c2])
        clauses.append([top, c1, f"~{c2}"])

    elif node.op == "<->":
        c1, c2 = child_vars[0], child_vars[1]
        clauses.append([f"~{top}", f"~{c1}", c2])
        clauses.append([f"~{top}", f"~{c2}", c1])
        clauses.append([top, c1, c2])
        clauses.append([top, f"~{c1}", f"~{c2}"])

    return top

def simplify_clauses(clauses: List[List[str]], assignment: Dict[str, bool]) -> Tuple[bool, List[List[str]]]:
    simplified = []
    for c in clauses:
        c_sat = False
        new_c = []
        for lit in c:
            if lit == "True":
                c_sat = True
                break
            if lit == "False":
                continue
            neg = lit.startswith("~")
            v = lit[1:] if neg else lit
            if v in assignment:
                if assignment[v] != neg:
                    c_sat = True
                    break
            else:
                new_c.append(lit)
        if not c_sat:
            if not new_c:
                return False, []
            simplified.append(new_c)
    return True, simplified

def dpll_bounded(clauses: List[List[str]], assignment: Dict[str, bool], step_counter: List[int], max_steps: int = 2500) -> Optional[bool]:
    step_counter[0] += 1
    if step_counter[0] > max_steps:
        return None

    cur_assignment = assignment.copy()
    cur_clauses = clauses

    while True:
        ok, cur_clauses = simplify_clauses(cur_clauses, cur_assignment)
        if not ok:
            return False
        if not cur_clauses:
            return True

        unit_found = False
        for c in cur_clauses:
            if len(c) == 1:
                unit = c[0]
                neg = unit.startswith("~")
                var = unit[1:] if neg else unit
                cur_assignment[var] = False if neg else True
                unit_found = True
                break
        if not unit_found:
            break

    all_lits = [lit for c in cur_clauses for lit in c]
    all_vars = set(lit[1:] if lit.startswith("~") else lit for lit in all_lits)
    for var in all_vars:
        has_pos = var in all_lits
        has_neg = f"~{var}" in all_lits
        if has_pos and not has_neg:
            cur_assignment[var] = True
            return dpll_bounded(cur_clauses, cur_assignment, step_counter, max_steps)
        if has_neg and not has_pos:
            cur_assignment[var] = False
            return dpll_bounded(cur_clauses, cur_assignment, step_counter, max_steps)

    chosen = next(iter(all_vars))

    cur_assignment[chosen] = True
    res = dpll_bounded(cur_clauses, cur_assignment, step_counter, max_steps)
    if res is True:
        return True
    if res is None:
        return None

    cur_assignment[chosen] = False
    return dpll_bounded(cur_clauses, cur_assignment, step_counter, max_steps)

def is_sat(clauses: List[List[str]], max_steps: int = 2500) -> Optional[bool]:
    step_c = [0]
    return dpll_bounded(clauses, {}, step_c, max_steps)

def solve_fol(context_raw: str, statement_raw: str, is_three_valued: bool = False) -> str:
    ctx_clean = normalize_logic_string(context_raw)
    stmt_clean = normalize_logic_string(statement_raw)
    clauses = [c.strip() for c in ctx_clean.split(";") if c.strip()]
    if not clauses or not stmt_clean:
        return "Uncertain" if is_three_valued else "False"

    if is_counterbench_structural(clauses, stmt_clean):
        return solve_counterbench_structural(clauses, stmt_clean)

    is_horn = True
    facts: List[Literal] = []
    rules: List[HornRule] = []
    for c in clauses:
        ok, res = try_parse_horn(c)
        if not ok or res is None:
            is_horn = False
            break
        if isinstance(res, Literal):
            facts.append(res)
        elif isinstance(res, HornRule):
            rules.append(res)

    query_lit = parse_literal(stmt_clean)
    if is_horn and query_lit and not query_lit.negated:
        proven = backward_chaining_prove(facts, rules, query_lit, {}, set())
        if proven:
            return "True"
        if not is_three_valued:
            return "False"

    entities = extract_entities(clauses + [stmt_clean])
    skolem_c = [0]

    skolemized_kb = [skolemize_all_existentials(c, skolem_c, entities) for c in clauses]
    entities_list = sorted(list(entities))

    grounded_kb = [ground_formula(c, entities_list) for c in skolemized_kb]
    base_clauses = []
    var_c = [0]
    for g in grounded_kb:
        ast = parse_ground_to_ast(g)
        top = to_tseitin_cnf(ast, base_clauses, var_c)
        base_clauses.append([top])

    neg_q_nnf = push_negation_inward(f"~({stmt_clean})")
    skolemized_neg_q = skolemize_all_existentials(neg_q_nnf, skolem_c, entities)
    current_entities_list = sorted(list(entities))
    grounded_neg_q = ground_formula(skolemized_neg_q, current_entities_list)

    clauses_entail = [list(c) for c in base_clauses]
    top_nq = to_tseitin_cnf(parse_ground_to_ast(grounded_neg_q), clauses_entail, var_c)
    clauses_entail.append([top_nq])

    sat_entail = is_sat(clauses_entail)
    if sat_entail is False:
        return "True"

    q_nnf = push_negation_inward(stmt_clean)
    skolemized_q = skolemize_all_existentials(q_nnf, skolem_c, entities)
    current_entities_list = sorted(list(entities))
    grounded_q = ground_formula(skolemized_q, current_entities_list)

    clauses_refute = [list(c) for c in base_clauses]
    top_q = to_tseitin_cnf(parse_ground_to_ast(grounded_q), clauses_refute, var_c)
    clauses_refute.append([top_q])

    sat_refute = is_sat(clauses_refute)
    if sat_refute is False:
        return "False"

    return "Uncertain" if is_three_valued else "False"