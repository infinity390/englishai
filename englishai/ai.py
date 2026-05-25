from .code import *
from .infer import *
def swap_i_you(node):
    if node is None:
        return None
    node.children = [
        swap_i_you(child)
        for child in node.children
    ]
    if node.children == []:
        if node.name == "i":
            return TreeNode("you")
        elif node.name == "you":
            return TreeNode("i")
    return node
def assume_gender(table):
    output = []
    for key, item in table.table_entry_list.items():
        if len(item.gender) == 2 and len(item.entry) != 0: 
            out = TreeNode(item.entry[0])
            output += [out.fx("girl"), out.fx("boy")]
    return list(set(output))
def answer(question, conversation=""):
    c = conversation.split(".")
    c = [item.strip() for item in c]
    c = [item for item in c if item.replace(" ","") != ""]
    table = Table()
    a = [code(item) for item in c]
    q = code(question)
    for item in a:
        table.create_new_nodes = False
        out = table.equate(item)
        if out is None:
            for item2 in assume_gender(table):
                orig = copy.deepcopy(table)
                out2 = table.equate(item2)
                if out2 is None:
                    continue
                out = table.equate(item)
                if out is not None:
                    break
                else:
                    table = orig
        if out is None:
            table.create_new_nodes = True
            out = table.equate(item)
        if out is None:
            return None
    table.create_new_nodes = False
    out = table.lambda_compute(q)
    if not isinstance(out, list):
        out = [out]
    out = [actor_to_phrase(swap_i_you(item)) for item in out]
    if len(out) == 1:
        return out[0]
    return out
