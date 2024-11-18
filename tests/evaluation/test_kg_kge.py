from unittest import TestCase
from tests.datasetFactory import PPIYeastSlimDataset
from mowl.models import GraphPlusPyKEENModel
from mowl.projection import OWL2VecStarProjector
from mowl.evaluation import PPIEvaluator
import mowl.error.messages as msg
from utils import auc_from_mr, allowed_diff

import torch as th
from pykeen.models import TransE

class TestKGRandomWalkModel(TestCase):

    @classmethod
    def setUpClass(self):
        self.ppi_dataset = PPIYeastSlimDataset()

    def init_model(self):
        model = GraphPlusPyKEENModel(self.ppi_dataset)
        model.set_projector(OWL2VecStarProjector())
        model.optimizer = th.optim.Adam
        model.lr = 0.01
        model.batch_size = 128
        model.set_kge_method(TransE)
        return model
        
    def test_evaluation_without_instantiating_evaluation_class(self):
        model = self.init_model()
        model.set_evaluator(PPIEvaluator)
        model.train(epochs=1)
        model.evaluate(self.ppi_dataset.testing, filter_ontologies = [self.ppi_dataset.ontology])
        mr = model.metrics["mr"]
        fmr = model.metrics["f_mr"]
        auc = model.metrics["auc"]

        true_auc = auc_from_mr(mr, len(self.ppi_dataset.evaluation_classes[0]))
        diff_auc = abs(true_auc - auc)
        
        self.assertTrue(mr > fmr)
        self.assertLess(diff_auc, allowed_diff)
        
    def test_evaluation_instantiating_evaluation_class(self):
        model = self.init_model()
        evaluator = PPIEvaluator(self.ppi_dataset)
        model.set_evaluator(evaluator)
        model.train(epochs=1)
        model.evaluate(self.ppi_dataset.testing, filter_ontologies = [self.ppi_dataset.ontology])

        mr = model.metrics["mr"]
        fmr = model.metrics["f_mr"]

        self.assertTrue(mr > fmr)
        
    def test_not_set_evaluator(self):
        model = self.init_model()
        model.train(epochs=1)

        with self.assertRaisesRegex(AttributeError, msg.EVALUATOR_NOT_SET):
            model.evaluate(self.ppi_dataset.testing)

        
