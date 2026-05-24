from .base import *
import itertools
import copy
from .decode import *
def valid_actor_eq(eq):
    try:
        eq = actor_to_phrase(eq)
    except:
        return False
    return True
class Table:
    def __init__(self):
        self.id_system = []
        self.table_entry_list = {}
        self.curr = 0
    def find_human(self, curr_id=None, step=[], create_new=True):
        item = None
        if curr_id is not None:
            if step == []:
                return curr_id
            item = self.table_entry_list[curr_id]
            for item2 in item.entry:
                if gender(TreeNode(item2)) == "female":
                    self.table_entry_list[curr_id].gender = [False]
                if gender(TreeNode(item2))   == "male":
                    self.table_entry_list[curr_id].gender = [True]
        for item3 in ["son", "daughter"]:
            if step[0] == item3:
                out = []
                for key, element in self.table_entry_list.items():
                    if key == curr_id:
                        continue
                    for item2 in ["mother", "father"]:
                        if self.find_human(key, [item2], False) == curr_id and (True if item3 == "son" else False) in element.gender:
                            out.append(key)
                if len(out) == 0:
                    if item.gender == [True]:
                        person = self.create()
                        person.father = curr_id
                        return person
                    if item.gender == [False]:
                        person = self.create()
                        self.table_entry_list[person].gender = [True if item3 == "son" else False]
                        self.table_entry_list[person].mother = curr_id
                        return person
                if len(out) == 1:
                    return self.find_human(out[0], step[1:])
                else:
                    return None
        if step[0] == "father":
            if item.father is None and create_new:
                item.father = self.create()
                self.table_entry_list[item.father].gender = [True]
            if item.father is not None:
                return self.find_human(item.father, step[1:])
        if step[0] == "mother":
            if item.mother is None and create_new:
                item.mother = self.create()
                self.table_entry_list[item.mother].gender = [True]
            if item.mother is not None:
                return self.find_human(item.mother, step[1:])
        for key, item in self.table_entry_list.items():
            if step[0] in item.entry:
                return self.find_human(key, step[1:])
        if create_new is False:
            return None
        curr_id = self.create()
        self.table_entry_list[curr_id].entry = [step[0]]
        return self.find_human(curr_id, step[1:])
    def create(self):
        out = TableEntry()
        self.table_entry_list[self.curr] = out
        self.curr = self.curr+1
        return self.curr - 1
    def find_id(self,eq):
        root = eq
        lst = []
        while len(root.children) != 0:
            lst.append(root.name)
            root = root.children[0]
        lst.append(root.name)
        lst = lst[::-1]
        return self.find_human(None,lst)
    def equate_id(self, a, b):
        n = TableEntry()
        p, q = self.table_entry_list[a], self.table_entry_list[b]
        n.entry = list(set(p.entry + q.entry))
        n.gender = list(set(p.gender) & set(q.gender))
        n.living_state = p.living_state and q.living_state
        n.emotional_state = list(set(p.emotional_state) & set(q.emotional_state))
        if p.father is not None and q.father is not None and p.father != q.father:
            n.father = self.equate_id(p.father, q.father)
        elif p.father is not None:
            n.father = p.father
        elif q.father is not None:
            n.father = q.father            
        if p.mother is not None and q.mother is not None and p.mother != q.mother:
            n.mother = self.equate_id(p.mother, q.mother)
        elif p.mother is not None:
            n.mother = p.mother
        elif q.father is not None:
            n.mother = q.mother
        g = self.create()
        self.id_system.append(list(sorted([g,a,b])))
        self.table_entry_list[g] = n
        self.table_entry_list.pop(a,None)
        self.table_entry_list.pop(b,None)
        return g
    def equate_eq(self, a, b):
        if not valid_actor_eq(a) or not valid_actor_eq(b):
            return None
        p = self.find_id(a)
        q = self.find_id(b)
        out = self.equate_id(p, q)
        self.adjust_id()
        return out
    def equate_bool_eq(self, eq):
        if len(eq.children) != 1 or not valid_actor_eq(eq.children[0]):
            return None
        number = self.find_id(eq.children[0])
        if eq.name == "live":
            if not self.table_entry_list[number].living_state:
                return None
        if eq.name == "die":
            self.table_entry_list[number].living_state = False
        if eq.name == "girl":
            if set(self.table_entry_list[number].gender) == set([True, False]) or self.table_entry_list[number].gender == [False]:
                self.table_entry_list[number].gender = [False]
            else:
                return None
        if eq.name == "boy":
            if set(self.table_entry_list[number].gender) == set([True, False]) or self.table_entry_list[number].gender == [True]:
                self.table_entry_list[number].gender = [True]
            else:
                return None
        return number
    def lambda_compute(self, eq):
        if eq.name == "lambda":
            output = []
            for key, item in self.table_entry_list.items():
                c = replace(eq.children[1], eq.children[0], TreeNode(str(key)).fx("id"))
                s = replace(eq.children[2], eq.children[0], TreeNode(str(key)).fx("id"))
                u = replace(eq.children[3], eq.children[0], TreeNode(str(key)).fx("id"))
                out = self.bool_eq(c)
                if out is True:
                    output.append(s)
                elif out is False:
                    output.append(u)
            output = list(set(output))
            if len(output) == 1:
                return output[0]
            return []
        return []
    def bool_eq(self, eq):
        number_lst = []
        number = None
        if eq.name == "equal":
            for item in eq.children:
                if item.name == "id":
                    number_lst.append(int(item.children[0]))
                elif valid_actor_eq(item):
                    number_lst.append(self.find_id(item))
                else:
                    return None
            if number_lst[0] == number_lst[1]:
                return True
            else:
                return False
        elif len(eq.children) == 1:
            item = eq.children[0]
            if item.name == "id":
                number = int(item.children[0])
            elif valid_actor_eq(item):
                number = self.find_id(item)
            else:
                return None
        else:
            return None
        if eq.name == "live":
            return self.table_entry_list[number].living_state
        if eq.name == "die":
            return not self.table_entry_list[number].living_state
        if eq.name == "girl":
            if len(self.table_entry_list[number].gender) == 1:
                return not self.table_entry_list[number].gender[0]
        if eq.name == "boy":
            if len(self.table_entry_list[number].gender) == 1:
                return self.table_entry_list[number].gender[0]
        return None
    def equate(self, eq):
        a = self.equate_bool_eq(eq)
        b = None
        if eq.name == "equal":
            b = self.equate_eq(*eq.children)
        if a is not None:
            return a
        if b is not None:
            return b
        return None
    def adjust_id(self):
        for item in self.id_system:
            for item2 in item[1:]:
                if item2 in self.table_entry_list.keys():
                    self.table_entry_list[item[0]] = self.table_entry_list[item2]
                    self.table_entry_list.pop(item2, None)
                for key, item3 in self.table_entry_list.items():
                    if item3.father == item2:
                        self.table_entry_list[key].father = item[0]
                    if item3.mother == item2:
                        self.table_entry_list[key].mother = item[0]
        self.id_system = []
    def __repr__(self):
        s = None
        if self.id_system == []:
            s = []
        else:
            s = [str(self.id_system)]
        for key, item in self.table_entry_list.items():
            s.append(f"id {key}")
            s.append(str(item))
            s.append("")
        return "\n".join(s)
