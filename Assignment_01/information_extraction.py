from __future__ import unicode_literals, print_function

import re
#import spacy

from pyclausie import ClausIE


#nlp = spacy.load('en')
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


def get_data_from_file(file_path='./assignment_01.data'):
    with open(file_path) as infile:
        cleaned_lines = [line.strip() for line in infile if not (line.startswith(('$$$', '###', '===')) and line == "\n")]

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


def select_trip(departs_on=None, departs_to=None):
    for trip in trips:
        if trip.departs_on == departs_on and trip.departs_to == departs_to:
            return trip


def add_trip(location=None, time=None):
    trip = select_trip(location, time)
    if trip is None:
        trip = Trip(location, time)
        trips.append(trip)
    return trip


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
        if triplet.subject in [e.text for e in doc.ents if e.label_ == 'PERSON' or 'ORG'] and triplet.object in [e.text for e in doc.ents if e.label_ == 'PERSON']:
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

    # Process (PERSON, has, PET)
    if root.lemma_ == 'have' and ('dog' in triplet.object or 'cat' in triplet.object):
        pet_type = 'dog' if 'dog' in triplet.object else 'cat'
        person = add_person(triplet.subject)

        person.addPet(pet_type)

    # Process (PERSON, travels, TRIP)
    if root.lemma_ in ['take', 'fly', 'leave', 'go'] and 'GPE' in [e.label_ for e in doc.ents]:
        person = add_person(triplet.subject)
        depart_to = [e.text for e in doc.ents if e.label_ == 'GPE'][0]
        departs_on = [e.text for e in doc.ents if e.label_ == 'DATE'][0]
        person.addTrip(departs_on=departs_on, departs_to=depart_to)


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
    for qword in ('who', 'what', 'when', 'where', 'does'):
        if qword in string.lower():
            return True

    return False


def answer_question(question=' '):
    while question[-1] != '?':
        question = raw_input("Please enter your question: ")

        if question[-1] != '?':
            print('This is not a question... please try again')

    cl = ClausIE.get_instance()
    q_trip = cl.extract_triples([preprocess_question(question)])[0]

    triplet_sentence = q_trip.subject + ' ' + q_trip.predicate + ' ' + q_trip.object
    doc = nlp(unicode(triplet_sentence))
    root = doc[:].root

    # retrieve answers for questions like (WHO, has, PET)
    # here's one just for dogs
    # you should really check the verb... this is just an example not the best way to do things
    if q_trip.subject.lower() == 'who' and root.lemma_ == 'have':

        answer = '{} has a {} named {}.'
        if q_trip.object == 'dog':
            for person in persons:
                pet = get_persons_pet(person.name)
                if pet and pet.type == 'dog':
                    print(answer.format(person.name, pet.type, pet.name))
        elif q_trip.object == 'cat':
            for person in persons:
                pet = get_persons_pet(person.name)
                if pet and pet.type == 'cat':
                    print(answer.format(person.name, pet.type, pet.name))

    # retrieve answers for questions like (WHO, like, PERSON)
    # again this is just an example, NOT the best way to do things. That's for you to figure out.
    elif q_trip.subject.lower() == 'who' and root.lemma_ == 'like' and q_trip.object in [e.text for e in doc.ents if e.label_ == 'PERSON' or e.label_ == 'ORG']:
        answer = '{} likes {}'

        liked_person = select_person(q_trip.object)

        for person in persons:
            if person.name != q_trip.object and liked_person in person.likes:
                print(answer.format(person.name, liked_person.name))

    elif q_trip.subject.lower() == 'does' and q_trip.predicate == 'like' and q_trip.object in [e.text for e in doc.ents if e.label_ == 'PERSON']:
        person = select_trip(q_trip.subject)
        liked_person = select_person(q_trip.object)
        if liked_person in person.likes:
            print(person.name, 'likes ', liked_person.name)
        else:
            print(person.name, 'does not like ', liked_person.name)




def process_data_from_input_file():
    sents = get_data_from_file()
    cl = ClausIE.get_instance()
    triples = cl.extract_triples(sents)

    for t in triples:
        try:
            process_relation_triplet(t)
        except:
            pass

def main():
    process_data_from_input_file()
    answer_question()


if __name__ == '__main__':
    main()

