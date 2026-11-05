from .base import *
import itertools
import copy


def combine_relation(node):
    node.children = [
        combine_relation(c)
        for c in node.children
    ]
    if node.name != "friend":
        return node
    if len(node.children) != 1:
        return node
    child = node.children[0]
    if child.name not in ["boy", "girl"]:
        return node
    if len(child.children) != 1:
        return node
    return TreeNode(
        child.name + "-friend",
        child.children
    )


def parse_noun_phrase(words):
    if not words:
        return None, None
    vocabulary = {
        "i", "you", "he", "she",
        "it", "we", "they",
        "my", "your", "his",
        "her", "our", "their",
        "myself", "yourself", "herself", "himself", "themselves", "ourselves",
        "father", "mother", "mom", "dad", "papa", "mama",
        "brother", "sister",
        "son", "daughter",
        "friend",
        "boy",
        "girl",
        "me",
        "him",
        "them",
        "us",
        "men",
        "women",
        "children",
        "people",
        "mice",
        "geese",
        "teeth",
        "feet"
    }
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
        "emma",
        "x", "y", "z", "w"
    }
    pronoun_map = {
        "your": "you",
        "my": "i",
        "his": "he",
        "her": "she",
        "their": "they",
        "our": "we",
        "me": "i",
        "myself": "i",
        "him": "he",
        "them": "they",
        "us": "we",
        "herself": "she",
        "himself": "he",
    }
    pronoun_number = {
        "i": "singular",
        "you": "plural",
        "he": "singular",
        "she": "singular",
        "it": "singular",
        "we": "plural",
        "they": "plural"
    }
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

    def atom(w):
        if w == "'s":
            return None, None
        if w.endswith("'s"):
            w = w[:-2]
        w = w.lower()
        raw = w
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
        w = pronoun_map.get(w, w)
        if w in pronoun_number:
            return (
                w,
                pronoun_number[w]
            )
        singular, is_plural = singularize(w)
        return (
            singular,
            "plural" if is_plural else "singular"
        )

    clean = []
    numbers = []
    for w in words:
        atom_word, number = atom(w)
        if atom_word is not None:
            clean.append(atom_word)
            numbers.append(number)
    if not clean:
        return None, None
    node = TreeNode(clean[0])
    for w in clean[1:]:
        node = node.fx(w)
    head_number = numbers[-1]
    return node, head_number


def has_branch(node, name):
    if node is None:
        return False
    if node.name in name and node.children != []:
        return True
    for child in node.children:
        if has_branch(child, name):
            return True
    return False


def parse_adjective(words):
    if not words:
        raise ValueError("Invalid adjective: <empty>")
    word = words[0]
    vocabulary = {
        "happy": "happy",
        "sad": "sad",
        "alive": "live",
        "dead": "die"
    }
    w = word.lower()
    if w not in vocabulary.keys() or len(words) != 1:
        raise ValueError(
            f"Invalid adjective: {word}"
        )
    return vocabulary[w]


def actor(words):
    node, number = parse_noun_phrase(words)
    node = combine_relation(node)
    if has_branch(node, ["you", "we", "they", "i", "she", "he"]):
        raise ValueError(f"Pronoun is branch node")
    root = copy.deepcopy(node)
    root2 = copy.deepcopy(node)
    while root2.children:
        root2 = root2.children[0]
    if root.children != [] and root2.name in ["you", "we", "they", "i", "she", "he"] and root2.name == words[0]:
        raise ValueError(f"Pronoun has a wrong form")
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

    def listen_word(self, word):
        pass