class TableEntry:
    def __init__(
        self,
        entry=[],
        father=None,
        mother=None,
        crush=[],
        killed=[],
        gender=[True, False],
        emotional_state=[True, False],
        living_state=True,
    ):

        self.entry = entry
        self.gender = gender
        self.emotional_state = emotional_state
        self.living_state = living_state
        self.father = father
        self.mother = mother
        self.killed = killed
        self.crush = crush
        self.detect_gender()
    def detect_gender(self):
        for item in self.entry:
            out = gender(item)
            if out == "male":
                self.gender = [True]
            elif out == "female":
                self.gender = [False]
                
        return self

    def __repr__(self):

        line = "+" + "-" * 60 + "+"

        s = line + "\n"

        s += f"| Father           : {self.father}\n"
        s += f"| Mother           : {self.mother}\n"

        s += f"| Gender           : {self.gender}\n"
        # s += f"| Emotional State  : {self.emotional_state}\n"
        s += f"| Living State     : {self.living_state}\n"

        # s += f"| Crush            : {self.crush}\n"
        # s += f"| Killed           : {self.killed}\n"

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
        lst = [(set(item.gender),set(item.emotional_state),set(item.living_state),set(item.entry)) for item in [self, other]]
        return lst[0] == lst[1]

def merge_state(values):

    if not values:
        return []

    final = set(values[0])

    for item in values[1:]:
        final &= set(item)

    return list(final)


