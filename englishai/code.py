from .base import *
import itertools
import copy

def combine_relation(node):
    node.children = [
        combine_relation(c)
        for c in node.children
    ]

    # only friend(...)
    if node.name != "friend":
        return node

    if len(node.children) != 1:
        return node

    child = node.children[0]

    # only boy(...) or girl(...)
    if child.name not in ["boy", "girl"]:
        return node

    if len(child.children) != 1:
        return node

    # combine
    return TreeNode(
        child.name + "-friend",
        child.children
    )
def parse_noun_phrase(words):

    if not words:
        return None, None

    # ---------------------------------
    # FIXED VOCABULARY
    # ---------------------------------

    vocabulary = {

        # pronouns
        "i", "you", "he", "she",
        "it", "we", "they",

        # possessives
        "my", "your", "his",
        "her", "our", "their",

        "myself", "yourself", "herself", "himself", "themselves", "ourselves",
        # family
        "father", "mother", "mom",
        "brother", "sister",
        "son", "daughter",

        # social
        "friend",
        "boy",
        "girl",

        # object pronouns
        "me",
        "him",
        "them",
        "us",
        "myself",

        # irregular plurals
        "men",
        "women",
        "children",
        "people",
        "mice",
        "geese",
        "teeth",
        "feet"
    }

    # ---------------------------------
    # ALLOWED PROPER NAMES
    # ---------------------------------

    names = {
        "john",
        "mary",
        "lucy",
        "bob",
        "alice",
        "michael",
        "david",
        "james",
        "sarah",
        "emma"
    }

    # ---------------------------------
    # PRONOUN NORMALIZATION
    # ---------------------------------

    pronoun_map = {

        # possessive pronouns
        "your": "you",
        "my": "i",
        "his": "he",
        "her": "she",
        "their": "they",
        "our": "we",

        # object pronouns
        "me": "i",
        "myself": "i",
        "him": "he",
        "them": "they",
        "us": "we",

        "herself":"she",
        "himself":"he",
        "myself":"i"
    }

    # ---------------------------------
    # PRONOUN NUMBER
    # ---------------------------------

    pronoun_number = {
        "i": "singular",
        "you": "plural",
        "he": "singular",
        "she": "singular",
        "it": "singular",
        "we": "plural",
        "they": "plural"
    }

    # ---------------------------------
    # IRREGULAR PLURALS
    # ---------------------------------

    irregular_plural = {
        "men": "man",
        "women": "woman",
        "children": "child",
        "people": "person",
        "mice": "mouse",
        "geese": "goose",
        "teeth": "tooth",
        "feet": "foot"
    }

    # ---------------------------------
    # SINGULARIZATION
    # ---------------------------------

    def singularize(w):

        if w in irregular_plural:
            return irregular_plural[w], True

        if w.endswith("ies") and len(w) > 3:
            return w[:-3] + "y", True

        if w.endswith("ses") and len(w) > 3:
            return w[:-2], True

        if w.endswith("s") and not w.endswith("ss") and len(w) > 1:
            return w[:-1], True

        return w, False

    # ---------------------------------
    # TOKEN NORMALIZATION
    # ---------------------------------

    def atom(w):

        if w == "'s":
            return None, None

        if w.endswith("'s"):
            w = w[:-2]

        w = w.lower()

        raw = w

        # ---------------------------------
        # PROPER NAME SUPPORT
        # ---------------------------------

        if raw in names:
            return raw, "singular"

        singular_candidate, _ = singularize(raw)

        if (
            raw not in vocabulary
            and singular_candidate not in vocabulary
        ):
            raise ValueError(
                f"Invalid vocabulary word: {raw}"
            )

        # pronoun normalization
        w = pronoun_map.get(w, w)

        # pronouns
        if w in pronoun_number:

            return (
                w,
                pronoun_number[w]
            )

        # nouns
        singular, is_plural = singularize(w)

        return (
            singular,
            "plural" if is_plural else "singular"
        )

    # ---------------------------------
    # CLEAN TOKENS
    # ---------------------------------

    clean = []
    numbers = []

    for w in words:

        atom_word, number = atom(w)

        if atom_word is not None:
            clean.append(atom_word)
            numbers.append(number)

    if not clean:
        return None, None

    # ---------------------------------
    # BUILD TREE
    # ---------------------------------

    node = TreeNode(clean[0])

    for w in clean[1:]:
        node = node.fx(w)

    head_number = numbers[-1]

    return node, head_number
