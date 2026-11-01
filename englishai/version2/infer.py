from .base import *
import itertools
import copy
from .decode import *
from .code import *

# how much create_node may create
CREATE_NONE = 0   # lookup only (rule conditions)
CREATE_LINK = 1   # may create function values, e.g. i's sister (rule ASSERTs)
CREATE_ALL = 2    # may also create new named entities (statements, questions)

VARS = ("x", "y", "z", "w")   # rule variables; each ranges over entities
KNOWER = "k"                  # internal variable of the lifted CLOSED rules
ALL_VARS = VARS + (KNOWER,)

NE = "!="         # rel key: ids an entity is known to differ from (hard fact)
SOFT = "~="       # rel key: ids assumed different because of their names (default)


class Contradiction(Exception):
    """Raised internally when a rule THROWs or a fact conflicts with another."""


class Condition:
    def __init__(self, expr, true=None, false=None, unknown=None):
        self.expr = expr
        self.true = true or []
        self.false = false or []
        self.unknown = unknown or []

    def __repr__(self):
        return (
            f"Condition("
            f"{self.expr!r}, "
            f"true={self.true!r}, "
            f"false={self.false!r}, "
            f"unknown={self.unknown!r})"
        )


# ---------------------------------------------------------------------------
# Rule language
#
#   FUNCTION name      one-valued link: every x has at most one (mother, father)
#   RELATION name      many-valued link: x may have several (sister, son, ...)
#   FACTIVE name       attitude whose content is true: x knows that P  =>  P
#   ATTITUDE name      attitude that only records what x holds (no truth)
#   ENTAILS a b        x a-s that P  =>  x b-s that P   (know => think)
#   CLOSED name        x names that P, and the rules derive Q from P  =>  x names that Q
#                      (every IF/ASSERT rule is re-run inside what x knows)
#   lines starting with # are comments
#   DISTINCT a b c     different names, different people, unless a statement
#                      says otherwise ("i am bob" is accepted, rules cannot
#                      merge them)
#   IF expr            branches TRUE / FALSE / UNKNOWN
#   ASSERT expr        add a fact           (expr may be "not ...")
#   THROW              contradiction
#   ASK expr           answer template for who-questions
#   ANSWER expr        a result for the enclosing ASK
#
# Nothing about girls, boys, mothers, ... is known to the Python code.
# ---------------------------------------------------------------------------
from pathlib import Path
RULES_FILE = Path(__file__).parent / "rules.txt"
RULES = RULES_FILE.read_text(encoding="utf-8")



def parse(s):
    lines = [
        (len(x) - len(x.lstrip()), x.strip())
        for x in s.splitlines()
        if x.strip() and not x.strip().startswith("#")
    ]

    def parse_block(i, indent):
        result = []
        while i < len(lines):
            level, text = lines[i]
            if level < indent:
                break
            if level > indent:
                raise SyntaxError(f"Unexpected indentation: {text}")
            if text.startswith("IF "):
                expr = text[3:]
                condition = Condition(code(expr), [], [], [])
                i += 1
                branches = {
                    "TRUE": condition.true,
                    "FALSE": condition.false,
                    "UNKNOWN": condition.unknown,
                }
                while i < len(lines):
                    level2, text2 = lines[i]
                    if level2 <= indent:
                        break
                    if text2 not in branches:
                        raise SyntaxError(
                            f"Expected TRUE/FALSE/UNKNOWN, got {text2!r}"
                        )
                    i += 1
                    branch, i = parse_block(i, level2 + 1)
                    branches[text2].extend(branch)
                result.append(condition)
            elif text.startswith("ASK "):
                expr = text[4:]
                i += 1
                children, i = parse_block(i, level + 1)
                result.append(("ASK", code(expr), children))
            else:
                head, *sentence = text.split(maxsplit=1)
                if head in ("FUNCTION", "RELATION", "DISTINCT", "FACTIVE", "ATTITUDE", "ENTAILS", "CLOSED"):
                    # raw name, not an expression
                    result.append((head, sentence[0] if sentence else None))
                elif sentence:
                    result.append((head, code(sentence[0])))
                else:
                    result.append((head, None))
                i += 1
        return result, i

    if not lines:
        return []
    return parse_block(0, lines[0][0])[0]