def get_equivalents(node, table):

    for entry in table:

        if node in entry.entry:
            return entry.entry

    return [node]


def expand(node, table):

    if not node.children:
        return get_equivalents(node, table)

    child_expanded = [expand(c, table) for c in node.children]

    results = []

    for combo in itertools.product(*child_expanded):

        base = TreeNode(node.name, list(combo))

        base.gender = merge_state(
            [c.gender for c in combo]
        )

        base.emotional_state = merge_state(
            [c.emotional_state for c in combo]
        )

        base.living_state = merge_state(
            [c.living_state for c in combo]
        )

        eqs = get_equivalents(base, table)

        for eq in eqs:

            eq.gender = merge_state(
                [eq.gender, base.gender]
            )

            eq.emotional_state = merge_state(
                [eq.emotional_state, base.emotional_state]
            )

            eq.living_state = merge_state(
                [eq.living_state, base.living_state]
            )

            results.append(eq)

    return list(set(results))


def infer(table):

    new_table = []

    for entry in table:

        expanded = []

        for expr in entry.entry:
            expanded.extend(expand(expr, table))

        entry.entry = list(set(expanded))

        new_table.append(entry)

    return [item.detect_gender() for item in new_table]


def merge_tables(table):

    merged = []

    for t in table:

        found = None

        for m in merged:
            if set(t.entry) & set(m.entry):
                found = m
                break

        if found:

            found.entry = list(
                set(found.entry + t.entry)
            )

            found.gender = merge_state(
                [found.gender, t.gender]
            )

            found.emotional_state = merge_state(
                [found.emotional_state, t.emotional_state]
            )

            found.living_state = merge_state(
                [found.living_state, t.living_state]
            )
        else:
            merged.append(t)
    return merged
def equal_a_b(table, a, b):
    for item in table:
        if a in item.entry and b in item.entry:
            return [True]
    return [False]
def condition_check(table, condition):
    if condition.name == "equal":
        return equal_a_b(table, a, b)
    for item in table:
        if condition.children[0] in item.entry:
            if condition.name in ["live", "die"] and set(item.living_state) != set([True, False]):
                if condition.name == "live":
                    return item.living_state
                else:
                    return [not item.living_state[0]]
            if condition.name in ["girl", "boy"] and set(item.gender) != set([True, False]):
                if condition.name == "boy":
                    return item.gender
                else:
                    return [not item.gender[0]]
    if condition.name == "live":
        return [True]
    if condition.name == "die":
        return [False]
    return [True, False]
def search_human(eq):
    output = []
    def helper(eq):
        if contain2(eq, "lambda"):
            for item in eq.children:
                helper(item)
            return
        if valid_actor_eq(eq):
            output.append(copy.deepcopy(eq))
        for item in eq.children:
            helper(item)
    helper(eq)
    return list(set(output))
def lambda_search(table, var, condition, satisfy, unsatisfy):
    output = []
    for item in table:
        for item2 in item.entry:
            c = condition_check(table, replace(condition, var, item2))
            if c == [True]:
                output.append(replace(satisfy, var, item2))
            elif c == [False]:
                output.append(replace(unsatisfy, var, item2))
    return list(set(output))
def query(table, eq):
    if eq.name == "lambda":
        return lambda_search(*([table]+eq.children))
    return []