def has_branch(node, name):
    """
    Returns True if any branch (child in tree path) matches the given name.
    """

    if node is None:
        return False

    if node.name in name and node.children != []:
        return True

    for child in node.children:
        if has_branch(child, name):
            return True

    return False
def parse_adjective(words):
    word = words[0]
    vocabulary = {
        "happy":"happy",
        "sad":"sad",
        "alive":"live",
        "dead":"die"
    }

    w = word.lower()

    if w not in vocabulary.keys() or len(words)!=1:
        raise ValueError(
            f"Invalid adjective: {word}"
        )
    
    return vocabulary[w]
def actor(words):

    node, number = parse_noun_phrase(words)

    node = combine_relation(node)
    if has_branch(node, ["you", "we", "they", "i", "she", "he"]):
        raise ValueError(
            f"Pronoun is branch node"
        )
    
    # ---------------------------------
    # ROOT ENTITY
    # ---------------------------------

    root = copy.deepcopy(node)
    root2 = copy.deepcopy(node)
    
    while root2.children:
        root2 = root2.children[0]
    if root.children != [] and root2.name in ["you", "we", "they", "i", "she", "he"] and root2.name == words[0]:
        raise ValueError(
            f"Pronoun has a wrong form"
        )
    # ---------------------------------
    # PERSON
    # ---------------------------------

    if root.name == "i":
        person = ["1st"]

    elif root.name == "you":
        person = ["2nd"]

    elif root.name in ["he", "she", "it"]:
        person = ["3rd"]

    elif root.name == "we":
        person = ["1st"]

    elif root.name == "they":
        person = ["3rd"]

    else:
        person = ["3rd"]

    # ---------------------------------
    # FORM DETECTION
    # ---------------------------------

    original = words[0].lower()

    subject_forms = {
        "i",
        "he",
        "she",
        "we",
        "they"
    }

    object_forms = {
        "me",
        "him",
        "her",
        "us",
        "them"
    }

    either_forms = {
        "you",
        "it"
    }

    if original in subject_forms:
        form = "subject"

    elif original in object_forms:
        form = "object"

    elif original in either_forms:
        form = "either"

    else:
        # normal nouns
        form = "either"

    return {
        "tree": node,
        "number": [number],
        "person": person,
        "form": form
    }

def aux_verb(word_list):
    if not word_list:
        return None

    w = " ".join(word_list).lower().strip()

    if w == "is":
        return {
            "tense": "present",
            "person": ["3rd"],
            "number": "singular"
        }

    if w == "am":
        return {
            "tense": "present",
            "person": ["1st"],
            "number": "singular"
        }

    if w == "are":
        return {
            "tense": "present",
            "person": ["2nd", "3rd"],
            "number": "plural"
        }

    if w == "was":
        return {
            "tense": "past",
            "person": ["1st", "3rd"],
            "number": "singular"
        }

    if w == "were":
        return {
            "tense": "past",
            "person": ["1st", "2nd", "3rd"],
            "number": "plural"
        }

    if w == "will":
        return {
            "tense": "future",
            "person": ["1st", "2nd", "3rd"]
        }
    
    raise ValueError(
            f"Invalid verb vocabulary: {w}"
        )

class Speech:
    def __init__(self):
        self.pronoun_map = {}
        self.sentence = []
    def listen_word(word):
        pass
    
