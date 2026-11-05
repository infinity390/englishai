from .base import *
import itertools
import copy
from .decode import *
from .code import *
from pathlib import Path

# how much create_node may create
CREATE_NONE = 0   # lookup only (rule conditions)
CREATE_LINK = 1   # may create function values, e.g. i's sister (rule ASSERTs)
CREATE_ALL = 2    # may also create new named entities (statements, questions)
CREATE_PHANTOM = 3  # statements only: "my sister's father" invents a sister if none is known

VARS = ("x", "y", "z", "w")   # rule variables; each ranges over entities
ALL_VARS = VARS + tuple(f"k{i}" for i in range(1, 9))   # every variable name rules may use
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
#   CLOSED name        x names that P, and the rules derive Q from P  =>  x names that Q.
#                      (parsed, but not implemented by the engine yet)
#   lines starting with # are comments
#   DISTINCT a b c     different names, different people, unless a statement
#                      says otherwise
#   IF expr            branches TRUE / FALSE / UNKNOWN
#   ASSERT expr        add a fact           (expr may be "not ...")
#   THROW              contradiction
#   ASK expr           answer template for who-questions
#   ANSWER expr        a result for the enclosing ASK
#
# Blocks may be indented by any consistent amount (1, 2, 4 spaces ...).
# ---------------------------------------------------------------------------
RULES_FILE = Path(__file__).parent / "rules.txt"
RULES = RULES_FILE.read_text(encoding="utf-8")

_DECLARATIONS = ("FUNCTION", "RELATION", "DISTINCT", "FACTIVE", "ATTITUDE", "ENTAILS", "CLOSED")


def parse(s):
    lines = [
        (len(x) - len(x.lstrip()), x.strip())
        for x in s.splitlines()
        if x.strip() and not x.strip().startswith("#")
    ]

    def child_indent(i, parent):
        """Indentation of the child block starting at line i (any depth > parent)."""
        if i < len(lines) and lines[i][0] > parent:
            return lines[i][0]
        return parent + 1

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
                    branch, i = parse_block(i, child_indent(i, level2))
                    branches[text2].extend(branch)
                result.append(condition)
            elif text.startswith("ASK "):
                expr = text[4:]
                i += 1
                children, i = parse_block(i, child_indent(i, level))
                result.append(("ASK", code(expr), children))
            else:
                head, *sentence = text.split(maxsplit=1)
                if head in _DECLARATIONS:
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


def _strip_ids(node):
    """Replace internal d_<id> references by a plain actor so they can be validated."""
    if not isinstance(node, TreeNode):
        return node
    if not node.children and node.name.startswith("d_") and node.name[2:].isdigit():
        return TreeNode("i")
    return TreeNode(node.name, [_strip_ids(c) for c in node.children])


def valid_actor_eq(eq):
    try:
        actor_to_phrase(_strip_ids(eq))
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
        self.know = know if know else {}      # attitude -> nested Table object

    def __repr__(self):
        line = "+" + "-" * 60 + "+"
        s = line + "\n"
        for key, item in sorted(self.attr.items()):
            s += f"{key} : {item}\n"
        for key, item in sorted(self.rel.items()):
            s += f"{key} -> {sorted(item)}\n"
        for key, sub_table in sorted(self.know.items()):
            s += f"{key} table:\n"
            for sub_line in str(sub_table).splitlines():
                s += f"  {sub_line}\n"
        s += line + "\n"
        s += "| Entries\n"
        if len(self.entry) == 0:
            s += "|   <empty>\n"
        else:
            for eq in self.entry:
                s += f"|   {eq}\n"
        s += line
        return s


