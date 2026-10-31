from .base import *
import itertools
import copy
from .decode import *
from .code import *

# how much create_node may create
CREATE_NONE = 0   # lookup only (rule conditions)
CREATE_LINK = 1   # may create function values, e.g. i's sister (rule ASSERTs)
CREATE_ALL = 2    # may also create new named entities (statements, questions)

NE = "!="         # rel key holding the ids an entity is known to differ from


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
#   FUNCTION name      declares a unary function (x's name is another entity)
#   IF expr            branches TRUE / FALSE / UNKNOWN
#   ASSERT expr        add a fact           (expr may be "not ...")
#   THROW              contradiction
#   ASK expr           answer template for who-questions
#   ANSWER expr        a result for the enclosing ASK
#
# Nothing about girls, boys, mothers, ... is known to the Python code.
# ---------------------------------------------------------------------------
RULES = """
FUNCTION mother
FUNCTION father
FUNCTION son
FUNCTION daughter
FUNCTION brother
FUNCTION sister

ASK who is x
 ANSWER x
 IF y's mother is x
  TRUE
   ANSWER y's mother
 IF y's father is x
  TRUE
   ANSWER y's father
 IF y's son is x
  TRUE
   ANSWER y's son
 IF y's daughter is x
  TRUE
   ANSWER y's daughter
 IF y's brother is x
  TRUE
   ANSWER y's brother
 IF y's sister is x
  TRUE
   ANSWER y's sister

ASSERT i am not you

IF x's father is y's father
 TRUE
  IF x's mother is y's mother
   TRUE
    IF x is y
     FALSE
      IF x is a girl
       TRUE
        ASSERT y's sister is x
       FALSE
        ASSERT y's brother is x

IF x is mary
 TRUE
  ASSERT x is a girl
  ASSERT x is not a boy
IF x is john
 TRUE
  ASSERT x is a boy
  ASSERT x is not a girl

IF x is a girl
 TRUE
  ASSERT x is not a boy
 FALSE
  ASSERT x is a boy

IF x is a boy
 TRUE
  ASSERT x is not a girl
 FALSE
  ASSERT x is a girl

IF x is y's mother
 TRUE
  ASSERT x is a girl
  ASSERT x is not a boy

IF x is y's father
 TRUE
  ASSERT x is a boy
  ASSERT x is not a girl

IF x is y's mother
 TRUE
  IF y is a boy
   TRUE
    ASSERT y is x's son
   FALSE
    ASSERT y is x's daughter

IF x is y's father
 TRUE
  IF y is a boy
   TRUE
    ASSERT y is x's son
   FALSE
    ASSERT y is x's daughter

IF x is y's son
 TRUE
  ASSERT x is a boy
  ASSERT x is not a girl

IF x is y's daughter
 TRUE
  ASSERT x is a girl
  ASSERT x is not a boy

IF x is y's brother
 TRUE
  ASSERT x is a boy
  ASSERT x is not a girl

IF x is y's sister
 TRUE
  ASSERT x is a girl
  ASSERT x is not a boy
"""