def show(x, level=0):
    space = " " * level
    for item in x:
        if isinstance(item, Condition):
            print(space + "IF", item.expr)
            print(space + " TRUE")
            show(item.true, level + 2)
            print(space + " FALSE")
            show(item.false, level + 2)
            print(space + " UNKNOWN")
            show(item.unknown, level + 2)
        elif len(item) == 3:
            head, expr, children = item
            print(space + head, expr)
            show(children, level + 1)
        else:
            head, equation = item
            if equation is None:
                print(space + head)
            else:
                print(space + head, equation)


def id_helper(a, b):
    a = set(a)
    b = set(b)
    a, b = a - b, b - a
    if len(a) == 1 and len(b) == 1:
        return list(a)[0], list(b)[0]
    return None


def collect_id_nodes(node):
    out = []
    if isinstance(node, TreeNode) and node.name == "id":
        out.append(node)
    for child in getattr(node, "children", []):
        out.extend(collect_id_nodes(child))
    return out


def valid_actor_eq(eq):
    try:
        actor_to_phrase(eq)
    except Exception:
        return False
    return True


def swap_pronouns(node):
    """Speaker/listener swap: i <-> you (the table stores the user's view)."""
    if not isinstance(node, TreeNode):
        return node
    name = node.name
    if name == "i":
        name = "you"
    elif name == "you":
        name = "i"
    return TreeNode(name, [swap_pronouns(c) for c in node.children])


class TableEntry:
    def __init__(self, entry=None, attr=None, rel=None, know=None):
        self.entry = entry if entry else []   # names that refer to this entity
        self.attr = attr if attr else {}      # unary facts / function links
        self.rel = rel if rel else {}         # binary facts: name -> {ids}
        self.know = know if know else {}      # attitude -> [propositions]

    def __repr__(self):
        line = "+" + "-" * 60 + "+"
        s = line + "\n"
        for key, item in sorted(self.attr.items()):
            s += f"{key} : {item}\n"
        for key, item in sorted(self.rel.items()):
            s += f"{key} -> {sorted(item)}\n"
        for key, item in sorted(self.know.items()):
            for text in sorted(repr(p) for p in item):
                s += f"{key} that {text}\n"
        s += line + "\n"
        s += "| Entries\n"
        if len(self.entry) == 0:
            s += "|   <empty>\n"
        else:
            for eq in self.entry:
                s += f"|   {eq}\n"
        s += line
        return s