def _merge_tables(target_table, source_table):
    """Recursively merge a source nested Table into a target nested Table.

    Ids in the two tables may not mean the same thing, so every source id is
    first mapped to a target id (by name where possible) and all links are
    translated through that mapping.
    """
    mapping = {}                                   # source id -> target id
    for src_id, src_ent in source_table.table_entry_list.items():
        target_id = None
        for eq in src_ent.entry:
            resolved = target_table._resolve(eq, CREATE_ALL)
            if resolved:
                target_id = resolved[0]
                break
        if target_id is None:
            if (src_id not in target_table.table_entry_list
                    and src_id not in target_table.alias):
                # nothing clashes: keep the shared id space so d_<id> stays valid
                target_table.table_entry_list[src_id] = TableEntry()
                target_table.curr = max(target_table.curr, src_id + 1)
                target_table._version += 1
                target_id = src_id
            else:
                target_id = target_table.create()
        mapping[src_id] = target_id

    def tr(i):
        i = source_table._find(i)
        if i not in mapping:
            mapping[i] = target_table.create()
        return target_table._find(mapping[i])

    def tent(src_id):
        return target_table.table_entry_list[target_table._find(mapping[src_id])]

    for src_id, src_ent in list(source_table.table_entry_list.items()):
        for eq in src_ent.entry:
            if eq not in tent(src_id).entry:
                tent(src_id).entry.append(eq)
        for k, v in src_ent.attr.items():
            val = tr(v) if k in source_table.functions else v
            cur = tent(src_id).attr.get(k)
            if cur is None:
                tent(src_id).attr[k] = val
            elif k in target_table.functions:
                target_table.equate_id(cur, val)
            elif cur != val:
                raise Contradiction(k)
        for k, targets in src_ent.rel.items():
            tent(src_id).rel.setdefault(k, set()).update(tr(t) for t in targets)
        for k, sub_sub in src_ent.know.items():
            ent = tent(src_id)
            if k not in ent.know:
                ent.know[k] = copy.deepcopy(sub_sub)
            else:
                _merge_tables(ent.know[k], sub_sub)
    target_table._propagate()


def _make_nested_table(parent_table, attitude_name):
    """
    Creates a nested Table for an attitude.
    Knowledge inheritance ONLY takes place if the attitude is FACTIVE.
    Otherwise (plain ATTITUDE), the nested table starts fresh/isolated.
    The (immutable) parsed rules are shared with the parent, not re-derived.
    """
    sub_table = Table.__new__(Table)
    for k in Table._SHARED:
        setattr(sub_table, k, getattr(parent_table, k))
    sub_table.table_entry_list = {}
    sub_table.alias = copy.deepcopy(parent_table.alias)
    sub_table.curr = parent_table.curr
    sub_table._version = 0
    sub_table.depth = parent_table.depth + 1

    if attitude_name in parent_table.factive:
        for k, v in parent_table.table_entry_list.items():
            sub_table.table_entry_list[k] = TableEntry(
                entry=copy.deepcopy(v.entry),
                attr=copy.deepcopy(v.attr),
                rel=copy.deepcopy(v.rel),
                know={}
            )
    return sub_table


