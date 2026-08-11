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
    a = [code(item) for item in c]
    q = code(question)
    table = prepare_table(a)
    out = table.lambda_compute(q)
    if not isinstance(out, list):
        out = [out]
    out = [actor_to_phrase(swap_i_you(item)) for item in out]
    if len(out) == 1:
        return out[0]
def prepare_table(given_code):
    table = Table()
    for item in a:
        table.process_entry()
        out = table.equate(item)
        if out is None:
            return None
    table.create_new_nodes = False
    table.process_entry()
    return table
    
    return out
