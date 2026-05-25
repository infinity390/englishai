from .base import *
import itertools
import copy
from .decode import *
def collect_id_nodes(node):
    out = []
    if (
        isinstance(node, TreeNode)
        and node.name == "id"
    ):
        out.append(node)
    for child in getattr(node, "children", []):
        out.extend(collect_id_nodes(child))
    return out
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
        self.create_new_nodes = True
    def find_human(self, curr_id=None, step=[], create_new=True):
        if create_new:
            create_new = self.create_new_nodes
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
        for item3 in ["brother", "sister"]:
            if step[0] == item3:
                out = []
                for key, element in self.table_entry_list.items():
                    if key == curr_id:
                        continue
                    for item2 in ["mother", "father"]:
                        a = self.find_human(key, [item2], False)
                        b = self.find_human(curr_id, [item2], False)
                        if a is not None and b is not None and a==b and\
                                  [True if item3 == "brother" else False] == element.gender:
                            if key not in out:
                                out.append(key)
                if len(out) == 0 and create_new:
                    person = self.create()
                    if self.table_entry_list[curr_id].father is not None:
                        self.table_entry_list[person].father = self.table_entry_list[curr_id].father
                    if self.table_entry_list[curr_id].mother is not None:
                        self.table_entry_list[person].mother = self.table_entry_list[curr_id].mother
                    if self.table_entry_list[curr_id].father is None and self.table_entry_list[curr_id].mother is None:
                        person_a = self.create()
                        self.table_entry_list[person].father = person_a
                        self.table_entry_list[curr_id].father = person_a
                    return person
                if len(out) == 1:
                    return self.find_human(out[0], step[1:], create_new)
                else:
                    return None
        for item3 in ["son", "daughter"]:
            if step[0] == item3:
                out = []
                for key, element in self.table_entry_list.items():
                    if key == curr_id:
                        continue
                    for item2 in ["mother", "father"]:
                        if self.find_human(key, [item2], False) == curr_id and [True if item3 == "son" else False] == element.gender:
                            out.append(key)
                if len(out) == 0 and create_new:
                    if item.gender == [True]:
                        person = self.create()
                        self.table_entry_list[person].gender = [True if item3 == "son" else False]
                        self.table_entry_list[person].father = curr_id
                        return person
                    if item.gender == [False]:
                        person = self.create()
                        self.table_entry_list[person].gender = [True if item3 == "son" else False]
                        self.table_entry_list[person].mother = curr_id
                        return person
                if len(out) == 1:
                    return self.find_human(out[0], step[1:], create_new)
                else:
                    return None
        if step[0] == "father":
            if item.father is None and create_new:
                item.father = self.create()
                self.table_entry_list[item.father].gender = [True]
            if item.father is not None:
                return self.find_human(item.father, step[1:], create_new)
        if step[0] == "mother":
            if item.mother is None and create_new:
                item.mother = self.create()
                self.table_entry_list[item.mother].gender = [True]
            if item.mother is not None:
                return self.find_human(item.mother, step[1:], create_new)
        for key, item in self.table_entry_list.items():
            if step[0] in item.entry:
                return self.find_human(key, step[1:], create_new)
        if create_new is False:
            return None
        curr_id = self.create()
        self.table_entry_list[curr_id].entry = [step[0]]
        return self.find_human(curr_id, step[1:], create_new)
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
        n.killed = list(set(p.killed + q.killed))
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
    def normalize_id(self, number):
        new_cat = []
        for item in self.id_system:
            done = True
            for i in range(new_cat):
                if len(set(new_cat[i]) & set(item)) != 0:
                    new_cat[i] += item
                    new_cat[i] = list(set(new_cat[i]))
                    done = False
                    break
            if done:
                new_cat.append(item)
        self.id_system = new_cat
        for item in self.id_system:
            if number in item:
                return item[0]
        return number
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
                    
            for i in range(len(output)-1,-1,-1):
                if output[i] == TreeNode("DELETE") or contain2(output[i], TreeNode("DELETE")):
                    output.pop(i)
            output2 = []
            for item in output:
                output2 += self.rm_eq_id(item)
            output = list(set(output2))
            
            if len(output) == 1:
                return output[0]
            return output
        return []
    def bool_eq(self, eq):
        number_lst = []
        number = None
        if eq.name == "equal":
            for item in eq.children:
                if item.name == "id":
                    number_lst.append(int(item.children[0].name))
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
        elif len(eq.children) == 2 and eq.name == "kill":
            number_lst = []
            for item in eq.children:
                if item.name == "id":
                    number_lst.append(int(item.children[0].name))
                elif valid_actor_eq(item):
                    number_lst.append(self.find_id(item))
                else:
                    return None
            if number_lst[1] in self.table_entry_list[number_lst[0]].killed:
                return True
            return False
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
    def equate_verb(self, eq):
        if eq.name in ["kill"] and len(eq.children) == 2:
            index = self.find_id(eq.children[0])
            self.table_entry_list[index].killed.append(self.find_id(eq.children[1]))
            return index
        return None
    def equate(self, eq):
        a = self.equate_bool_eq(eq)
        b = None
        c = None
        if eq.name == "equal":
            b = self.equate_eq(*eq.children)
        if eq.name == "kill":
            c = self.equate_verb(eq)
            c = self.equate_bool_eq(eq.children[1].fx("die"))
        if a is not None:
            return a
        if b is not None:
            return b
        if c is not None:
            return c
        return None
    def alias_gen(self):
        for key, item in self.table_entry_list.items():
            item.alias = list(item.entry)

        relations = [
            "mother",
            "father",
            "son",
            "daughter",
            "sister",
            "brother"
        ]

        for _ in range(2):
            snapshot = {
                k: list(v.alias)
                for k, v in self.table_entry_list.items()
            }

            for key, aliases in snapshot.items():

                if not aliases:
                    continue

                # shortest alias
                base = min(
                    aliases,
                    key=lambda x: len(str_form(x))
                )

                # FIX:
                # avoid TreeNode(TreeNode(...))
                base_node = (
                    base
                    if isinstance(base, TreeNode)
                    else TreeNode(base)
                )

                for relation in relations:

                    targets = self.find_human(
                        key,
                        [relation],
                        False
                    )

                    if targets is None:
                        continue

                    # normalize single value -> list
                    if not isinstance(targets, list):
                        targets = [targets]

                    new_alias = base_node.fx(relation)

                    for target in targets:

                        if target not in self.table_entry_list:
                            continue

                        if (
                            new_alias
                            not in self.table_entry_list[target].alias
                        ):
                            self.table_entry_list[target].alias.append(
                                new_alias
                            )
    def find_from_id(self, number):
        out = [item if isinstance(item, TreeNode) else TreeNode(item) for item in self.table_entry_list[number].alias]
        return list(set(out))
        # return list(sorted(out, key=lambda x: len(str_form(x))))[0]
    def rm_eq_id(self, eq):
        self.alias_gen()
        id_nodes = collect_id_nodes(eq)
        if not id_nodes:
            return [eq]
        replacement_choices = []
        for node in id_nodes:
            number = int(node.children[0].name)
            aliases = self.find_from_id(number)
            if aliases == []:
                aliases = [node]
            replacement_choices.append(aliases)
        outputs = []
        for combo in itertools.product(*replacement_choices):
            new_eq = eq
            for old_node, new_node in zip(
                id_nodes,
                combo
            ):
                new_eq = replace(
                    new_eq,
                    old_node,
                    new_node
                )
            outputs.append(new_eq)
        return outputs
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
        # self.id_system = []
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
        entry=None,
        father=None,
        mother=None,
        crush=[],
        killed=None,
        gender=[True, False],
        emotional_state=[True, False],
        living_state=True
    ):
        self.entry = entry if entry else []
        self.gender = gender
        self.emotional_state = emotional_state
        self.living_state = living_state
        self.father = father
        self.mother = mother
        self.killed = killed if killed else []
        self.alias = entry if entry else []
        self.crush = crush
        self.detect_gender()
    def detect_gender(self):
        for item in self.entry:
            if isinstance(item, str):
                item = TreeNode(item)
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
        lst = [(set(item.gender),set(item.emotional_state),set(item.living_state),set(item.entry)) for item in [self, other]]
        return lst[0] == lst[1]