def parse_verb(words):
    if not words:
        return None
    if len(words) != 1:
        raise ValueError(
            f"Verb parser accepts exactly one word: {words}"
        )
    verb = words[0].lower()
    vocabulary = {
        # base forms
        "eat", "go", "see", "give",
        "take", "run", "die",
        "come", "do", "have",
        "walk", "study", "kill", "want",
        "love", "hate", "help",
        # tense forms

        # irregular forms
        "ate", "went", "gone",
        "saw", "seen",
        "gave", "given",
        "took", "taken",
        "ran", "died",
        "came",
        "did", "done",
        "had",
        "has",
        "does"
    }
    irregular = {

        "ate": ("eat", "past"),
        "went": ("go", "past"),
        "gone": ("go", "past"),
        "saw": ("see", "past"),
        "seen": ("see", "past"),
        "gave": ("give", "past"),
        "given": ("give", "past"),
        "took": ("take", "past"),
        "taken": ("take", "past"),
        "ran": ("run", "past"),
        "died": ("die", "past"),
        "dies": ("die", "present"),
        "came": ("come", "past"),
        "did": ("do", "past"),
        "done": ("do", "past"),
        "had": ("have", "past"),

        "has": (
            "have",
            "present",
            ["3rd"],
            "singular"
        ),

        "does": (
            "do",
            "present",
            ["3rd"],
            "singular"
        )
    }
    def estimate_root(v):

        # -------------------------
        # IRREGULAR VERBS (finite forms)
        # -------------------------
        if v in irregular:
            return irregular[v][0]

        # -------------------------
        # ING FORMS (continuous)
        # -------------------------
        if v.endswith("ing"):
            stem = v[:-3]
            
            # ---------------------
            # FIX IRREGULAR CONTINUOUS
            # ---------------------
            if stem in ["dy", "ly"]:  # handles dying, lying, trying
                return stem[:-1] + "ie"

            # ---------------------
            # CVC doubling: running → run
            # ---------------------
            if len(stem) >= 2 and stem[-1] == stem[-2] and stem not in ["kill"]:
                stem = stem[:-1]

            return stem
        if v.endswith("ed"):
            return v[:-2]
        # -------------------------
        # IED → Y
        # -------------------------
        if v.endswith("ied"):
            return v[:-3] + "y"

        # -------------------------
        # IES → Y
        # -------------------------
        if v.endswith("ies"):
            return v[:-3] + "y"

        # -------------------------
        # ES CASE (careful)
        # -------------------------
        if v.endswith("es"):
            if len(v) > 3 and v[-3] not in "aeiou":
                return v[:-2]
            return v[:-1]

        # -------------------------
        # SIMPLE S
        # -------------------------
        if v.endswith("s") and not v.endswith("ss"):
            return v[:-1]

        return v
    estimated = estimate_root(verb)
    
    if (
        verb not in vocabulary
        and estimated not in vocabulary
    ):
        raise ValueError(
            f"Invalid verb vocabulary: {verb}"
        )
    
    if verb in irregular:
        data = irregular[verb]
        if len(data) == 2:
            root, tense = data
            return {
                "root": root,
                "tense": tense,
                "person": ["1st", "2nd", "3rd"],
                "number": ['plural', 'singular'],
                "continuous": False
            }
        root, tense, person, number = data
        return {
            "root": root,
            "tense": tense,
            "person": person,
            "number": [number],
            "continuous": False
        }
    if verb.endswith("ing"):
        stem = verb[:-3]
        if (
            len(stem) >= 2
            and stem[-1] == stem[-2]
            and stem not in ["kill"]
        ):
            stem = stem[:-1]
        root = None
        
        if stem in ["dy", "ly"]:
            root = stem[:-1]+"ie"
        else:
            root = stem
            
        return {
            "root": root,
            "tense": "present",
            "person": ["1st", "2nd", "3rd"],
            "number": ['plural', 'singular'],
            "continuous": True
        }
    if verb.endswith("ied"):
        return {
            "root": verb[:-3] + "y",
            "tense": "past",
            "person": ["1st", "2nd", "3rd"],
            "number": ['plural', 'singular'],
            "continuous": False
        }
    if verb.endswith("ed"):
        return {
            "root": verb[:-2],
            "tense": "past",
            "person": ["1st", "2nd", "3rd"],
            "number": ['plural', 'singular'],
            "continuous": False
        }
    if verb.endswith("ies"):
        return {
            "root": verb[:-3] + "y",
            "tense": "present",
            "person": ["3rd"],
            "number": ["singular"],
            "continuous": False
        }
    if verb.endswith("es"):
        return {
            "root": verb[:-2],
            "tense": "present",
            "person": ["3rd"],
            "number": ["singular"],
            "continuous": False
        }
    if verb.endswith("s") and not verb.endswith("ss"):
        return {
            "root": verb[:-1],
            "tense": "present",
            "person": ["3rd"],
            "number": ["singular"],
            "continuous": False
        }
    return {
        "root": verb,
        "tense": "present",
        "person": ["1st", "2nd", "3rd"],
        "number": ["singular", "plural"],
        "continuous": False
    }