# ---------------------------------------------------------------------------
# verbs
# ---------------------------------------------------------------------------
VERB_VOCAB = {
    "eat", "go", "see", "give",
    "take", "run", "die",
    "come", "do", "have",
    "walk", "study", "kill", "want",
    "love", "hate", "help",
    "tell", "say", "know", "knew", "known", "think", "thought",
    "ate", "went", "gone", "told", "tells",
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

# form -> (root, tense) or (root, tense, person, number)
VERB_IRREGULAR = {
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
    "told": ("tell", "past"),
    "said": ("say", "past"),
    "knew": ("know", "past"),
    "known": ("know", "past"),
    "thought": ("think", "past"),
    "tells": ("tell", "present", ["3rd"], "singular"),
    "says": ("say", "present", ["3rd"], "singular"),
    "died": ("die", "past"),
    "dies": ("die", "present", ["3rd"], "singular"),
    "came": ("come", "past"),
    "did": ("do", "past"),
    "done": ("do", "past"),
    "had": ("have", "past"),
    "has": ("have", "present", ["3rd"], "singular"),
    "does": ("do", "present", ["3rd"], "singular"),
}


def _first_known(candidates):
    """First candidate that is a known verb (None if there is none)."""
    for c in candidates:
        if c and c in VERB_VOCAB:
            return c
    return None


def _doubled(stem):
    """running -> runn -> run"""
    if len(stem) >= 2 and stem[-1] == stem[-2]:
        return stem[:-1]
    return None


def _root_ing(stem):
    if stem in ("dy", "ly"):                    # dying -> die
        return _first_known([stem[:-1] + "ie"])
    return _first_known([stem, stem + "e", _doubled(stem)])   # loving -> love


def _root_ed(stem):
    return _first_known([
        stem,                                    # walked -> walk
        stem + "e",                              # loved  -> love
        _doubled(stem),                          # stopped -> stop
        stem[:-1] + "y" if stem.endswith("i") else None,   # studied -> study
    ])


def _root_s(verb):
    return _first_known([
        verb[:-3] + "y" if verb.endswith("ies") else None,  # studies -> study
        verb[:-2],                               # goes -> go
        verb[:-1],                               # takes -> take, kills -> kill
    ])


def parse_verb(words):
    if not words:
        return None
    if len(words) != 1:
        raise ValueError(
            f"Verb parser accepts exactly one word: {words}"
        )
    verb = words[0].lower()

    def result(root, tense, person=None, number=None, continuous=False):
        return {
            "root": root,
            "tense": tense,
            "person": person or ["1st", "2nd", "3rd"],
            "number": number or ["plural", "singular"],
            "continuous": continuous
        }

    if verb in VERB_IRREGULAR:
        data = VERB_IRREGULAR[verb]
        if len(data) == 2:
            return result(*data)
        root, tense, person, number = data
        return result(root, tense, person, [number])

    if verb in VERB_VOCAB:
        return result(verb, "present")

    if verb.endswith("ing") and len(verb) > 4:
        root = _root_ing(verb[:-3])
        if root:
            return result(root, "present", continuous=True)

    if verb.endswith("ed") and len(verb) > 3:
        root = _root_ed(verb[:-2])
        if root:
            return result(root, "past")

    if verb.endswith("s") and not verb.endswith("ss"):
        root = _root_s(verb)
        if root:
            return result(root, "present", ["3rd"], ["singular"])

    raise ValueError(
        f"Invalid verb vocabulary: {verb}"
    )


# verbs about what someone holds: know(john, die(mary)), want(john, kill(john, mary))
ATTITUDE_VERBS = {"know", "think", "want"}

# "x knows / thinks THAT <sentence>"          ->  know(x, S) / think(x, S)
THAT_VERBS = {"know", "think"}

# "x wants [y] TO <infinitive>"              ->  want(x, P)
#   i want john to be dead      want(i,die(john))
#   i want john to kill mary    want(i,kill(john,mary))
#   i want to kill mary         want(i,kill(i,mary))
WANT_VERBS = {"want"}

DO_AUX = ("do", "does", "did")

PRONOUNS = ["she", "he", "i", "we", "they", "you"]


VALID_NOUNS = {
    "boy", "girl", "father", "mother", "friend"
}


def validate_noun(word):
    w = word.lower()
    if w in VALID_NOUNS:
        return True
    if w.endswith("s") and w[:-1] in VALID_NOUNS:
        return True
    irregular_plural = {
        "men", "women", "children",
        "people", "mice", "geese",
        "feet", "teeth"
    }
    if w in irregular_plural:
        return True
    return False


NON_NOUN_BLOCKLIST = {
    "is", "are", "am", "was", "were", "be", "been", "being",
    "do", "does", "did",
    "have", "has", "had",
    "will", "would", "shall", "should",
    "can", "could", "may", "might",
    "go", "goes", "went", "gone",
    "eat", "eats", "ate",
    "see", "saw", "seen",
    "kill", "killed", "killing"
}


def parse_category(words):
    if not words:
        return None
    # a noun is "girl" or "a girl"; longer chunks such as "mary is my mother"
    # are sentences, not nouns (they only end in a noun)
    if len(words) > 2 or (len(words) == 2 and words[0].lower() not in ("a", "an")):
        raise ValueError(f"Invalid noun phrase: {' '.join(words)}")
    word = words[-1].lower()
    if word in NON_NOUN_BLOCKLIST:
        raise ValueError(f"Invalid noun (verb detected): {word}")
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
    if len(words) == 2 and words[0].lower() in ["a", "an"]:
        return {
            "root": word,
            "number": "singular"
        }
    if word in irregular_plural:
        return {
            "root": irregular_plural[word],
            "number": "plural"
        }
    if word.endswith("s") and not word.endswith("ss"):
        return {
            "root": word[:-1],
            "number": "plural"
        }
    return {"root": word, "number": "singular"}


SYNONYMS = {
    "boy": "boy",
    "man": "boy",
    "male": "boy",
    "girl": "girl",
    "woman": "girl",
    "female": "girl",
    "father": "father",
    "dad": "father",
    "papa": "father",
    "mother": "mother",
    "mom": "mother",
    "mama": "mother",
    "friend": "friend",
    "mate": "friend",
    "buddy": "friend",
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
    node.name = SYNONYMS.get(node.name, node.name)
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
        except Exception:
            return False

    def valid_adjective(chunk):
        try:
            return parse_adjective(chunk) is not None
        except Exception:
            return False

    def valid_aux(chunk):
        try:
            return aux_verb(chunk) is not None
        except Exception:
            return False

    def valid_noun(chunk):
        try:
            return parse_category(chunk) is not None
        except Exception:
            return False

    def valid_verb(chunk):
        try:
            return parse_verb(chunk) is not None
        except Exception:
            return False

    parsers = [
        ("actor", valid_actor),
        ("aux", valid_aux),
        ("verb", valid_verb),
        ("to", lambda x: valid_given("to", x)),
        ("be", lambda x: valid_given("be", x)),      # infinitive "to be dead"
        ("not", lambda x: valid_given("not", x)),
        ("that", lambda x: valid_given("that", x)),
        ("who", lambda x: valid_given("who", x)),
        ("whom", lambda x: valid_given("whom", x)),
        ("what", lambda x: valid_given("what", x)),
        ("noun", valid_noun),
        ("adjective", valid_adjective),
    ]

    def recurse(index, splits, funcs):
        if index >= n:
            for i in range(len(funcs) - 1):
                if funcs[i] == "actor" and funcs[i + 1] == "actor":
                    if i == 0 or funcs[i - 1] != "aux":
                        return
            results.append((splits[:], funcs[:]))
            return

        for end in range(index + 1, n + 1):
            chunk = words[index:end]
            matched_any = False

            for name, parser in parsers:
                try:
                    if parser(chunk):
                        matched_any = True
                        splits.append(chunk)
                        funcs.append(name)
                        recurse(end, splits, funcs)
                        splits.pop()
                        funcs.pop()
                except Exception:
                    pass

            if not matched_any:
                splits.append(chunk)
                funcs.append("sentence")
                recurse(end, splits, funcs)
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


# ---------------------------------------------------------------------------
# want
# ---------------------------------------------------------------------------
def _bad_reflexive(subject_tree, obj_tree, word):
    """'i want to kill me' is wrong, 'i want to kill myself' is right."""
    if obj_tree == subject_tree and obj_tree.name in PRONOUNS:
        return len(word) <= 4 or word[-4:] != "self"
    return False


def _infinitive(subject, split, funcs):
    """The part after 'to' of a want sentence, as a tree about `subject`.

        die              -> die(subject)
        kill mary        -> kill(subject, mary)
        be dead          -> die(subject)
        be a girl        -> girl(subject)
    """
    if funcs == ["verb"]:
        root = parse_verb(split[0])["root"]
        if root in ("kill",):                  # kill needs an object
            return None
        return TreeNode(root, [subject])
    if funcs == ["verb", "actor"]:
        root = parse_verb(split[0])["root"]
        obj = actor(split[1])
        if obj["form"] == "subject":           # "to kill she"
            return None
        if _bad_reflexive(subject, obj["tree"], split[1][0].lower()):
            return None
        return TreeNode(root, [subject, obj["tree"]])
    if funcs == ["be", "adjective"]:
        return subject.fx(parse_adjective(split[1]))
    if funcs == ["be", "noun"]:
        return subject.fx(parse_category(split[1])["root"])
    return None


def parse_want(split, funcs):
    """Statements and yes/no questions with want.

        i want john to be dead       want(i,die(john))
        i want john to kill mary     want(i,kill(john,mary))
        i want to kill mary          want(i,kill(i,mary))
        i want to die                want(i,die(i))
        does john want mary to die   question(want(john,die(mary)))

    Returns None when the chunks are not a want sentence.
    """
    i = 0
    question = False
    if funcs[:1] == ["verb"] and split[0][0].lower() in DO_AUX:
        question = True
        i = 1
    if len(funcs) < i + 3 or funcs[i] != "actor" or funcs[i + 1] != "verb":
        return None
    want_verb = parse_verb(split[i + 1])
    if want_verb["root"] not in WANT_VERBS:
        return None
    if question and split[i + 1][0].lower() not in WANT_VERBS:
        return None                            # "does john wants ..."
    wanter = actor(split[i])
    if wanter["form"] == "object":             # "me want ..."
        return None
    j = i + 2
    if funcs[j] == "actor":                    # i want JOHN to ...
        who = actor(split[j])
        if who["form"] == "subject":           # "i want he to die"
            return None
        subject = who["tree"]
        j += 1
    else:                                      # i want to ...
        subject = wanter["tree"]
    if j >= len(funcs) or funcs[j] != "to":
        return None
    content = _infinitive(subject, split[j + 1:], funcs[j + 1:])
    if content is None:
        return None
    out = TreeNode("want", [wanter["tree"], content])
    return out.fx("question") if question else out


# ---------------------------------------------------------------------------
# what / who questions
#
#   what do i know          query(know(i,what))
#   what does john want     query(want(john,what))
#   who killed mary         query(kill(who,mary))
#   who did i kill          query(kill(i,who))
#   who wants to kill mary  query(want(who,kill(who,mary)))
#   who is dead             query(die(who))
#
# The sentence is rewritten as a statement about a placeholder name
# ("lucy killed mary"), parsed normally, and the placeholder becomes `who`.
# ---------------------------------------------------------------------------
PLACEHOLDERS = ["lucy", "sarah", "emma", "david", "james", "michael"]


def _has_node(tree, name):
    return tree.name == name or any(_has_node(c, name) for c in tree.children)


def _is_actor(words):
    try:
        return bool(words) and actor(words) is not None
    except Exception:
        return False


def parse_wh(words):
    lower = [w.lower() for w in words]
    if len(lower) < 2 or lower[0] not in ("who", "whom", "what"):
        return None
    rest, rest_l = words[1:], lower[1:]
    if lower[0] == "what":
        # what do/does/did <actor> know/think/want
        if len(rest) >= 3 and rest_l[0] in DO_AUX:
            try:
                root = parse_verb([rest_l[-1]])["root"]
                if root not in ATTITUDE_VERBS:
                    return None
                holder = actor(rest[1:-1])["tree"]
            except ValueError:
                return None
            return normalize_synonyms(
                TreeNode("query", [TreeNode(root, [holder, TreeNode("what")])])
            )
        return None
    if rest_l[0] in DO_AUX:                      # who did i kill / who does john want to kill
        statement = rest[1:]
        if not statement:
            return None
        placeholder = next((p for p in PLACEHOLDERS if p not in lower), None)
        statement = statement + [placeholder]
    elif rest_l[0] in ("is", "are", "was", "were") and _is_actor(rest[1:]):
        return None                              # "who is my father": the who-is template
    else:                                        # who killed mary / who is dead
        placeholder = next((p for p in PLACEHOLDERS if p not in lower), None)
        statement = [placeholder] + rest
    try:
        inner = code(" ".join(statement))
    except ValueError:
        return None
    if inner is None:
        return None
    inner = replace(inner, TreeNode(placeholder), TreeNode("who"))
    if not _has_node(inner, "who"):
        return None
    return TreeNode("query", [inner])


# ---------------------------------------------------------------------------
# saying facts in English (for "what do i know")
# ---------------------------------------------------------------------------
POSSESSIVE = {"i": "my", "you": "your", "he": "his", "she": "her",
              "it": "its", "we": "our", "they": "their"}
ADJECTIVE_OF = {"die": "dead", "live": "alive", "happy": "happy", "sad": "sad"}
# events are told in the past ("you killed mary"), states in the present
VERB_PAST = {"kill": "killed", "eat": "ate", "give": "gave", "take": "took",
             "go": "went", "tell": "told", "say": "said", "come": "came",
             "run": "ran", "walk": "walked", "see": "saw", "help": "helped"}


def term_text(t):
    if not t.children:
        return t.name
    owner = t.children[0]
    if not owner.children and owner.name in POSSESSIVE:
        own = POSSESSIVE[owner.name]
    else:
        own = term_text(owner) + "'s"
    return f"{own} {t.name}"


def _plural(t):
    return not t.children and t.name in ("you", "we", "they")


def _be(t):
    if not t.children and t.name == "i":
        return "am"
    return "are" if _plural(t) else "is"


def _present(root, t):
    if (not t.children and t.name in ("i",)) or _plural(t):
        return root
    if root.endswith(("s", "sh", "ch", "x", "o")):
        return root + "es"
    if root.endswith("y") and root[-2:-1] not in "aeiou":
        return root[:-1] + "ies"
    return root + "s"


def _article(word):
    return ("an " if word[0] in "aeiou" else "a ") + word


def _predicate(pred, t):
    if pred in ADJECTIVE_OF:
        return f"{_be(t)} {ADJECTIVE_OF[pred]}"
    return f"{_be(t)} {_article(pred)}"


def say_fact(fact):
    kind = fact[0]
    if kind == "equal":
        return f"{term_text(fact[1])} {_be(fact[1])} {term_text(fact[2])}"
    if kind == "link":
        _, rel, owner, target = fact
        return f"{term_text(target)} {_be(target)} {term_text(TreeNode(rel, [owner]))}"
    if kind == "unary":
        return f"{term_text(fact[2])} {_predicate(fact[1], fact[2])}"
    _, rel, a, b = fact
    verb = VERB_PAST.get(rel) or _present(rel, a)
    return f"{term_text(a)} {verb} {term_text(b)}"


def _to_clause(fact, holder):
    """The 'to ...' part of 'you want to kill mary / john to be dead'."""
    kind = fact[0]
    if kind == "unary":
        subject, rest = fact[2], "be " + (
            ADJECTIVE_OF.get(fact[1]) or _article(fact[1]))
    elif kind == "binary":
        subject, rest = fact[2], f"{fact[1]} {term_text(fact[3])}"
    elif kind == "link":
        subject = fact[3]
        rest = f"be {term_text(TreeNode(fact[1], [fact[2]]))}"
    else:
        subject, rest = fact[1], f"be {term_text(fact[2])}"
    if subject == holder:
        return f"to {rest}"
    return f"{term_text(subject)} to {rest}"


def say_attitude(att, holder, fact):
    """you know that mary is dead / you want to kill mary / john wants mary to die"""
    h = f"{term_text(holder)} {_present(att, holder)}"
    if att == "want":
        return f"{h} {_to_clause(fact, holder)}"
    return f"{h} that {say_fact(fact)}"



def infer_equation2(split, funcs):
    if funcs == ["actor", "verb", "actor", "that", "sentence"]:
        a = actor(split[0])["tree"]
        a2 = actor(split[2])["tree"]
        eq = code(" ".join(split[4:][0]))
        if split[1][0] in "tell told tells said says say".split(" "):
            return TreeNode("convey", [a, a2, eq])
    if split[0] != ["who"] and combine_features(split[:2], funcs[:2])["valid"] is False:
        return None
    last_actor = None
    if funcs == ["actor", "verb", "that", "sentence"]:
        root = parse_verb(split[1])["root"]
        if root in THAT_VERBS:
            try:
                inner = code(" ".join(split[3]))
            except ValueError:
                return None
            if inner is None:
                return None
            return TreeNode(root, [actor(split[0])["tree"], inner])
    if (
        funcs == ["verb", "actor", "verb", "that", "sentence"]
        and split[0][0].lower() in DO_AUX
    ):
        root = parse_verb(split[2])["root"]
        if root in THAT_VERBS:
            try:
                inner = code(" ".join(split[4]))
            except ValueError:
                return None
            if inner is None:
                return None
            return TreeNode(root, [actor(split[1])["tree"], inner]).fx("question")
    if funcs == ["aux", "actor", "actor"]:
        a1 = actor(split[1])["tree"]
        a2 = actor(split[2])["tree"]
        return TreeNode("equal", [a1, a2]).fx("question")
    if funcs.count("actor") == 2:
        if len(split) >= 3 and funcs[-1] == "actor" and actor(split[-1])["form"] == "subject":
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
    want = parse_want(split, funcs)
    if want is not None:
        return want
    if funcs == ["who", "aux", "actor"]:
        a = actor(split[2])["tree"]
        return a.fx("who")
    if funcs == ["actor", "aux", "adjective"]:
        return actor(split[0])["tree"].fx(parse_adjective(split[2]))
    if funcs == ["actor", "aux", "not", "adjective"]:
        return actor(split[0])["tree"].fx(parse_adjective(split[3])).fx("not")
    if funcs == ["actor", "aux", "noun"]:
        return actor(split[0])["tree"].fx(parse_category(split[2])["root"])
    if funcs == ["aux", "actor", "noun"]:
        a = actor(split[1])["tree"]
        v = parse_category(split[2])["root"]
        return TreeNode(v, [a]).fx("question")
    if funcs == ["aux", "actor", "adjective"]:
        a = actor(split[1])["tree"]
        return a.fx(parse_adjective(split[2])).fx("question")
    if (
        funcs == ["verb", "actor", "verb", "actor"]
        and split[0][0].lower() in DO_AUX
    ):
        a, b = actor(split[1])["tree"], last_actor["tree"]
        return TreeNode(parse_verb(split[2])["root"], [a, b]).fx("question")
    if funcs == ["actor", "aux", "not", "noun"]:
        lst = " ".join(split[0] + split[1] + split[3])
        return code(lst).fx("not")
    if funcs == ["actor", "verb", "to", "verb"]:
        v1 = parse_verb(split[1])["root"]
        if v1 in WANT_VERBS:                   # want is handled by parse_want
            return None
        v2 = parse_verb(split[3])["root"]
        a1 = actor(split[0])["tree"]
        return TreeNode(v1, [a1, a1.fx(v2)])
    if funcs == ["actor", "verb", "to", "verb", "actor"]:
        v1 = parse_verb(split[1])["root"]
        if v1 in WANT_VERBS:
            return None
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
        return TreeNode("equal", [actor(split[0])["tree"], last_actor["tree"]])
    return None


def infer_equation(split, funcs):
    out = infer_equation2(split, funcs)
    return normalize_synonyms(out)


def code(sentence):
    words = sentence.split()
    lower = [w.lower() for w in words]
    wh = parse_wh(words)
    if wh is not None:
        return wh
    limit = lower.index("that") if "that" in lower else len(words)
    if "not" in lower[:limit]:
        neg_index = lower.index("not")
        sub_words = words[:neg_index] + words[neg_index + 1:]
        sub_code = code(" ".join(sub_words))
        if sub_code is not None:
            return TreeNode("not", [sub_code])

    out = split_sentence(words)
    if len(out) == 0:
        return None
    else:
        for out2 in out:
            out3 = infer_equation(*out2)
            if out3 is not None:
                return out3
    return actor(words)["tree"]