class Table:
    MAX_ROUNDS = 100

    def __init__(self, rules=RULES):
        self.table_entry_list = {}
        self.alias = {}        # merged-away id -> surviving id
        self.curr = 0
        self.rule = parse(rules)
        self.functions = self._declared("FUNCTION")
        self.relations = self._declared("RELATION")
        self.factive = self._declared("FACTIVE")
        self.entails = {}                  # attitude -> weaker attitudes it implies
        for r in self.rule:
            if isinstance(r, tuple) and r[0] == "ENTAILS" and r[1]:
                strong, *weak = r[1].split()
                self.entails.setdefault(strong, set()).update(weak)
        mentioned = set(self.entails) | {
            w for ws in self.entails.values() for w in ws
        }
        self.closed = self._declared("CLOSED")
        self.attitudes = (
            self._declared("ATTITUDE") | self.factive | mentioned | self.closed
        )
        self.distinct_groups = [
            r[1].split()
            for r in self.rule
            if isinstance(r, tuple) and r[0] == "DISTINCT" and r[1]
        ]
        # rules that are run to a fixed point (everything except templates)
        self.inference_rules = [
            (r, self._rule_vars(r)) for r in self.rule
            if not (isinstance(r, tuple) and r[0] in ("ASK", "FUNCTION", "RELATION", "DISTINCT", "FACTIVE", "ATTITUDE", "ENTAILS", "CLOSED"))
        ]
        # the same rules, re-run inside what a knower knows (CLOSED attitudes)
        self.lifted_rules = []
        for att in sorted(self.closed):
            for r, _ in self.inference_rules:
                if isinstance(r, Condition) and not self._cond_mentions_attitude(r):
                    lifted = self._lift_condition(r, att)
                    self.lifted_rules.append(
                        (lifted, self._rule_vars(lifted), att)
                    )

    def _declared(self, head):
        return {
            r[1].strip()
            for r in self.rule
            if isinstance(r, tuple) and r[0] == head and r[1]
        }

    def _apply_distinct(self):
        """DISTINCT groups: entities with different names are assumed different."""
        for group in self.distinct_groups:
            owners = {}                       # name -> {entity ids}
            for key, ent in self.table_entry_list.items():
                for e in ent.entry:
                    if not e.children and e.name in group:
                        owners.setdefault(e.name, set()).add(key)
            for a, b in itertools.combinations(sorted(owners), 2):
                for p in owners[a]:
                    for q in owners[b]:
                        if p == q:
                            continue          # explicitly said to be the same
                        for u, v in ((p, q), (q, p)):
                            self.table_entry_list[u].rel.setdefault(
                                SOFT, set()
                            ).add(v)

    def _incompatible(self, p, q, seen=None):
        """
        True if merging p and q would certainly contradict: they carry opposite
        unary facts (girl vs boy, dead vs alive, ...), are known to differ, or
        their mothers/fathers/... are incompatible in turn.
        """
        p, q = self._find(p), self._find(q)
        if p == q:
            return False
        seen = seen if seen is not None else set()
        if (p, q) in seen or (q, p) in seen:
            return False
        seen.add((p, q))
        if q in self._targets(p, NE) or q in self._targets(p, SOFT):
            return True
        a, b = self.table_entry_list[p], self.table_entry_list[q]
        for key, val in a.attr.items():
            if key in self.functions:
                other = b.attr.get(key)
                if other is not None and self._incompatible(val, other, seen):
                    return True
            elif b.attr.get(key) not in (None, val):
                return True
        return False

    def _prop_key(self, eq, create=CREATE_NONE):
        """
        Canonical form of a proposition, with every entity replaced by its
        current id, so that "john killed mary" is recognised however john and
        mary were named, and survives merges.
        """
        is_term = (not eq.children) or (
            eq.name in self.functions and len(eq.children) == 1
        )
        if is_term:
            i = self.create_node(eq, create)
            if i is not None:
                return ("e", self._find(i))
            return ("?", repr(eq))
        keys = [self._prop_key(c, create) for c in eq.children]
        if eq.name == "equal":
            keys.sort(key=repr)
        return (eq.name, tuple(keys))

    def _entailed(self, name):
        """Every attitude implied by `name` (know => think => ...)."""
        out, todo = set(), [name]
        while todo:
            for weaker in self.entails.get(todo.pop(), ()):
                if weaker not in out and weaker != name:
                    out.add(weaker)
                    todo.append(weaker)
        return out

    def _knows(self, ent, name, prop_key):
        return any(
            self._prop_key(t) == prop_key for t in ent.know.get(name, [])
        )

    def _expr_vars(self, node):
        """Rule variables (x, y, z, w) occurring in an expression."""
        out = set()
        if not node.children and node.name in ALL_VARS:
            out.add(node.name)
        for c in node.children:
            out |= self._expr_vars(c)
        return out

    def _rule_vars(self, rule):
        """Variables a rule uses, in VARS order."""
        found = set()

        def walk(r):
            if isinstance(r, list):
                for item in r:
                    walk(item)
            elif isinstance(r, Condition):
                found.update(self._expr_vars(r.expr))
                walk(r.true)
                walk(r.false)
                walk(r.unknown)
            elif isinstance(r, tuple):
                for part in r[1:]:
                    if isinstance(part, list):
                        walk(part)
                    elif isinstance(part, TreeNode):
                        found.update(self._expr_vars(part))

        walk(rule)
        return [v for v in ALL_VARS if v in found]

    def _mentions_attitude(self, expr):
        return expr.name in self.attitudes or any(
            self._mentions_attitude(c) for c in expr.children
        )

    def _cond_mentions_attitude(self, cond):
        """Does a condition (or one nested in its branches) test an attitude?"""
        if self._mentions_attitude(cond.expr):
            return True
        return any(
            self._cond_mentions_attitude(item)
            for branch in (cond.true, cond.false, cond.unknown)
            for item in branch
            if isinstance(item, Condition)
        )

    def _lift_items(self, items, att):
        out = []
        for item in items:
            if isinstance(item, Condition):
                if not self._cond_mentions_attitude(item):
                    out.append(self._lift_condition(item, att))
            elif isinstance(item, tuple) and item[0] == "ASSERT":
                # facts about what others know are not passed on any further
                if not self._mentions_attitude(item[1]):
                    out.append(
                        ("ASSERT", TreeNode(att, [TreeNode(KNOWER), item[1]]))
                    )
        return out

    def _lift_condition(self, cond, att):
        """
        IF E / TRUE a / FALSE b / UNKNOWN c   becomes, for a knower k:
        IF k knows E: TRUE a;  otherwise IF k knows not E: FALSE b, else c;
        and every ASSERT P becomes ASSERT k knows P.
        """
        def know(p):
            return TreeNode(att, [TreeNode(KNOWER), p])

        e = cond.expr
        neg = (
            e.children[0]
            if e.name == "not" and len(e.children) == 1
            else TreeNode("not", [e])
        )
        return Condition(
            know(e),
            self._lift_items(cond.true, att),
            [],
            [
                Condition(
                    know(neg),
                    self._lift_items(cond.false, att),
                    [],
                    self._lift_items(cond.unknown, att),
                )
            ],
        )

    def _has_free_var(self, node):
        """True if a template variable (x, y, z, w) is still present in node."""
        return bool(self._expr_vars(node))

    def _is_rel(self, node):
        """r(z) where r is a RELATION: a set of entities, not one entity."""
        return node.name in self.relations and len(node.children) == 1

    def _split_rel(self, eq):
        """
        For equal(a, b) where exactly one side is a relation term r(z),
        return (entity_expr, r(z)); otherwise None.
        """
        l, r = eq.children
        if self._is_rel(l) and not self._is_rel(r):
            return r, l
        if self._is_rel(r) and not self._is_rel(l):
            return l, r
        return None

    # ------------------------------------------------------------------
    # state
    # ------------------------------------------------------------------
    def _snapshot(self):
        return copy.deepcopy(
            (self.table_entry_list, self.alias, self.curr)
        )

    def _restore(self, snap):
        self.table_entry_list, self.alias, self.curr = snap

    def copy_table(a, b):
        a._restore(b._snapshot())

    def _consistent(self, fn):
        """Run fn on a scratch copy; True if no contradiction. Always rolls back."""
        snap = self._snapshot()
        try:
            fn()
            self._propagate()
            return True
        except Contradiction:
            return False
        finally:
            self._restore(snap)

    # ------------------------------------------------------------------
    # entities
    # ------------------------------------------------------------------
    def create(self):
        i = self.curr
        self.table_entry_list[i] = TableEntry()
        self.curr += 1
        return i

    def _find(self, i):
        while i in self.alias:
            i = self.alias[i]
        return i

    def find_id(self, n):
        n = self._find(n)
        if n not in self.table_entry_list:
            return []
        return list(self.table_entry_list[n].entry)

    def _targets(self, a, name):
        ent = self.table_entry_list[self._find(a)]
        return {self._find(i) for i in ent.rel.get(name, ())}

    def create_node(self, node, create=CREATE_NONE):
        """
        Resolve an expression to an entity id (None if unknown).
        create >= CREATE_LINK: missing function values (i's sister) are created.
        create >= CREATE_ALL : unknown names are created too.
        """
        if node.name.startswith("d_"):
            return self._find(int(node.name[2:]))
        if not node.children:
            for key, ent in self.table_entry_list.items():
                if node in ent.entry:
                    return key
            if create < CREATE_ALL:
                return None
            out = self.create()
            self.table_entry_list[out].entry.append(node)
            return out
        if node.name in self.functions and len(node.children) == 1:
            base = self.create_node(node.children[0], create)
            if base is None:
                return None
            ent = self.table_entry_list[self._find(base)]
            if node.name in ent.attr:
                return self._find(ent.attr[node.name])
            if create >= CREATE_LINK:
                new = self.create()
                ent.attr[node.name] = new
                return new
        return None

    def equate_id(self, a, b, explicit=False):
        """
        Merge two entities (smaller id survives). Raises Contradiction.
        explicit=True: the user said so; it may override a name-based default.
        """
        a, b = self._find(a), self._find(b)
        if a == b:
            return a
        if b in self._targets(a, NE):
            raise Contradiction("known to be different")
        if not explicit and b in self._targets(a, SOFT):
            raise Contradiction("assumed different (different names)")
        keep, drop = min(a, b), max(a, b)
        q = self.table_entry_list.pop(drop)
        self.alias[drop] = keep

        p = self.table_entry_list[keep]
        for e in q.entry:
            if e not in p.entry:
                p.entry.append(e)
        for name, targets in q.rel.items():
            p.rel.setdefault(name, set()).update(targets)
        for name, props in q.know.items():
            for t in props:
                if not self._knows(p, name, self._prop_key(t)):
                    p.know.setdefault(name, []).append(t)

        for key, val in q.attr.items():
            keep = self._find(keep)
            p = self.table_entry_list[keep]
            if key not in p.attr:
                p.attr[key] = val
            elif key in self.functions:
                self.equate_id(p.attr[key], val)     # same entity -> same mother
            elif p.attr[key] != val:
                raise Contradiction(key)
        return self._find(keep)

    # ------------------------------------------------------------------
    # facts
    # ------------------------------------------------------------------
    def _set_attr(self, name, node, val):
        attr = self.table_entry_list[self._find(node)].attr
        cur = attr.get(name)
        if cur is not None and cur != val:
            raise Contradiction(name)
        attr[name] = val

    def _wellformed(self, eq):
        if eq.name == "not" and len(eq.children) == 1:
            return self._wellformed(eq.children[0])
        if eq.name in self.attitudes and len(eq.children) == 2:
            return (
                valid_actor_eq(eq.children[0])
                and self._wellformed(eq.children[1])
            )
        return (
            len(eq.children) in (1, 2)
            and all(valid_actor_eq(c) for c in eq.children)
        )

    def _assert_expr(self, eq, positive=True, create=CREATE_LINK):
        """
        Add a fact. Returns True if something was recorded, False if the
        fact could not be expressed (skipped). Raises Contradiction on conflict.
        """
        if eq.name == "not" and len(eq.children) == 1:
            return self._assert_expr(eq.children[0], not positive, create)

        if eq.name in self.attitudes and len(eq.children) == 2:
            if not positive:
                return False                     # "x does not know P" not stored
            who = self.create_node(eq.children[0], create)
            if who is None:
                return False
            prop = eq.children[1]
            if eq.name in self.factive:
                self._assert_expr(prop, True, create)   # may raise Contradiction
            ent = self.table_entry_list[self._find(who)]
            key = self._prop_key(prop, create)
            for name in [eq.name] + sorted(self._entailed(eq.name)):
                if not self._knows(ent, name, key):
                    ent.know.setdefault(name, []).append(prop)
            return True

        if eq.name == "equal" and len(eq.children) == 2:
            if self._is_rel(eq.children[0]) or self._is_rel(eq.children[1]):
                sp = self._split_rel(eq)
                if sp is None or not positive:
                    return False                 # not stored
                ent, term = sp
                x = self.create_node(ent, create)
                owner = self.create_node(term.children[0], create)
                if x is None or owner is None:
                    return False
                self.table_entry_list[self._find(owner)].rel.setdefault(
                    term.name, set()
                ).add(self._find(x))
                return True
            p = self.create_node(eq.children[0], create)
            q = self.create_node(eq.children[1], create)
            if p is None or q is None:
                return False
            p, q = self._find(p), self._find(q)
            if positive:
                self.equate_id(p, q, explicit=(create >= CREATE_ALL))
                return True
            if p == q:
                raise Contradiction("same entity asserted different")
            self.table_entry_list[p].rel.setdefault(NE, set()).add(q)
            self.table_entry_list[q].rel.setdefault(NE, set()).add(p)
            return True

        if len(eq.children) == 1:
            n = self.create_node(eq.children[0], create)
            if n is None:
                return False
            self._set_attr(eq.name, n, "true" if positive else "false")
            return True

        if len(eq.children) == 2:
            if not positive:
                return False
            a = self.create_node(eq.children[0], create)
            b = self.create_node(eq.children[1], create)
            if a is None or b is None:
                return False
            self.table_entry_list[self._find(a)].rel.setdefault(
                eq.name, set()
            ).add(self._find(b))
            return True

        return False

    def _eval(self, eq, create=CREATE_NONE):
        """Stored truth value of eq: True / False / None (unknown)."""
        if eq.name == "not" and len(eq.children) == 1:
            v = self._eval(eq.children[0], create)
            return None if v is None else (not v)

        if eq.name in self.attitudes and len(eq.children) == 2:
            who = self.create_node(eq.children[0], create)
            if who is None:
                return None
            key = self._prop_key(eq.children[1], create)
            ent = self.table_entry_list[self._find(who)]
            return True if self._knows(ent, eq.name, key) else None

        if eq.name == "equal" and len(eq.children) == 2:
            if self._is_rel(eq.children[0]) or self._is_rel(eq.children[1]):
                sp = self._split_rel(eq)
                if sp is None:
                    return None
                ent, term = sp
                x = self.create_node(ent, create)
                owner = self.create_node(term.children[0], create)
                if x is None or owner is None:
                    return None
                # membership is only ever proven, never disproven (open world)
                if self._find(x) in self._targets(owner, term.name):
                    return True
                return None
            p = self.create_node(eq.children[0], create)
            q = self.create_node(eq.children[1], create)
            if p is None or q is None:
                return None
            p, q = self._find(p), self._find(q)
            if p == q:
                return True
            if self._incompatible(p, q):
                return False
            return None          # open world: not proven different

        if len(eq.children) == 1:
            n = self.create_node(eq.children[0], create)
            if n is None:
                return None
            val = self.table_entry_list[self._find(n)].attr.get(eq.name)
            if val == "true":
                return True
            if val == "false":
                return False
            return None

        if len(eq.children) == 2:
            a = self.create_node(eq.children[0], create)
            b = self.create_node(eq.children[1], create)
            if a is None or b is None:
                return None
            return True if self._find(b) in self._targets(a, eq.name) else None

        return None

    # ------------------------------------------------------------------
    # rule engine
    # ------------------------------------------------------------------
    def _bind(self, eq, env):
        """Replace each bound variable by a reference to its entity."""
        for var, ident in env.items():
            eq = replace(eq, TreeNode(var), TreeNode(f"d_{ident}"))
        return eq

    def _answers(self, body, env):
        used = [v for v in VARS if v in env and v in self._expr_vars(body)]
        lists = [self.find_id(env[v]) or [None] for v in used]
        out = []
        for combo in itertools.product(*lists):
            item = body
            for var, name in zip(used, combo):
                if name is not None:
                    item = replace(item, TreeNode(var), name)
            out.append(item)
        return out

    def process_rule(self, rule, env=None, answers=None):
        """
        Run one rule with its variables bound by env ({"x": id, "y": id, ...}).
        Effects are applied to the table; ANSWERs are appended to `answers`.
        Raises Contradiction on THROW or conflicting facts.
        """
        env = env or {}
        if isinstance(rule, list):
            for item in rule:
                self.process_rule(item, env, answers)
        elif isinstance(rule, Condition):
            v = self._eval(self._bind(rule.expr, env))
            if v is True:
                branch = rule.true
            elif v is False:
                branch = rule.false
            else:
                branch = rule.unknown
            self.process_rule(branch, env, answers)
        elif isinstance(rule, tuple):
            head = rule[0]
            if head == "ASK":
                self.process_rule(rule[2], env, answers)
            elif head == "ANSWER":
                if answers is not None and rule[1] is not None:
                    answers.extend(self._answers(rule[1], env))
            elif head == "THROW":
                raise Contradiction("THROW")
            elif head == "ASSERT":
                # rules may create links (i's sister) but never new names
                self._assert_expr(
                    self._bind(rule[1], env), True, CREATE_LINK
                )

    def _signature(self):
        return str(self)

    def _propagate(self):
        """Run all inference rules until nothing changes. Raises Contradiction."""
        for _ in range(self.MAX_ROUNDS):
            self._apply_distinct()
            before = self._signature()
            ids = list(self.table_entry_list.keys())
            for rule, variables in self.inference_rules:
                # only the variables a rule really uses are enumerated
                for combo in itertools.product(ids, repeat=len(variables)):
                    if any(i not in self.table_entry_list for i in combo):
                        continue
                    self.process_rule(rule, dict(zip(variables, combo)))
            for rule, variables, att in self.lifted_rules:
                knowers = [
                    i for i, ent in self.table_entry_list.items()
                    if ent.know.get(att)
                ]
                if not knowers:
                    continue
                base = [v for v in variables if v != KNOWER]
                for combo in itertools.product(ids, repeat=len(base)):
                    if any(i not in self.table_entry_list for i in combo):
                        continue
                    for kn in knowers:
                        if kn not in self.table_entry_list:
                            continue
                        env = dict(zip(base, combo))
                        env[KNOWER] = kn
                        self.process_rule(rule, env)
            if self._signature() == before:
                return
        raise RuntimeError("rules did not reach a fixed point")

    def process_all_rule(self):
        """[] on success, None if the table is contradictory."""
        try:
            self._propagate()
            return []
        except Contradiction:
            return None

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def context(self, eq):
        """
        Tell the table a fact. Returns True if accepted,
        None if it was inexpressible or contradicts what is known
        (the table is rolled back in that case).
        """
        if not self._wellformed(eq):
            return None
        snap = self._snapshot()
        try:
            if not self._assert_expr(eq, True, CREATE_ALL):
                self._restore(snap)
                return None
            self._propagate()
            return True
        except Contradiction:
            self._restore(snap)
            return None

    def question(self, eq):
        """
        Yes/no query. True / False / None (unknown).
        The table is left unchanged.
        """
        if eq.name == "question":
            eq = eq.children[0]
        if not self._wellformed(eq):
            return None
        snap = self._snapshot()
        try:
            return self._decide(eq)
        except Contradiction:
            return None          # table itself is contradictory
        finally:
            self._restore(snap)

    def _decide(self, eq):
        self._propagate()
        self._eval(eq, CREATE_ALL)       # materialise the names it mentions
        self._propagate()                # let rules say things about them
        v = self._eval(eq, CREATE_ALL)
        if v is not None:
            return v
        return self._refute(eq)

    def _refute(self, eq):
        """
        Not stored: test by refutation. If assuming it true breaks the rules
        it is False; if assuming it false breaks them it is True.
        """
        if eq.name == "not" and len(eq.children) == 1:
            r = self._refute(eq.children[0])
            return None if r is None else (not r)

        can_true = self._consistent(
            lambda: self._assert_expr(eq, True, CREATE_ALL)
        )
        can_false = self._consistent(
            lambda: self._assert_expr(eq, False, CREATE_ALL)
        )
        if can_true and not can_false:
            return True
        if can_false and not can_true:
            return False
        return None

    def ask(self, eq):
        """
        question(...) -> True/False/None
        who(...)      -> list of phrases produced by the ASK templates
        """
        if eq.name == "question":
            return self.question(eq)
        if eq.name != "who" or not eq.children:
            return None
        snap = self._snapshot()
        try:
            self._propagate()
            target = eq.children[0]
            if self._is_rel(target):
                # "who is my sister": every member of the relation
                base = self.create_node(target.children[0], CREATE_ALL)
                if base is None:
                    return None
                self._propagate()
                outs = sorted(self._targets(base, target.name))
            else:
                out = self.create_node(target, CREATE_ALL)
                if out is None:
                    return None
                self._propagate()
                outs = [self._find(out)]
            answers = []
            ids = list(self.table_entry_list.keys())
            for out in outs:
                for rule in self.rule:
                    if (
                        isinstance(rule, tuple)
                        and rule[0] == "ASK"
                        and rule[1].name == "who"
                    ):
                        others = [v for v in self._rule_vars(rule) if v != "x"]
                        for combo in itertools.product(ids, repeat=len(others)):
                            env = {"x": out, **dict(zip(others, combo))}
                            self.process_rule(rule, env, answers)
            phrases = []
            for item in answers:
                if self._has_free_var(item) or not var_in_eq(item):
                    continue          # template variable x / y never got a name
                item = swap_pronouns(item)
                try:
                    p = actor_to_phrase(item)
                except Exception:
                    continue
                if p not in phrases:
                    phrases.append(p)
            return phrases
        except Contradiction:
            return None
        finally:
            self._restore(snap)

    def __repr__(self):
        s = []
        if self.alias:
            s.append(f"alias {sorted(self.alias.items())}")
        for key, item in sorted(self.table_entry_list.items()):
            s.append(f"id {key}")
            s.append(str(item))
            s.append("")
        return "\n".join(s)