VALID_NOUNS = {
    # basic nouns
    "boy", "girl", "man", "woman",
    "father", "mother", 
    "son", "daughter",
    "friend",

    # pronouns
    "i", "you", "he", "she", "it", "we", "they",
    "me", "him", "her", "us", "them",

    # irregular plural roots
    "man", "woman", "child", "person",
    "mouse", "goose", "foot", "tooth"
}
def validate_noun(word):

    w = word.lower()

    if w in VALID_NOUNS:
        return True

    # allow simple plural forms if root exists
    if w.endswith("s") and w[:-1] in VALID_NOUNS:
        return True

    # allow irregular plurals
    irregular_plural = {
        "men", "women", "children",
        "people", "mice", "geese",
        "feet", "teeth"
    }

    if w in irregular_plural:
        return True

    return False
NON_NOUN_BLOCKLIST = {
    # copula verbs
    "is", "are", "am", "was", "were", "be", "been", "being",

    # auxiliary verbs
    "do", "does", "did",
    "have", "has", "had",
    "will", "would", "shall", "should",
    "can", "could", "may", "might",

    # obvious verbs
    "go", "goes", "went", "gone",
    "eat", "eats", "ate",
    "see", "saw", "seen",
    "kill", "killed", "killing"
}
def parse_category(words):

    if not words:
        return None

    word = words[-1].lower()
    if word in NON_NOUN_BLOCKLIST:
        raise ValueError(f"Invalid noun (verb detected): {word}")
    # -------------------------
    # VALIDATION
    # -------------------------

    if not validate_noun(word):
        raise ValueError(f"Invalid noun: {word}")

    irregular_plural = {
        "men": "man",
        "women": "woman",
        "children": "child",
        "people": "person",
        "mice": "mouse",
        "geese": "goose",
        "feet": "foot",
        "teeth": "tooth"
    }

    # -------------------------
    # ARTICLE RULE
    # -------------------------

    if len(words) == 2 and words[0].lower() in ["a", "an"]:
        return {
            "root": word,
            "number": "singular"
        }

    # -------------------------
    # IRREGULAR PLURAL
    # -------------------------

    if word in irregular_plural:
        return {
            "root": irregular_plural[word],
            "number": "plural"
        }

    # -------------------------
    # REGULAR PLURAL
    # -------------------------

    if word.endswith("s") and not word.endswith("ss"):
        return {
            "root": word[:-1],
            "number": "plural"
        }

    return None
SYNONYMS = {

    # boy group
    "boy": "boy",
    "man": "boy",
    "male": "boy",

    # girl group
    "girl": "girl",
    "woman": "girl",
    "female": "girl",

    # father group
    "father": "father",
    "dad": "father",
    "papa": "father",

    # mother group
    "mother": "mother",
    "mom": "mother",
    "mama": "mother",

    # friend group
    "friend": "friend",
    "mate": "friend",
    "buddy": "friend",

    # pronouns (optional normalization layer)
    "i": "i",
    "me": "i",
    "myself": "i",

    "you": "you",
    "yourself": "you",

    "he": "he",
    "him": "he",

    "she": "she",
    "her": "she",

    "they": "they",
    "them": "they"
}
def normalize_synonyms(node):

    if node is None:
        return None

    # -------------------------
    # normalize current node
    # -------------------------

    node.name = SYNONYMS.get(node.name, node.name)

    # -------------------------
    # recurse children
    # -------------------------

    node.children = [
        normalize_synonyms(child)
        for child in node.children
    ]

    return node
