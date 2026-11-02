from .base import *
import itertools
import copy
from .decode import *


class Contradiction(Exception):
    """Raised internally when a statement conflicts with what the table holds."""


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


def _as_node(x):
    """Entries are names (str); aliases are trees. Never wrap a TreeNode twice."""
    return x if isinstance(x, TreeNode) else TreeNode(x)


def _unique(items):
    """Order-preserving de-duplication that only needs ==, not hashing."""
    out = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


class TableEntry:
    def __init__(
        self,
        entry=None,
        father=None,
        mother=None,
        sister=None,
        brother=None,
        daughter=None,
        son=None,
        crush=None,
        killed=None,
        gender=None,
        emotional_state=None,
        living_state=True,
    ):
        # copies everywhere: the old mutable defaults ([True, False]) and
        # `self.alias = entry` shared one list between entries
        self.entry = list(entry) if entry else []
        self.gender = list(gender) if gender is not None else [True, False]
        self.emotional_state = (
            list(emotional_state) if emotional_state is not None else [True, False]
        )
        self.living_state = living_state
        self.father = father
        self.mother = mother
        self.killed = list(killed) if killed else []
        self.alias = list(self.entry)
        self.crush = list(crush) if crush else []
        self.sister = list(sister) if sister else []
        self.brother = list(brother) if brother else []
        self.daughter = list(daughter) if daughter else []
        self.son = list(son) if son else []
        self.process()

    def process(self):
        """Narrow gender using the names this entity goes by."""
        for item in self.entry:
            out = gender(_as_node(item))
            if out == "male":
                self.gender = [g for g in self.gender if g is True]
            elif out == "female":
                self.gender = [g for g in self.gender if g is False]
        return self

    def __repr__(self):
        line = "+" + "-" * 60 + "+"
        s = line + "\n"
        s += f"| Father           : {self.father}\n"
        s += f"| Mother           : {self.mother}\n"
        s += f"| Sister           : {self.sister}\n"
        s += f"| Brother          : {self.brother}\n"
        s += f"| Daughter         : {self.daughter}\n"
        s += f"| Son              : {self.son}\n"
        s += f"| Gender           : {self.gender}\n"
        s += f"| Living State     : {self.living_state}\n"
        s += f"| Killed           : {self.killed}\n"
        s += line + "\n"
        s += "| Entries\n"
        if len(self.entry) == 0:
            s += "|   <empty>\n"
        else:
            for eq in self.entry:
                s += f"|   {eq}\n"
        s += line
        return s

    def __eq__(self, other):
        if not isinstance(other, TableEntry):
            return NotImplemented
        return (
            set(self.gender) == set(other.gender)
            and set(self.emotional_state) == set(other.emotional_state)
            and self.living_state == other.living_state
            and all(e in other.entry for e in self.entry)
            and all(e in self.entry for e in other.entry)
        )

    __hash__ = None