class Table:
    MAX_ROUNDS = 100
    MAX_DEPTH = 2          # how deeply "x knows that y thinks that ..." tables may nest

    # attributes derived from the rules; never mutated, so shared between copies
    _SHARED = ("rule", "functions", "relations", "factive", "entails",
               "closed", "attitudes", "distinct_groups", "inference_rules")

    def __init__(self, rules=RULES):
        self.table_entry_list = {}
        self.alias = {}        # merged-away id -> surviving id
        self.curr = 0
        self._version = 0      # bumped whenever entities are created / merged / restored
        self.depth = 0         # nesting level of attitude tables

        if isinstance(rules, str):
            self.rule = parse(rules)
        else:
            self.rule = rules

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
            if not (isinstance(r, tuple) and r[0] == "ASK") and not (
                isinstance(r, tuple) and r[0] in _DECLARATIONS
            )
        ]

    def __deepcopy__(self, memo):
        new = Table.__new__(Table)
        memo[id(self)] = new
        for k, v in self.__dict__.items():
            setattr(new, k, v if k in self._SHARED else copy.deepcopy(v, memo))
        return new

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
        out, todo = set(), [name]
        while todo:
            for weaker in self.entails.get(todo.pop(), ()):
                if weaker not in out and weaker != name:
                    out.add(weaker)
                    todo.append(weaker)
        return out

    def _knows(self, ent, name, prop):
        if name not in ent.know:
            return False
        return ent.know[name].question(prop) is True

    def _expr_vars(self, node):
        out = set()
        if not node.children and node.name in ALL_VARS:
            out.add(node.name)
        for c in node.children:
            out |= self._expr_vars(c)
        return out

    def _rule_vars(self, rule):
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

    def _has_free_var(self, node):
        return bool(self._expr_vars(node))

    def _term_for(self, i, seen=()):
        """A name or function term (e.g. father(you)) that denotes entity i, or None."""
        i = self._find(i)
        ent = self.table_entry_list.get(i)
        if ent is None or i in seen:
            return None
        if ent.entry:
            return ent.entry[0]
        for j, owner in self.table_entry_list.items():
            for key, val in owner.attr.items():
                if key in self.functions and self._find(val) == i:
                    inner = self._term_for(j, seen + (i,))
                    if inner is not None:
                        return TreeNode(key, [inner])
        return None

    def _ensure(self, i):
        i = self._find(i)
        if i not in self.table_entry_list:
            self.table_entry_list[i] = TableEntry()
            self.curr = max(self.curr, i + 1)
            self._version += 1
        return i

    def _absorb(self, other):
        """Add everything in `other` to this table.  Both tables must share one
        id space (this table was seeded as a copy of `other`).  Nested attitude
        tables are not copied."""
        for i in list(other.table_entry_list):
            self._ensure(i)
        for d, k in other.alias.items():
            a, b = self._ensure(d), self._ensure(k)
            if a != b:
                self.equate_id(a, b, explicit=True)
        for i, oe in other.table_entry_list.items():
            se = self.table_entry_list[self._find(i)]
            for e in oe.entry:
                if e not in se.entry:
                    se.entry.append(e)
            for key, val in oe.attr.items():
                se = self.table_entry_list[self._find(i)]
                if key in self.functions:
                    val = self._ensure(val)
                    if key in se.attr:
                        self.equate_id(se.attr[key], val)
                    else:
                        se.attr[key] = val
                elif key not in se.attr:
                    se.attr[key] = val
                elif se.attr[key] != val:
                    raise Contradiction(key)
            for key, targets in oe.rel.items():
                se = self.table_entry_list[self._find(i)]
                se.rel.setdefault(key, set()).update(self._ensure(t) for t in targets)
        self._propagate()

    def _named(self, node):
        """Replace d_<id> leaves by a name or function term denoting the entity.

        Nested attitude tables have their own id space, so a proposition that
        is moved into one must refer to entities by name ("mary") or by a path
        from a named entity ("father(you)"), not by parent id.  Entities with
        no such description keep their d_<id>.
        """
        if not isinstance(node, TreeNode):
            return node
        if not node.children and node.name.startswith("d_") and node.name[2:].isdigit():
            term = self._term_for(int(node.name[2:]))
            return term if term is not None else node
        return TreeNode(node.name, [self._named(c) for c in node.children])

    def _is_rel(self, node):
        return node.name in self.relations and len(node.children) == 1

    def _split_rel(self, eq):
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
        self._version += 1

    def copy_table(self, other):
        self._restore(other._snapshot())

    def _consistent(self, fn):
        # Note: if fn() merely returns False (fact not representable) this still
        # counts as consistent; _refute relies on that to answer "unknown"
        # rather than a wrong True/False.
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
        self._version += 1
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

    def _resolve(self, node, create=CREATE_NONE, top=True):
        if (node.name.startswith("d_") and not node.children
                and node.name[2:].isdigit()):
            i = self._find(int(node.name[2:]))
            if i not in self.table_entry_list:
                # id from another table (e.g. a nested attitude table)
                if create < CREATE_LINK:
                    return []
                self.table_entry_list[i] = TableEntry()
                self.curr = max(self.curr, i + 1)
                self._version += 1
            return [i]
        if not node.children:
            for key, ent in self.table_entry_list.items():
                if node in ent.entry:
                    return [key]
            if create < CREATE_ALL:
                return []
            out = self.create()
            self.table_entry_list[out].entry.append(node)
            return [out]
        if len(node.children) != 1:
            return []
        owners = self._resolve(node.children[0], create, top=False)
        if node.name in self.functions:
            out = []
            for owner in owners:
                ent = self.table_entry_list[self._find(owner)]
                if node.name in ent.attr:
                    out.append(self._find(ent.attr[node.name]))
                elif create >= CREATE_LINK and len(owners) == 1:
                    new = self.create()
                    ent.attr[node.name] = new
                    out.append(new)
            return list(dict.fromkeys(out))
        if node.name in self.relations:
            out = []
            for owner in owners:
                out.extend(sorted(self._targets(owner, node.name)))
            out = list(dict.fromkeys(out))
            if not out and not top and create >= CREATE_PHANTOM and len(owners) == 1:
                new = self.create()
                self.table_entry_list[self._find(owners[0])].rel.setdefault(
                    node.name, set()
                ).add(new)
                out = [new]
            return out
        return []

    def create_node(self, node, create=CREATE_NONE):
        ids = self._resolve(node, create, top=False)
        return ids[0] if len(ids) == 1 else None

    def equate_id(self, a, b, explicit=False):
        a, b = self._find(a), self._find(b)
        if a == b:
            return a
        if b in self._targets(a, NE):
            raise Contradiction("known to be different")
        if not explicit and b in self._targets(a, SOFT):
            raise Contradiction("assumed different (different names)")
        keep, drop = min(a, b), max(a, b)
        self._version += 1
        q = self.table_entry_list.pop(drop)
        self.alias[drop] = keep

        p = self.table_entry_list[keep]
        for e in q.entry:
            if e not in p.entry:
                p.entry.append(e)
        for name, targets in q.rel.items():
            p.rel.setdefault(name, set()).update(targets)
        for name, sub_q in q.know.items():
            if name not in p.know:
                p.know[name] = copy.deepcopy(sub_q)
            else:
                _merge_tables(p.know[name], sub_q)

        for key, val in q.attr.items():
            keep = self._find(keep)
            p = self.table_entry_list[keep]
            if key not in p.attr:
                p.attr[key] = val
            elif key in self.functions:
                self.equate_id(p.attr[key], val)
            elif p.attr[key] != val:
                raise Contradiction(key)

        keep = self._find(keep)
        if keep in self._targets(keep, NE):
            raise Contradiction("known to be different")
        soft = self.table_entry_list[keep].rel.get(SOFT)
        if soft:
            soft -= {i for i in soft if self._find(i) == keep}
        return keep

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
        if eq.name == "not" and len(eq.children) == 1:
            return self._assert_expr(eq.children[0], not positive, create)

        if eq.name in self.attitudes and len(eq.children) == 2:
            if not positive:
                return False
            who = self.create_node(eq.children[0], create)
            if who is None:
                return False
            prop = eq.children[1]
            if eq.name in self.factive:
                if not self._assert_expr(prop, True, create):
                    return False
            if self.depth >= self.MAX_DEPTH:
                return True          # too deeply nested: stop (avoids endless know-that-know-that)
            prop = self._named(prop)
            ent = self.table_entry_list[self._find(who)]
            for name in [eq.name] + sorted(self._entailed(eq.name)):
                if name == eq.name and name in self.factive:
                    # factive: the table is just the current world, so rebuild it
                    # (otherwise it goes stale when later facts are learned)
                    ent.know[name] = _make_nested_table(self, name)
                elif name not in ent.know:
                    if eq.name in self.factive and eq.name in ent.know:
                        # x knows P => x thinks everything x knows: seed the
                        # weaker table from the stronger one (same id space)
                        ent.know[name] = copy.deepcopy(ent.know[eq.name])
                        ent.know[name].seeded = True
                    else:
                        ent.know[name] = _make_nested_table(self, name)
                elif getattr(ent.know[name], "seeded", False) and eq.name in ent.know:
                    ent.know[name]._absorb(ent.know[eq.name])
                if not ent.know[name].context(prop):
                    return False
            return True

        if eq.name == "equal" and len(eq.children) == 2:
            if self._is_rel(eq.children[0]) or self._is_rel(eq.children[1]):
                sp = self._split_rel(eq)
                if sp is None or not positive:
                    return False
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
        if eq.name == "not" and len(eq.children) == 1:
            v = self._eval(eq.children[0], create)
            return None if v is None else (not v)

        if eq.name in self.attitudes and len(eq.children) == 2:
            who = self.create_node(eq.children[0], create)
            if who is None:
                return None
            ent = self.table_entry_list[self._find(who)]
            if eq.name not in ent.know:
                return None
            return ent.know[eq.name].question(self._named(eq.children[1]))

        if eq.name == "equal" and len(eq.children) == 2:
            if self._is_rel(eq.children[0]) or self._is_rel(eq.children[1]):
                sp = self._split_rel(eq)
                if sp is None:
                    return None
                ent, term = sp
                x = self.create_node(ent, create)
                owners = self._resolve(term.children[0], create)
                if x is None or not owners:
                    return None
                x = self._find(x)
                if any(x in self._targets(o, term.name) for o in owners):
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
            return None

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
        for var, ident in env.items():
            eq = replace(eq, TreeNode(var), TreeNode(f"d_{ident}"))
        return eq

    def _answers(self, body, env):
        body_vars = self._expr_vars(body)
        used = [v for v in ALL_VARS if v in env and v in body_vars]
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
                self._assert_expr(
                    self._bind(rule[1], env), True, CREATE_LINK
                )

    def _signature(self):
        return str(self)

    def _propagate(self):
        # NOTE: product(ids, repeat=len(variables)) grows as n**k, so rules
        # with many variables get slow on large tables.
        for _ in range(self.MAX_ROUNDS):
            self._apply_distinct()
            before = self._signature()
            ids = list(self.table_entry_list.keys())
            for rule, variables in self.inference_rules:
                for combo in itertools.product(ids, repeat=len(variables)):
                    if any(i not in self.table_entry_list for i in combo):
                        continue
                    self.process_rule(rule, dict(zip(variables, combo)))
            if self._signature() == before:
                return
        raise RuntimeError("rules did not reach a fixed point")

    def process_all_rule(self):
        snap = self._snapshot()
        try:
            self._propagate()
            return []
        except Contradiction:
            self._restore(snap)
            return None

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def context(self, eq):
        if not self._wellformed(eq):
            return None
        snap = self._snapshot()
        try:
            if not self._assert_expr(eq, True, CREATE_PHANTOM):
                self._restore(snap)
                return None
            self._propagate()
            return True
        except Contradiction:
            self._restore(snap)
            return None

    def question(self, eq):
        if eq.name == "question":
            eq = eq.children[0]
        if not self._wellformed(eq):
            return None
        snap = self._snapshot()
        try:
            return self._decide(eq)
        except Contradiction:
            return None
        finally:
            self._restore(snap)

    def _decide(self, eq):
        self._propagate()
        self._eval(eq, CREATE_ALL)
        self._propagate()
        v = self._eval(eq, CREATE_ALL)
        if v is not None:
            return v
        return self._refute(eq)

    def _refute(self, eq):
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
        if eq.name == "question":
            return self.question(eq)
        if eq.name != "who" or not eq.children:
            return None
        snap = self._snapshot()
        try:
            self._propagate()
            target = eq.children[0]
            if self._is_rel(target):
                owners = self._resolve(target.children[0], CREATE_ALL)
                if not owners:
                    return None
                self._propagate()
                outs = sorted({
                    m
                    for o in owners
                    for m in self._targets(self._find(o), target.name)
                })
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