def split_sentence(words):
    results = []
    n = len(words)
    def valid_given(given, chunk):
        return given == " ".join(chunk)
    def valid_actor(chunk):
        try:
            return actor(chunk) is not None
        except:
            return False
    def valid_adjective(chunk):
        try:
            return parse_adjective(chunk) is not None
        except:
            return False
    def valid_aux(chunk):
        try:
            return aux_verb(chunk) is not None
        except:
            return False
    def valid_noun(chunk):
        try:
            return parse_category(chunk) is not None
        except:
            return False
    def valid_verb(chunk):
        try:
            return parse_verb(chunk) is not None
        except:
            return False
    parsers = [
        ("actor", valid_actor),
        ("aux", valid_aux),
        ("verb", valid_verb),
        ("to", lambda x: valid_given("to", x)),
        ("not", lambda x: valid_given("not", x)),
        ("who", lambda x: valid_given("who", x)),
        ("noun", valid_noun),
        ("adjective", valid_adjective)
    ]
    def recurse(index, splits, funcs):
        if index >= n:
            for i in range(len(funcs) - 1):
                if (
                    funcs[i] == "actor"
                    and funcs[i + 1] == "actor"
                ):
                    return
            results.append((
                splits[:],
                funcs[:]
            ))
            return
        for end in range(index + 1, n + 1):
            chunk = words[index:end]
            for name, parser in parsers:
                if parser(chunk):
                    splits.append(chunk)
                    funcs.append(name)
                    recurse(
                        end,
                        splits,
                        funcs
                    )
                    splits.pop()
                    funcs.pop()
    recurse(0, [], [])
    return results
def combine_features(split, funcs):
    result = {
        "tense": None,
        "person": None,
        "number": None,
        "continuous": False,
        "valid": True
    }
    person_intersection = None
    number_intersection = None
    for chunk, fn in zip(split, funcs):
        if fn == "actor":

            act = actor(chunk)
            persons = act["person"]
            numbers = act["number"]
            
            if person_intersection is None:
                person_intersection = set(persons)
            else:
                person_intersection &= set(persons)
            if number_intersection is None:
                number_intersection = set(numbers)
            else:
                number_intersection &= set(numbers)
        elif fn == "aux":
            aux = aux_verb(chunk)
            if aux is None:
                continue
            persons = aux.get(
                "person",
                ["1st", "2nd", "3rd"]
            )
            numbers = []
            if "number" in aux:
                numbers = [aux["number"]]
            if aux.get("tense") is not None:
                result["tense"] = aux["tense"]
            if person_intersection is None:
                person_intersection = set(persons)
            else:
                person_intersection &= set(persons)

            # intersect number
            if numbers:

                if number_intersection is None:
                    number_intersection = set(numbers)
                else:
                    number_intersection &= set(numbers)
        elif fn == "verb":
            verb = parse_verb(chunk)
            
            persons = verb["person"]
            numbers = verb["number"]
            
            if result["tense"] is None:
                result["tense"] = verb["tense"]

            result["continuous"] = verb["continuous"]

            if person_intersection is None:
                person_intersection = set(persons)
            else:
                person_intersection &= set(persons)
            if number_intersection is None:
                number_intersection = set(numbers)
            else:
                number_intersection &= set(numbers)
    if (
        person_intersection is not None
        and len(person_intersection) == 0
    ):
        result["valid"] = False

    if (
        number_intersection is not None
        and len(number_intersection) == 0
    ):
        result["valid"] = False

    result["person"] = (
        sorted(list(person_intersection))
        if person_intersection is not None
        else []
    )

    result["number"] = (
        sorted(list(number_intersection))
        if number_intersection is not None
        else []
    )
    return result
