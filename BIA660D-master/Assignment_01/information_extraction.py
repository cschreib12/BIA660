from __future__ import unicode_literals, print_function

import re
# import spacy

from pyclausie import ClausIE


# nlp = spacy.load('en')
import en_core_web_sm
nlp = en_core_web_sm.load()
cl = ClausIE.get_instance()

re_spaces = re.compile(r'\s+')


class Person(object):
    def __init__(self, name, likes=None, has=None, travels=None):
        """
        :param name: the person's name
        :type name: basestring
        :param likes: (Optional) an initial list of likes
        :type likes: list
        :param dislikes: (Optional) an initial list of likes
        :type dislikes: list
        :param has: (Optional) an initial list of things the person has
        :type has: list
        :param travels: (Optional) an initial list of the person's travels
        :type travels: list
        """
        self.name = name
        self.likes = [] if likes is None else likes
        self.has = [] if has is None else has
        self.travels = [] if travels is None else travels

    def __repr__(self):
        return self.name


class Pet(object):
    def __init__(self, pet_type, name=None):
        self.name = name
        self.type = pet_type


class Trip(object):
    def __init__(self):
        self.departs_on = None
        self.departs_to = None


persons = []
pets = []
trips = []


def get_data_from_file(file_path='./chatbot_data.txt'):
    with open(file_path) as infile:
        cleaned_lines = [line.strip() for line in infile if not (line.startswith(('$$$', '###', '===')) or line == "\n")]

    return cleaned_lines


def select_person(name):
    for person in persons:
        if person.name == name:
            return person


def add_person(name):
    person = select_person(name)

    if person is None:
        new_person = Person(name)
        persons.append(new_person)

        return new_person

    return person


def select_pet(name):
    for pet in pets:
        if pet.name == name:
            return pet


def add_pet(type, name=None):
    pet = None

    if name:
        pet = select_pet(name)

    if pet is None:
        pet = Pet(type, name)
        pets.append(pet)

    return pet


def get_persons_pet(person_name):

    person = select_person(person_name)

    for thing in person.has:
        if isinstance(thing, Pet):
            return thing



def process_relation_triplet(triplet):
    """
    Process a relation triplet found by ClausIE and store the data

    find relations of types:
    (PERSON, likes, PERSON)
    (PERSON, has, PET)
    (PET, has_name, NAME)
    (PERSON, travels, TRIP)
    (TRIP, departs_on, DATE)
    (TRIP, departs_to, PLACE)

    :param triplet: The relation triplet from ClausIE
    :type triplet: tuple
    :return: a triplet in the formats specified above
    :rtype: tuple
    """

    sentence = triplet.subject + ' ' + triplet.predicate + ' ' + triplet.object

    doc = nlp(unicode(sentence))

    for t in doc:
        if t.pos_ == 'VERB' and t.head == t:
            root = t
        # elif t.pos_ == 'NOUN'

    # also, if only one sentence
    # root = doc[:].root
    subj_span = doc.char_span(sentence.find(triplet.subject, len(triplet.subject)))
    obj_span = doc.char_span(sentence.find(triplet.object), len(sentence))


    """
    CURRENT ASSUMPTIONS:
    - People's names are unique (i.e. there only exists one person with a certain name).
    - Pet's names are unique
    - The only pets are dogs and cats
    - Only one person can own a specific pet
    - A person can own only one pet
    """


    # Process (PERSON, likes, PERSON) relations
    if root.lemma_ == 'like':
        if triplet.subject in [e.text for e in doc.ents if e.label_ == 'PERSON'] and triplet.object in [e.text for e in doc.ents if e.label_ == 'PERSON']:
            s = add_person(triplet.subject)
            o = add_person(triplet.object)
            s.likes.append(o)

    if root.lemma_ == 'be' and triplet.object.startswith('friends with'):
        fw_doc = nlp(unicode(triplet.object))
        with_token = [t for t in fw_doc if t.text == 'with'][0]
        fw_who = [t for t in with_token.children if t.dep_ == 'pobj'][0].text
        # fw_who = [e for e in fw_doc.ents if e.label_ == 'PERSON'][0].text

        if triplet.subject in [e.text for e in doc.ents if e.label_ == 'PERSON'] and fw_who in [e.text for e in doc.ents if e.label_ == 'PERSON']:
            s = add_person(triplet.subject)
            o = add_person(fw_who)
            s.likes.append(o)
            o.likes.append(s)


    # Process (PET, has, NAME)
    if triplet.subject.endswith('name') and ('dog' in triplet.subject or 'cat' in triplet.subject):
        obj_span = doc.char_span(sentence.find(triplet.object), len(sentence))

        # handle single names, but what about compound names? Noun chunks might help.
        if len(obj_span) == 1 and obj_span[0].pos_ == 'PROPN':
            name = triplet.object
            subj_start = sentence.find(triplet.subject)
            subj_doc = doc.char_span(subj_start, subj_start + len(triplet.subject))

            s_people = [token.text for token in subj_doc if token.ent_type_ == 'PERSON']
            assert len(s_people) == 1
            s_person = select_person(s_people[0])

            s_pet_type = 'dog' if 'dog' in triplet.subject else 'cat'

            pet = add_pet(s_pet_type, name)

            s_person.has.append(pet)


