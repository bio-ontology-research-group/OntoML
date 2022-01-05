import os

import numpy as np
from scipy.stats import rankdata

from mowl.model import Model
from jpype.types import *

from org.semanticweb.owlapi.manchestersyntax.renderer import ManchesterOWLSyntaxOWLObjectRendererImpl
from org.mowl.Onto2Vec import Onto2VecShortFormProvider
from org.semanticweb.owlapi.model import AxiomType
from sklearn.metrics import pairwise_distances
import gensim
import logging

MAX_FLOAT = np.finfo(np.float32).max

class CorpusGenerator(object):

    def __init__(self, filepath):
        self.filepath = filepath

    def __iter__(self):
        with open(self.filepath) as f:
            for line in f:
                yield line.strip().split(' ')

class Onto2Vec(Model):

    def __init__(self, dataset, w2v_params={}):
        super().__init__(dataset)
        self.axioms_filepath = os.path.join(
            dataset.data_root, dataset.dataset_name, 'axioms.o2v')
        self.w2v_params = w2v_params
        self.model_filepath = os.path.join(
            dataset.data_root, dataset.dataset_name, 'w2v.model')
        self.w2v_model = None
        
    def _create_axioms_corpus(self):
        logging.info("Generating axioms corpus")
        renderer = ManchesterOWLSyntaxOWLObjectRendererImpl()
        shortFormProvider = Onto2VecShortFormProvider()
        renderer.setShortFormProvider(shortFormProvider)
        with open(self.axioms_filepath, 'w') as f:
            for owl_class in self.dataset.ontology.getClassesInSignature():
                axioms = self.dataset.ontology.getAxioms(owl_class)
                for axiom in axioms:
                    rax = renderer.render(axiom)
                    rax = rax.replaceAll(JString("[\\r\\n|\\r|\\n()]"), JString(""))
                    f.write(f'{rax}\n')

    def _load_pretrained_model(self):
        return None

    def train(self):
        if not os.path.exists(self.axioms_filepath):
            self.dataset.infer_axioms()
            self._create_axioms_corpus()

        sentences = CorpusGenerator(self.axioms_filepath)

        self.w2v_model = self._load_pretrained_model()
        if not self.w2v_model:
            self.w2v_model = gensim.models.Word2Vec(
                sentences=sentences, **self.w2v_params)
        else:
            # retrain the pretrained model with our axioms
            self.w2v_model.build_vocab(sentences, update=True)
            self.w2v_model.train(sentences, total_examples=self.w2v_model.corpus_count, epochs=100, **self.w2v_params)
            # (following example from: https://github.com/bio-ontology-research-group/opa2vec/blob/master/runWord2Vec.py )
        self.w2v_model.save(self.model_filepath)


    def train_or_load_model(self):
        if not os.path.exists(self.model_filepath):
            self.train()
        if not self.w2v_model:
            self.w2v_model = gensim.models.Word2Vec.load(
                self.model_filepath)


    def get_classes_pairs_from_axioms(self, data_subset, filter_properties):
        classes_pairs_set = set()
        all_classes_set = set()
        for axiom in data_subset.getAxioms():
            if axiom.getAxiomType() != AxiomType.SUBCLASS_OF:
                continue
            try:
                # see Java methods of classes:
                # http://owlcs.github.io/owlapi/apidocs_4/uk/ac/manchester/cs/owl/owlapi/OWLSubClassOfAxiomImpl.html
                # http://owlcs.github.io/owlapi/apidocs_4/uk/ac/manchester/cs/owl/owlapi/OWLObjectSomeValuesFromImpl.html
                cls1 = str(axiom.getSubClass())
                cls2 = str(axiom.getSuperClass().getFiller())
                object_property = str(axiom.getSuperClass().getProperty())
                if object_property in filter_properties:
                    classes_pairs_set.add((cls1, cls2))
                    all_classes_set.add(cls1)
                    all_classes_set.add(cls2)
            except AttributeError as e:
                # no getFiller on some axioms (which are not related to protein-protein interactions, but are other kinds of axioms)
                pass
        return list(all_classes_set), list(classes_pairs_set)


    def evaluate_ppi(self, ppi_axiom_properties=['<http://interacts_with>']):
        """
        Evaluate predicted protein-protein interactions relative to the test ontology, which has the set of interactions kept back from model training.
        """
        self.train_or_load_model()
        model = self.w2v_model
        training_classes, training_classes_pairs = self.get_classes_pairs_from_axioms(self.dataset.ontology, ppi_axiom_properties)
        _, testing_classes_pairs = self.get_classes_pairs_from_axioms(self.dataset.testing, ppi_axiom_properties)

        # some classes in the training set don't make it into the model (maybe their frequency is too low)
        available_training_classes = [c for c in training_classes if c in model.wv]
        class_to_index = {available_training_classes[i]: i for i in range(0, len(available_training_classes))}

        # dict "protein-index-1 => set( protein-indexes-2 )" of the trained PPI pairs
        training_pairs_exclude_indexes = dict()
        for training_pair in training_classes_pairs:
            i1 = class_to_index.get(training_pair[0])
            i2 = class_to_index.get(training_pair[1])
            if i1 is not None and i2 is not None:
                exclude_ids_set = training_pairs_exclude_indexes.get(i1, set())
                training_pairs_exclude_indexes[i1] = exclude_ids_set
                exclude_ids_set.add(i2)

        testing_classes_pairs = sorted(testing_classes_pairs, key=lambda pair: pair[0])
        embeddings = model.wv[available_training_classes]
        observed_ranks = list()
        previous_i1 = None  # to preserve memory, we compare one protein to all the others at a time
        for testing_pair in testing_classes_pairs:
            i1 = class_to_index.get(testing_pair[0])
            i2 = class_to_index.get(testing_pair[1])
            if i1 is not None and i2 is not None:
                # prepare a new row of class comparisons
                if previous_i1 != i1:
                    previous_i1 = i1
                    # Word2Vec.n_similarity only returns an aggregated similarity of all vectors, so staying with this:
                    class_distances = pairwise_distances([embeddings[i1]], embeddings, metric='cosine')[0]

                    # disregard the protein-protein interactions which came naturally from the training set
                    exclude_ids_set = training_pairs_exclude_indexes.get(i1, set())
                    for exclude_i2 in exclude_ids_set:
                        class_distances[exclude_i2] = MAX_FLOAT
                    # disregard the similarity of protein with itself
                    class_distances[i1] = MAX_FLOAT

                    # For each protein, it is ranked how similar (per the model) it is to the current i1.
                    # The lower the rank, the higher the protein similarity.
                    ranked_indexes = rankdata(class_distances, method='average')
                observed_ranks.append(ranked_indexes[i2])

        # We queried the similarity ranks of all the testing set protein-protein interactions, and collected the
        # ranks in observed_ranks. Let's bin the ranks and see if good ranks appear more often, and also
        # calculate the mean rank.
        histogram = np.histogram(observed_ranks, bins=[0, 1.1, 10.1, 100.1, 10000000])[0]
        rank_1 = histogram[0]
        rank_10 = histogram[0] + histogram[1]
        rank_100 = histogram[0] + histogram[1] + histogram[2]
        return(np.mean(observed_ranks), rank_1, rank_10, rank_100)