def infer_equation2(split, funcs):
    if split[0] != ["who"] and combine_features(split[:2], funcs[:2])["valid"] is False:
        
        return None

    last_actor = None
    if funcs.count("actor") == 2:
        if len(split)>=3 and funcs[-1] == "actor" and actor(split[-1])["form"] == "subject":
            return None
        lst = []
        for i in range(len(funcs)):
            if funcs[i] == "actor":
                lst.append(i)
        ga = gender(actor(split[lst[0]])["tree"])
        last_actor = actor(split[lst[1]])
        if ga == "male":
            last_actor["tree"] = replace(last_actor["tree"], TreeNode("he"), actor(split[lst[0]])["tree"])
        elif ga == "female":
            last_actor["tree"] = replace(last_actor["tree"], TreeNode("she"), actor(split[lst[0]])["tree"])
        if actor(split[lst[0]])["tree"] == actor(split[lst[1]])["tree"] and last_actor["tree"].name in ["she", "he", "i", "we", "they", "you"]:
            if len(split[lst[1]][0]) <= 4 or split[lst[1]][0][-4:] != "self":
                return None
    if funcs == ["actor", "verb", "noun"]:
        v = parse_verb(split[1])["root"]
        a = actor(split[0])["tree"]
        if parse_category(split[2])["root"] in ["friend"]:
            return TreeNode(v, [a,TreeNode("lambda", [TreeNode("A"),\
                                                      TreeNode("TRUE"),\
                                                      TreeNode("equal", [actor(split[0])["tree"], TreeNode("A").fx(parse_category(split[2])["root"])]),\
                                                      TreeNode("DELETE")])])
        else:
            return TreeNode(v, [a,TreeNode("lambda", [TreeNode("A"), TreeNode("A").fx(parse_category(split[2])["root"]), TreeNode("A"), TreeNode("DELETE")])])
    if funcs == ["aux", "actor", "adjective"]:
        a = actor(split[1])["tree"]
        v = parse_adjective(split[2])
        return TreeNode("lambda", [TreeNode("A"), TreeNode(v, [a]), TreeNode("yes"), TreeNode("no")])
    if funcs == ["who", "aux", "actor"]:
        a = actor(split[2])["tree"]
        return TreeNode("lambda", [TreeNode("A"), TreeNode("equal", [TreeNode("A"), a]), TreeNode("A"), TreeNode("DELETE")])
    if funcs == ["who", "verb", "actor"]:
        v = parse_verb(split[1])["root"]
        a = actor(split[2])["tree"]
        return TreeNode("lambda", [TreeNode("A"), TreeNode(v, [TreeNode("A"), a]), TreeNode("A"), TreeNode("DELETE")])
    if funcs == ["actor", "aux", "adjective"]:
        return actor(split[0])["tree"].fx(parse_adjective(split[2]))
    if funcs == ["actor", "aux", "not", "adjective"]:
        return actor(split[0])["tree"].fx(parse_adjective(split[3])).fx("not")
    if funcs == ["actor", "aux", "noun"]:
        return actor(split[0])["tree"].fx(parse_category(split[2])["root"])
    if funcs == ["aux", "actor", "noun"]:
        a = actor(split[1])["tree"]
        v = parse_category(split[2])["root"]
        return TreeNode("lambda", [TreeNode("A"), TreeNode(v, [a]), TreeNode("yes"), TreeNode("no")])
    if funcs == ["actor", "verb", "to", "verb"]:
        v1 = parse_verb(split[1])["root"]
        v2 = parse_verb(split[3])["root"]
        a1 = actor(split[0])["tree"]
        return TreeNode(v1, [a1, a1.fx(v2)])
    if funcs == ["actor", "verb", "to", "verb", "actor"]:
        v1 = parse_verb(split[1])["root"]
        v2 = parse_verb(split[3])["root"]
        a1 = actor(split[0])["tree"]
        return TreeNode(v1, [a1, TreeNode(v2, [a1, last_actor["tree"]])])
    if funcs == ["actor", "aux", "verb", "actor"]:
        if parse_verb(split[2])["continuous"] is False:
            return None
        a, b = actor(split[0])["tree"], last_actor["tree"]
        return TreeNode(parse_verb(split[2])["root"], [a, b])
    if funcs == ["actor", "aux", "verb"]:
        out = parse_verb(split[2])["root"]
        if out in ["kill"]:
            return None
        return actor(split[0])["tree"].fx(out)
    if funcs == ["actor", "verb"]:
        return actor(split[0])["tree"].fx(parse_verb(split[1])["root"])
    if funcs == ["actor", "verb", "actor"]:
        return TreeNode(parse_verb(split[1])["root"], [actor(split[0])["tree"], last_actor["tree"]])
    if funcs == ["actor", "aux", "actor"]:
        return TreeNode("equal",[actor(split[0])["tree"], last_actor["tree"]])
    return None
def infer_equation(split, funcs):
    return normalize_synonyms(infer_equation2(split, funcs))
def code(sentence):
    out = split_sentence(
        sentence.split()
    )
    if len(out) == 0:
        
        return None
    else:
        out = out[0]
        return infer_equation(*out)