def preprocess_question(question):
    # remove articles: a, an, the

    q_words = question.split(' ')

    # when won't this work?
    for article in ('a', 'an', 'the'):
        try:
            q_words.remove(article)
        except:
            pass

    return re.sub(re_spaces, ' ', ' '.join(q_words))


def has_question_word(string):
    # note: there are other question words
    for qword in ('who', 'what'):
        if qword in string.lower():
            return True

    return False


def make_sentence_from_triplet(triplet):
    return triplet.subject + ' ' + triplet.predicate + ' ' + triplet.object

def answer_question(question=' '):
    while question[-1] != '?':
        question = raw_input("Please enter your question: ")

        if question[-1] != '?':
            print('This is not a question... please try again')

    # my question preprocesser may break things. This was just a demo.
    # Don't think that you have to use it for all questions, or even that you have to use it at all.
    # Don't use my code blindly. Think critically about what it is doing and whether or not that's what you want.
    q_trip = cl.extract_triples([preprocess_question(question)])[0]

    triplet_sentence = make_sentence_from_triplet(q_trip) + '?'
    doc = nlp(triplet_sentence)
    root = doc[:].root

    # retrieve answers for questions like (WHO, has, PET)
    # here's one just for dogs
    # you should really check the verb... this is just an example not the best way to do things
    if q_trip.subject.lower() == 'who' and q_trip.object == 'dog':

        answer = '{} has a {} named {}.'

        for person in persons:
            pet = get_persons_pet(person.name)
            if pet and pet.type == 'dog':
                print(answer.format(person.name, 'dog', pet.name))

    # retrieve answers for questions like (WHO, like, PERSON)
    # again this is just an example, NOT the best way to do things. That's for you to figure out.
    elif q_trip.subject.lower() == 'who' and root.lemma_ == 'like' and q_trip.object in [e.text for e in doc.ents if e.label_ == 'PERSON' or e.label_ == 'ORG']:
        answer = '{} likes {}'

        liked_person = select_person(q_trip.object)

        for person in persons:
            if person.name != q_trip.object and liked_person in person.likes:
                print(answer.format(person.name, liked_person.name))


def process_data_from_input_file(path='assignment_01.data'):
    sents = get_data_from_file(path)

    triples = cl.extract_triples(sents)

    for t in triples:
        try:
            process_relation_triplet(t)
        except:
            pass
    return triples

def main():
    triples = process_data_from_input_file()
    answer_question()


if __name__ == '__main__':
    main()

