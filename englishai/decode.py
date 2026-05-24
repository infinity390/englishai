from .base import *
def actor_to_phrase(node, obj_form=False):
    if node is None:
        return ""
    if node.name in ["i", "she", "he", "they", "we"] and obj_form:
        return {"i":"me", "she":"her", "he":"him", "they":"them", "we":"us"}[node.name]
    allowed_relations = {
        "father",
        "mother",
        "friend",
        "boy-friend",
        "girl-friend",
        "son"
    }
    allowed_pronouns = {
        "i", "you", "he", "she", "we", "they"
    }
    allowed_names = {
        "john", "lucy", "mary", "bob", "alice", "emma", "david"
    }
    pronoun_possessive = {
        "i": "my",
        "you": "your",
        "he": "his",
        "she": "her",
        "we": "our",
        "they": "their"
    }
    if not node.children:
        w = node.name.lower()
        if w not in allowed_pronouns and w not in allowed_names:
            raise ValueError(f"Invalid terminal word: {w}")
        return w
    name = node.name.lower()
    if name not in allowed_relations:
        raise ValueError(f"Invalid relation node: {name}")
    child = node.children[0]
    base = actor_to_phrase(child)
    if base in pronoun_possessive:
        base = pronoun_possessive[base]
    if base in pronoun_possessive.values():
        return f"{base} {name}"
    return f"{base}'s {name}"
def noun_phrase_conv(eq, to=False, tense="present", continuous=False, obj_form=False, reflex=False):

    if eq is None:
        return ""
    if eq.name == "equal":
        aux = ["is"]
        a = actor_to_phrase(eq.children[0])
        if continuous or eq.children[0].name in ["they", "you", "we", "mothers", "fathers", "friends"]:
            aux = ["are"]
        if eq.children[0].name == "i":
            aux = ["am"]
        if tense == "past":
            if aux == ["are"]:
                aux = ["were"]
            else:
                aux = ["was"]
        b = actor_to_phrase(eq.children[1],  obj_form=True)
        lst = a.split(" ")+aux+b.split(" ")
        return " ".join(lst)
    if eq.name == "want":
        if len(eq.children) == 2 and len(eq.children[1].children) == 2 and eq.children[0] == eq.children[1].children[0]:
            a = noun_phrase_conv(eq.children[0].fx("want"), to=False, tense=tense, continuous=continuous)
            b = noun_phrase_conv(eq.children[1].children[1].fx(eq.children[1].name), to=True, tense="present", continuous=False, obj_form=True, reflex=(eq.children[1].children[0] == eq.children[1].children[1]))
            lst = a.split(" ")+b.split(" ")
            return " ".join(lst)
        if len(eq.children) == 2 and len(eq.children[1].children) == 1 and eq.children[0] == eq.children[1].children[0]:
            a = noun_phrase_conv(eq.children[0].fx("want"), to=False, tense=tense, continuous=continuous)
            b = f"to {eq.children[1].name}"
            lst = a.split(" ")+b.split(" ")
            return " ".join(lst)
    verb = eq.name
    children = eq.children or []

    allowed_verbs = {
        "kill", "die", "want", "love", "hate",
        "see", "give", "take", "run", "come", "be"
    }

    if verb not in allowed_verbs:
        raise ValueError(f"Invalid verb: {verb}")

    def aux(subject, tense):
        subject = subject.lower()
        singular = {"i", "he", "she", "it"}
        plural = {"friends"}
        single = subject in singular or (subject not in singular and subject not in plural)
        if tense == "past":
            return "was" if single else "were"
        return "is" if single else "are"
    def make_ing(v):

        if v == "die":
            return "dying"

        if v.endswith("e") and v not in ["be", "see"]:
            v = v[:-1]

        if (
            len(v) >= 3
            and v[-1] not in "aeiou"
            and v[-2] in "aeiou"
            and v[-3] not in "aeiou"
        ):
            v = v + v[-1]

        return v + "ing"
    def make_past(v):

        if v == "die":
            return "died"
        if v == "run":
            return "ran"
        if v == "come":
            return "came"

        return v + "ed"
    def present_agree(v, subject):

        subject = subject.lower()
        singular_3rd = {"he", "she", "it"}

        if subject in singular_3rd:
            if v.endswith("y") and v[-2] not in "aeiou":
                return v[:-1] + "ies"
            if v.endswith(("s", "sh", "ch", "x", "z")):
                return v + "es"
            return v + "s"

        return v
    def base_form(v):
        if continuous:
            return make_ing(v)
        if tense == "past":
            return make_past(v)
        return v

    v = base_form(verb)
    def render(x, obj_form=False):
        try:
            phrase = actor_to_phrase(x, obj_form=obj_form)
            if phrase is not None:
                return phrase
        except:
            pass
        
        if not x.children:
            return x.name
    
        return noun_phrase_conv(x, to=False, tense=tense, continuous=continuous)
    if to:
        if len(children) == 1:
            if reflex and children[0].name in ["he", "she", "us", "you", "we", "they", "i"]:
                children[0].name = {"he":"himself", "she":"herself", "i":"myself", "you":"yourself"}[children[0].name]
            return f"to {verb} {render(children[0], obj_form=obj_form)}"
        if len(children) == 2:
            return f"{render(children[0])} to {verb} {render(children[1], obj_form=obj_form)}"
        return f"to {verb}"
    if len(children) == 1:

        subj = render(children[0])
        
        if reflex and children[0].name in ["he", "she", "us", "you", "we", "they", "i"]:
            subj = {"he":"himself", "she":"herself", "i":"myself", "you":"yourself"}[children[0].name]
        if continuous:
            return f"{subj} {aux(subj, tense)} {make_ing(verb)}"
        if tense == "present":
            v2 = present_agree(verb, subj)
            return f"{subj} {v2}"

        return f"{subj} {v}"
    if len(children) == 2:
        
        subj = render(children[0])
        obj = render(children[1], obj_form=True)
        
        if children[0] == children[1] and children[0].name in ["he", "she", "us", "you", "we", "they"]:
            obj = {"he":"himself", "she":"herself", "i":"myself", "you":"yourself"}[children[0].name]
        if continuous:
            return f"{subj} {aux(subj, tense)} {make_ing(verb)} {obj}"
        if children[0] == children[1] and children[0] in ["he", "she", "we", "they", "i", "you"]:
            obj += "self"
        if tense == "present":
            v2 = present_agree(verb, subj)
            return f"{subj} {v2} {obj}"

        return f"{subj} {v} {obj}"
    return f"{verb}({', '.join(render(c) for c in children)})"
def decode(eq, tense="present", continuous=False):
    return noun_phrase_conv(eq, tense=tense, continuous=continuous).replace("-", " ")