class Table:
    MAX_ALIAS_COMBOS = 1000

    def __init__(self):
        self.table_entry_list = {}
        self.merged = {}              # merged-away id -> surviving id
        self.curr = 0
        self.create_new_nodes = True

    # ------------------------------------------------------------------
    # state: ids, snapshots
    # ------------------------------------------------------------------
    @property
    def id_system(self):
        """Merge groups, smallest id (the survivor) first. Kept for display."""
        groups = {}
        for old in self.merged:
            groups.setdefault(self.normalize_id(old), []).append(old)
        return [sorted([root] + olds) for root, olds in sorted(groups.items())]

    def normalize_id(self, number):
        while number in self.merged:
            number = self.merged[number]
        return number

    def _normalized(self, ids):
        return sorted({self.normalize_id(i) for i in ids})

    def _snapshot(self):
        return copy.deepcopy((self.table_entry_list, self.merged, self.curr))

    def _restore(self, snap):
        self.table_entry_list, self.merged, self.curr = snap

    def _atomic(self, fn):
        """Run fn; if it fails (None / contradiction) the table is rolled back."""
        snap = self._snapshot()
        try:
            out = fn()
        except Contradiction:
            out = None
        if out is None:
            self._restore(snap)
        return out

    def _check(self):
        """Raise Contradiction if any entity has become impossible."""
        for ent in self.table_entry_list.values():
            ent.process()
            if not ent.gender or not ent.emotional_state:
                raise Contradiction("no possible gender / feeling left")

    def create(self, entry=None):
        ident = self.curr
        self.table_entry_list[ident] = TableEntry(entry=entry)
        self.curr += 1
        return ident

    # ------------------------------------------------------------------
    # path resolution: "john's mother's sister"  ->  ids
    # ------------------------------------------------------------------
    def _lookup_name(self, name, create):
        for key, ent in self.table_entry_list.items():
            if name in ent.entry:
                return key
        if not create:
            return None
        return self.create([name])

    def _parent_id(self, key, relation):
        ident = getattr(self.table_entry_list[key], relation)
        return None if ident is None else self.normalize_id(ident)

    def _parent(self, curr, relation, create):
        ent = self.table_entry_list[curr]
        ident = self._parent_id(curr, relation)
        if ident is None and create:
            ident = self.create()
            self.table_entry_list[ident].gender = [relation == "father"]
            setattr(ent, relation, ident)
        return [] if ident is None else [ident]

    def _siblings(self, curr, relation, create):
        ent = self.table_entry_list[curr]
        male = relation == "brother"
        mine = (self._parent_id(curr, "father"), self._parent_id(curr, "mother"))
        found = set(self._normalized(getattr(ent, relation)))
        if None not in mine:
            for key, other in self.table_entry_list.items():
                if (
                    key != curr
                    and other.gender == [male]
                    and (
                        self._parent_id(key, "father"),
                        self._parent_id(key, "mother"),
                    ) == mine
                ):
                    found.add(key)
        found.discard(curr)
        setattr(ent, relation, sorted(found))
        if not found and create:
            found = {self._phantom_sibling(curr, male)}
        return sorted(found)

    def _phantom_sibling(self, curr, male):
        """Someone has to be 'my sister': invent her, with the same parents."""
        ent = self.table_entry_list[curr]
        person = self.create()
        self.table_entry_list[person].gender = [male]
        for relation, parent_is_male in (("father", True), ("mother", False)):
            parent = self._parent_id(curr, relation)
            if parent is None:
                parent = self.create()
                self.table_entry_list[parent].gender = [parent_is_male]
                setattr(ent, relation, parent)
            setattr(self.table_entry_list[person], relation, parent)
        getattr(ent, "brother" if male else "sister").append(person)
        return person

    def _children(self, curr, relation, create):
        ent = self.table_entry_list[curr]
        male = relation == "son"
        found = set(self._normalized(getattr(ent, relation)))
        for key, other in self.table_entry_list.items():
            if (
                key != curr
                and other.gender == [male]
                and curr in (
                    self._parent_id(key, "father"),
                    self._parent_id(key, "mother"),
                )
            ):
                found.add(key)
        found.discard(curr)
        setattr(ent, relation, sorted(found))
        if not found and create:
            person = self.create()
            child = self.table_entry_list[person]
            child.gender = [male]          # the old code forgot this when the parent's gender was known
            if ent.gender == [True]:
                child.father = curr
            elif ent.gender == [False]:
                child.mother = curr
            getattr(ent, relation).append(person)
            found = {person}
        return sorted(found)

    def find_human(self, curr_id=None, step=None, create_new=True):
        """
        Follow a path of relations from an entity (or from a name when
        curr_id is None: step[0] is then the name). Returns a list of ids.
        create_new=False never adds anything to the table.
        """
        step = list(step) if step else []
        create_new = create_new and self.create_new_nodes
        if curr_id is None:
            if not step:
                return []
            curr_id = self._lookup_name(step[0], create_new)
            if curr_id is None:
                return []
            step = step[1:]
        curr_id = self.normalize_id(curr_id)
        if curr_id not in self.table_entry_list:
            return []
        if not step:
            return [curr_id]

        self.table_entry_list[curr_id].process()
        relation, rest = step[0], step[1:]
        if relation in ("father", "mother"):
            found = self._parent(curr_id, relation, create_new)
        elif relation in ("brother", "sister"):
            found = self._siblings(curr_id, relation, create_new)
        elif relation in ("son", "daughter"):
            found = self._children(curr_id, relation, create_new)
        else:
            return []                       # not a relation we can follow
        out = []
        for ident in found:
            out += self.find_human(ident, rest, create_new)
        return _unique(out)

    def find_id(self, eq, create=True):
        """Ids an actor expression refers to; create=False is a pure lookup."""
        root = eq
        names = []
        while len(root.children) != 0:
            names.append(root.name)
            root = root.children[0]
        names.append(root.name)
        names.reverse()
        ids = self.find_human(None, names, create)
        return _unique(self.normalize_id(i) for i in ids)

    def _ids(self, item):
        """Non-creating lookup for queries; None if nothing is known."""
        if item.name == "id":
            return [self.normalize_id(int(item.children[0].name))]
        if not valid_actor_eq(item):
            return None
        return self.find_id(item, create=False) or None

    # ------------------------------------------------------------------
    # merging
    # ------------------------------------------------------------------
    def equate_id(self, a, b):
        """Merge two entities in place (smaller id survives). Raises Contradiction."""
        a, b = self.normalize_id(a), self.normalize_id(b)
        if a == b:
            return a
        keep, drop = min(a, b), max(a, b)
        p = self.table_entry_list[keep]
        q = self.table_entry_list.pop(drop)
        self.merged[drop] = keep

        if p.living_state != q.living_state:
            raise Contradiction("one is dead, the other alive")
        p.entry = _unique(p.entry + q.entry)
        p.alias = _unique(p.alias + q.alias)
        p.crush = _unique(p.crush + q.crush)
        p.gender = [g for g in p.gender if g in q.gender]
        p.emotional_state = [g for g in p.emotional_state if g in q.emotional_state]
        p.killed = self._normalized(p.killed + q.killed)
        for relation in ("sister", "brother", "daughter", "son"):
            merged = set(
                self.normalize_id(i)
                for i in getattr(p, relation) + getattr(q, relation)
            ) - {keep, drop}
            setattr(p, relation, sorted(merged))
        p.process()
        if not p.gender or not p.emotional_state:
            raise Contradiction("no possible gender / feeling left")

        for relation in ("father", "mother"):
            mine, theirs = getattr(p, relation), getattr(q, relation)
            if mine is None:
                setattr(p, relation, theirs)
            elif theirs is not None:
                self.equate_id(mine, theirs)      # same person -> same parents
        return self.normalize_id(keep)

    def adjust_id(self):
        """Kept for compatibility: merging is now done in place, nothing to fix."""
        return None

    def process_entry(self):
        """Derive what follows from parents / children / siblings."""
        ids = list(self.table_entry_list.keys())
        for ent in self.table_entry_list.values():
            ent.process()
        for key in ids:
            ent = self.table_entry_list[key]
            for key2 in ids:
                if key == key2:
                    continue
                other = self.table_entry_list[key2]
                # key is a parent of key2
                if key in (
                    self._parent_id(key2, "father"),
                    self._parent_id(key2, "mother"),
                ):
                    if other.gender == [True]:
                        ent.son.append(key2)
                    elif other.gender == [False]:
                        ent.daughter.append(key2)
                # key2 lists key as its child, so key2 is a parent of key
                if key in self._normalized(other.son) or key in self._normalized(other.daughter):
                    if other.gender == [True] and ent.father is None:
                        ent.father = key2
                    elif other.gender == [False] and ent.mother is None:
                        ent.mother = key2
                # same two parents: siblings
                mine = (self._parent_id(key, "father"), self._parent_id(key, "mother"))
                theirs = (self._parent_id(key2, "father"), self._parent_id(key2, "mother"))
                if None not in mine and mine == theirs:
                    if other.gender == [True]:
                        ent.brother.append(key2)
                    elif other.gender == [False]:
                        ent.sister.append(key2)
        for key in ids:
            ent = self.table_entry_list[key]
            for relation in ("brother", "sister", "daughter", "son"):
                setattr(
                    ent, relation,
                    [i for i in self._normalized(getattr(ent, relation)) if i != key],
                )

    def equate_eq(self, a, b):
        """Declare two actor expressions to be the same person."""
        if not valid_actor_eq(a) or not valid_actor_eq(b):
            return None

        def run():
            p = self.find_id(a)
            q = self.find_id(b)
            if not p or not q:
                return None
            if set(p) == set(q):
                return 0
            pair = id_helper(p, q)
            if pair is None:
                return None
            self.process_entry()
            merged = self.equate_id(*pair)
            self._check()
            return merged

        return self._atomic(run)

    # ------------------------------------------------------------------
    # statements
    # ------------------------------------------------------------------
    def equate_bool_eq(self, eq):
        """Record a one-place fact: live / die / girl / boy / happy / sad."""
        if len(eq.children) != 1 or not valid_actor_eq(eq.children[0]):
            return None

        def run():
            ids = self.find_id(eq.children[0])
            if not ids:
                return None
            for number in ids:
                ent = self.table_entry_list[number]
                if eq.name == "live":
                    if not ent.living_state:
                        return None
                elif eq.name == "die":
                    ent.living_state = False
                elif eq.name in ("girl", "boy"):
                    wanted = eq.name == "boy"
                    if wanted not in ent.gender:     # also catches "mary is a boy"
                        return None
                    ent.gender = [wanted]
                elif eq.name in ("happy", "sad"):
                    wanted = eq.name == "happy"
                    if wanted not in ent.emotional_state:
                        return None
                    ent.emotional_state = [wanted]
                else:
                    return None                      # unknown predicate: not recorded
            self._check()
            return ids

        return self._atomic(run)

    def equate_verb(self, eq):
        if eq.name in ["kill"] and len(eq.children) == 2:
            def run():
                index = self.find_id(eq.children[0])
                index2 = self.find_id(eq.children[1])
                if len(index) != 1 or len(index2) == 0:
                    return None
                killer = self.table_entry_list[index[0]]
                killer.killed = self._normalized(killer.killed + index2)
                return index

            return self._atomic(run)
        return None

    def equate(self, eq):
        """Tell the table a fact. Returns None (and changes nothing) if it fails."""
        def run():
            if eq.name == "equal" and len(eq.children) == 2:
                return self.equate_eq(*eq.children)
            if eq.name == "kill" and len(eq.children) == 2:
                c = self.equate_verb(eq)
                if c is None:
                    return None
                d = self.equate_bool_eq(eq.children[1].fx("die"))
                if d is None:
                    return None
                return c
            return self.equate_bool_eq(eq)

        return self._atomic(run)

    # ------------------------------------------------------------------
    # queries (never change the table)
    # ------------------------------------------------------------------
    def bool_eq(self, eq):
        """True / False / None (unknown)."""
        if eq.name == "equal" and len(eq.children) == 2:
            sets = [self._ids(c) for c in eq.children]
            if any(s is None for s in sets):
                return None
            a, b = set(sets[0]), set(sets[1])
            if a & b:
                return True if len(a) == 1 or len(b) == 1 else None
            return False

        if len(eq.children) == 1:
            ids = self._ids(eq.children[0])
            if ids is None:
                return None
            values = []
            for number in ids:
                ent = self.table_entry_list[number]
                if eq.name == "live":
                    values.append(ent.living_state)
                elif eq.name == "die":
                    values.append(not ent.living_state)
                elif eq.name == "girl" and len(ent.gender) == 1:
                    values.append(ent.gender[0] is False)
                elif eq.name == "boy" and len(ent.gender) == 1:
                    values.append(ent.gender[0] is True)
                elif eq.name in ("happy", "sad") and len(ent.emotional_state) == 1:
                    values.append(ent.emotional_state[0] is (eq.name == "happy"))
            return values[0] if len(set(values)) == 1 else None

        if len(eq.children) == 2 and eq.name == "kill":
            killers, victims = (self._ids(c) for c in eq.children)
            if killers is None or victims is None:
                return None
            killed = set(self._normalized(self.table_entry_list[killers[0]].killed))
            return bool(killed) and set(victims) <= killed
        return None

    def lambda_compute(self, eq):
        """lambda(var, condition, if_true, if_false): every entity answers once."""
        if eq.name != "lambda":
            return []
        var, condition, if_true, if_false = eq.children[:4]
        output = []
        for key in list(self.table_entry_list.keys()):   # queries must not resize the dict they iterate
            marker = TreeNode(str(key)).fx("id")
            out = self.bool_eq(replace(condition, var, marker))
            if out is True:
                output.append(replace(if_true, var, marker))
            elif out is False:
                output.append(replace(if_false, var, marker))

        output = [
            item for item in output
            if item != TreeNode("DELETE") and not contain2(item, TreeNode("DELETE"))
        ]
        self.alias_gen()                                  # once, not once per answer
        expanded = []
        for item in output:
            expanded += self.rm_eq_id(item, refresh=False)
        output = _unique(expanded)
        return output[0] if len(output) == 1 else output

    # ------------------------------------------------------------------
    # names for ids
    # ------------------------------------------------------------------
    def alias_gen(self):
        """Give every entity names like "my mother", built from its relatives."""
        relations = ["mother", "father", "son", "daughter", "sister", "brother"]
        for ent in self.table_entry_list.values():
            ent.alias = _unique(_as_node(e) for e in ent.entry)
        for _ in range(2):
            snapshot = {k: list(v.alias) for k, v in self.table_entry_list.items()}
            for key, aliases in snapshot.items():
                if not aliases:
                    continue
                base = min(aliases, key=lambda node: len(str_form(node)))
                for relation in relations:
                    targets = self.find_human(key, [relation], False)
                    if len(targets) != 1:
                        continue
                    target = targets[0]
                    new_alias = base.fx(relation)
                    if (
                        target in self.table_entry_list
                        and new_alias not in self.table_entry_list[target].alias
                    ):
                        self.table_entry_list[target].alias.append(new_alias)

    def find_from_id(self, number):
        number = self.normalize_id(number)
        if number not in self.table_entry_list:
            return []
        return _unique(_as_node(a) for a in self.table_entry_list[number].alias)

    def rm_eq_id(self, eq, refresh=True):
        """Replace id(n) nodes by names / descriptions of entity n."""
        if refresh:
            self.alias_gen()
        id_nodes = collect_id_nodes(eq)
        if not id_nodes:
            return [eq]
        choices = []
        for node in id_nodes:
            aliases = self.find_from_id(int(node.children[0].name))
            choices.append(aliases or [node])
        outputs = []
        for combo in itertools.islice(
            itertools.product(*choices), self.MAX_ALIAS_COMBOS
        ):
            new_eq = eq
            for old_node, new_node in zip(id_nodes, combo):
                new_eq = replace(new_eq, old_node, new_node)
            outputs.append(new_eq)
        return outputs

    def __repr__(self):
        s = [str(self.id_system)] if self.merged else []
        for key, item in self.table_entry_list.items():
            s.append(f"id {key}")
            s.append(str(item))
            s.append("")
        return "\n".join(s)