def parse(s):
    lines = [
        (len(x) - len(x.lstrip()), x.strip())
        for x in s.splitlines()
        if x.strip()
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
                if head == "FUNCTION":
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
    def __init__(self, entry=None, attr=None, rel=None):
        self.entry = entry if entry else []   # names that refer to this entity
        self.attr = attr if attr else {}      # unary facts / function links
        self.rel = rel if rel else {}         # binary facts: name -> {ids}

    def __repr__(self):
        line = "+" + "-" * 60 + "+"
        s = line + "\n"
        for key, item in sorted(self.attr.items()):
            s += f"{key} : {item}\n"
        for key, item in sorted(self.rel.items()):
            s += f"{key} -> {sorted(item)}\n"
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
        self.functions = {
            r[1].strip()
            for r in self.rule
            if isinstance(r, tuple) and r[0] == "FUNCTION" and r[1]
        }
        # rules that are run to a fixed point (everything except templates)
        self.inference_rules = [
            r for r in self.rule
            if not (isinstance(r, tuple) and r[0] in ("ASK", "FUNCTION"))
        ]

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

    def equate_id(self, a, b):
        """Merge two entities (smaller id survives). Raises Contradiction."""
        a, b = self._find(a), self._find(b)
        if a == b:
            return a
        if b in self._targets(a, NE):
            raise Contradiction("known to be different")
        keep, drop = min(a, b), max(a, b)
        q = self.table_entry_list.pop(drop)
        self.alias[drop] = keep

        p = self.table_entry_list[keep]
        for e in q.entry:
            if e not in p.entry:
                p.entry.append(e)
        for name, targets in q.rel.items():
            p.rel.setdefault(name, set()).update(targets)

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

        if eq.name == "equal" and len(eq.children) == 2:
            p = self.create_node(eq.children[0], create)
            q = self.create_node(eq.children[1], create)
            if p is None or q is None:
                return False
            p, q = self._find(p), self._find(q)
            if positive:
                self.equate_id(p, q)
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

        if eq.name == "equal" and len(eq.children) == 2:
            p = self.create_node(eq.children[0], create)
            q = self.create_node(eq.children[1], create)
            if p is None or q is None:
                return None
            p, q = self._find(p), self._find(q)
            if p == q:
                return True
            if q in self._targets(p, NE):
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
    def _bind(self, eq, x, y):
        eq = replace(eq, TreeNode("x"), TreeNode(f"d_{x}"))
        return replace(eq, TreeNode("y"), TreeNode(f"d_{y}"))

    def _answers(self, body, x, y):
        xs = self.find_id(x) or [None]
        ys = self.find_id(y) or [None]
        out = []
        for a in xs:
            for b in ys:
                item = body
                if a is not None:
                    item = replace(item, TreeNode("x"), a)
                if b is not None:
                    item = replace(item, TreeNode("y"), b)
                out.append(item)
        return out

    def process_rule(self, rule, x=None, y=None, answers=None):
        """
        Run one rule with x, y bound to entity ids.
        Effects are applied to the table; ANSWERs are appended to `answers`.
        Raises Contradiction on THROW or conflicting facts.
        """
        if isinstance(rule, list):
            for item in rule:
                self.process_rule(item, x, y, answers)
        elif isinstance(rule, Condition):
            v = self._eval(self._bind(rule.expr, x, y))
            if v is True:
                branch = rule.true
            elif v is False:
                branch = rule.false
            else:
                branch = rule.unknown
            self.process_rule(branch, x, y, answers)
        elif isinstance(rule, tuple):
            head = rule[0]
            if head == "ASK":
                self.process_rule(rule[2], x, y, answers)
            elif head == "ANSWER":
                if answers is not None and rule[1] is not None:
                    answers.extend(self._answers(rule[1], x, y))
            elif head == "THROW":
                raise Contradiction("THROW")
            elif head == "ASSERT":
                # rules may create links (i's sister) but never new names
                self._assert_expr(
                    self._bind(rule[1], x, y), True, CREATE_LINK
                )

    def _signature(self):
        return str(self)

    def _propagate(self):
        """Run all inference rules until nothing changes. Raises Contradiction."""
        for _ in range(self.MAX_ROUNDS):
            before = self._signature()
            ids = list(self.table_entry_list.keys())
            for rule in self.inference_rules:
                for x in ids:
                    if x not in self.table_entry_list:
                        continue
                    for y in ids:
                        if y not in self.table_entry_list:
                            continue
                        self.process_rule(rule, x, y)
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
            out = self.create_node(eq.children[0], CREATE_ALL)
            if out is None:
                return None
            self._propagate()
            answers = []
            ids = list(self.table_entry_list.keys())
            for rule in self.rule:
                if (
                    isinstance(rule, tuple)
                    and rule[0] == "ASK"
                    and rule[1].name == "who"
                ):
                    for other in ids:
                        self.process_rule(rule, out, other, answers)
            phrases = []
            for item in answers:
                if not var_in_eq(item):
                    continue
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
